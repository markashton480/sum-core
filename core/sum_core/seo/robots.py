"""
Name: robots
Path: core/sum_core/seo/robots.py
Purpose: Serve robots.txt with configurable content and sitemap reference.
Family: Technical SEO (M4-006)
Dependencies: Wagtail Site, SiteSettings
"""

from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from sum_core.branding.models import SiteSettings
from wagtail.models import Site


def robots_view(request: HttpRequest) -> HttpResponse:
    """
    Serve robots.txt for the current site.

    Behavior:
    - If SiteSettings.robots_txt is set, use that content.
    - Otherwise, use default (allow all + sitemap reference).
    - Always ensures Sitemap: line is present (appended if missing).
    """
    site = Site.find_for_request(request)

    # Get site settings
    try:
        site_settings = SiteSettings.for_site(site) if site else None
    except Exception:
        site_settings = None

    # Get custom robots content if configured
    robots_content = ""
    if site_settings and hasattr(site_settings, "robots_txt"):
        robots_content = (site_settings.robots_txt or "").strip()

    # If no custom content, use default
    if not robots_content:
        robots_content = _get_default_robots_txt()

    # Ensure sitemap reference is present
    sitemap_url = request.build_absolute_uri("/sitemap.xml")
    sitemap_line = f"Sitemap: {sitemap_url}"

    # Check if sitemap line already exists (case-insensitive)
    has_sitemap = any(
        line.strip().lower().startswith("sitemap:")
        for line in robots_content.splitlines()
    )

    if not has_sitemap:
        # Append sitemap line
        robots_content = f"{robots_content}\n\n{sitemap_line}"

    return HttpResponse(robots_content.strip() + "\n", content_type="text/plain")


def _get_default_robots_txt() -> str:
    """
    Return default robots.txt content.

    Allows all user agents by default.
    Note: Sitemap line will be added automatically by robots_view.
    """
    return """User-agent: *
Disallow:"""
