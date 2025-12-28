"""
Name: Dynamic form async tasks
Path: core/sum_core/forms/tasks.py
Purpose: Send dynamic form notifications, auto-replies, and webhooks asynchronously.
Family: Forms, Leads, Integrations.
Dependencies: Celery, Django email backend, HTTP client, Lead model.
"""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import logging
import re
import socket
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

import requests
from celery import shared_task
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.template.loader import render_to_string
from django.utils import timezone
from sum_core.ops.sentry import set_sentry_context

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from sum_core.forms.models import FormDefinition
    from sum_core.leads.models import Lead

MAX_RETRIES = 3
RETRY_BACKOFF = 60  # seconds; exponential backoff uses 60, 120, 240
WEBHOOK_TIMEOUT = 10  # seconds
NAME_TOKEN = re.compile(r"{{\s*name\s*}}")
NAME_NEWLINE = re.compile(r"[\r\n]+")
NAME_CONTROL = re.compile(r"[\x00-\x1F\x7F]")
WEBHOOK_SIGNATURE_HEADER = "X-SUM-Webhook-Signature"


def _parse_recipients(emails: str) -> list[str]:
    """
    Parse a comma-separated string of email addresses into a cleaned list.

    Invalid email addresses are ignored and logged for observability.
    """
    recipients: list[str] = []
    for raw_email in emails.split(","):
        email = raw_email.strip()
        if not email:
            continue
        try:
            validate_email(email)
        except ValidationError:
            logger.warning("Invalid notification email", extra={"email": email})
            continue
        recipients.append(email)
    return recipients


def _resolve_webhook_host(
    hostname: str,
) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    addresses: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
    try:
        results = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return addresses

    for family, _, _, _, sockaddr in results:
        if family == socket.AF_INET:
            ip_value = sockaddr[0]
        elif family == socket.AF_INET6:
            ip_value = sockaddr[0]
        else:
            continue
        try:
            addresses.append(ipaddress.ip_address(ip_value))
        except ValueError:
            logger.warning(
                "Webhook URL resolved to invalid IP",
                extra={"hostname": hostname, "ip": ip_value},
            )
    return addresses


def _validate_webhook_url(webhook_url: str) -> tuple[bool, str]:
    try:
        parsed = urlsplit(webhook_url)
    except ValueError:
        return False, "Webhook URL is invalid"

    scheme = (parsed.scheme or "").lower()
    if scheme not in {"http", "https"}:
        return False, "Webhook URL must use http or https"

    hostname = (parsed.hostname or "").lower()
    if not hostname:
        return False, "Webhook URL host is missing"

    if (
        hostname == "localhost"
        or hostname.endswith(".localhost")
        or hostname.endswith(".local")
    ):
        return False, "Webhook URL host is not allowed"

    try:
        addresses = [ipaddress.ip_address(hostname)]
    except ValueError:
        addresses = _resolve_webhook_host(hostname)
        if not addresses:
            return False, "Webhook URL host could not be resolved"

    for address in addresses:
        if not address.is_global:
            return False, "Webhook URL resolves to a non-public IP"

    return True, ""


def _build_webhook_payload(
    lead: Lead, form_definition: FormDefinition, request_id: str | None = None
) -> dict[str, object]:
    """
    Build the webhook payload for dynamic form submissions.

    The payload includes form metadata, submission data, and attribution fields.
    """
    filtered_data = _filter_webhook_data(
        lead.form_data,
        allowlist=form_definition.get_webhook_allowlist(),
        denylist=form_definition.get_webhook_denylist(),
    )
    payload: dict[str, object] = {
        "event": "form.submitted",
        "timestamp": (lead.submitted_at or timezone.now()).isoformat(),
        "form": {
            "id": form_definition.id,
            "name": form_definition.name,
            "slug": form_definition.slug,
        },
        "submission": {
            "id": lead.id,
            "contact": {
                "name": lead.name,
                "email": lead.email,
                "phone": lead.phone,
                "message": lead.message,
            },
            "data": filtered_data,
            "created_at": lead.submitted_at.isoformat() if lead.submitted_at else None,
        },
        "attribution": {
            "source_url": lead.page_url,
            "landing_page": lead.landing_page_url,
            "utm_source": lead.utm_source,
            "utm_medium": lead.utm_medium,
            "utm_campaign": lead.utm_campaign,
            "utm_term": lead.utm_term,
            "utm_content": lead.utm_content,
        },
    }
    if request_id:
        payload["request_id"] = request_id
    return payload


