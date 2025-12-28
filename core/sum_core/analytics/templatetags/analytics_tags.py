"""
Name: Analytics Tags
Path: core/sum_core/analytics/templatetags/analytics_tags.py
Purpose: Template tags for injecting GA4/GTM scripts based on SiteSettings.
Family: Analytics
Dependencies: SiteSettings, Django templates
"""

from django import template
from django.utils.html import json_script
from sum_core.branding.models import SiteSettings

register = template.Library()


@register.simple_tag(takes_context=True)
def analytics_head(context):
    """
    Emits analytics configuration data for client-side loading.
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
        config = {
            "gtm_container_id": gtm_id,
            "ga_measurement_id": "",
            "cookie_banner_enabled": settings.cookie_banner_enabled,
        }
    elif ga4_id:
        config = {
            "gtm_container_id": "",
            "ga_measurement_id": ga4_id,
            "cookie_banner_enabled": settings.cookie_banner_enabled,
        }
    else:
        return ""

    return json_script(config, "sum-analytics-config")


@register.simple_tag(takes_context=True)
def analytics_body(context):
    """
    Reserved for future analytics markup (kept for template compatibility).
    """
    return ""
