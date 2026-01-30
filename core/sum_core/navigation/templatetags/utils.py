"""
Name: Navigation Template Tags Shared Utilities
Path: core/sum_core/navigation/templatetags/utils.py
Purpose: Shared utilities for navigation template tags (cache, link extraction, active detection).
Family: Navigation System (Phase 1: Foundation)
Dependencies: django.template, django.core.cache, wagtail.models, sum_core.navigation
"""

from __future__ import annotations

import copy
import logging
import re
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.core.cache import cache
from sum_core.navigation.cache import get_nav_cache_key
from sum_core.utils.contact import normalize_phone_href
from wagtail.models import Page

if TYPE_CHECKING:
    from django.http import HttpRequest

logger = logging.getLogger(__name__)

# =============================================================================
# Constants
# =============================================================================

CACHE_TTL_DEFAULT = 300  # 5 minutes in seconds (reduced from 1 hour for better UX)
CACHE_KEY_PREFIX = "nav"


# =============================================================================
# Cache Helpers
# =============================================================================


def get_cache_ttl() -> int:
    """Get cache TTL from settings or fall back to CACHE_TTL_DEFAULT."""
    return getattr(settings, "NAV_CACHE_TTL", CACHE_TTL_DEFAULT)


def make_cache_key(tag_name: str, site_id: int) -> str:
    """
    Build a site-specific cache key matching spec format.

    Delegates to shared helper to prevent key format drift.
    """
    return str(get_nav_cache_key(site_id, tag_name))


def cache_get_or_build(
    cache_key: str, builder: Callable[[], dict[str, Any]]
) -> dict[str, Any]:
    """
    Read-through cache: return cached dict on hit, or build→store→return on miss.

    Falls back gracefully to builder if cache fails.
    """
    try:
        cached = cache.get(cache_key)
        if cached is not None:
            # Return type is dict[str, Any], assert it explicitly for mypy
            result: dict[str, Any] = cached
            return result
    except Exception as e:
        # Cache backend failed, continue to build
        logger.debug("Cache read failed for key '%s': %s", cache_key, e)

    result = builder()

    try:
        cache.set(cache_key, result, timeout=get_cache_ttl())
    except Exception as e:
        # Cache write failed, just return the result
        logger.debug("Cache write failed for key '%s': %s", cache_key, e)

    return result


# =============================================================================
# Link Extraction Helpers
# =============================================================================


def extract_link_data(link_value: Any) -> dict[str, Any]:
    """
    Extract link metadata from a UniversalLinkValue or raw dict.

    Returns dict with: href, text, is_external, opens_new_tab, attrs, attrs_str

    Handles both:
    - UniversalLinkValue objects (from proper StreamField loading)
    - Raw dicts (from tests or JSON data)
    """
    if link_value is None:
        return {
            "href": "#",
            "text": "",
            "is_external": False,
            "opens_new_tab": False,
            "attrs": {},
            "attrs_str": "",
        }

    # Check if it has computed properties (UniversalLinkValue)
    # Properties aren't callable, so check for property descriptor on the class
    href_attr = getattr(type(link_value), "href", None)
    if href_attr is not None and isinstance(href_attr, property):
        # This is a proper UniversalLinkValue with computed properties
        return {
            "href": link_value.href,
            "text": link_value.text,
            "is_external": link_value.is_external,
            "opens_new_tab": link_value.opens_new_tab,
            "attrs": link_value.attrs,
            "attrs_str": link_value.attrs_str,
        }

    # Fallback: treat as dict and compute values directly
    # This handles raw dict input from tests or when blocks aren't fully instantiated
    link_type = None
    if hasattr(link_value, "get"):
        link_type = link_value.get("link_type")
    elif hasattr(link_value, "__getitem__"):
        try:
            link_type = link_value["link_type"]
        except (KeyError, TypeError):
            # Intentional: link_type stays None, handled by fallback logic below
            pass

    # Compute href from dict
    href = "#"
    if link_type == "page":
        page = link_value.get("page") if hasattr(link_value, "get") else None
        if page:
            href = getattr(page, "url", "#")
    elif link_type == "url":
        href = link_value.get("url", "#") if hasattr(link_value, "get") else "#"
    elif link_type == "path":
        href = link_value.get("path", "#") if hasattr(link_value, "get") else "#"
    elif link_type == "email":
        email = link_value.get("email", "") if hasattr(link_value, "get") else ""
        href = f"mailto:{email}" if email else "#"
    elif link_type == "phone":
        phone = link_value.get("phone", "") if hasattr(link_value, "get") else ""
        if phone:
            phone_href = normalize_phone_href(phone)
            href = phone_href if phone_href else "#"
    elif link_type == "anchor":
        anchor = link_value.get("anchor", "") if hasattr(link_value, "get") else ""
        anchor = anchor.lstrip("#")
        href = f"#{anchor}" if anchor else "#"

    # Compute text from dict
    text = ""
    if hasattr(link_value, "get"):
        text = link_value.get("link_text", "") or link_value.get("text", "")
        if not text:
            # Fallback based on link type
            if link_type == "page":
                page = link_value.get("page")
                text = getattr(page, "title", "Link") if page else "Link"
            elif link_type == "url":
                text = link_value.get("url", "Link") or "Link"
            elif link_type == "path":
                text = link_value.get("path", "Link") or "Link"
            elif link_type == "email":
                text = link_value.get("email", "Email") or "Email"
            elif link_type == "phone":
                text = link_value.get("phone", "Phone") or "Phone"
            elif link_type == "anchor":
                text = link_value.get("anchor", "Link").lstrip("#") or "Link"
            else:
                text = "Link"

    # Determine if external
    is_external = link_type == "url"

    # Determine if opens in new tab
    open_in_new_tab = None
    if hasattr(link_value, "get"):
        open_in_new_tab = link_value.get("open_in_new_tab")
    if open_in_new_tab is True:
        opens_new_tab = True
    elif open_in_new_tab is False:
        opens_new_tab = False
    else:
        opens_new_tab = is_external  # Default: new tab for external

    # Build attrs
    attrs = {}
    if opens_new_tab:
        attrs["target"] = "_blank"
        attrs["rel"] = "noopener noreferrer"
    if link_type == "phone":
        attrs["data-contact-type"] = "phone"
    elif link_type == "email":
        attrs["data-contact-type"] = "email"

    # Build attrs_str
    attrs_str = " ".join(f'{k}="{v}"' for k, v in attrs.items())

    return {
        "href": href,
        "text": text,
        "is_external": is_external,
        "opens_new_tab": opens_new_tab,
        "attrs": attrs,
        "attrs_str": attrs_str,
    }


