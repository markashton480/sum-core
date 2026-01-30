"""
Form async tasks package - re-exports for backwards compatibility.
"""

from .base import (
    MAX_RETRIES,
    NAME_CONTROL,
    NAME_NEWLINE,
    NAME_TOKEN,
    RETRY_BACKOFF,
    WEBHOOK_SIGNATURE_HEADER,
    WEBHOOK_TIMEOUT,
    build_webhook_body,
    build_webhook_headers,
    build_webhook_payload,
    build_webhook_signature,
    filter_webhook_data,
    interpolate_name,
    parse_recipients,
    resolve_webhook_host,
    validate_webhook_url,
)
from .email import send_auto_reply, send_form_notification
from .webhook import send_webhook

# Backwards compatibility: underscore-prefixed aliases for external imports
_build_webhook_body = build_webhook_body
_build_webhook_headers = build_webhook_headers
_build_webhook_payload = build_webhook_payload
_build_webhook_signature = build_webhook_signature
_filter_webhook_data = filter_webhook_data
_interpolate_name = interpolate_name
_parse_recipients = parse_recipients
_resolve_webhook_host = resolve_webhook_host
_validate_webhook_url = validate_webhook_url

__all__ = [
    "MAX_RETRIES",
    "NAME_CONTROL",
    "NAME_NEWLINE",
    "NAME_TOKEN",
    "RETRY_BACKOFF",
    "WEBHOOK_SIGNATURE_HEADER",
    "WEBHOOK_TIMEOUT",
    "_build_webhook_body",
    "_build_webhook_headers",
    "_build_webhook_payload",
    "_build_webhook_signature",
    "_filter_webhook_data",
    "_interpolate_name",
    "_parse_recipients",
    "_resolve_webhook_host",
    "_validate_webhook_url",
    "build_webhook_body",
    "build_webhook_headers",
    "build_webhook_payload",
    "build_webhook_signature",
    "filter_webhook_data",
    "interpolate_name",
    "parse_recipients",
    "resolve_webhook_host",
    "send_auto_reply",
    "send_form_notification",
    "send_webhook",
    "validate_webhook_url",
]
