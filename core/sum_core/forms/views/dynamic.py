"""
Name: Dynamic form submission handler
Path: core/sum_core/forms/views/dynamic.py
Purpose: Handle dynamic FormDefinition-based form submissions.
Family: Forms, Leads, Attribution, Notifications, Webhooks.
Dependencies: FormDefinition, DynamicFormGenerator, Lead service, SpamChecks.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from django.core.cache import cache
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest, JsonResponse
from django.utils.text import get_valid_filename
from sum_core.forms.cache import (
    FORM_DEFINITION_CACHE_TTL_SECONDS,
    ensure_form_definition_cache_version,
    get_form_definition_cache_key,
    get_form_definition_cache_version,
)
from sum_core.forms.dynamic import DynamicFormGenerator
from sum_core.forms.models import FormDefinition
from sum_core.forms.services import run_spam_checks
from sum_core.forms.views.base import (
    build_attribution_data,
    format_form_errors,
    get_config,
    spam_response,
)
from sum_core.leads.services import create_lead_from_submission
from sum_core.ops.request_utils import get_client_ip
from wagtail.models import Site

if TYPE_CHECKING:
    from sum_core.leads.models import Lead

logger = logging.getLogger(__name__)


def handle_dynamic_form_submission(
    request: HttpRequest, data: dict[str, Any], site: Site
) -> JsonResponse:
    """Process dynamic form submissions from FormDefinition."""
    form_definition_id = data.get("form_definition_id")
    form_definition = get_form_definition(form_definition_id, site)
    if form_definition is None:
        return JsonResponse(
            {
                "success": False,
                "errors": {"__all__": ["Form definition not found"]},
            },
            status=400,
        )

    if not form_definition.is_active:
        return JsonResponse(
            {"success": False, "errors": {"__all__": ["Form is inactive"]}},
            status=400,
        )

    config = get_config(site)
    spam_result = run_spam_checks(
        form_data=data,
        ip_address=get_client_ip(request),
        site_id=site.id,
        time_token=data.get("_time_token", ""),
        honeypot_field_name="website",
        rate_limit_per_hour=config.rate_limit_per_ip_per_hour,
        min_seconds_to_submit=config.min_seconds_to_submit,
    )
    response = spam_response(spam_result, request)
    if response:
        return response

    form_class = DynamicFormGenerator(form_definition).generate_form_class()
    form = form_class(data=data, files=request.FILES)

    if not form.is_valid():
        return JsonResponse(
            {"success": False, "errors": format_form_errors(form)},
            status=400,
        )

    lead_values, lead_field_names, lead_field_errors = resolve_dynamic_lead_fields(
        form_definition, form.cleaned_data
    )
    if lead_field_errors:
        return JsonResponse(
            {"success": False, "errors": lead_field_errors},
            status=400,
        )

    form_data = build_dynamic_form_data(
        form, form_definition, request, lead_field_names=lead_field_names
    )
    attribution = build_attribution_data(data, request)

    try:
        lead = create_lead_from_submission(
            name=lead_values["name"],
            email=lead_values["email"],
            message=lead_values["message"],
            form_type=form_definition.slug,
            phone=form.cleaned_data.get("phone"),
            form_data=form_data or None,
            attribution=attribution,
        )
    except ValueError:
        cleanup_uploaded_files(form_data)
        logger.warning("Lead creation failed for dynamic form", exc_info=True)
        return JsonResponse(
            {
                "success": False,
                "errors": {
                    "__all__": ["Unable to process submission. Please try again."]
                },
            },
            status=400,
        )

    from sum_core.forms.views.static import queue_static_notification_tasks

    queue_static_notification_tasks(lead, site.id, request)
    queue_dynamic_form_tasks(lead, form_definition, request)

    return JsonResponse(
        {
            "success": True,
            "message": form_definition.success_message
            or "Thank you for your submission!",
            "lead_id": lead.id,
        },
        status=200,
    )


def _resolve_lead_field_name(
    form_definition: FormDefinition,
    cleaned_data: dict[str, Any],
    *,
    target_name: str,
    block_types: set[str],
    label: str,
) -> tuple[str | None, str | None]:
    if target_name in cleaned_data:
        return target_name, None

    candidates: list[str] = []
    for block in form_definition.fields:
        if block.block_type in block_types:
            field_name = block.value.get("field_name")
            if field_name:
                candidates.append(field_name)

    name_counts: dict[str, int] = {}
    for name in candidates:
        name_counts[name] = name_counts.get(name, 0) + 1

    unique_candidates = list(name_counts.keys())

    if not unique_candidates:
        return (
            None,
            f"{label} field is required. Add a {label.lower()} field named "
            f"'{target_name}'.",
        )
    if len(unique_candidates) == 1 and name_counts[unique_candidates[0]] == 1:
        return unique_candidates[0], None
    return (
        None,
        f"Multiple {label.lower()} fields found. Rename the primary field to "
        f"'{target_name}'.",
    )


def resolve_dynamic_lead_fields(
    form_definition: FormDefinition, cleaned_data: dict[str, Any]
) -> tuple[dict[str, str], dict[str, str], dict[str, list[str]]]:
    """Resolve lead fields from dynamic form data with safe defaults."""
    lead_values: dict[str, str] = {}
    lead_field_names: dict[str, str] = {}
    errors: dict[str, list[str]] = {}

    required_specs = [
        ("name", {"text_input"}, "Name"),
        ("email", {"email_input"}, "Email"),
        ("message", {"textarea"}, "Message"),
    ]

    for target_name, block_types, label in required_specs:
        field_name, config_error = _resolve_lead_field_name(
            form_definition,
            cleaned_data,
            target_name=target_name,
            block_types=block_types,
            label=label,
        )
        if config_error:
            errors[target_name] = [config_error]
            continue

        assert field_name is not None, (
            "Expected field_name to be resolved when config_error is falsy. "
            "This indicates an internal configuration error in FormDefinition."
        )
        value = cleaned_data.get(field_name, "")
        if not str(value).strip():
            errors[target_name] = [f"{label} is required"]
            continue

        lead_values[target_name] = str(value).strip()
        lead_field_names[target_name] = field_name or target_name

    return lead_values, lead_field_names, errors


def validate_dynamic_lead_fields(
    cleaned_data: dict[str, Any], form_definition: FormDefinition | None = None
) -> dict[str, list[str]]:
    """
    Backwards-compatible wrapper for dynamic lead field validation.

    If form_definition is not provided, returns no errors.
    """
    if form_definition is None:
        return {}
    _lead_values, _lead_field_names, errors = resolve_dynamic_lead_fields(
        form_definition, cleaned_data
    )
    return errors


def build_dynamic_form_data(
    form,
    form_definition: FormDefinition,
    request: HttpRequest,
    *,
    lead_field_names: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Extract non-core dynamic fields, persisting uploads to storage."""
    standard_fields = {"name", "email", "message", "phone"}
    if lead_field_names:
        standard_fields.update(lead_field_names.values())
    data: dict[str, Any] = {}
    for field_name, value in form.cleaned_data.items():
        if field_name in standard_fields:
            continue
        if isinstance(value, UploadedFile):
            data[field_name] = store_uploaded_file(value, form_definition, field_name)
        else:
            data[field_name] = value

    data["ip_address"] = get_client_ip(request)
    return data


