"""
Webhook delivery tasks for dynamic forms.
"""

from __future__ import annotations

import logging
from urllib.parse import urlsplit

import requests
from celery import shared_task
from django.utils import timezone
from sum_core.ops.sentry import set_sentry_context

from .base import (
    MAX_RETRIES,
    RETRY_BACKOFF,
    WEBHOOK_TIMEOUT,
    build_webhook_body,
    build_webhook_headers,
    build_webhook_payload,
    validate_webhook_url,
)

logger = logging.getLogger(__name__)


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
    """Send webhook with form submission data."""
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
        url_valid, url_error = validate_webhook_url(webhook_url)

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
        payload = build_webhook_payload(lead, form_definition, request_id=request_id)
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
    body = build_webhook_body(payload)
    headers = build_webhook_headers(webhook_secret, body)

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