def _filter_webhook_data(
    data: dict[str, object] | None,
    *,
    allowlist: set[str],
    denylist: set[str],
) -> dict[str, object]:
    filtered = dict(data or {})
    if allowlist:
        filtered = {key: value for key, value in filtered.items() if key in allowlist}
    if denylist:
        filtered = {
            key: value for key, value in filtered.items() if key not in denylist
        }
    return filtered


def _build_webhook_body(payload: dict[str, object]) -> str:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True)


def _build_webhook_signature(secret: str, body: str) -> str:
    return hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()


def _build_webhook_headers(secret: str, body: str) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if secret:
        signature = _build_webhook_signature(secret, body)
        headers[WEBHOOK_SIGNATURE_HEADER] = f"sha256={signature}"
    return headers


def _interpolate_name(template: str, name: str) -> str:
    """Replace the {{name}} placeholder with a sanitized name for plain text."""
    safe_name = NAME_NEWLINE.sub(" ", str(name or "")).strip()
    safe_name = NAME_CONTROL.sub("", safe_name)
    return NAME_TOKEN.sub(safe_name, template)


@shared_task(
    bind=True,
    max_retries=MAX_RETRIES,
    default_retry_delay=RETRY_BACKOFF,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
)
def send_form_notification(
    self,
    lead_id: int,
    form_definition_id: int,
    request_id: str | None = None,
) -> None:
    """
    Send email notification to admin recipients when a dynamic form is submitted.
    """
    from django.db import transaction
    from sum_core.forms.models import FormDefinition
    from sum_core.leads.models import EmailStatus, Lead

    set_sentry_context(
        request_id=request_id,
        lead_id=lead_id,
        task="send_form_notification",
    )

    try:
        form_definition = FormDefinition.objects.get(id=form_definition_id)
    except FormDefinition.DoesNotExist:
        Lead.objects.filter(id=lead_id).update(
            form_notification_status=EmailStatus.FAILED,
            form_notification_last_error="Form definition missing",
        )
        logger.warning(
            "Skipping form notification: form definition missing",
            extra={"lead_id": lead_id, "form_definition_id": form_definition_id},
        )
        return

    recipients = _parse_recipients(form_definition.notification_emails)

    attempt_count = 0
    try:
        with transaction.atomic():
            lead = Lead.objects.select_for_update(nowait=True).get(id=lead_id)

            if lead.form_notification_status == EmailStatus.SENT:
                logger.info(
                    "Form notification already sent, skipping",
                    extra={
                        "lead_id": lead_id,
                        "request_id": request_id or "-",
                    },
                )
                return

            if (
                lead.form_notification_status == EmailStatus.IN_PROGRESS
                and self.request.retries == 0
            ):
                logger.info(
                    "Form notification already in progress, skipping",
                    extra={
                        "lead_id": lead_id,
                        "request_id": request_id or "-",
                    },
                )
                return

            if lead.form_notification_status == EmailStatus.DISABLED:
                logger.info(
                    "Form notification disabled, skipping",
                    extra={
                        "lead_id": lead_id,
                        "request_id": request_id or "-",
                    },
                )
                return

            if not form_definition.email_notification_enabled:
                lead.form_notification_status = EmailStatus.DISABLED
                lead.form_notification_last_error = ""
                lead.save(
                    update_fields=[
                        "form_notification_status",
                        "form_notification_last_error",
                    ]
                )
                return

            if not recipients:
                lead.form_notification_status = EmailStatus.FAILED
                lead.form_notification_last_error = (
                    "No notification recipients configured"
                )
                lead.save(
                    update_fields=[
                        "form_notification_status",
                        "form_notification_last_error",
                    ]
                )
                return

            lead.form_notification_status = EmailStatus.IN_PROGRESS
            lead.form_notification_attempts += 1
            lead.save(
                update_fields=[
                    "form_notification_status",
                    "form_notification_attempts",
                ]
            )
            attempt_count = lead.form_notification_attempts
    except Lead.DoesNotExist:
        logger.warning(
            "Skipping form notification: lead missing",
            extra={"lead_id": lead_id, "form_definition_id": form_definition_id},
        )
        return

    context = {"lead": lead, "form_definition": form_definition}
    subject = f"New {form_definition.name} Submission"

    try:
        html_message = render_to_string(
            "sum_core/emails/form_notification.html", context
        )
        plain_message = render_to_string(
            "sum_core/emails/form_notification.txt", context
        )
    except Exception as exc:
        error_message = f"Template render failed: {str(exc)[:500]}"
        try:
            with transaction.atomic():
                lead = Lead.objects.select_for_update(nowait=False).get(id=lead_id)
                lead.form_notification_last_error = error_message
                lead.form_notification_status = (
                    EmailStatus.IN_PROGRESS
                    if self.request.retries < MAX_RETRIES
                    else EmailStatus.FAILED
                )
                lead.save(
                    update_fields=[
                        "form_notification_status",
                        "form_notification_last_error",
                    ]
                )
        except Lead.DoesNotExist:
            logger.warning(
                "Form notification lead missing during error update",
                extra={"lead_id": lead_id, "request_id": request_id or "-"},
            )
            return

        if self.request.retries < MAX_RETRIES:
            logger.warning(
                "Form notification template render failed, will retry",
                extra={
                    "lead_id": lead_id,
                    "request_id": request_id or "-",
                    "attempt": attempt_count,
                },
            )
            raise

        logger.error(
            "Form notification template render failed permanently",
            extra={
                "lead_id": lead_id,
                "request_id": request_id or "-",
                "attempts": attempt_count,
            },
        )
        return

    try:
        send_mail(
            subject=subject,
            message=plain_message,
            html_message=html_message,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@example.com"),
            recipient_list=recipients,
            fail_silently=False,
        )
    except Exception as exc:
        error_message = str(exc)[:500]
        try:
            with transaction.atomic():
                lead = Lead.objects.select_for_update(nowait=False).get(id=lead_id)
                lead.form_notification_last_error = error_message
                lead.form_notification_status = (
                    EmailStatus.IN_PROGRESS
                    if self.request.retries < MAX_RETRIES
                    else EmailStatus.FAILED
                )
                lead.save(
                    update_fields=[
                        "form_notification_status",
                        "form_notification_last_error",
                    ]
                )
        except Lead.DoesNotExist:
            logger.warning(
                "Form notification lead missing during error update",
                extra={"lead_id": lead_id, "request_id": request_id or "-"},
            )
            return

        if self.request.retries < MAX_RETRIES:
            logger.warning(
                "Form notification failed, will retry",
                extra={
                    "lead_id": lead_id,
                    "request_id": request_id or "-",
                    "attempt": attempt_count,
                },
            )
            raise

        logger.error(
            "Form notification failed permanently",
            extra={
                "lead_id": lead_id,
                "request_id": request_id or "-",
                "attempts": attempt_count,
            },
        )
        return

    try:
        with transaction.atomic():
            lead = Lead.objects.select_for_update(nowait=True).get(id=lead_id)
            lead.form_notification_status = EmailStatus.SENT
            lead.form_notification_sent_at = timezone.now()
            lead.form_notification_last_error = ""
            lead.save(
                update_fields=[
                    "form_notification_status",
                    "form_notification_sent_at",
                    "form_notification_last_error",
                ]
            )
    except Lead.DoesNotExist:
        logger.warning(
            "Form notification lead missing during success update",
            extra={"lead_id": lead_id, "request_id": request_id or "-"},
        )
        return

    logger.info(
        "Form notification sent successfully",
        extra={"lead_id": lead_id, "request_id": request_id or "-"},
    )