def store_uploaded_file(
    uploaded_file: UploadedFile,
    form_definition: FormDefinition,
    field_name: str,
) -> dict[str, Any]:
    """Save uploaded file to storage and return metadata for form_data."""
    safe_name = get_valid_filename(uploaded_file.name or "upload")
    safe_form_slug = get_valid_filename(str(form_definition.slug))
    safe_field_name = get_valid_filename(field_name)
    unique_name = f"{uuid4().hex}_{safe_name}"
    path = f"forms/{safe_form_slug}/{safe_field_name}/{unique_name}"
    saved_path = default_storage.save(path, uploaded_file)
    return {
        "name": uploaded_file.name,
        "path": saved_path,
        "size": uploaded_file.size,
        "content_type": uploaded_file.content_type,
    }


def cleanup_uploaded_files(form_data: dict[str, Any]) -> None:
    """Delete any uploaded files from storage when lead creation fails."""
    for field_name, value in form_data.items():
        if isinstance(value, dict) and "path" in value:
            file_path = value["path"]
            try:
                if default_storage.exists(file_path):
                    default_storage.delete(file_path)
            except Exception:
                logger.warning(
                    f"Failed to cleanup orphaned file: {file_path}",
                    exc_info=True,
                )


def get_form_definition(
    form_definition_id: str | None, site: Site
) -> FormDefinition | None:
    """Fetch a form definition for the current site."""
    if not form_definition_id:
        return None
    try:
        form_definition_pk = int(form_definition_id)
    except (TypeError, ValueError):
        return None
    version = get_form_definition_cache_version(site.pk, form_definition_pk)
    if version:
        cache_key = get_form_definition_cache_key(site.pk, form_definition_pk, version)
        form_definition = cache.get(cache_key)
        if form_definition is not None:
            return form_definition

    form_definition = (
        FormDefinition.objects.select_related("site")
        .filter(pk=form_definition_pk, site=site)
        .first()
    )
    if form_definition is not None:
        version = ensure_form_definition_cache_version(site.pk, form_definition_pk)
        cache_key = get_form_definition_cache_key(site.pk, form_definition_pk, version)
        cache.set(
            cache_key,
            form_definition,
            timeout=FORM_DEFINITION_CACHE_TTL_SECONDS,
        )
    return form_definition


