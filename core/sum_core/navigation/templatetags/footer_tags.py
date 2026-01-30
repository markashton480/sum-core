"""
Name: Footer Navigation Template Tags
Path: core/sum_core/navigation/templatetags/footer_tags.py
Purpose: Template tag for rendering footer navigation with social and business info.
Family: Navigation System (Phase 1: Foundation)
Dependencies: django.template, sum_core.navigation
"""

from __future__ import annotations

import copy
from typing import Any

from django.conf import settings
from django.utils import timezone
from sum_core.navigation.models import FooterNavigation
from sum_core.navigation.services import get_effective_footer_settings
from wagtail.models import Site

from .utils import (
    cache_get_or_build,
    extract_link_data,
    make_cache_key,
    render_footer_copyright,
)


def footer_nav(context: dict[str, Any]) -> dict[str, Any]:
    """
    Return footer navigation context dict.

    Context keys:
        - tagline: str
        - link_sections: list of section dicts (title, links)
        - social: dict with facebook/instagram/linkedin/youtube/x/tiktok keys
        - business: dict with company_name, phone_number, email, address
        - copyright: dict with raw and rendered keys

    Copyright placeholders:
        - {year} -> current year
        - {company_name} -> effective company name

    Usage:
        {% load navigation_tags %}
        {% footer_nav as footer %}
        {{ footer.copyright.rendered }}
    """
    request = context.get("request")
    if request is None:
        return {}

    site = Site.find_for_request(request)
    if site is None:
        return {}

    cache_key = make_cache_key("footer", site.id)

    def build() -> dict[str, Any]:
        footer_settings = get_effective_footer_settings(site)
        footer_nav_model = FooterNavigation.for_site(site)

        link_sections = []
        if footer_nav_model.link_sections:
            for section_block in footer_nav_model.link_sections:
                section_value = (
                    section_block.value
                    if hasattr(section_block, "value")
                    else section_block
                )
                title = section_value.get("title", "")
                links_data = []

                for link_item in section_value.get("links", []):
                    link_value = (
                        link_item.value if hasattr(link_item, "value") else link_item
                    )
                    link_data = extract_link_data(link_value)
                    links_data.append(
                        {
                            "label": link_data["text"],
                            "text": link_data["text"],
                            "href": link_data["href"],
                            "is_external": link_data["is_external"],
                            "opens_new_tab": link_data["opens_new_tab"],
                            "attrs": link_data["attrs"],
                            "attrs_str": link_data["attrs_str"],
                        }
                    )

                link_sections.append(
                    {
                        "title": title,
                        "links": links_data,
                    }
                )

        business = {
            "company_name": footer_settings.company_name,
            "phone_number": footer_settings.phone_number,
            "email": footer_settings.email,
            "address": footer_settings.address,
        }

        copyright_raw = footer_settings.copyright_text

        return {
            "tagline": footer_settings.tagline,
            "link_sections": link_sections,
            "social": footer_settings.social,
            "business": business,
            "copyright": {
                "raw": copyright_raw,
            },
        }

    base_context = cache_get_or_build(cache_key, build)
    result = copy.deepcopy(base_context)

    copyright_data = result.setdefault("copyright", {})
    raw_text = str(copyright_data.get("raw") or "")
    copyright_data["raw"] = raw_text
    if getattr(settings, "VISUAL_TEST", False):
        frozen_year = getattr(settings, "VISUAL_TEST_FROZEN_YEAR", None)
        year = frozen_year if isinstance(frozen_year, int) else timezone.now().year
    else:
        year = timezone.now().year

    copyright_data["rendered"] = render_footer_copyright(
        raw_text,
        result.get("business", {}).get("company_name", ""),
        year,
    )

    return result
