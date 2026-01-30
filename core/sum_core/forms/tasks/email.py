"""
Email notification tasks for dynamic forms.
"""

from __future__ import annotations

import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from sum_core.ops.sentry import set_sentry_context

from .base import MAX_RETRIES, RETRY_BACKOFF, interpolate_name, parse_recipients

logger = logging.getLogger(__name__)


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
    """Send email notification to admin recipients when a dynamic form is submitted."""
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

    recipients = parse_recipients(form_definition.notification_emails)

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
    """Send auto-reply email to the submitter."""
    from django.core.exceptions import ValidationError
    from django.core.validators import validate_email
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
    subject = interpolate_name(subject, name)
    body = interpolate_name(body, name)

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
