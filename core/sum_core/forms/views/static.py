"""
Name: Static form submission handler
Path: core/sum_core/forms/views/static.py
Purpose: Handle legacy/static Contact and Quote form submissions.
Family: Forms, Leads, Attribution, Notifications.
Dependencies: FormConfiguration, Lead service, SpamChecks.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any

from django.core.validators import validate_email
from django.http import HttpRequest, JsonResponse
from sum_core.forms.models import FormConfiguration
from sum_core.forms.services import run_spam_checks
from sum_core.forms.views.base import UK_PHONE_REGEX, get_config, spam_response
from sum_core.leads.services import AttributionData, create_lead_from_submission
from sum_core.ops.request_utils import get_client_ip
from wagtail.models import Site

if TYPE_CHECKING:
    from sum_core.leads.models import Lead

logger = logging.getLogger(__name__)


def handle_static_form_submission(
    request: HttpRequest, data: dict[str, Any], site: Site
) -> JsonResponse:
    """Process legacy/static form submissions."""
    config = get_config(site)

    spam_result = run_spam_checks(
        form_data=data,
        ip_address=get_client_ip(request),
        site_id=site.id,
        time_token=data.get("_time_token", ""),
        honeypot_field_name=config.honeypot_field_name,
        rate_limit_per_hour=config.rate_limit_per_ip_per_hour,
        min_seconds_to_submit=config.min_seconds_to_submit,
    )
    response = spam_response(spam_result, request)
    if response:
        return response

    validation_errors = validate_static_submission(data, config)
    if validation_errors:
        return JsonResponse(
            {"success": False, "errors": validation_errors},
            status=400,
        )

    try:
        lead = create_static_lead(data, site)
    except ValueError:
        logger.warning("Lead creation failed for static form", exc_info=True)
        return JsonResponse(
            {
                "success": False,
                "errors": {
                    "__all__": ["Unable to process submission. Please try again."]
                },
            },
            status=400,
        )

    queue_static_notification_tasks(lead, site.id, request)

    return JsonResponse(
        {
            "success": True,
            "message": "Thank you for your submission",
            "lead_id": lead.id,
        },
        status=200,
    )


def validate_static_submission(data: dict, config: FormConfiguration) -> dict:
    """Validate required submission fields. Returns dict of field -> error messages."""
    errors: dict[str, list[str]] = {}

    required_fields = {
        "name": "Name is required",
        "email": "Email is required",
        "message": "Message is required",
    }

    for field, error_msg in required_fields.items():
        value = data.get(field, "").strip()
        if not value:
            errors[field] = [error_msg]

    email = data.get("email", "").strip()
    if email and "email" not in errors:
        try:
            validate_email(email)
        except Exception:
            errors["email"] = ["Please enter a valid email address"]

    phone = data.get("phone", "").strip()
    if phone:
        phone_normalized = re.sub(r"[\s\-\(\)]", "", phone)
        if not UK_PHONE_REGEX.match(phone_normalized):
            errors["phone"] = ["Please enter a valid UK phone number"]

    form_type = data.get("form_type", "").strip()
    if not form_type:
        if config.default_form_type:
            pass
        else:
            errors["form_type"] = ["Form type is required"]

    return errors


def create_static_lead(data: dict, site: Site) -> Lead:
    """Create Lead from validated static submission data."""
    form_type = data.get("form_type", "").strip()
    if not form_type:
        config = get_config(site)
        form_type = config.default_form_type or "unknown"

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

    config = get_config(site)
    standard_fields.add(config.honeypot_field_name)

    extra_data: dict[str, Any] = {}
    for key, value in data.items():
        if key not in standard_fields and not key.startswith("_"):
            extra_data[key] = value

    return create_lead_from_submission(
        name=data.get("name", ""),
        email=data.get("email", ""),
        message=data.get("message", ""),
        form_type=form_type,
        phone=data.get("phone"),
        form_data=extra_data if extra_data else None,
        attribution=attribution,
    )


def queue_static_notification_tasks(
    lead: Lead, site_id: int, request: HttpRequest
) -> None:
    """Queue async notification tasks after lead creation."""
    from sum_core.leads.models import EmailStatus, WebhookStatus, ZapierStatus
    from sum_core.leads.tasks import (
        send_lead_notification,
        send_lead_webhook,
        send_zapier_webhook,
    )

    request_id = getattr(request, "request_id", None)

    try:
        send_lead_notification.delay(lead.id, request_id=request_id, site_id=site_id)
    except Exception as e:
        logger.exception(f"Failed to queue email notification for lead {lead.id}")
        lead.email_status = EmailStatus.FAILED
        lead.email_last_error = f"Failed to queue task: {str(e)[:500]}"
        lead.save(update_fields=["email_status", "email_last_error"])

    try:
        send_lead_webhook.delay(lead.id, request_id=request_id)
    except Exception as e:
        logger.exception(f"Failed to queue webhook notification for lead {lead.id}")
        lead.webhook_status = WebhookStatus.FAILED
        lead.webhook_last_error = f"Failed to queue task: {str(e)[:500]}"
        lead.save(update_fields=["webhook_status", "webhook_last_error"])

    try:
        send_zapier_webhook.delay(lead.id, site_id, request_id=request_id)
    except Exception as e:
        logger.exception(f"Failed to queue Zapier webhook for lead {lead.id}")
        lead.zapier_status = ZapierStatus.FAILED
        lead.zapier_last_error = f"Failed to queue task: {str(e)[:500]}"
        lead.save(update_fields=["zapier_status", "zapier_last_error"])
