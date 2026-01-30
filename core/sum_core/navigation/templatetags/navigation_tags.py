"""
Name: Navigation Template Tags
Path: core/sum_core/navigation/templatetags/navigation_tags.py
Purpose: Provide template tags for rendering header, footer, and sticky CTA navigation.
Family: Navigation System (Phase 1: Foundation)
Dependencies: django.template, django.core.cache, wagtail.models, sum_core.navigation

Tags:
    - header_nav: Returns header menu context with active detection
    - footer_nav: Returns footer links, social, business info, and copyright
    - sticky_cta: Returns mobile sticky CTA bar configuration
    - desktop_sticky_cta: Returns desktop sticky CTA configuration

This module re-exports template tags from split modules for backwards compatibility.
"""

from __future__ import annotations

import logging

from django import template
from django.utils import timezone
from sum_core.navigation.services import get_effective_header_settings
from sum_core.utils.contact import normalize_phone_href as _normalize_phone_href

from .footer_tags import footer_nav
from .header_tags import (
    _apply_header_active_states,
    _build_header_base_data,
    header_nav,
)
from .sticky_cta_tags import desktop_sticky_cta, sticky_cta
from .utils import CACHE_KEY_PREFIX, CACHE_TTL_DEFAULT
from .utils import cache_get_or_build as _cache_get_or_build
from .utils import extract_cta_link as _extract_cta_link
from .utils import extract_link_data as _extract_link_data
from .utils import get_ancestor_pks as _get_ancestor_pks
from .utils import get_cache_ttl as _get_cache_ttl
from .utils import get_current_page as _get_current_page
from .utils import is_active_section as _is_active_section
from .utils import is_current_page as _is_current_page
from .utils import is_current_page_by_pk as _is_current_page_by_pk
from .utils import is_current_path as _is_current_path
from .utils import make_cache_key as _make_cache_key
from .utils import render_footer_copyright as _render_footer_copyright

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

register = template.Library()

register.simple_tag(takes_context=True)(header_nav)
register.simple_tag(takes_context=True)(footer_nav)
register.simple_tag(takes_context=True)(sticky_cta)
register.simple_tag(takes_context=True)(desktop_sticky_cta)

__all__ = [
    "CACHE_KEY_PREFIX",
    "CACHE_TTL_DEFAULT",
    "_apply_header_active_states",
    "_build_header_base_data",
    "_cache_get_or_build",
    "_extract_cta_link",
    "_extract_link_data",
    "_get_ancestor_pks",
    "_get_cache_ttl",
    "_get_current_page",
    "_is_active_section",
    "_is_current_page",
    "_is_current_page_by_pk",
    "_is_current_path",
    "_make_cache_key",
    "_normalize_phone_href",
    "_render_footer_copyright",
    "desktop_sticky_cta",
    "footer_nav",
    "get_effective_header_settings",
    "header_nav",
    "register",
    "sticky_cta",
    "timezone",
]