@shared_task(
    bind=True,
    max_retries=MAX_RETRIES,
    default_retry_delay=RETRY_BACKOFF,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
)
def send_auto_reply(
    self,
    lead_id: int,
    form_definition_id: int,
    request_id: str | None = None,
) -> None:
    """
    Send auto-reply email to the submitter.
    """
    from django.db import transaction
    from sum_core.forms.models import FormDefinition
    from sum_core.leads.models import EmailStatus, Lead

    set_sentry_context(
        request_id=request_id,
        lead_id=lead_id,
        task="send_auto_reply",
    )

    try:
        form_definition = FormDefinition.objects.get(id=form_definition_id)
    except FormDefinition.DoesNotExist:
        Lead.objects.filter(id=lead_id).update(
            auto_reply_status=EmailStatus.FAILED,
            auto_reply_last_error="Form definition missing",
        )
        logger.warning(
            "Skipping auto reply: form definition missing",
            extra={"lead_id": lead_id, "form_definition_id": form_definition_id},
        )
        return

    attempt_count = 0
    try:
        with transaction.atomic():
            lead = Lead.objects.select_for_update(nowait=True).get(id=lead_id)

            if lead.auto_reply_status == EmailStatus.SENT:
                logger.info(
                    "Auto reply already sent, skipping",
                    extra={"lead_id": lead_id, "request_id": request_id or "-"},
                )
                return

            if (
                lead.auto_reply_status == EmailStatus.IN_PROGRESS
                and self.request.retries == 0
            ):
                logger.info(
                    "Auto reply already in progress, skipping",
                    extra={"lead_id": lead_id, "request_id": request_id or "-"},
                )
                return

            if lead.auto_reply_status == EmailStatus.DISABLED:
                logger.info(
                    "Auto reply disabled, skipping",
                    extra={"lead_id": lead_id, "request_id": request_id or "-"},
                )
                return

            if not form_definition.auto_reply_enabled:
                lead.auto_reply_status = EmailStatus.DISABLED
                lead.auto_reply_last_error = ""
                lead.save(update_fields=["auto_reply_status", "auto_reply_last_error"])
                return

            submitter_email = (lead.email or lead.form_data.get("email") or "").strip()
            if not submitter_email:
                lead.auto_reply_status = EmailStatus.FAILED
                lead.auto_reply_last_error = "Submitter email missing"
                lead.save(update_fields=["auto_reply_status", "auto_reply_last_error"])
                return

            try:
                validate_email(submitter_email)
            except ValidationError:
                lead.auto_reply_status = EmailStatus.FAILED
                lead.auto_reply_last_error = "Submitter email invalid"
                lead.save(update_fields=["auto_reply_status", "auto_reply_last_error"])
                return

            lead.auto_reply_status = EmailStatus.IN_PROGRESS
            lead.auto_reply_attempts += 1
            lead.save(update_fields=["auto_reply_status", "auto_reply_attempts"])
            attempt_count = lead.auto_reply_attempts
    except Lead.DoesNotExist:
        logger.warning(
            "Skipping auto reply: lead missing",
            extra={"lead_id": lead_id, "form_definition_id": form_definition_id},
        )
        return

    subject = form_definition.auto_reply_subject or "Thank you for contacting us"
    body = form_definition.auto_reply_body or form_definition.success_message

    name = lead.name or lead.form_data.get("name", "there")
    subject = _interpolate_name(subject, name)
    body = _interpolate_name(body, name)

    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@example.com"),
            recipient_list=[submitter_email],
            fail_silently=False,
        )
    except Exception as exc:
        error_message = str(exc)[:500]
        try:
            with transaction.atomic():
                lead = Lead.objects.select_for_update(nowait=False).get(id=lead_id)
                lead.auto_reply_last_error = error_message
                lead.auto_reply_status = (
                    EmailStatus.IN_PROGRESS
                    if self.request.retries < MAX_RETRIES
                    else EmailStatus.FAILED
                )
                lead.save(update_fields=["auto_reply_status", "auto_reply_last_error"])
        except Lead.DoesNotExist:
            logger.warning(
                "Auto reply lead missing during error update",
                extra={"lead_id": lead_id, "request_id": request_id or "-"},
            )
            return

        if self.request.retries < MAX_RETRIES:
            logger.warning(
                "Auto reply failed, will retry",
                extra={
                    "lead_id": lead_id,
                    "request_id": request_id or "-",
                    "attempt": attempt_count,
                },
            )
            raise

        logger.error(
            "Auto reply failed permanently",
            extra={
                "lead_id": lead_id,
                "request_id": request_id or "-",
                "attempts": attempt_count,
            },
        )
        return

    try:
        with transaction.atomic():
            lead = Lead.objects.select_for_update(nowait=True).get(id=lead_id)
            lead.auto_reply_status = EmailStatus.SENT
            lead.auto_reply_sent_at = timezone.now()
            lead.auto_reply_last_error = ""
            lead.save(
                update_fields=[
                    "auto_reply_status",
                    "auto_reply_sent_at",
                    "auto_reply_last_error",
                ]
            )
    except Lead.DoesNotExist:
        logger.warning(
            "Auto reply lead missing during success update",
            extra={"lead_id": lead_id, "request_id": request_id or "-"},
        )
        return

    logger.info(
        "Auto reply sent successfully",
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
def send_webhook(
    self,
    lead_id: int,
    form_definition_id: int,
    request_id: str | None = None,
) -> None:
    """
    Send webhook with form submission data.
    """
    from django.db import DatabaseError, transaction
    from sum_core.forms.models import FormDefinition
    from sum_core.leads.models import Lead, WebhookStatus

    set_sentry_context(
        request_id=request_id,
        lead_id=lead_id,
        task="send_form_webhook",
    )

    try:
        form_definition = FormDefinition.objects.get(id=form_definition_id)
    except FormDefinition.DoesNotExist:
        Lead.objects.filter(id=lead_id).update(
            form_webhook_status=WebhookStatus.FAILED,
            form_webhook_last_error="Form definition missing",
        )
        logger.warning(
            "Skipping webhook: form definition missing",
            extra={"lead_id": lead_id, "form_definition_id": form_definition_id},
        )
        return

    webhook_url = (form_definition.webhook_url or "").strip()
    url_valid = True
    url_error = ""
    if webhook_url:
        url_valid, url_error = _validate_webhook_url(webhook_url)

    attempt_count = 0
    try:
        with transaction.atomic():
            lead = Lead.objects.select_for_update(nowait=False).get(id=lead_id)

            if lead.form_webhook_status == WebhookStatus.SENT:
                logger.info(
                    "Form webhook already sent, skipping",
                    extra={"lead_id": lead_id, "request_id": request_id or "-"},
                )
                return

            if (
                lead.form_webhook_status == WebhookStatus.IN_PROGRESS
                and self.request.retries == 0
            ):
                logger.info(
                    "Form webhook already in progress, skipping",
                    extra={"lead_id": lead_id, "request_id": request_id or "-"},
                )
                return

            if lead.form_webhook_status == WebhookStatus.DISABLED:
                logger.info(
                    "Form webhook disabled, skipping",
                    extra={"lead_id": lead_id, "request_id": request_id or "-"},
                )
                return

            if not form_definition.webhook_enabled:
                lead.form_webhook_status = WebhookStatus.DISABLED
                lead.form_webhook_last_error = ""
                lead.save(
                    update_fields=[
                        "form_webhook_status",
                        "form_webhook_last_error",
                    ]
                )
                return

            if not webhook_url:
                lead.form_webhook_status = WebhookStatus.FAILED
                lead.form_webhook_last_error = "Webhook URL missing"
                lead.save(
                    update_fields=[
                        "form_webhook_status",
                        "form_webhook_last_error",
                    ]
                )
                return

            if not url_valid:
                lead.form_webhook_status = WebhookStatus.FAILED
                lead.form_webhook_last_error = url_error[:500]
                lead.form_webhook_last_status_code = None
                lead.save(
                    update_fields=[
                        "form_webhook_status",
                        "form_webhook_last_error",
                        "form_webhook_last_status_code",
                    ]
                )
                webhook_host = None
                try:
                    webhook_host = urlsplit(webhook_url).hostname
                except ValueError:
                    webhook_host = None
                logger.warning(
                    "Blocked webhook URL for security reasons",
                    extra={
                        "lead_id": lead_id,
                        "request_id": request_id or "-",
                        "webhook_host": webhook_host,
                    },
                )
                return

            lead.form_webhook_status = WebhookStatus.IN_PROGRESS
            lead.form_webhook_attempts += 1
            lead.save(update_fields=["form_webhook_status", "form_webhook_attempts"])
            attempt_count = lead.form_webhook_attempts
    except DatabaseError as exc:
        logger.warning(
            "Form webhook locked, will retry",
            extra={"lead_id": lead_id, "request_id": request_id or "-"},
        )
        raise self.retry(exc=exc)
    except Lead.DoesNotExist:
        logger.warning(
            "Skipping webhook: lead missing",
            extra={"lead_id": lead_id, "form_definition_id": form_definition_id},
        )
        return

    try:
        payload = _build_webhook_payload(lead, form_definition, request_id=request_id)
    except Exception as exc:
        error_message = f"Webhook payload build failed: {str(exc)[:500]}"
        try:
            with transaction.atomic():
                lead = Lead.objects.select_for_update(nowait=False).get(id=lead_id)
                lead.form_webhook_last_error = error_message
                lead.form_webhook_last_status_code = None
                lead.form_webhook_status = (
                    WebhookStatus.IN_PROGRESS
                    if self.request.retries < MAX_RETRIES
                    else WebhookStatus.FAILED
                )
                lead.save(
                    update_fields=[
                        "form_webhook_status",
                        "form_webhook_last_error",
                        "form_webhook_last_status_code",
                    ]
                )
        except Lead.DoesNotExist:
            logger.warning(
                "Form webhook lead missing during payload error update",
                extra={"lead_id": lead_id, "request_id": request_id or "-"},
            )
            return

        if self.request.retries < MAX_RETRIES:
            logger.warning(
                "Form webhook payload build failed, will retry",
                extra={
                    "lead_id": lead_id,
                    "request_id": request_id or "-",
                    "attempt": attempt_count,
                },
            )
            raise self.retry(exc=exc)

        logger.error(
            "Form webhook payload build failed permanently",
            extra={
                "lead_id": lead_id,
                "request_id": request_id or "-",
                "attempts": attempt_count,
            },
        )
        return

    webhook_secret = (form_definition.webhook_signing_secret or "").strip()
    body = _build_webhook_body(payload)
    headers = _build_webhook_headers(webhook_secret, body)

    try:
        response = requests.post(
            webhook_url,
            data=body,
            headers=headers,
            timeout=WEBHOOK_TIMEOUT,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        status_code = getattr(getattr(exc, "response", None), "status_code", None)
        error_message = str(exc)[:500]
        try:
            with transaction.atomic():
                lead = Lead.objects.select_for_update(nowait=False).get(id=lead_id)
                lead.form_webhook_last_error = error_message
                lead.form_webhook_last_status_code = status_code
                lead.form_webhook_status = (
                    WebhookStatus.IN_PROGRESS
                    if self.request.retries < MAX_RETRIES
                    else WebhookStatus.FAILED
                )
                lead.save(
                    update_fields=[
                        "form_webhook_status",
                        "form_webhook_last_error",
                        "form_webhook_last_status_code",
                    ]
                )
        except Lead.DoesNotExist:
            logger.warning(
                "Form webhook lead missing during error update",
                extra={"lead_id": lead_id, "request_id": request_id or "-"},
            )
            return

        if self.request.retries < MAX_RETRIES:
            logger.warning(
                "Form webhook failed, will retry",
                extra={
                    "lead_id": lead_id,
                    "request_id": request_id or "-",
                    "attempt": attempt_count,
                },
            )
            raise

        logger.error(
            "Form webhook failed permanently",
            extra={
                "lead_id": lead_id,
                "request_id": request_id or "-",
                "attempts": attempt_count,
            },
        )
        return

    try:
        with transaction.atomic():
            lead = Lead.objects.select_for_update(nowait=False).get(id=lead_id)
            lead.form_webhook_status = WebhookStatus.SENT
            lead.form_webhook_sent_at = timezone.now()
            lead.form_webhook_last_error = ""
            lead.form_webhook_last_status_code = response.status_code
            lead.save(
                update_fields=[
                    "form_webhook_status",
                    "form_webhook_sent_at",
                    "form_webhook_last_error",
                    "form_webhook_last_status_code",
                ]
            )
    except Lead.DoesNotExist:
        logger.warning(
            "Form webhook lead missing during success update",
            extra={"lead_id": lead_id, "request_id": request_id or "-"},
        )
        return

    logger.info(
        "Form webhook sent successfully",
        extra={"lead_id": lead_id, "request_id": request_id or "-"},
    )
