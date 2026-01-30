"""
Name: Sticky CTA Navigation Template Tags
Path: core/sum_core/navigation/templatetags/sticky_cta_tags.py
Purpose: Template tags for rendering mobile and desktop sticky CTA bars.
Family: Navigation System (Phase 1: Foundation)
Dependencies: django.template, sum_core.navigation
"""

from __future__ import annotations

from typing import Any

from sum_core.navigation.services import (
    get_effective_desktop_sticky_cta,
    get_effective_header_settings,
)
from sum_core.utils.contact import normalize_phone_href
from wagtail.models import Site

from .utils import (
    cache_get_or_build,
    extract_cta_link,
    get_current_page,
    make_cache_key,
)


def sticky_cta(context: dict[str, Any]) -> dict[str, Any]:
    """
    Return sticky CTA (mobile) context dict.

    Context keys:
        - enabled: bool (mobile_cta_enabled)
        - phone_enabled: bool
        - phone_number: str
        - phone_href: str
        - button_enabled: bool
        - button_text: str
        - button_href: str
        - button_attrs: dict
        - label: str
        - compact_label: str

    Usage:
        {% load navigation_tags %}
        {% sticky_cta as cta %}
        {% if cta.enabled %}...{% endif %}
    """
    request = context.get("request")
    if request is None:
        return {}

    site = Site.find_for_request(request)
    if site is None:
        return {}

    cache_key = make_cache_key("sticky", site.id)

    def build() -> dict[str, Any]:
        header_settings = get_effective_header_settings(site)

        phone_number = header_settings.phone_number or ""
        phone_href = normalize_phone_href(phone_number)

        button_link_data = extract_cta_link(header_settings.mobile_cta_button.link)

        return {
            "enabled": header_settings.mobile_cta_enabled,
            "phone_enabled": header_settings.mobile_cta_phone_enabled,
            "phone_number": phone_number,
            "phone_href": phone_href,
            "button_enabled": header_settings.mobile_cta_button.enabled,
            "button_text": header_settings.mobile_cta_button.text,
            "button_href": button_link_data["href"] if button_link_data else "#",
            "button_attrs": button_link_data["attrs"] if button_link_data else {},
            "label": header_settings.mobile_cta_label,
            "compact_label": header_settings.mobile_cta_label_compact,
        }

    return cache_get_or_build(cache_key, build)


def desktop_sticky_cta(context: dict[str, Any]) -> dict[str, Any]:
    """
    Return desktop sticky CTA context dict.

    Context keys:
        - enabled: bool
        - label: str
        - button_text: str
        - button_href: str
        - button_attrs: dict
    """
    request = context.get("request")
    if request is None:
        return {}

    site = Site.find_for_request(request)
    if site is None:
        return {}

    page = get_current_page(context)
    resolved = get_effective_desktop_sticky_cta(site, page=page)
    snippet = resolved.snippet
    if not resolved.enabled or snippet is None:
        return {"enabled": False}

    button_link_data = extract_cta_link(snippet.button_link)

    return {
        "enabled": True,
        "label": snippet.label or "",
        "button_text": snippet.button_text or "",
        "button_href": button_link_data["href"] if button_link_data else "#",
        "button_attrs": button_link_data["attrs"] if button_link_data else {},
    }
