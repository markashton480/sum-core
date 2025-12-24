"""
Name: seo_tags
Path: core/sum_core/seo/templatetags/seo_tags.py
Purpose: Render SEO meta + Open Graph tags with platform-standard defaults/fallbacks.
Family: base template head rendering; SEO verification tests
Dependencies: Wagtail Page, SiteSettings, SeoFieldsMixin/OpenGraphMixin
"""

from typing import Any

from django import template
from sum_core.branding.models import SiteSettings
from wagtail.models import Page, Site

register = template.Library()


def _resolve_site(request, page) -> Site | None:
    if request is not None:
        return Site.find_for_request(request)
    if isinstance(page, Page):
        return page.get_site()
    return None


@register.inclusion_tag("sum_core/includes/seo/meta.html", takes_context=True)
def render_meta(context, page):
    """
    Renders standard SEO meta tags: title, description, robots, canonical.
    """
    request = context.get("request")

    site = _resolve_site(request, page)
    site_settings = SiteSettings.for_site(site) if site else None

    # 1) Meta title precedence:
    # meta_title (platform) -> seo_title (Wagtail) -> "{title} | {company_name/site_name}"
    meta_title = (getattr(page, "meta_title", "") or "").strip()
    if not meta_title:
        meta_title = (getattr(page, "seo_title", "") or "").strip()
    if not meta_title and hasattr(page, "get_meta_title") and site_settings:
        meta_title = (page.get_meta_title(site_settings) or "").strip()
    if not meta_title:
        page_title = (getattr(page, "title", "") or "").strip()
        site_name = ""
        if site_settings:
            site_name = (getattr(site_settings, "company_name", "") or "").strip()
        if not site_name and site:
            site_name = (site.site_name or "").strip()
        meta_title = f"{page_title} | {site_name}" if site_name else page_title

    # 2) Meta description precedence:
    # meta_description (platform) -> search_description (Wagtail) -> omitted
    meta_description = ""
    if hasattr(page, "get_meta_description"):
        meta_description = (page.get_meta_description() or "").strip()
    if not meta_description:
        meta_description = (getattr(page, "meta_description", "") or "").strip()
    if not meta_description:
        meta_description = (getattr(page, "search_description", "") or "").strip()

    # 3) Robots meta from flags
    noindex = bool(getattr(page, "seo_noindex", False))
    nofollow = bool(getattr(page, "seo_nofollow", False))
    robots_val = (
        f"{'noindex' if noindex else 'index'}, {'nofollow' if nofollow else 'follow'}"
    )

    # 4) Canonical URL (absolute when request present)
    canonical_url = ""
    if request is not None:
        relative = ""
        if isinstance(page, Page):
            relative = page.get_url(request=request) or getattr(page, "url", "") or "/"
        else:
            relative = getattr(page, "url", "") or "/"
        canonical_url = request.build_absolute_uri(relative or "/")
    elif hasattr(page, "get_canonical_url"):
        canonical_url = (page.get_canonical_url(None) or "").strip()
    elif isinstance(page, Page):
        canonical_url = (page.get_full_url() or "").strip()

    return {
        "meta_title": meta_title,
        "meta_description": meta_description,
        "robots_content": robots_val,
        "canonical_url": canonical_url,
        "request": request,
    }


