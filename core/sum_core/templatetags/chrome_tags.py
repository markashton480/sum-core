"""
Template tags for page chrome utilities.
"""

from __future__ import annotations

from urllib.parse import unquote

from django import template
from sum_core.branding.models import SiteSettings
from sum_core.pages.chrome import HEADER_BLOCK_TYPES
from wagtail.models import Site

register = template.Library()

# Optional page type imports - graceful degradation if not available
try:
    from sum_core.pages.home import HomePage
except ImportError:
    HomePage = None

try:
    from sum_core.pages.blog import BlogIndexPage, BlogPostPage
except ImportError:
    BlogIndexPage = None
    BlogPostPage = None

try:
    from sum_core.pages.legal import LegalPage
except ImportError:
    LegalPage = None

try:
    from sum_core.pages.portfolio import PortfolioIndexPage
except ImportError:
    PortfolioIndexPage = None

try:
    from sum_core.pages.services import ServiceIndexPage
except ImportError:
    ServiceIndexPage = None

try:
    from sum_core.pages.standard import StandardPage
except ImportError:
    StandardPage = None

COOKIE_CONSENT = "sum_cookie_consent"
COOKIE_CONSENT_VERSION = "sum_cookie_consent_v"
CONSENT_VALUES = {"accepted", "rejected"}


@register.simple_tag
def header_transparent_at_top(page=None) -> bool:
    """Resolve header transparency state with safe fallbacks."""
    if page is None:
        return False

    specific = getattr(page, "specific", page)

    if hasattr(specific, "header_transparent_at_top"):
        return bool(getattr(specific, "header_transparent_at_top"))

    if hasattr(specific, "has_hero_block"):
        return bool(getattr(specific, "has_hero_block"))

    return False


@register.simple_tag(takes_context=True)
def hero_context(
    context,
    page=None,
    *,
    status: str | None = None,
    headline: str | None = None,
    subheadline: str | None = None,
    gradient_style: str | None = None,
    ctas: list | None = None,
    section_id: str | None = None,
    extra_template: str | None = None,
) -> dict[str, object]:
    """Build a standard hero context payload for templates."""
    if page is None:
        return {}

    specific = getattr(page, "specific", page)
    request = context.get("request")

    breadcrumbs = []
    if hasattr(specific, "get_breadcrumbs"):
        breadcrumbs = specific.get_breadcrumbs(request=request)

    # UI rule: no breadcrumbs on homepage (site root page). Schema generation
    # still uses `page.get_breadcrumbs`, so we only hide in chrome templates.
    site = None
    if request is not None:
        site = Site.find_for_request(request)
    if site is None:
        site = specific.get_site()
    if site is not None and getattr(site, "root_page_id", None) == specific.id:
        breadcrumbs = []

    if headline:
        resolved_headline = headline
    else:
        resolved_headline = getattr(specific, "title", "")
    resolved_gradient = gradient_style or getattr(
        specific, "hero_gradient_style", "primary"
    )

    return {
        "status": status or "",
        "headline": resolved_headline,
        "subheadline": subheadline or "",
        "gradient_style": resolved_gradient,
        "ctas": ctas or [],
        "breadcrumbs": breadcrumbs,
        "section_id": section_id or "",
        "extra_template": extra_template or "",
    }


@register.simple_tag(takes_context=True)
def breadcrumbs_for_display(context, page=None) -> list[dict[str, object]]:
    """
    Return breadcrumbs for UI display.

    Contract: breadcrumbs render everywhere except the homepage (site root page).
    """
    if page is None or not hasattr(page, "get_breadcrumbs"):
        return []

    request = context.get("request")
    specific = getattr(page, "specific", page)
    breadcrumbs = specific.get_breadcrumbs(request=request)

    site = None
    if request is not None:
        site = Site.find_for_request(request)
    if site is None:
        site = specific.get_site()
    if site is not None and getattr(site, "root_page_id", None) == specific.id:
        return []

    return breadcrumbs


@register.filter
def is_header_block(block: object) -> bool:
    """
    Return True when a StreamField BoundBlock represents a header/hero block type.

    Used by template-owned hero page templates to skip rendering legacy
    header/hero blocks that may still exist in StreamField content.
    """
    block_type = getattr(block, "block_type", None)
    return bool(block_type and block_type in HEADER_BLOCK_TYPES)


def _get_site_settings(request) -> SiteSettings | None:
    if request is None:
        site = Site.objects.filter(is_default_site=True).first()
    else:
        site = (
            Site.find_for_request(request)
            or Site.objects.filter(is_default_site=True).first()
        )

    if site is None:
        return None

    return SiteSettings.for_site(site)


def _decode_cookie(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        return unquote(value)
    except Exception:
        return value


@register.simple_tag(takes_context=True)
def cookie_banner_should_render(context) -> bool:
    request = context.get("request")
    site_settings = _get_site_settings(request)
    if site_settings is None or not site_settings.cookie_banner_enabled:
        return False

    if request is None:
        return True

    consent = _decode_cookie(request.COOKIES.get(COOKIE_CONSENT))
    version = _decode_cookie(request.COOKIES.get(COOKIE_CONSENT_VERSION))

    if consent in CONSENT_VALUES and version == site_settings.cookie_consent_version:
        return False

    return True


@register.simple_tag
def cookie_banner_section_id(page=None) -> str:
    if page is None:
        return ""

    specific = getattr(page, "specific", page)

    if HomePage is not None and isinstance(specific, HomePage):
        return "home-12"

    if StandardPage is not None and isinstance(specific, StandardPage):
        if getattr(specific, "slug", "") == "about":
            return "about-10"
        return ""

    if ServiceIndexPage is not None and isinstance(specific, ServiceIndexPage):
        return "services-14"

    if PortfolioIndexPage is not None and isinstance(specific, PortfolioIndexPage):
        return "portfolio-08"

    if BlogIndexPage is not None and isinstance(specific, BlogIndexPage):
        return "blog-list-07"

    if BlogPostPage is not None and isinstance(specific, BlogPostPage):
        return "blog-article-08"

    if LegalPage is not None and isinstance(specific, LegalPage):
        return "legal-01"

    return ""


@register.simple_tag
def sticky_cta_section_id(page=None) -> str:
    if page is None:
        return ""

    specific = getattr(page, "specific", page)

    if ServiceIndexPage is not None and isinstance(specific, ServiceIndexPage):
        return "services-12"

    return ""
