"""
Name: Service Page Models
Path: core/sum_core/pages/services.py
Purpose: ServiceIndexPage and ServicePage models for service content organization.
Family: SUM Platform – Page Types
Dependencies: Wagtail Page model, sum_core.blocks.base.PageStreamBlock
"""

from __future__ import annotations

from django.db import models
from sum_core.blocks.base import BodyStreamBlock
from sum_core.pages.mixins import (
    BreadcrumbMixin,
    DesktopStickyCTAMixin,
    OpenGraphMixin,
    SeoFieldsMixin,
)
from wagtail.admin.panels import FieldPanel, ObjectList, TabbedInterface
from wagtail.fields import RichTextField, StreamField
from wagtail.models import Page


class ServiceIndexPage(
    DesktopStickyCTAMixin, SeoFieldsMixin, OpenGraphMixin, BreadcrumbMixin, Page
):
    """
    Landing page for services that lists all child ServicePage items.

    Provides an intro StreamField for content above the service listing,
    and automatically displays all published child ServicePage instances
    in a grid.
    """

    hero_status = models.CharField(
        blank=True,
        max_length=120,
        help_text="Optional eyebrow/status line above the hero heading.",
    )
    hero_heading = RichTextField(
        blank=True,
        features=["italic", "bold"],
        help_text="Main hero heading. Use Italic for accent emphasis.",
    )
    hero_subheading = models.TextField(
        blank=True,
        help_text="Optional supporting copy shown alongside the hero heading.",
    )
    hero_gradient_style = models.CharField(
        max_length=16,
        choices=[
            ("primary", "Primary gradient"),
            ("secondary", "Secondary gradient"),
            ("accent", "Accent gradient"),
        ],
        default="primary",
        help_text="Gradient theme for the hero background.",
    )
    intro: StreamField = StreamField(
        BodyStreamBlock(),
        blank=True,
        null=True,
        use_json_field=True,
        help_text="Optional intro content area displayed above the service grid.",
    )
    show_service_grid = models.BooleanField(
        default=True,
        help_text="Show the automatic grid of child services below the intro.",
    )

    content_panels = Page.content_panels + [
        FieldPanel("hero_status"),
        FieldPanel("hero_heading"),
        FieldPanel("hero_subheading"),
        FieldPanel("hero_gradient_style"),
        FieldPanel("intro"),
        FieldPanel("show_service_grid"),
    ]

    promote_panels = SeoFieldsMixin.promote_panels + OpenGraphMixin.open_graph_panels
    settings_panels = (
        Page.settings_panels + DesktopStickyCTAMixin.desktop_sticky_cta_panels
    )

    edit_handler = TabbedInterface(
        [
            ObjectList(content_panels, heading="Content"),
            ObjectList(promote_panels, heading="Promote"),
            ObjectList(settings_panels, heading="Settings"),
            ObjectList(SeoFieldsMixin.seo_analysis_panels, heading="SEO"),
        ]
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
        services = []
        if self.show_service_grid:
            services = self.get_children().live().public().type(ServicePage)

        context["services"] = services
        return context

    @property
    def header_transparent_at_top(self) -> bool:
        """Return True when the header should be transparent at the top."""
        return True


class ServicePage(
    DesktopStickyCTAMixin, SeoFieldsMixin, OpenGraphMixin, BreadcrumbMixin, Page
):
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
        BodyStreamBlock(),
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

    promote_panels = SeoFieldsMixin.promote_panels + OpenGraphMixin.open_graph_panels
    settings_panels = (
        Page.settings_panels + DesktopStickyCTAMixin.desktop_sticky_cta_panels
    )

    edit_handler = TabbedInterface(
        [
            ObjectList(content_panels, heading="Content"),
            ObjectList(promote_panels, heading="Promote"),
            ObjectList(settings_panels, heading="Settings"),
            ObjectList(SeoFieldsMixin.seo_analysis_panels, heading="SEO"),
        ]
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
        """Return True because ServicePage hero is template-owned."""
        return True

    @property
    def header_transparent_at_top(self) -> bool:
        """Return True when the header should be transparent at the top."""
        return True
