"""
Name: schema
Path: core/sum_core/seo/schema.py
Purpose: Build JSON-LD schema dicts for LocalBusiness, Article, FAQPage, BreadcrumbList, Service.
Family: seo_tags.render_schema; SEO tests
Dependencies: Wagtail Page tree, SiteSettings, page mixins/fields
"""

from __future__ import annotations

from typing import Any

from django.http import HttpRequest
from django.utils.html import strip_tags
from sum_core.branding.models import SiteSettings
from wagtail.models import Page


def build_localbusiness_schema(
    site_settings: SiteSettings | None, request: HttpRequest | None
) -> dict[str, Any] | None:
    """
    Build LocalBusiness schema from SiteSettings.

    Returns None if site_settings is missing or insufficient data.
    """
    if not site_settings:
        return None

    company_name = (site_settings.company_name or "").strip()
    if not company_name:
        return None

    schema: dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "LocalBusiness",
        "name": company_name,
    }

    # Address
    address = (site_settings.address or "").strip()
    if address:
        schema["address"] = address

    # Phone
    phone = (site_settings.phone_number or "").strip()
    if phone:
        schema["telephone"] = phone

    # Email
    email = (site_settings.email or "").strip()
    if email:
        schema["email"] = email

    # Business hours
    hours = (site_settings.business_hours or "").strip()
    if hours:
        schema["openingHours"] = hours

    return schema


def build_breadcrumb_schema(
    page: Page, request: HttpRequest | None = None
) -> dict[str, Any] | None:
    """
    Build BreadcrumbList schema for the given page.

    Returns None if page has no breadcrumb trail (unlikely for normal use).
    """
    if not hasattr(page, "get_breadcrumbs"):
        return None

    breadcrumbs = page.get_breadcrumbs(request=request)
    if not breadcrumbs:
        return None

    items = []
    for position, crumb in enumerate(breadcrumbs, start=1):
        url = crumb.get("url", "")
        # Make absolute if request is available
        if url and request and not url.startswith("http"):
            url = request.build_absolute_uri(url)

        items.append(
            {
                "@type": "ListItem",
                "position": position,
                "name": crumb.get("title", ""),
                "item": url,
            }
        )

    if not items:
        return None

    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": items,
    }


def build_article_schema(
    page: Page, request: HttpRequest | None = None
) -> dict[str, Any] | None:
    """
    Build Article schema for BlogPostPage.

    Currently simplified; expects page to have title, first_published_at, and optionally featured_image.
    """
    schema: dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": page.title,
    }

    # datePublished
    if hasattr(page, "first_published_at") and page.first_published_at:
        schema["datePublished"] = page.first_published_at.isoformat()

    # image (featured_image)
    if hasattr(page, "featured_image") and page.featured_image:
        image = page.featured_image
        rendition = image.get_rendition("original")
        image_url = rendition.url
        if request and not image_url.startswith("http"):
            image_url = request.build_absolute_uri(image_url)
        schema["image"] = image_url

    # author (optional for now)
    if hasattr(page, "author") and page.author:
        schema["author"] = {"@type": "Person", "name": str(page.author)}

    return schema


def build_faq_schema(faq_items: list[dict[str, Any]]) -> dict[str, Any] | None:
    """
    Build FAQPage schema from a list of FAQ items.

    Each item should have 'question' and 'answer' keys.
    Returns None if no items.
    """
    if not faq_items:
        return None

    main_entity = []
    for item in faq_items:
        question = item.get("question", "").strip()
        raw_answer = item.get("answer", "")

        # Handle RichText or str for answer
        if hasattr(raw_answer, "source"):
            answer_text = strip_tags(raw_answer.source)
        else:
            answer_text = strip_tags(str(raw_answer))

        if question and answer_text:
            main_entity.append(
                {
                    "@type": "Question",
                    "name": question,
                    "acceptedAnswer": {"@type": "Answer", "text": answer_text},
                }
            )

    if not main_entity:
        return None

    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": main_entity,
    }


def build_service_schema(
    page: Page, site_settings: SiteSettings | None, request: HttpRequest | None
) -> dict[str, Any] | None:
    """
    Build Service schema for ServicePage.

    Minimal v1: name, description, url, provider (from SiteSettings).
    """
    schema: dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "Service",
        "name": page.title,
    }

    # description
    description = ""
    if hasattr(page, "short_description"):
        description = (page.short_description or "").strip()
    if not description and hasattr(page, "meta_description"):
        description = (page.meta_description or "").strip()
    if description:
        schema["description"] = description

    # url
    url = ""
    if hasattr(page, "get_url"):
        url = page.get_url(request=request)
    if url and request and not url.startswith("http"):
        url = request.build_absolute_uri(url)
    if url:
        schema["url"] = url

    # provider
    if site_settings and site_settings.company_name:
        schema["provider"] = {
            "@type": "Organization",
            "name": site_settings.company_name,
        }

    return schema


def extract_faq_items_from_streamfield(body) -> list[dict[str, Any]]:
    """
    Extract FAQ items from a StreamField body.

    Returns a list of {'question': str, 'answer': str} dicts.
    """
    faq_items: list[dict[str, Any]] = []
    if not body:
        return faq_items

    for block in body:
        if block.block_type == "faq":
            items = block.value.get("items", [])
            for item in items:
                faq_items.append(
                    {
                        "question": item.get("question", ""),
                        "answer": item.get("answer", ""),
                    }
                )

    return faq_items