def queue_dynamic_form_tasks(
    lead: Lead, form_definition: FormDefinition, request: HttpRequest
) -> None:
    """Queue async tasks for dynamic form notifications and webhooks."""
    from sum_core.forms.tasks import (
        send_auto_reply,
        send_form_notification,
        send_webhook,
    )
    from sum_core.leads.models import EmailStatus, WebhookStatus

    request_id = getattr(request, "request_id", None)
    update_fields: list[str] = []

    queue_form_notification = False
    if form_definition.email_notification_enabled:
        if form_definition.notification_emails.strip():
            lead.form_notification_status = EmailStatus.PENDING
            lead.form_notification_last_error = ""
            update_fields.extend(
                ["form_notification_status", "form_notification_last_error"]
            )
            queue_form_notification = True
        else:
            lead.form_notification_status = EmailStatus.FAILED
            lead.form_notification_last_error = "No notification recipients configured"
            update_fields.extend(
                ["form_notification_status", "form_notification_last_error"]
            )
    else:
        lead.form_notification_status = EmailStatus.DISABLED
        lead.form_notification_last_error = ""
        update_fields.extend(
            ["form_notification_status", "form_notification_last_error"]
        )

    submitter_email = (lead.email or lead.form_data.get("email") or "").strip()
    queue_auto_reply = False
    if form_definition.auto_reply_enabled:
        if submitter_email:
            lead.auto_reply_status = EmailStatus.PENDING
            lead.auto_reply_last_error = ""
            update_fields.extend(["auto_reply_status", "auto_reply_last_error"])
            queue_auto_reply = True
        else:
            lead.auto_reply_status = EmailStatus.FAILED
            lead.auto_reply_last_error = "Submitter email missing"
            update_fields.extend(["auto_reply_status", "auto_reply_last_error"])
    else:
        lead.auto_reply_status = EmailStatus.DISABLED
        lead.auto_reply_last_error = ""
        update_fields.extend(["auto_reply_status", "auto_reply_last_error"])

    queue_webhook = False
    if form_definition.webhook_enabled:
        if form_definition.webhook_url:
            lead.form_webhook_status = WebhookStatus.PENDING
            lead.form_webhook_last_error = ""
            update_fields.extend(["form_webhook_status", "form_webhook_last_error"])
            queue_webhook = True
        else:
            lead.form_webhook_status = WebhookStatus.FAILED
            lead.form_webhook_last_error = "Webhook URL missing"
            update_fields.extend(["form_webhook_status", "form_webhook_last_error"])
    else:
        lead.form_webhook_status = WebhookStatus.DISABLED
        lead.form_webhook_last_error = ""
        update_fields.extend(["form_webhook_status", "form_webhook_last_error"])

    if update_fields:
        lead.save(update_fields=sorted(set(update_fields)))

    if queue_form_notification:
        try:
            send_form_notification.delay(
                lead.id, form_definition.id, request_id=request_id
            )
        except Exception as exc:
            logger.exception(
                "Failed to queue form notification task",
                extra={
                    "lead_id": lead.id,
                    "form_definition_id": form_definition.id,
                },
            )
            lead.form_notification_status = EmailStatus.FAILED
            lead.form_notification_last_error = (
                f"Failed to queue task: {str(exc)[:500]}"
            )
            lead.save(
                update_fields=[
                    "form_notification_status",
                    "form_notification_last_error",
                ]
            )

    if queue_auto_reply:
        try:
            send_auto_reply.delay(lead.id, form_definition.id, request_id=request_id)
        except Exception as exc:
            logger.exception(
                "Failed to queue auto reply task",
                extra={
                    "lead_id": lead.id,
                    "form_definition_id": form_definition.id,
                },
            )
            lead.auto_reply_status = EmailStatus.FAILED
            lead.auto_reply_last_error = f"Failed to queue task: {str(exc)[:500]}"
            lead.save(update_fields=["auto_reply_status", "auto_reply_last_error"])

    if queue_webhook:
        try:
            send_webhook.delay(lead.id, form_definition.id, request_id=request_id)
        except Exception as exc:
            logger.exception(
                "Failed to queue form webhook task",
                extra={
                    "lead_id": lead.id,
                    "form_definition_id": form_definition.id,
                },
            )
            lead.form_webhook_status = WebhookStatus.FAILED
            lead.form_webhook_last_error = f"Failed to queue task: {str(exc)[:500]}"
            lead.save(update_fields=["form_webhook_status", "form_webhook_last_error"])
