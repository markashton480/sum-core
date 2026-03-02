"""
Name: Image Delivery Template Tags
Path: core/sum_core/templatetags/image_delivery_tags.py
Purpose: Render responsive picture markup and fallback URLs from shared profiles.
Family: sum_core templates.
Dependencies: Django template library, image delivery services.
"""

from __future__ import annotations

from typing import Any

from django import template
from django.template.defaultfilters import striptags
from django.utils.html import conditional_escape, format_html
from django.utils.safestring import SafeString, mark_safe
from sum_core.images.services import build_responsive_payload, resolve_fallback_url

register = template.Library()


def _render_attrs(attrs: dict[str, Any]) -> SafeString:
    rendered: list[str] = []
    for key, value in attrs.items():
        if value in (None, ""):
            continue
        rendered.append(f'{key}="{conditional_escape(value)}"')
    return mark_safe(" ".join(rendered))


@register.simple_tag
def responsive_picture(image: Any, profile: str, alt: str = "", **kwargs) -> SafeString:
    """
    Render responsive image markup for a configured profile.

    Usage:
      {% responsive_picture image "card_landscape" alt=item.alt_text class="foo" %}
    """
    if image is None:
        return mark_safe("")

    payload = build_responsive_payload(image, str(profile))

    class_name = kwargs.get("class", "")
    loading = kwargs.get("loading") or payload.loading
    fetchpriority = kwargs.get("fetchpriority") or payload.fetchpriority
    decoding = kwargs.get("decoding", "async")

    image_alt = str(alt or getattr(image, "title", ""))

    img_attrs = {
        "src": payload.fallback_src,
        "alt": striptags(image_alt),
        "class": class_name,
        "loading": loading,
        "fetchpriority": fetchpriority,
        "decoding": decoding,
        "width": payload.fallback_width,
        "height": payload.fallback_height,
    }

    if payload.fallback_srcset:
        img_attrs["srcset"] = payload.fallback_srcset
        img_attrs["sizes"] = payload.sizes

    img_html = format_html("<img {}>", _render_attrs(img_attrs))

    if not payload.webp_srcset:
        return img_html

    source_attrs = {
        "type": "image/webp",
        "srcset": payload.webp_srcset,
        "sizes": payload.sizes,
    }
    source_html = format_html("<source {}>", _render_attrs(source_attrs))

    return format_html("<picture>{}{}</picture>", source_html, img_html)


@register.simple_tag
def responsive_img_url(image: Any, profile: str) -> str:
    """Resolve the best fallback URL for contexts that need a plain URL."""
    if image is None:
        return ""
    return resolve_fallback_url(image, str(profile))
