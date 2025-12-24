"""
Name: Service Page Models
Path: core/sum_core/pages/services.py
Purpose: ServiceIndexPage and ServicePage models for service content organization.
Family: SUM Platform – Page Types
Dependencies: Wagtail Page model, sum_core.blocks.base.PageStreamBlock
"""

from __future__ import annotations

from django.db import models
from sum_core.blocks.base import PageStreamBlock
from sum_core.pages.mixins import BreadcrumbMixin, OpenGraphMixin, SeoFieldsMixin
from wagtail.admin.panels import FieldPanel
from wagtail.fields import StreamField
from wagtail.models import Page


class ServiceIndexPage(SeoFieldsMixin, OpenGraphMixin, BreadcrumbMixin, Page):
    """
    Landing page for services that lists all child ServicePage items.

    Provides an intro StreamField for content above the service listing,
    and automatically displays all published child ServicePage instances
    in a grid.
    """

    intro: StreamField = StreamField(
        PageStreamBlock(),
        blank=True,
        null=True,
        use_json_field=True,
        help_text="Optional intro content area displayed above the service grid.",
    )

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
    ]

    promote_panels = (
        SeoFieldsMixin.seo_panels
        + OpenGraphMixin.open_graph_panels
        + Page.promote_panels
    )

    # NOTE: parent_page_types is intentionally NOT set here.
    # Wagtail's default (inherited from Page) allows ANY parent page type.
    # Client projects should restrict via their HomePage's subpage_types.
    # Empty list would mean "no parents allowed" (i.e., can't be created).

    # Only allow ServicePage children
    subpage_types: list[str] = ["sum_core_pages.ServicePage"]

    # v0.6 rendering contract: themes own page templates under theme/
    template: str = "theme/service_index_page.html"

    class Meta:
        verbose_name = "Service Index Page"
        verbose_name_plural = "Service Index Pages"

    def get_context(self, request, *args, **kwargs):
        """Add live, public ServicePage children to context."""
        context = super().get_context(request, *args, **kwargs)

        # Get all live, public ServicePage children
        services = self.get_children().live().public().specific().type(ServicePage)

        context["services"] = services
        return context


class ServicePage(SeoFieldsMixin, OpenGraphMixin, BreadcrumbMixin, Page):
    """
    Individual service detail page.

    Contains featured image, short description, and full StreamField body
    for detailed service information. Must be created under ServiceIndexPage.
    """

    featured_image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Featured image displayed at the top of the service page and in service listings.",
    )

    short_description = models.CharField(
        max_length=250,
        blank=True,
        help_text="Brief description shown in service listings and below the page title (max 250 characters).",
    )

    body: StreamField = StreamField(
        PageStreamBlock(),
        blank=True,
        null=True,
        use_json_field=True,
        help_text="Detailed content for this service.",
    )

    content_panels = Page.content_panels + [
        FieldPanel("featured_image"),
        FieldPanel("short_description"),
        FieldPanel("body"),
    ]

    promote_panels = (
        SeoFieldsMixin.seo_panels
        + OpenGraphMixin.open_graph_panels
        + Page.promote_panels
    )

    # ServicePage must be created under ServiceIndexPage
    parent_page_types: list[str] = ["sum_core_pages.ServiceIndexPage"]

    # ServicePage is a leaf page - no children allowed
    subpage_types: list[str] = []

    # v0.6 rendering contract: themes own page templates under theme/
    template: str = "theme/service_page.html"

    class Meta:
        verbose_name = "Service Page"
        verbose_name_plural = "Service Pages"

    @property
    def has_hero_block(self) -> bool:
        """Check if the StreamField body contains any hero blocks."""
        if not self.body:
            return False

        hero_block_types = ["hero_image", "hero_gradient", "hero"]

        for block in self.body:
            if block.block_type in hero_block_types:
                return True
        return False
