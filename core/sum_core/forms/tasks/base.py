"""
Shared utilities and constants for form async tasks.
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

from django.utils import timezone

if TYPE_CHECKING:
    from sum_core.forms.models import FormDefinition
    from sum_core.leads.models import Lead

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_BACKOFF = 60
WEBHOOK_TIMEOUT = 10
NAME_TOKEN = re.compile(r"{{\s*name\s*}}")
NAME_NEWLINE = re.compile(r"[\r\n]+")
NAME_CONTROL = re.compile(r"[\x00-\x1F\x7F]")
WEBHOOK_SIGNATURE_HEADER = "X-SUM-Webhook-Signature"


def parse_recipients(emails: str) -> list[str]:
    """Parse a comma-separated string of email addresses into a cleaned list. Invalid addresses are logged and ignored."""
    from django.core.exceptions import ValidationError
    from django.core.validators import validate_email

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


def resolve_webhook_host(
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


def validate_webhook_url(webhook_url: str) -> tuple[bool, str]:
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
        addresses = resolve_webhook_host(hostname)
        if not addresses:
            return False, "Webhook URL host could not be resolved"

    for address in addresses:
        if not address.is_global:
            return False, "Webhook URL resolves to a non-public IP"

    return True, ""


def build_webhook_payload(
    lead: Lead, form_definition: FormDefinition, request_id: str | None = None
) -> dict[str, object]:
    """Build the webhook payload for dynamic form submissions."""
    filtered_data = filter_webhook_data(
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


def filter_webhook_data(
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


def build_webhook_body(payload: dict[str, object]) -> str:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True)


def build_webhook_signature(secret: str, body: str) -> str:
    return hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()


def build_webhook_headers(secret: str, body: str) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if secret:
        signature = build_webhook_signature(secret, body)
        headers[WEBHOOK_SIGNATURE_HEADER] = f"sha256={signature}"
    return headers


def interpolate_name(template: str, name: str) -> str:
    """Replace the {{name}} placeholder with a sanitized name for plain text."""
    safe_name = NAME_NEWLINE.sub(" ", str(name or "")).strip()
    safe_name = NAME_CONTROL.sub("", safe_name)
    if len(safe_name) > 100:
        safe_name = safe_name[:100]
    return NAME_TOKEN.sub(safe_name, template)
