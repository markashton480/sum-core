"""
Name: Page Mixins (SEO, Open Graph, Breadcrumbs)
Path: core/sum_core/pages/mixins.py
Purpose: Provide reusable Wagtail Page mixins for SEO fields, Open Graph metadata, and breadcrumbs.
Family: SUM Platform – Page Types (mixed into Wagtail Page models)
Dependencies: Django models, Wagtail Page, wagtailimages, sum_core.branding.models.SiteSettings
"""

from __future__ import annotations

from typing import Any

from django.db import models
from django.http import HttpRequest
from sum_core.branding.models import SiteSettings
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.models import Page


class SeoFieldsMixin(models.Model):
    """
    Adds SEO fields + helper methods.

    Fields:
    - meta_title: short title suitable for search snippets (<title>)
    - meta_description: short summary suitable for <meta name="description">
    """

    meta_title = models.CharField(
        max_length=60,
        blank=True,
        help_text="Optional. If blank, defaults to “{page title} | {site name}”.",
    )
    meta_description = models.TextField(
        max_length=160,
        blank=True,
        help_text="Optional. Brief summary for search engines (recommended max 160 characters).",
    )

    seo_noindex = models.BooleanField(
        default=False,
        help_text="If checked, this page will be hidden from search engines (noindex).",
        verbose_name="No-Index",
    )
    seo_nofollow = models.BooleanField(
        default=False,
        help_text="If checked, search engines will not follow links on this page (nofollow).",
        verbose_name="No-Follow",
    )

    seo_panels = [
        MultiFieldPanel(
            [
                FieldPanel("meta_title"),
                FieldPanel("meta_description"),
                FieldPanel("seo_noindex"),
                FieldPanel("seo_nofollow"),
            ],
            heading="SEO",
        )
    ]

    class Meta:
        abstract = True

    def get_meta_title(self, site_settings: SiteSettings) -> str:
        """
        Return meta title for <title>.

        Fallback: "{page.title} | {site_settings.company_name}" (or site hostname/name if blank).
        """
        if self.meta_title:
            return str(self.meta_title)

        if getattr(self, "seo_title", None):
            return str(self.seo_title)

        site_name = (site_settings.company_name or "").strip()
        if not site_name:
            # Wagtail SiteSettings always has a related Site, but keep this defensive.
            site_name = (
                getattr(getattr(site_settings, "site", None), "site_name", "") or "Site"
            )

        return f"{self.title} | {site_name}"

    def get_meta_description(self) -> str:
        """
        Return meta description for <meta name="description">.

        Precedence:
        - SeoFieldsMixin.meta_description
        - Wagtail's Page.search_description (Promote tab)
        - empty string
        """
        description = (self.meta_description or "").strip()
        if description:
            return description
        return (getattr(self, "search_description", "") or "").strip()

    def get_canonical_url(self, request: HttpRequest | None = None) -> str:
        """
        Return canonical URL for this page.

        - If request provided: absolute URL.
        - Otherwise: relative (best-effort).
        """
        page: Page = self
        relative = page.get_url(request=request)
        if request is None:
            return relative or ""
        return str(request.build_absolute_uri(relative or "/"))


class OpenGraphMixin(models.Model):
    """
    Adds Open Graph fields + helper methods.

    OG image fallback chain:
    page og_image -> page featured_image (if present) -> SiteSettings.og_default_image
    """

    og_image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Optional. If blank, uses the page featured image (if present), otherwise the site default OG image.",
    )

    open_graph_panels = [
        MultiFieldPanel(
            [
                FieldPanel("og_image"),
            ],
            heading="Social / Open Graph",
        )
    ]

    class Meta:
        abstract = True

    def get_og_title(self, site_settings: SiteSettings) -> str:
        """Default to the SEO title."""
        if isinstance(self, SeoFieldsMixin):
            return self.get_meta_title(site_settings)
        return getattr(self, "title", "")

    def get_og_description(self) -> str:
        """Default to the SEO description."""
        if isinstance(self, SeoFieldsMixin):
            return self.get_meta_description()
        return ""

    def get_og_image(self, site_settings: SiteSettings) -> Any | None:
        """
        Return the best available Wagtail Image for OG rendering.

        Returns a wagtailimages.Image or None.
        """
        og_image = getattr(self, "og_image", None)
        if og_image:
            return og_image

        featured_image = getattr(self, "featured_image", None)
        if featured_image:
            return featured_image

        return getattr(site_settings, "og_default_image", None)


class BreadcrumbMixin(models.Model):
    """Adds a helper to compute breadcrumb trails from the Wagtail tree."""

    class Meta:
        abstract = True

    def get_breadcrumbs(
        self, request: HttpRequest | None = None
    ) -> list[dict[str, Any]]:
        """
        Return breadcrumbs from the site's root page down to this page.

        Each item has: {title, url, is_current}
        """
        page: Page = self
        ancestors = (
            page.get_ancestors(inclusive=True)
            .live()
            .public()
            .exclude(depth=1)  # exclude the Wagtail "Root" node
        )

        crumbs: list[dict[str, Any]] = []
        for ancestor in ancestors:
            url = ancestor.get_url(request=request)
            crumbs.append(
                {
                    "title": ancestor.title,
                    "url": url or "",
                    "is_current": ancestor.id == page.id,
                }
            )
        return crumbs
