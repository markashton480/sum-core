"""
Name: Banner Template Tags
Path: core/sum_core/banners/templatetags/banner_tags.py
Purpose: Provide template tags for alert banners.
"""

from __future__ import annotations

import hashlib
from urllib.parse import unquote

from django import template
from django.db.models import F
from sum_core.banners.models import AlertBanner

register = template.Library()

BANNER_DISMISS_COOKIE = "sum_alert_banner_dismissed"


@register.simple_tag
def get_active_banner() -> AlertBanner | None:
    """
    Return the currently active alert banner, if any.
    """

    return (
        AlertBanner.objects.active()
        .order_by(F("start_date").desc(nulls_last=True), "-id")
        .first()
    )


def _decode_cookie(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        return unquote(value)
    except (ValueError, UnicodeDecodeError):
        return value


@register.simple_tag
def get_banner_identifier(
    active_banner: AlertBanner | None = None,
    fallback_message: str = "",
) -> str:
    """Return a stable identifier for the current banner."""
    banner_id = getattr(active_banner, "id", None)
    if banner_id:
        digest_source = "|".join(
            [
                str(getattr(active_banner, "message", "")),
                str(getattr(active_banner, "link_text", "")),
                str(getattr(active_banner, "link_url", "")),
                str(getattr(active_banner, "background_color", "")),
                str(getattr(active_banner, "dismissible", "")),
            ]
        )
        digest = hashlib.sha256(digest_source.encode("utf-8")).hexdigest()[:12]
        return f"alert:{banner_id}:{digest}"

    if fallback_message:
        digest = hashlib.sha256(fallback_message.encode("utf-8")).hexdigest()[:12]
        return f"message:{digest}"

    return ""


@register.simple_tag(takes_context=True)
def banner_is_dismissed(context, banner_identifier: str) -> bool:
    """Return True when the request cookie matches the current banner."""
    if not banner_identifier:
        return False
    request = context.get("request")
    if request is None:
        return False
    dismissed = _decode_cookie(request.COOKIES.get(BANNER_DISMISS_COOKIE))
    return dismissed == banner_identifier
