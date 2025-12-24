"""
Name: Lead async tasks
Path: core/sum_core/leads/tasks.py
Purpose: Send lead notifications and webhooks asynchronously with retries and status tracking.
Family: Leads, forms, integrations, ops visibility.
Dependencies: Celery, Django email backend, HTTP client, Lead model.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import requests
from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from sum_core.ops.sentry import set_sentry_context

if TYPE_CHECKING:
    from sum_core.leads.models import Lead

logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 3
RETRY_BACKOFF = 60  # Base backoff in seconds (60, 120, 240)
WEBHOOK_TIMEOUT = 10  # seconds


def build_lead_notification_context(lead: Lead) -> dict:
    """
    Build template context for lead notification email.

    Args:
        lead: The Lead instance to build context for.

    Returns:
        Dictionary with all context variables for email templates.
    """
    return {
        "lead_id": lead.id,
        "name": lead.name,
        "email": lead.email,
        "phone": lead.phone,
        "message": lead.message,
        "form_type": lead.form_type,
        "submitted_at": lead.submitted_at,
        "page_url": lead.page_url,
        "referrer_url": lead.referrer_url,
        "lead_source": lead.lead_source,
        "lead_source_display": (
            lead.get_lead_source_display() if lead.lead_source else ""
        ),
        "lead_source_detail": lead.lead_source_detail,
        "utm_source": lead.utm_source,
        "utm_medium": lead.utm_medium,
        "utm_campaign": lead.utm_campaign,
        "utm_term": lead.utm_term,
        "utm_content": lead.utm_content,
        "landing_page_url": lead.landing_page_url,
        "site_name": getattr(settings, "WAGTAIL_SITE_NAME", ""),
    }


def build_webhook_payload(lead: Lead) -> dict:
    """
    Build JSON payload for webhook POST matching SSOT schema.

    Args:
        lead: The Lead instance to build payload for.

    Returns:
        Dictionary matching the SSOT webhook payload schema.
    """
    return {
        "lead_id": lead.id,
        "name": lead.name,
        "email": lead.email,
        "phone": lead.phone,
        "message": lead.message,
        "form_type": lead.form_type,
        "form_data": lead.form_data,
        "lead_source": lead.lead_source,
        "utm_source": lead.utm_source,
        "utm_medium": lead.utm_medium,
        "utm_campaign": lead.utm_campaign,
        "page_url": lead.page_url,
        "submitted_at": lead.submitted_at.isoformat() if lead.submitted_at else None,
    }


@shared_task(
    bind=True,
    max_retries=MAX_RETRIES,
    default_retry_delay=RETRY_BACKOFF,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
)
def send_lead_notification(
    self, lead_id: int, request_id: str | None = None, site_id: int | None = None
) -> None:
    """
    Send email notification for a new lead.

    This task is idempotent and concurrency-safe - uses select_for_update()
    to prevent duplicate sends under concurrent execution.

    Args:
        lead_id: The ID of the Lead to send notification for.
        request_id: Optional correlation ID from originating request.
        site_id: Optional ID of the Wagtail Site to fetch branding settings from.
    """
    from django.db import transaction
    from sum_core.branding.models import SiteSettings
    from sum_core.leads.models import EmailStatus, Lead
    from wagtail.models import Site

    # Set Sentry context for error tracking
    set_sentry_context(
        request_id=request_id,
        lead_id=lead_id,
        site_id=site_id,
        task="send_lead_notification",
    )

    # Get notification email address
    notification_email = getattr(settings, "LEAD_NOTIFICATION_EMAIL", "")

    attempt_count = 0

    # Use select_for_update within a transaction for concurrency safety
    try:
        with transaction.atomic():
            lead = Lead.objects.select_for_update(nowait=False).get(id=lead_id)

            # Idempotency check - don't resend if already sent (with lock held)
            if lead.email_status == EmailStatus.SENT:
                logger.info(
                    "Lead email already sent, skipping",
                    extra={
                        "lead_id": lead_id,
                        "site_id": site_id,
                        "request_id": request_id or "-",
                    },
                )
                return

            if (
                lead.email_status == EmailStatus.IN_PROGRESS
                and self.request.retries == 0
            ):
                logger.info(
                    "Lead email already in progress, skipping",
                    extra={
                        "lead_id": lead_id,
                        "site_id": site_id,
                        "request_id": request_id or "-",
                    },
                )
                return

            if not notification_email:
                logger.warning(
                    "No LEAD_NOTIFICATION_EMAIL configured, skipping",
                    extra={"lead_id": lead_id, "request_id": request_id or "-"},
                )
                lead.email_status = EmailStatus.FAILED
                lead.email_last_error = "No notification email address configured"
                lead.email_attempts += 1
                lead.save(
                    update_fields=["email_status", "email_last_error", "email_attempts"]
                )
                return

            lead.email_status = EmailStatus.IN_PROGRESS
            lead.email_attempts += 1
            lead.save(update_fields=["email_status", "email_attempts"])
            attempt_count = lead.email_attempts
    except Lead.DoesNotExist:
        logger.error(
            "Lead not found for email notification",
            extra={
                "lead_id": lead_id,
                "site_id": site_id,
                "request_id": request_id or "-",
            },
        )
        return

    # Build email context and render templates
    context = build_lead_notification_context(lead)

    # Prepare email configuration (defaults)
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@example.com")
    reply_to = []
    subject_prefix = ""

    # Apply SiteSettings branding if available
    if site_id:
        try:
            site = Site.objects.get(id=site_id)
            site_settings = SiteSettings.for_site(site)

            if site_settings.notification_from_email:
                name = site_settings.notification_from_name
                email = site_settings.notification_from_email
                if name:
                    from_email = f"{name} <{email}>"
                else:
                    from_email = email

            if site_settings.notification_reply_to_email:
                reply_to = [site_settings.notification_reply_to_email]

            if site_settings.notification_subject_prefix:
                subject_prefix = f"{site_settings.notification_subject_prefix} "
        except (Site.DoesNotExist, SiteSettings.DoesNotExist):
            # Fallback to defaults regardless of error in fetching settings
            pass

    try:
        subject_raw = render_to_string(
            "sum_core/emails/lead_notification_subject.txt", context
        ).strip()
        subject = f"{subject_prefix}{subject_raw}"
        body = render_to_string("sum_core/emails/lead_notification_body.txt", context)
    except Exception as e:
        error_message = f"Template render failed: {str(e)[:500]}"
        with transaction.atomic():
            lead = Lead.objects.select_for_update(nowait=False).get(id=lead_id)
            lead.email_last_error = error_message
            lead.email_status = EmailStatus.FAILED
            lead.save(update_fields=["email_status", "email_last_error"])
        logger.error(
            "Lead email template render failed",
            extra={"lead_id": lead_id, "request_id": request_id or "-"},
        )
        return

    msg = EmailMultiAlternatives(
        subject=subject,
        body=body,
        from_email=from_email,
        to=[notification_email],
        reply_to=reply_to or None,
    )

    # Check if HTML template exists (it should, but safety first)
    try:
        html_body = render_to_string(
            "sum_core/emails/lead_notification_body.html", context
        )
        msg.attach_alternative(html_body, "text/html")
    except Exception as e:
        logger.warning(
            "Failed to render HTML lead email, sending text only",
            extra={"error": str(e), "lead_id": lead_id},
        )

    try:
        msg.send(fail_silently=False)
    except Exception as e:
        error_message = str(e)[:500]
        with transaction.atomic():
            lead = Lead.objects.select_for_update(nowait=False).get(id=lead_id)
            lead.email_last_error = error_message
            lead.email_status = (
                EmailStatus.IN_PROGRESS
                if self.request.retries < MAX_RETRIES
                else EmailStatus.FAILED
            )
            lead.save(update_fields=["email_status", "email_last_error"])

        if self.request.retries < MAX_RETRIES:
            logger.warning(
                "Lead email failed, will retry",
                extra={
                    "lead_id": lead_id,
                    "request_id": request_id or "-",
                    "attempt": attempt_count,
                },
            )
            raise

        logger.error(
            "Lead email failed permanently",
            extra={
                "lead_id": lead_id,
                "request_id": request_id or "-",
                "attempts": attempt_count,
            },
        )
        return

    with transaction.atomic():
        lead = Lead.objects.select_for_update(nowait=False).get(id=lead_id)
        lead.email_status = EmailStatus.SENT
        lead.email_sent_at = timezone.now()
        lead.email_last_error = ""
        lead.save(update_fields=["email_status", "email_sent_at", "email_last_error"])

    logger.info(
        "Lead email notification sent successfully",
        extra={"lead_id": lead_id, "request_id": request_id or "-"},
    )


@shared_task(
    bind=True,
    max_retries=MAX_RETRIES,
    default_retry_delay=RETRY_BACKOFF,
    autoretry_for=(requests.RequestException,),
    retry_backoff=True,
    retry_backoff_max=300,
)
def send_lead_webhook(self, lead_id: int, request_id: str | None = None) -> None:
    """
    Send webhook notification for a new lead.

    This task is idempotent and concurrency-safe - uses select_for_update()
    to prevent duplicate sends under concurrent execution.

    If no webhook URL is configured, the status is set to 'disabled'.

    Args:
        lead_id: The ID of the Lead to send webhook for.
        request_id: Optional correlation ID from originating request.
    """
    from django.db import transaction
    from sum_core.leads.models import Lead, WebhookStatus

    # Set Sentry context for error tracking
    set_sentry_context(request_id=request_id, lead_id=lead_id, task="send_lead_webhook")

    webhook_url = getattr(settings, "ZAPIER_WEBHOOK_URL", "")
    attempt_count = 0

    try:
        with transaction.atomic():
            lead = Lead.objects.select_for_update(nowait=False).get(id=lead_id)

            # Idempotency check - don't resend if already sent (with lock held)
            if lead.webhook_status == WebhookStatus.SENT:
                logger.info(
                    "Lead webhook already sent, skipping",
                    extra={"lead_id": lead_id, "request_id": request_id or "-"},
                )
                return

            if (
                lead.webhook_status == WebhookStatus.IN_PROGRESS
                and self.request.retries == 0
            ):
                logger.info(
                    "Lead webhook already in progress, skipping",
                    extra={"lead_id": lead_id, "request_id": request_id or "-"},
                )
                return

            # Check if webhook URL is configured
            if not webhook_url:
                lead.webhook_status = WebhookStatus.DISABLED
                lead.save(update_fields=["webhook_status"])
                logger.info(
                    "Lead webhook disabled (no URL configured)",
                    extra={"lead_id": lead_id, "request_id": request_id or "-"},
                )
                return

            lead.webhook_status = WebhookStatus.IN_PROGRESS
            lead.webhook_attempts += 1
            lead.save(update_fields=["webhook_status", "webhook_attempts"])
            attempt_count = lead.webhook_attempts
    except Lead.DoesNotExist:
        logger.error(
            "Lead not found for webhook notification",
            extra={"lead_id": lead_id, "request_id": request_id or "-"},
        )
        return

    # Build JSON payload
    payload = build_webhook_payload(lead)

    try:
        response = requests.post(
            webhook_url,
            json=payload,
            timeout=WEBHOOK_TIMEOUT,
            headers={"Content-Type": "application/json"},
        )
    except requests.Timeout as e:
        error_message = f"Request timeout: {str(e)[:200]}"
        with transaction.atomic():
            lead = Lead.objects.select_for_update(nowait=False).get(id=lead_id)
            lead.webhook_last_error = error_message
            lead.webhook_last_status_code = None
            lead.webhook_status = (
                WebhookStatus.IN_PROGRESS
                if self.request.retries < MAX_RETRIES
                else WebhookStatus.FAILED
            )
            lead.save(
                update_fields=[
                    "webhook_status",
                    "webhook_last_error",
                    "webhook_last_status_code",
                ]
            )

        if self.request.retries < MAX_RETRIES:
            logger.warning(
                "Lead webhook timeout, will retry",
                extra={
                    "lead_id": lead_id,
                    "request_id": request_id or "-",
                    "attempt": attempt_count,
                },
            )
            raise

        logger.error(
            "Lead webhook failed permanently: timeout",
            extra={"lead_id": lead_id, "request_id": request_id or "-"},
        )
        return
    except requests.RequestException as e:
        error_message = str(e)[:500]
        with transaction.atomic():
            lead = Lead.objects.select_for_update(nowait=False).get(id=lead_id)
            lead.webhook_last_error = error_message
            lead.webhook_last_status_code = None
            lead.webhook_status = (
                WebhookStatus.IN_PROGRESS
                if self.request.retries < MAX_RETRIES
                else WebhookStatus.FAILED
            )
            lead.save(
                update_fields=[
                    "webhook_status",
                    "webhook_last_error",
                    "webhook_last_status_code",
                ]
            )

        if self.request.retries < MAX_RETRIES:
            logger.warning(
                "Lead webhook failed, will retry",
                extra={
                    "lead_id": lead_id,
                    "request_id": request_id or "-",
                    "attempt": attempt_count,
                },
            )
            raise

        logger.error(
            "Lead webhook failed permanently",
            extra={"lead_id": lead_id, "request_id": request_id or "-"},
        )
        return

    with transaction.atomic():
        lead = Lead.objects.select_for_update(nowait=False).get(id=lead_id)
        lead.webhook_last_status_code = response.status_code

        if response.ok:
            lead.webhook_status = WebhookStatus.SENT
            lead.webhook_sent_at = timezone.now()
            lead.webhook_last_error = ""
            lead.save(
                update_fields=[
                    "webhook_status",
                    "webhook_sent_at",
                    "webhook_last_status_code",
                    "webhook_last_error",
                ]
            )
            logger.info(
                "Lead webhook sent successfully",
                extra={"lead_id": lead_id, "request_id": request_id or "-"},
            )
            return

        error_message = f"HTTP {response.status_code}: {response.text[:200]}"
        lead.webhook_last_error = error_message
        lead.webhook_status = (
            WebhookStatus.IN_PROGRESS
            if self.request.retries < MAX_RETRIES
            else WebhookStatus.FAILED
        )
        lead.save(
            update_fields=[
                "webhook_status",
                "webhook_last_status_code",
                "webhook_last_error",
            ]
        )

    if self.request.retries < MAX_RETRIES:
        logger.warning(
            "Lead webhook failed, will retry",
            extra={
                "lead_id": lead_id,
                "request_id": request_id or "-",
                "attempt": attempt_count,
                "status_code": response.status_code,
            },
        )
        raise requests.RequestException(error_message)

    logger.error(
        "Lead webhook failed permanently",
        extra={
            "lead_id": lead_id,
            "request_id": request_id or "-",
            "status_code": response.status_code,
        },
    )


# Zapier-specific retry configuration (M4-007)
ZAPIER_MAX_RETRIES = 5
ZAPIER_RETRY_BACKOFF = 60  # Base backoff in seconds


@shared_task(
    bind=True,
    max_retries=ZAPIER_MAX_RETRIES,
    default_retry_delay=ZAPIER_RETRY_BACKOFF,
    autoretry_for=(requests.RequestException,),
    retry_backoff=True,
    retry_backoff_max=600,
)
def send_zapier_webhook(
    self, lead_id: int, site_id: int, request_id: str | None = None
) -> None:
    """
    Send Zapier webhook for a new lead using per-site configuration.

    This task is idempotent and concurrency-safe - uses select_for_update()
    to prevent duplicate sends under concurrent execution (CM-001 pattern).

    If Zapier is not configured for the site, the status is set to 'disabled'.

    Args:
        lead_id: The ID of the Lead to send webhook for.
        site_id: The ID of the Wagtail Site to fetch Zapier config from.
        request_id: Optional correlation ID from originating request.
    """
    from django.db import transaction
    from sum_core.branding.models import SiteSettings
    from sum_core.integrations.zapier import build_zapier_payload, send_zapier_request
    from sum_core.leads.models import Lead, ZapierStatus
    from wagtail.models import Site

    # Set Sentry context for error tracking
    set_sentry_context(
        request_id=request_id,
        lead_id=lead_id,
        site_id=site_id,
        task="send_zapier_webhook",
    )

    attempt_count = 0
    site: Site | None = None
    site_settings: SiteSettings | None = None

    try:
        with transaction.atomic():
            lead = Lead.objects.select_for_update(nowait=False).get(id=lead_id)

            # Idempotency check - don't resend if already sent (with lock held)
            if lead.zapier_status == ZapierStatus.SENT:
                logger.info(
                    "Lead Zapier webhook already sent, skipping",
                    extra={
                        "lead_id": lead_id,
                        "site_id": site_id,
                        "request_id": request_id or "-",
                    },
                )
                return

            if (
                lead.zapier_status == ZapierStatus.IN_PROGRESS
                and self.request.retries == 0
            ):
                logger.info(
                    "Lead Zapier webhook already in progress, skipping",
                    extra={
                        "lead_id": lead_id,
                        "site_id": site_id,
                        "request_id": request_id or "-",
                    },
                )
                return

            # Get site and settings
            try:
                site = Site.objects.get(id=site_id)
            except Site.DoesNotExist:
                logger.error(
                    "Site not found for Zapier webhook",
                    extra={
                        "lead_id": lead_id,
                        "site_id": site_id,
                        "request_id": request_id or "-",
                    },
                )
                lead.zapier_status = ZapierStatus.FAILED
                lead.zapier_last_error = f"Site {site_id} not found"
                lead.save(update_fields=["zapier_status", "zapier_last_error"])
                return

            # Get SiteSettings for Zapier configuration
            try:
                site_settings = SiteSettings.for_site(site)
            except SiteSettings.DoesNotExist:
                logger.info(
                    "Lead Zapier disabled (no SiteSettings)",
                    extra={
                        "lead_id": lead_id,
                        "site_id": site_id,
                        "request_id": request_id or "-",
                    },
                )
                lead.zapier_status = ZapierStatus.DISABLED
                lead.save(update_fields=["zapier_status"])
                return

            # Check if Zapier is enabled and URL is configured
            if not site_settings.zapier_enabled or not site_settings.zapier_webhook_url:
                logger.info(
                    "Lead Zapier disabled by config",
                    extra={
                        "lead_id": lead_id,
                        "site_id": site_id,
                        "request_id": request_id or "-",
                        "zapier_enabled": site_settings.zapier_enabled,
                        "url_configured": bool(site_settings.zapier_webhook_url),
                    },
                )
                lead.zapier_status = ZapierStatus.DISABLED
                lead.save(update_fields=["zapier_status"])
                return

            lead.zapier_status = ZapierStatus.IN_PROGRESS
            lead.zapier_attempt_count += 1
            lead.zapier_last_attempt_at = timezone.now()
            lead.save(
                update_fields=[
                    "zapier_status",
                    "zapier_attempt_count",
                    "zapier_last_attempt_at",
                ]
            )
            attempt_count = lead.zapier_attempt_count
    except Lead.DoesNotExist:
        logger.error(
            "Lead not found for Zapier webhook",
            extra={
                "lead_id": lead_id,
                "site_id": site_id,
                "request_id": request_id or "-",
            },
        )
        return

    if site is None or site_settings is None:
        return

    # Build payload and send request
    payload = build_zapier_payload(lead, site)
    result = send_zapier_request(site_settings.zapier_webhook_url, payload)

    if result.success:
        with transaction.atomic():
            lead = Lead.objects.select_for_update(nowait=False).get(id=lead_id)
            lead.zapier_status = ZapierStatus.SENT
            lead.zapier_last_error = ""
            lead.save(
                update_fields=[
                    "zapier_status",
                    "zapier_last_error",
                ]
            )
        logger.info(
            "Lead Zapier webhook sent successfully",
            extra={
                "lead_id": lead_id,
                "site_id": site_id,
                "request_id": request_id or "-",
            },
        )
        return

    error_message = result.error_message[:500]
    with transaction.atomic():
        lead = Lead.objects.select_for_update(nowait=False).get(id=lead_id)
        lead.zapier_last_error = error_message
        lead.zapier_status = (
            ZapierStatus.IN_PROGRESS
            if self.request.retries < ZAPIER_MAX_RETRIES
            else ZapierStatus.FAILED
        )
        lead.save(update_fields=["zapier_status", "zapier_last_error"])

    if self.request.retries < ZAPIER_MAX_RETRIES:
        logger.warning(
            "Lead Zapier webhook failed, will retry",
            extra={
                "lead_id": lead_id,
                "site_id": site_id,
                "request_id": request_id or "-",
                "attempt": attempt_count,
            },
        )
        raise requests.RequestException(error_message)

    logger.error(
        "Lead Zapier webhook failed permanently",
        extra={
            "lead_id": lead_id,
            "site_id": site_id,
            "request_id": request_id or "-",
            "attempts": attempt_count,
        },
    )
