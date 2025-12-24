"""
Name: Form submission handler
Path: core/sum_core/forms/views.py
Purpose: Accept Contact/Quote submissions, apply spam checks, persist Leads.
Family: Forms, Leads, Attribution, Notifications.
Dependencies: FormConfiguration, Lead service, Django cache, Wagtail Site.
"""

from __future__ import annotations

import json
import re
from typing import Any

from django.core.validators import validate_email
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_protect
from sum_core.forms.models import FormConfiguration
from sum_core.forms.services import run_spam_checks
from sum_core.leads.services import AttributionData, create_lead_from_submission
from sum_core.ops.request_utils import get_client_ip
from wagtail.models import Site

# UK phone validation regex - accepts common UK formats
# Matches: 07xxx, +447xxx, 0044 7xxx, 01xxx, 02xxx, 03xxx, etc.
UK_PHONE_REGEX = re.compile(
    r"^(?:"
    r"(?:\+44|0044)[\s\-]?7\d{3}[\s\-]?\d{6}"  # UK mobile with country code
    r"|07\d{3}[\s\-]?\d{6}"  # UK mobile without country code
    r"|(?:\+44|0044)[\s\-]?[123]\d{2,3}[\s\-]?\d{6,7}"  # UK landline with country code
    r"|0[123]\d{2,3}[\s\-]?\d{6,7}"  # UK landline without country code
    r")$"
)


