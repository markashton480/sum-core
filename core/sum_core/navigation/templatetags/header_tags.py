"""
Name: Header Navigation Template Tags
Path: core/sum_core/navigation/templatetags/header_tags.py
Purpose: Template tag for rendering header navigation with active detection.
Family: Navigation System (Phase 1: Foundation)
Dependencies: django.template, sum_core.navigation
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sum_core.navigation.services import get_effective_header_settings
from sum_core.utils.contact import normalize_phone_href
from wagtail.models import Page, Site

from .utils import (
    cache_get_or_build,
    extract_cta_link,
    extract_link_data,
    get_ancestor_pks,
    get_current_page,
    is_current_page_by_pk,
    is_current_path,
    make_cache_key,
)

if TYPE_CHECKING:
    from django.http import HttpRequest


def header_nav(context: dict[str, Any]) -> dict[str, Any]:
    """
    Return header navigation context dict.

    Context keys:
        - menu_items: list of menu item dicts
        - show_phone: bool
        - phone_number: str (only if show_phone True)
        - phone_href: str (tel: normalized)
        - header_cta: dict with enabled, text, href, attrs
        - current_page: Page object or None

    Caching Strategy:
        Base menu data (structure, labels, hrefs, etc.) is cached under
        nav:header:{site_id}. Active states (is_current, is_active) are
        computed per-request and applied via deep copy to avoid mutating cache.

    Usage:
        {% load navigation_tags %}
        {% header_nav as nav %}
        {{ nav.menu_items }}
    """
    request = context.get("request")
    if request is None:
        return {}

    site = Site.find_for_request(request)
    if site is None:
        return {}

    current_page = get_current_page(context)

    cache_key = make_cache_key("header", site.id)
    base_data = cache_get_or_build(cache_key, lambda: _build_header_base_data(site))

    result = _apply_header_active_states(base_data, current_page, request)
    result["current_page"] = current_page

    return result


def _build_header_base_data(site: Site) -> dict[str, Any]:
    """Build cacheable header navigation base data without per-request active states."""
    header_settings = get_effective_header_settings(site)

    menu_items_base: list[dict[str, Any]] = []
    if header_settings.menu_items:
        for item in header_settings.menu_items:
            menu_items_base.append(_build_menu_item_base(item))

    cta_link_data = extract_cta_link(header_settings.header_cta.link)
    header_cta = {
        "enabled": header_settings.header_cta.enabled,
        "text": header_settings.header_cta.text,
        "href": cta_link_data["href"] if cta_link_data else "#",
        "attrs": cta_link_data["attrs"] if cta_link_data else {},
    }

    phone_number = header_settings.phone_number or ""
    phone_href = normalize_phone_href(phone_number)
    show_phone = header_settings.show_phone_in_header

    return {
        "menu_items_base": menu_items_base,
        "show_phone": show_phone,
        "phone_number": phone_number if show_phone else "",
        "phone_href": phone_href if show_phone else "",
        "header_cta": header_cta,
    }


def _build_menu_item_base(item_block: Any) -> dict[str, Any]:
    """Build base menu item dict without active states (cacheable). Includes page_pk for later active detection."""
    value = item_block.value if hasattr(item_block, "value") else item_block

    label = value.get("label", "")
    link_value = value.get("link")
    link_data = extract_link_data(link_value)

    linked_page_pk: int | None = None
    link_type: str | None = None
    if link_value:
        link_type = link_value.get("link_type") if hasattr(link_value, "get") else None
        linked_page = link_value.get("page") if hasattr(link_value, "get") else None
        if linked_page:
            linked_page_pk = linked_page.pk

    children_blocks = value.get("children", [])
    children_base = _build_children_base(children_blocks)
    has_children = bool(children_blocks)

    featured_image = value.get("featured_image")
    featured_label = value.get("featured_label", "")
    featured_title = value.get("featured_title", "")
    featured_link_text = value.get("featured_link_text", "")
    featured_link_value = value.get("featured_link")
    featured_link_data = (
        extract_link_data(featured_link_value) if featured_link_value else None
    )

    return {
        "label": label,
        "href": link_data["href"],
        "is_external": link_data["is_external"],
        "opens_new_tab": link_data["opens_new_tab"],
        "attrs": link_data["attrs"],
        "attrs_str": link_data["attrs_str"],
        "has_children": has_children,
        "children_base": children_base,
        "featured_image": featured_image,
        "featured_label": featured_label,
        "featured_title": featured_title,
        "featured_link_text": featured_link_text,
        "featured_link": featured_link_data,
        "_page_pk": linked_page_pk,
        "_link_type": link_type,
    }


def _build_children_base(children_blocks: list[Any]) -> list[dict[str, Any]]:
    """Recursively build base data for a list of children blocks."""
    children_base: list[dict[str, Any]] = []

    for child_block in children_blocks:
        child_value = (
            child_block.value if hasattr(child_block, "value") else child_block
        )
        child_label = child_value.get("label", "")
        child_link = child_value.get("link")
        child_link_data = extract_link_data(child_link)

        child_page_pk: int | None = None
        child_link_type: str | None = None
        if child_link and hasattr(child_link, "get"):
            child_link_type = child_link.get("link_type")
            child_page = child_link.get("page")
            if child_page:
                child_page_pk = child_page.pk

        grand_children_blocks = child_value.get("children", [])
        grand_children_base = _build_children_base(grand_children_blocks)
        has_children = bool(grand_children_blocks)

        children_base.append(
            {
                "label": child_label,
                "href": child_link_data["href"],
                "is_external": child_link_data["is_external"],
                "opens_new_tab": child_link_data["opens_new_tab"],
                "attrs": child_link_data["attrs"],
                "attrs_str": child_link_data["attrs_str"],
                "has_children": has_children,
                "children_base": grand_children_base,
                "_page_pk": child_page_pk,
                "_link_type": child_link_type,
            }
        )
    return children_base


def _apply_header_active_states(
    base_data: dict[str, Any],
    current_page: Page | None,
    request: HttpRequest | None,
) -> dict[str, Any]:
    """Apply per-request active states to base header data. Returns a new dict without mutating cached base_data."""
    import copy

    result: dict[str, Any] = copy.deepcopy(base_data)

    ancestor_pks = get_ancestor_pks(current_page)

    menu_items: list[dict[str, Any]] = []
    for item_base in result.get("menu_items_base", []):
        item = _apply_item_active_state(item_base, current_page, request, ancestor_pks)
        menu_items.append(item)

    result["menu_items"] = menu_items
    result.pop("menu_items_base", None)

    return result


def _apply_children_active_states(
    children_base: list[dict[str, Any]],
    current_page: Page | None,
    request: HttpRequest | None,
    ancestor_pks: set[int],
) -> tuple[list[dict[str, Any]], bool]:
    """Recursively apply active states to children. Returns (list of processed children, bool indicating if any descendant is active)."""
    children: list[dict[str, Any]] = []
    any_child_active = False

    for child_base in children_base:
        child_page_pk = child_base.get("_page_pk")
        child_link_type = child_base.get("_link_type")
        child_href = child_base.get("href", "#")

        child_is_current = False
        child_is_active = False

        if child_link_type == "page" and child_page_pk is not None:
            child_is_current = is_current_page_by_pk(child_page_pk, current_page)
            child_is_active = child_page_pk in ancestor_pks
        else:
            child_is_current = is_current_path(child_href, request, child_link_type)
            child_is_active = child_is_current

        grand_children_base = child_base.get("children_base", [])
        grand_children, grandchild_active = _apply_children_active_states(
            grand_children_base, current_page, request, ancestor_pks
        )

        if grandchild_active:
            child_is_active = True

        if child_is_active:
            any_child_active = True

        child = {
            "label": child_base.get("label", ""),
            "href": child_href,
            "is_external": child_base.get("is_external", False),
            "opens_new_tab": child_base.get("opens_new_tab", False),
            "attrs": child_base.get("attrs", {}),
            "attrs_str": child_base.get("attrs_str", ""),
            "is_current": child_is_current,
            "is_active": child_is_active,
            "has_children": child_base.get("has_children", False),
            "children": grand_children,
        }
        children.append(child)

    return children, any_child_active


def _apply_item_active_state(
    item_base: dict[str, Any],
    current_page: Page | None,
    request: HttpRequest | None,
    ancestor_pks: set[int],
) -> dict[str, Any]:
    """Apply active state to a single menu item and its children."""
    page_pk = item_base.get("_page_pk")
    link_type = item_base.get("_link_type")
    href = item_base.get("href", "#")

    is_current = False
    is_active = False

    if link_type == "page" and page_pk is not None:
        is_current = is_current_page_by_pk(page_pk, current_page)
        is_active = page_pk in ancestor_pks
    else:
        is_current = is_current_path(href, request, link_type)
        is_active = is_current

    children_base_list = item_base.get("children_base", [])
    children, child_active = _apply_children_active_states(
        children_base_list, current_page, request, ancestor_pks
    )

    if child_active:
        is_active = True

    return {
        "label": item_base.get("label", ""),
        "href": href,
        "is_external": item_base.get("is_external", False),
        "opens_new_tab": item_base.get("opens_new_tab", False),
        "attrs": item_base.get("attrs", {}),
        "attrs_str": item_base.get("attrs_str", ""),
        "is_current": is_current,
        "is_active": is_active,
        "has_children": item_base.get("has_children", False),
        "children": children,
        "featured_image": item_base.get("featured_image"),
        "featured_label": item_base.get("featured_label", ""),
        "featured_title": item_base.get("featured_title", ""),
        "featured_link_text": item_base.get("featured_link_text", ""),
        "featured_link": item_base.get("featured_link"),
    }