@register.inclusion_tag("sum_core/includes/seo/og.html", takes_context=True)
def render_og(context, page):
    """
    Renders Open Graph tags.
    """
    request = context.get("request")

    site = _resolve_site(request, page)
    site_settings = SiteSettings.for_site(site) if site else None

    meta = render_meta(context, page)
    canonical_url = meta.get("canonical_url", "")
    meta_title = meta.get("meta_title", "")
    meta_description = meta.get("meta_description", "")

    # OG Title precedence: og_title -> helper -> meta title
    og_title = (getattr(page, "og_title", "") or "").strip()
    if not og_title and hasattr(page, "get_og_title") and site_settings:
        og_title = (page.get_og_title(site_settings) or "").strip()
    if not og_title:
        og_title = (meta_title or "").strip() or (getattr(page, "title", "") or "")

    # OG Description precedence: og_description -> helper -> meta description
    og_description = (getattr(page, "og_description", "") or "").strip()
    if not og_description and hasattr(page, "get_og_description"):
        og_description = (page.get_og_description() or "").strip()
    if not og_description:
        og_description = (meta_description or "").strip()

    og_type = "website"

    og_url = canonical_url

    # OG Image fallback chain: page og_image -> featured_image -> site default
    og_image = None
    if hasattr(page, "get_og_image") and site_settings:
        og_image = page.get_og_image(site_settings)
    else:
        if hasattr(page, "og_image") and page.og_image:
            og_image = page.og_image
        elif hasattr(page, "featured_image") and page.featured_image:
            og_image = page.featured_image
        elif site_settings and site_settings.og_default_image:
            og_image = site_settings.og_default_image

    site_name = ""
    if site_settings:
        site_name = (getattr(site_settings, "company_name", "") or "").strip()
    if not site_name and site:
        site_name = (site.site_name or "").strip()

    return {
        "og_title": og_title,
        "og_description": og_description,
        "og_type": og_type,
        "og_url": og_url,
        "og_image": og_image,
        "site_name": site_name,
        "request": request,
    }


@register.simple_tag(takes_context=True)
def absolute_url(context, url):
    """
    Returns the absolute URL for a given relative URL.
    Uses request from context if available.
    """
    request = context.get("request")
    if request:
        return request.build_absolute_uri(url)
    return url


@register.inclusion_tag("sum_core/includes/seo/schema.html", takes_context=True)
def render_schema(context, page):
    """
    Renders JSON-LD structured data for the page.

    Emits:
    - LocalBusiness (HomePage, ContactPage)
    - Article (BlogPostPage)
    - Service (ServicePage)
    - FAQPage (pages containing FAQBlock)
    - BreadcrumbList (all pages)
    """
    import json

    from sum_core.seo.schema import (
        build_article_schema,
        build_breadcrumb_schema,
        build_faq_schema,
        build_localbusiness_schema,
        build_service_schema,
        extract_faq_items_from_streamfield,
    )

    request = context.get("request")
    site = _resolve_site(request, page)
    site_settings = SiteSettings.for_site(site) if site else None

    schemas: list[dict[str, Any]] = []

    if not isinstance(page, Page):
        return {"schema_json_list": schemas}

    # Determine page type
    page_type = page.specific_class.__name__ if hasattr(page, "specific_class") else ""

    # LocalBusiness (HomePage, ContactPage)
    if page_type in ["HomePage", "ContactPage"]:
        localbusiness = build_localbusiness_schema(site_settings, request)
        if localbusiness:
            schemas.append(localbusiness)

    # Article (BlogPostPage)
    if page_type == "BlogPostPage":
        article = build_article_schema(page.specific, request)
        if article:
            schemas.append(article)

    # Service (ServicePage)
    if page_type == "ServicePage":
        service = build_service_schema(page.specific, site_settings, request)
        if service:
            schemas.append(service)

    # FAQPage (pages containing FAQBlock)
    if hasattr(page.specific, "body"):
        faq_items = extract_faq_items_from_streamfield(page.specific.body)
        if faq_items:
            faq_schema = build_faq_schema(faq_items)
            if faq_schema:
                schemas.append(faq_schema)

    # BreadcrumbList (all pages)
    breadcrumb = build_breadcrumb_schema(page.specific, request)
    if breadcrumb:
        schemas.append(breadcrumb)

    # Serialize to JSON strings
    schema_json_list = [
        json.dumps(schema, ensure_ascii=False, indent=2) for schema in schemas
    ]

    return {"schema_json_list": schema_json_list}
