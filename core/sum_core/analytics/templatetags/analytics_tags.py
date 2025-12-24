"""
Name: Analytics Tags
Path: core/sum_core/analytics/templatetags/analytics_tags.py
Purpose: Template tags for injecting GA4/GTM scripts based on SiteSettings.
Family: Analytics
Dependencies: SiteSettings, Django templates
"""

from django import template
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from sum_core.branding.models import SiteSettings

register = template.Library()


@register.simple_tag(takes_context=True)
def analytics_head(context):
    """
    Renders the appropriate analytics script for the <head> section.
    Priority:
    1. GTM (if gtm_container_id is set)
    2. GA4 (if ga_measurement_id is set)
    3. None
    """
    request = context.get("request")
    if not request:
        return ""

    settings = SiteSettings.for_request(request)
    gtm_id = getattr(settings, "gtm_container_id", "").strip()
    ga4_id = getattr(settings, "ga_measurement_id", "").strip()

    if gtm_id:
        return mark_safe(
            render_to_string(
                "sum_core/includes/analytics/gtm_head.html",
                {"gtm_container_id": gtm_id},
            )
        )
    elif ga4_id:
        return mark_safe(
            render_to_string(
                "sum_core/includes/analytics/ga4_head.html",
                {"ga_measurement_id": ga4_id},
            )
        )

    return ""


@register.simple_tag(takes_context=True)
def analytics_body(context):
    """
    Renders the appropriate analytics script for the start of <body>.
    Only renders GTM noscript fallback if GTM is active.
    """
    request = context.get("request")
    if not request:
        return ""

    settings = SiteSettings.for_request(request)
    gtm_id = getattr(settings, "gtm_container_id", "").strip()

    if gtm_id:
        return mark_safe(
            render_to_string(
                "sum_core/includes/analytics/gtm_body.html",
                {"gtm_container_id": gtm_id},
            )
        )

    return ""