def extract_cta_link(cta_link_stream: Any) -> dict[str, Any] | None:
    """
    Extract CTA link from a SingleLinkStreamBlock (StreamField with max 1).

    Returns link data dict or None if not set.
    """
    if cta_link_stream is None or len(cta_link_stream) == 0:
        return None

    # SingleLinkStreamBlock contains 'link' blocks
    first_block = cta_link_stream[0]
    link_value = first_block.value if hasattr(first_block, "value") else first_block
    return extract_link_data(link_value)


def render_footer_copyright(raw: str, company_name: str, year: int) -> str:
    """Render footer copyright text with safe placeholder replacement."""
    if not raw:
        return ""

    rendered = raw.replace("{year}", str(year)).replace(
        "{company_name}", company_name or ""
    )
    rendered = re.sub(r"\s+\.", ".", rendered)
    rendered = re.sub(r"\s+,", ",", rendered)
    rendered = re.sub(r"\s{2,}", " ", rendered).strip()
    return rendered


# =============================================================================
# Active Detection Helpers
# =============================================================================


def get_current_page(context: dict[str, Any]) -> Page | None:
    """
    Get the current page from template context.

    Checks context['page'] or context['self'] (Wagtail convention).
    """
    page = context.get("page")
    if page is None:
        page = context.get("self")
    if isinstance(page, Page):
        return page
    return None


def is_current_page(linked_page: Page | None, current_page: Page | None) -> bool:
    """Check if linked page is exactly the current page."""
    if linked_page is None or current_page is None:
        return False
    return bool(linked_page.pk == current_page.pk)


def is_active_section(linked_page: Page | None, current_page: Page | None) -> bool:
    """
    Check if current page is the linked page or a descendant.

    Used for section highlighting (e.g., /services/ link is active on /services/roofing/).
    """
    if linked_page is None or current_page is None:
        return False
    if linked_page.pk == current_page.pk:
        return True
    # Check if current page is a descendant of linked page
    return bool(current_page.is_descendant_of(linked_page))


def get_ancestor_pks(current_page: Page | None) -> set[int]:
    """Return current page ancestor PKs (inclusive) or an empty set."""
    if current_page is None:
        return set()
    return set(current_page.get_ancestors(inclusive=True).values_list("pk", flat=True))


def is_current_path(
    href: str, request: HttpRequest | None, link_type: str | None = None
) -> bool:
    """
    Check if href matches current request path (for non-page links).

    Only safe for path-based comparison when link is not a page.
    """
    if request is None or not href or href == "#":
        return False
    if link_type == "page":
        # Page links should use page-based detection
        return False
    return bool(request.path == href)


def is_current_page_by_pk(page_pk: int, current_page: Page | None) -> bool:
    """Check if a page PK matches the current page."""
    if current_page is None:
        return False
    return bool(current_page.pk == page_pk)


# =============================================================================
# Deep Copy Helper
# =============================================================================


def deep_copy_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Deep copy a dictionary to avoid mutating cached data."""
    return copy.deepcopy(data)
