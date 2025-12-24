"""
Name: Branding Template Tags
Path: core/sum_core/branding/templatetags/branding_tags.py
Purpose: Exposes branding-related template tags, including access to SiteSettings and branding-driven CSS/font helpers.
Family: Used by Django templates to retrieve branding configuration and inject runtime styles.
Dependencies: Django template system, Wagtail Site and SiteSettings, Django cache.
"""

from __future__ import annotations

import colorsys
from collections.abc import Callable
from typing import Any
from urllib.parse import quote_plus

from django import template
from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest
from django.utils.html import SafeString, format_html
from django.utils.safestring import mark_safe
from sum_core.branding.models import SiteSettings
from wagtail.models import Site

register = template.Library()

FONT_FALLBACK_STACK = (
    'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
)


@register.simple_tag(takes_context=True)
def get_site_settings(context: dict[str, Any]) -> SiteSettings:
    """
    Return the SiteSettings for the current request/site.

    Caches per-request to avoid repeated DB hits.
    """

    request = context.get("request")
    if request is None or not isinstance(request, HttpRequest):
        raise ValueError(
            "get_site_settings requires 'request' in the template context."
        )

    cached_settings = getattr(request, "_site_settings_cache", None)
    if cached_settings is not None:
        return cached_settings

    site = Site.find_for_request(request)
    if site is None:
        site = Site.objects.get(is_default_site=True)

    site_settings = SiteSettings.for_site(site)
    request._site_settings_cache = site_settings
    return site_settings


def _format_font_value(font_name: str) -> str:
    family = font_name.strip()
    if not family:
        return ""
    return f'"{family}", {FONT_FALLBACK_STACK}'


def _hex_to_hsl(hex_value: str) -> tuple[int, int, int] | None:
    """
    Convert hex color to CSS HSL values (h=0-360, s=0-100, l=0-100).
    """
    hex_value = hex_value.lstrip("#")
    if len(hex_value) not in (3, 6):
        return None

    if len(hex_value) == 3:
        hex_value = "".join(c * 2 for c in hex_value)

    try:
        r, g, b = (int(hex_value[i : i + 2], 16) / 255.0 for i in (0, 2, 4))
        hue, lightness, saturation = colorsys.rgb_to_hls(r, g, b)
        return round(hue * 360), round(saturation * 100), round(lightness * 100)
    except (ValueError, IndexError):
        return None


