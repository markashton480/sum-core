"""
Name: sitemap
Path: core/sum_core/seo/sitemap.py
Purpose: Generate per-site sitemap.xml per platform Technical SEO requirements.
Family: Technical SEO (M4-006)
Dependencies: Wagtail Site/Page models, SeoFieldsMixin (seo_noindex), optional SiteSettings
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from django.http import HttpRequest, HttpResponse
from django.template.loader import render_to_string
from wagtail.models import Page, Site


def sitemap_view(request: HttpRequest) -> HttpResponse:
    """
    Generate and return sitemap.xml for the current site.

    Includes all published pages for the current Site, excluding:
    - Unpublished pages (draft/private)
    - Pages with seo_noindex=True
    - LandingPages (if they exist as a page type)

    Each URL includes:
    - <loc> (absolute URL)
    - <lastmod> (ISO 8601 date format)
    - <changefreq> (derived from page type/activity)
    - <priority> (derived from page depth and type)
    """
    site = Site.find_for_request(request)
    if not site:
        return HttpResponse(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>',
            content_type="application/xml",
        )

    # Get all live, public pages under this site's root page
    # Filter to only specific pages (using .specific() allows us to check page-specific attributes)
    pages = (
        Page.objects.descendant_of(site.root_page, inclusive=True)
        .live()  # Only published pages
        .public()  # Only public (not private) pages
        .specific()  # Get the specific page types (not base Page)
        .select_related("content_type")
    )

    # Build URL entries
    url_entries: list[dict[str, Any]] = []
    for page in pages:
        # Exclude pages with seo_noindex=True
        if getattr(page, "seo_noindex", False):
            continue

        # Exclude LandingPage types if they exist
        # Note: LandingPage doesn't exist yet in the codebase, but we'll check the class name
        if page.__class__.__name__ == "LandingPage":
            continue

        url = page.get_full_url(request=request)
        if not url:
            continue

        # Determine lastmod
        lastmod = _get_lastmod(page)

        # Determine changefreq based on page type
        changefreq = _get_changefreq(page)

        # Determine priority based on page depth and type
        priority = _get_priority(page, site)

        url_entries.append(
            {
                "loc": url,
                "lastmod": lastmod.strftime("%Y-%m-%d") if lastmod else "",
                "changefreq": changefreq,
                "priority": f"{priority:.1f}",
            }
        )

    # Render XML using a template
    xml_content = render_to_string(
        "sum_core/seo/sitemap.xml",
        {
            "url_entries": url_entries,
        },
    )

    return HttpResponse(xml_content, content_type="application/xml; charset=utf-8")


def _get_lastmod(page: Page) -> datetime | None:
    """
    Get the last modification date for a page.

    Prefers last_published_at, then latest_revision_created_at, then None.
    """
    if hasattr(page, "last_published_at") and page.last_published_at:
        return page.last_published_at  # type: ignore[no-any-return]

    if hasattr(page, "latest_revision_created_at") and page.latest_revision_created_at:
        return page.latest_revision_created_at  # type: ignore[no-any-return]

    # Fallback to first_published_at if available
    if hasattr(page, "first_published_at") and page.first_published_at:
        return page.first_published_at  # type: ignore[no-any-return]

    return None


def _get_changefreq(page: Page) -> str:
    """
    Determine change frequency based on page type.

    - HomePage: weekly
    - ServiceIndexPage, BlogIndexPage: weekly
    - ServicePage, BlogPostPage: monthly
    - Others: monthly
    """
    page_type = page.__class__.__name__

    if page_type == "HomePage":
        return "weekly"
    elif page_type in ("ServiceIndexPage", "BlogIndexPage"):
        return "weekly"
    elif page_type in ("ServicePage", "BlogPostPage"):
        return "monthly"
    else:
        return "monthly"


def _get_priority(page: Page, site: Site) -> float:
    """
    Determine priority based on page depth and type.

    - Site root (HomePage): 1.0
    - Depth 1 (top-level pages): 0.8
    - Depth 2 (second-level pages): 0.6
    - Deeper pages: 0.5
    """
    if page.id == site.root_page_id:
        return 1.0

    depth = page.depth - site.root_page.depth

    if depth == 1:
        return 0.8
    elif depth == 2:
        return 0.6
    else:
        return 0.5