@method_decorator(csrf_protect, name="dispatch")
class FormSubmissionView(View):
    """
    Handle form submissions from Contact and Quote forms.

    Accepts POST with JSON or form-encoded data.
    Performs spam checks, validates input, and creates Lead records.

    Response codes:
    - 200: Success, Lead created
    - 400: Validation error (missing fields, spam detected)
    - 429: Rate limit exceeded
    - 405: Method not allowed (not POST)
    """

    def post(self, request, *args, **kwargs) -> JsonResponse:
        """Handle form submission POST request."""
        # Parse request data
        data = self._parse_request_data(request)
        if data is None:
            return JsonResponse(
                {"success": False, "errors": {"__all__": ["Invalid request data"]}},
                status=400,
            )

        # Get site from request
        site = self._get_site(request)
        if site is None:
            return JsonResponse(
                {"success": False, "errors": {"__all__": ["Site not found"]}},
                status=400,
            )

        # Get form configuration
        config = self._get_config(site)

        # Run spam checks
        spam_result = run_spam_checks(
            form_data=data,
            ip_address=get_client_ip(request),
            site_id=site.id,
            time_token=data.get("_time_token", ""),
            honeypot_field_name=config.honeypot_field_name,
            rate_limit_per_hour=config.rate_limit_per_ip_per_hour,
            min_seconds_to_submit=config.min_seconds_to_submit,
        )

        if spam_result.should_rate_limit:
            return JsonResponse(
                {"success": False, "errors": {"__all__": ["Too many requests"]}},
                status=429,
            )

        if spam_result.is_spam:
            # Return 400 for spam (indistinguishable from validation error to bots)
            is_xhr = request.headers.get("X-Requested-With") == "XMLHttpRequest"
            if is_xhr and spam_result.reason.startswith("Submitted too quickly"):
                message = "Please wait a moment and try again."
            elif is_xhr and spam_result.reason == "Time token expired":
                message = "Please refresh the page and try again."
            else:
                message = "Invalid submission"

            return JsonResponse(
                {"success": False, "errors": {"__all__": [message]}},
                status=400,
            )

        # Validate required fields
        validation_errors = self._validate_submission(data, config)
        if validation_errors:
            return JsonResponse(
                {"success": False, "errors": validation_errors},
                status=400,
            )

        # Create Lead (must happen before any side effects)
        try:
            lead = self._create_lead(data, site)
        except ValueError as e:
            return JsonResponse(
                {"success": False, "errors": {"__all__": [str(e)]}},
                status=400,
            )

        # Queue notification tasks AFTER lead is safely persisted
        # Failure to queue does NOT lose the lead - we update status fields
        self._queue_notification_tasks(lead, site.id, request)

        return JsonResponse(
            {
                "success": True,
                "message": "Thank you for your submission",
                "lead_id": lead.id,
            },
            status=200,
        )

    def _parse_request_data(self, request) -> dict[str, Any] | None:
        """Parse request body as JSON or form data."""
        from typing import cast

        content_type = request.content_type or ""

        if "application/json" in content_type:
            try:
                # helper to shut up mypy no-any-return
                return cast(dict[str, Any], json.loads(request.body))
            except (json.JSONDecodeError, ValueError):
                return None

        # Fall back to form-encoded data
        return cast(dict[str, Any], request.POST.dict())

    def _get_site(self, request) -> Site | None:
        """Get the Wagtail Site for this request."""
        site = Site.find_for_request(request)
        if site is not None:
            return site

        return Site.objects.filter(is_default_site=True).first() or Site.objects.first()

    def _get_config(self, site: Site) -> FormConfiguration:
        """Get or create FormConfiguration for site."""
        return FormConfiguration.get_for_site(site)

    def _validate_submission(self, data: dict, config: FormConfiguration) -> dict:
        """
        Validate required submission fields.

        Returns dict of field -> error messages, empty if valid.
        """
        errors: dict[str, list[str]] = {}

        # Required fields
        required_fields = {
            "name": "Name is required",
            "email": "Email is required",
            "message": "Message is required",
        }

        for field, error_msg in required_fields.items():
            value = data.get(field, "").strip()
            if not value:
                errors[field] = [error_msg]

        # Email format validation (only if email is present)
        email = data.get("email", "").strip()
        if email and "email" not in errors:
            try:
                validate_email(email)
            except Exception:
                errors["email"] = ["Please enter a valid email address"]

        # Phone validation (optional, but if provided must be valid UK format)
        phone = data.get("phone", "").strip()
        if phone:
            # Normalize: remove common separators for regex matching
            phone_normalized = re.sub(r"[\s\-\(\)]", "", phone)
            if not UK_PHONE_REGEX.match(phone_normalized):
                errors["phone"] = ["Please enter a valid UK phone number"]

        # Form type - required or use default
        form_type = data.get("form_type", "").strip()
        if not form_type:
            if config.default_form_type:
                # Will use default, no error
                pass
            else:
                errors["form_type"] = ["Form type is required"]

        return errors

    def _create_lead(self, data: dict, site: Site):
        """
        Create Lead from validated submission data.

        Uses the canonical Lead service to ensure "no lost leads" invariant.
        """
        # Determine form type
        form_type = data.get("form_type", "").strip()
        if not form_type:
            config = self._get_config(site)
            form_type = config.default_form_type or "unknown"

        # Build attribution data
        attribution = AttributionData(
            utm_source=data.get("utm_source", ""),
            utm_medium=data.get("utm_medium", ""),
            utm_campaign=data.get("utm_campaign", ""),
            utm_term=data.get("utm_term", ""),
            utm_content=data.get("utm_content", ""),
            landing_page_url=data.get("landing_page_url", ""),
            page_url=data.get("page_url", ""),
            referrer_url=data.get("referrer_url", ""),
        )

        # Collect additional form data (excluding standard fields)
        standard_fields = {
            "name",
            "email",
            "phone",
            "message",
            "form_type",
            "utm_source",
            "utm_medium",
            "utm_campaign",
            "utm_term",
            "utm_content",
            "landing_page_url",
            "page_url",
            "referrer_url",
            "_time_token",
            "csrfmiddlewaretoken",
        }

        # Get honeypot field name to exclude it
        config = self._get_config(site)
        standard_fields.add(config.honeypot_field_name)

        extra_data: dict[str, Any] = {}
        for key, value in data.items():
            if key not in standard_fields and not key.startswith("_"):
                extra_data[key] = value

        # Create the lead using canonical service
        return create_lead_from_submission(
            name=data.get("name", ""),
            email=data.get("email", ""),
            message=data.get("message", ""),
            form_type=form_type,
            phone=data.get("phone"),
            form_data=extra_data if extra_data else None,
            attribution=attribution,
        )

    def _queue_notification_tasks(self, lead, site_id: int, request) -> None:
        """
        Queue async notification tasks after lead creation.

        Failure to queue does NOT lose the lead - we update status fields
        to reflect the queueing failure for visibility in admin.

        This ensures the "no lost leads" invariant is maintained even when
        Celery/broker is unavailable.

        Args:
            lead: The created Lead instance.
            site_id: The Wagtail Site ID for per-site configuration lookup.
            request: The HTTP request (for extracting request_id).
        """
        import logging

        from sum_core.leads.models import EmailStatus, WebhookStatus, ZapierStatus
        from sum_core.leads.tasks import (
            send_lead_notification,
            send_lead_webhook,
            send_zapier_webhook,
        )

        logger = logging.getLogger(__name__)

        # Get request_id set by CorrelationIdMiddleware (if available)
        request_id = getattr(request, "request_id", None)

        # Attempt to queue email notification task
        try:
            send_lead_notification.delay(
                lead.id, request_id=request_id, site_id=site_id
            )
        except Exception as e:
            logger.exception(f"Failed to queue email notification for lead {lead.id}")
            lead.email_status = EmailStatus.FAILED
            lead.email_last_error = f"Failed to queue task: {str(e)[:500]}"
            lead.save(update_fields=["email_status", "email_last_error"])

        # Attempt to queue webhook notification task
        try:
            send_lead_webhook.delay(lead.id, request_id=request_id)
        except Exception as e:
            logger.exception(f"Failed to queue webhook notification for lead {lead.id}")
            lead.webhook_status = WebhookStatus.FAILED
            lead.webhook_last_error = f"Failed to queue task: {str(e)[:500]}"
            lead.save(update_fields=["webhook_status", "webhook_last_error"])

        # Attempt to queue Zapier webhook task (M4-007)
        try:
            send_zapier_webhook.delay(lead.id, site_id, request_id=request_id)
        except Exception as e:
            logger.exception(f"Failed to queue Zapier webhook for lead {lead.id}")
            lead.zapier_status = ZapierStatus.FAILED
            lead.zapier_last_error = f"Failed to queue task: {str(e)[:500]}"
            lead.save(update_fields=["zapier_status", "zapier_last_error"])


# Convenience function-based view for URL routing
form_submission_view = FormSubmissionView.as_view()