def _build_css_variables(site_settings: SiteSettings) -> list[str]:
    variables: list[str] = []

    # Inject HSL variables from Primary Color
    if site_settings.primary_color:
        hsl = _hex_to_hsl(site_settings.primary_color)
        if hsl:
            hue, saturation, lightness = hsl
            variables.extend(
                [
                    f"    --brand-h: {hue};",
                    f"    --brand-s: {saturation}%;",
                    f"    --brand-l: {lightness}%;",
                ]
            )
        else:
            # Fallback if invalid hex, let CSS defaults handle it
            pass

    # If no primary color set, we do NOT inject defaults here.
    # We rely on main.css :root variables to provide the default "Gold" theme.

    # -------------------------------------------------------------------------
    # 2) Secondary Colour
    # -------------------------------------------------------------------------
    if site_settings.secondary_color:
        variables.append(
            f"    --color-secondary-custom: {site_settings.secondary_color};"
        )
        secondary_hsl = _hex_to_hsl(site_settings.secondary_color)
        if secondary_hsl:
            variables.extend(
                [
                    f"    --secondary-h: {secondary_hsl[0]};",
                    f"    --secondary-s: {secondary_hsl[1]}%;",
                    f"    --secondary-l: {secondary_hsl[2]}%;",
                ]
            )

    # -------------------------------------------------------------------------
    # 3) Accent Colour
    # -------------------------------------------------------------------------
    if site_settings.accent_color:
        variables.append(f"    --color-accent-custom: {site_settings.accent_color};")
        accent_hsl = _hex_to_hsl(site_settings.accent_color)
        if accent_hsl:
            variables.extend(
                [
                    f"    --accent-h: {accent_hsl[0]};",
                    f"    --accent-s: {accent_hsl[1]}%;",
                    f"    --accent-l: {accent_hsl[2]}%;",
                ]
            )

    # -------------------------------------------------------------------------
    # 4) Semantic Neutrals (Background, Text, Surface)
    #    Output HSL components if configured, enabling full theme overrides.
    # -------------------------------------------------------------------------

    if site_settings.background_color:
        bg_hsl = _hex_to_hsl(site_settings.background_color)
        if bg_hsl:
            variables.extend(
                [
                    f"    --background-h: {bg_hsl[0]};",
                    f"    --background-s: {bg_hsl[1]}%;",
                    f"    --background-l: {bg_hsl[2]}%;",
                ]
            )

    if site_settings.text_color:
        txt_hsl = _hex_to_hsl(site_settings.text_color)
        if txt_hsl:
            variables.extend(
                [
                    f"    --text-h: {txt_hsl[0]};",
                    f"    --text-s: {txt_hsl[1]}%;",
                    f"    --text-l: {txt_hsl[2]}%;",
                ]
            )

    if site_settings.surface_color:
        surf_hsl = _hex_to_hsl(site_settings.surface_color)
        if surf_hsl:
            variables.extend(
                [
                    f"    --surface-h: {surf_hsl[0]};",
                    f"    --surface-s: {surf_hsl[1]}%;",
                    f"    --surface-l: {surf_hsl[2]}%;",
                ]
            )

    heading_font = _format_font_value(site_settings.heading_font)
    if heading_font:
        variables.append(f"    --font-heading: {heading_font};")

    body_font = _format_font_value(site_settings.body_font)
    if body_font:
        variables.append(f"    --font-body: {body_font};")

    return variables


def _cacheable_response(cache_key: str, build: Callable[[], SafeString]) -> SafeString:
    if settings.DEBUG:
        return build()

    cached = cache.get(cache_key)
    if cached:
        return cached

    rendered = build()
    cache.set(cache_key, rendered, timeout=None)
    return rendered


@register.simple_tag(takes_context=True)
def branding_css(context: dict[str, Any]) -> SafeString:
    """
    Emit a <style> block with CSS variables sourced from SiteSettings.

    In development, the output is regenerated on every call.
    In production, the output is cached per site and invalidated on settings changes.
    """

    site_settings = get_site_settings(context)
    cache_key = f"branding_css:{site_settings.site_id}"

    def build() -> SafeString:
        variables = _build_css_variables(site_settings)
        css_lines = [":root {", *variables, "}"]
        css = mark_safe("\n".join(css_lines))
        return format_html('<style id="branding-css">\n{}\n</style>', css)

    return _cacheable_response(cache_key, build)


def _unique_fonts(site_settings: SiteSettings) -> list[str]:
    fonts = []
    for font in (site_settings.heading_font, site_settings.body_font):
        cleaned = font.strip() if font else ""
        if cleaned and cleaned not in fonts:
            fonts.append(cleaned)

    # If no fonts configured, fallback to the design system defaults
    if not fonts:
        return ["Fraunces", "Manrope"]

    return fonts


@register.simple_tag(takes_context=True)
def branding_fonts(context: dict[str, Any]) -> SafeString:
    """
    Emit Google Fonts <link> tags for configured heading/body fonts.

    In development, the output is regenerated on every call.
    In production, the output is cached per site and invalidated on settings changes.
    """

    site_settings = get_site_settings(context)
    cache_key = f"branding_fonts:{site_settings.site_id}"

    def build() -> SafeString:
        fonts = _unique_fonts(site_settings)
        if not fonts:
            return ""

        families = "&".join(
            f"family={quote_plus(font)}:wght@300;400;500;600;700" for font in fonts
        )
        href = f"https://fonts.googleapis.com/css2?{families}&display=swap"

        links = [
            '<link rel="preconnect" href="https://fonts.googleapis.com">',
            '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>',
            f'<link rel="stylesheet" href="{href}">',
        ]

        return mark_safe("\n".join(links))

    return _cacheable_response(cache_key, build)
