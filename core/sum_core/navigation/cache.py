"""
Name: Navigation Cache Invalidation Layer
Path: core/sum_core/navigation/cache.py
Purpose: Provide cache key helpers and signal-based invalidation for navigation caching.
Family: Navigation System (Phase 1: Foundation)
Dependencies: django.core.cache, django.db.models.signals, wagtail.signals

Key Functions:
    - get_nav_cache_key(site_id, nav_type): Get a single cache key
    - get_nav_cache_keys(site_id): Get all nav cache keys for a site
    - invalidate_nav_cache(site_id, types): Invalidate specific or all nav cache keys
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from wagtail.models import Site
from wagtail.signals import page_published, page_unpublished

if TYPE_CHECKING:
    from django.db.models import Model
    from wagtail.models import Page

logger = logging.getLogger(__name__)

# =============================================================================
# Constants
# =============================================================================

CACHE_KEY_PREFIX = "nav"
NAV_TYPES = frozenset({"header", "footer", "sticky"})


# =============================================================================
# Cache Key Helpers
# =============================================================================


def get_nav_cache_key(site_id: int, nav_type: str) -> str:
    """
    Get a single navigation cache key for a site.

    Args:
        site_id: The site ID
        nav_type: One of 'header', 'footer', 'sticky'

    Returns:
        Cache key in format: nav:{type}:{site_id}
    """
    return f"{CACHE_KEY_PREFIX}:{nav_type}:{site_id}"


def get_nav_cache_keys(site_id: int) -> list[str]:
    """
    Get all navigation cache keys for a site.

    Args:
        site_id: The site ID

    Returns:
        List of cache keys: ['nav:header:{site_id}', 'nav:footer:{site_id}', 'nav:sticky:{site_id}']
    """
    return [
        f"{CACHE_KEY_PREFIX}:header:{site_id}",
        f"{CACHE_KEY_PREFIX}:footer:{site_id}",
        f"{CACHE_KEY_PREFIX}:sticky:{site_id}",
    ]


def invalidate_nav_cache(site_id: int, *, types: set[str] | None = None) -> None:
    """
    Invalidate navigation cache keys for a site.

    Args:
        site_id: The site ID
        types: Optional set of nav types to invalidate (e.g. {'header', 'sticky'}).
               If None, all nav cache keys are invalidated.
    """
    if types is None:
        # Delete all nav cache keys
        keys = get_nav_cache_keys(site_id)
    else:
        # Delete only specified types
        keys = [
            get_nav_cache_key(site_id, nav_type)
            for nav_type in types
            if nav_type in NAV_TYPES
        ]

    if keys:
        try:
            cache.delete_many(keys)
            logger.debug("Invalidated nav cache keys for site %s: %s", site_id, keys)
        except Exception:
            # Log but don't fail if cache deletion fails
            logger.exception("Failed to invalidate nav cache keys for site %s", site_id)


# =============================================================================
# Signal Handlers
# =============================================================================


def _get_sites_for_page(page: Page) -> list[Site]:
    """
    Get all sites that a page belongs to.

    Returns list of Sites the page is under (typically one, but handles multi-site).
    """
    # Walk up the tree to find the site this page belongs to
    try:
        # Get the root page for this page's tree
        ancestors = page.get_ancestors(inclusive=True)
        root_page = ancestors.first()
        if root_page:
            # Find sites that have this root page
            return list(Site.objects.filter(root_page=root_page))
    except Exception:
        pass

    # Fallback: check all sites
    return []


@receiver(post_save, dispatch_uid="nav_cache_header_save")
def _on_header_navigation_save(sender: type[Model], instance: Model, **kwargs) -> None:
    """Invalidate header + sticky cache when HeaderNavigation is saved."""
    # Import here to avoid circular imports
    from sum_core.navigation.models import HeaderNavigation

    if sender is HeaderNavigation:
        site_id = instance.site_id
        if site_id:
            invalidate_nav_cache(site_id, types={"header", "sticky"})
            logger.debug(
                "HeaderNavigation saved, invalidated header+sticky for site %s", site_id
            )


@receiver(post_save, dispatch_uid="nav_cache_footer_save")
def _on_footer_navigation_save(sender: type[Model], instance: Model, **kwargs) -> None:
    """Invalidate footer cache when FooterNavigation is saved."""
    from sum_core.navigation.models import FooterNavigation

    if sender is FooterNavigation:
        site_id = instance.site_id
        if site_id:
            invalidate_nav_cache(site_id, types={"footer"})
            logger.debug(
                "FooterNavigation saved, invalidated footer for site %s", site_id
            )


@receiver(post_save, dispatch_uid="nav_cache_branding_save")
def _on_branding_settings_save(sender: type[Model], instance: Model, **kwargs) -> None:
    """Invalidate all nav cache when Branding SiteSettings is saved."""
    from sum_core.branding.models import SiteSettings

    if sender is SiteSettings:
        site_id = instance.site_id
        if site_id:
            invalidate_nav_cache(site_id)  # All types
            logger.debug(
                "Branding SiteSettings saved, invalidated all nav for site %s", site_id
            )


@receiver(page_published, dispatch_uid="nav_cache_page_published")
def _on_page_published(sender: type, instance: Page, **kwargs) -> None:
    """Invalidate nav cache for relevant site(s) when a page is published."""
    sites = _get_sites_for_page(instance)
    for site in sites:
        invalidate_nav_cache(site.id)
        logger.debug("Page published, invalidated nav cache for site %s", site.id)

    # If no sites found, invalidate all sites as safe fallback
    if not sites:
        for site in Site.objects.all():
            invalidate_nav_cache(site.id)
            logger.debug(
                "Page published (no sites found), invalidated nav cache for site %s",
                site.id,
            )


@receiver(page_unpublished, dispatch_uid="nav_cache_page_unpublished")
def _on_page_unpublished(sender: type, instance: Page, **kwargs) -> None:
    """Invalidate nav cache for relevant site(s) when a page is unpublished."""
    sites = _get_sites_for_page(instance)
    for site in sites:
        invalidate_nav_cache(site.id)
        logger.debug("Page unpublished, invalidated nav cache for site %s", site.id)

    # If no sites found, invalidate all sites as safe fallback
    if not sites:
        for site in Site.objects.all():
            invalidate_nav_cache(site.id)
            logger.debug(
                "Page unpublished (no sites found), invalidated nav cache for site %s",
                site.id,
            )


@receiver(post_delete, dispatch_uid="nav_cache_page_delete")
def _on_page_delete(sender: type[Model], instance: Model, **kwargs) -> None:
    """Invalidate nav cache when a page is deleted."""
    # Import Page here to check if sender is a Page subclass
    from wagtail.models import Page as WagtailPage

    # Only handle Page subclasses
    if not isinstance(instance, WagtailPage):
        return

    # At delete time, page relationships may already be gone
    # Try to find sites, but fallback to invalidating all sites
    sites = _get_sites_for_page(instance)

    if sites:
        for site in sites:
            invalidate_nav_cache(site.id)
            logger.debug("Page deleted, invalidated nav cache for site %s", site.id)
    else:
        # Safe fallback: invalidate all sites
        for site in Site.objects.all():
            invalidate_nav_cache(site.id)
            logger.debug(
                "Page deleted (no sites found), invalidated nav cache for site %s",
                site.id,
            )
