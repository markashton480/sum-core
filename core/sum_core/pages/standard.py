"""
Name: Standard Page Model
Path: core/sum_core/pages/standard.py
Purpose: A reusable general-purpose content page using StreamField with BodyStreamBlock.
Family: SUM Platform – Page Types
Dependencies: Wagtail Page model, sum_core.blocks.base.BodyStreamBlock
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
from wagtail.admin.panels import FieldPanel
from wagtail.fields import StreamField
from wagtail.models import Page


class StandardPage(
    DesktopStickyCTAMixin, SeoFieldsMixin, OpenGraphMixin, BreadcrumbMixin, Page
):
    """
    General-purpose content page for About, FAQ, Terms, Service Overview, etc.

    Uses BodyStreamBlock so editors can compose content blocks (no hero/header
    blocks) while the hero is owned by the page template.
    """

    hero_intro = models.TextField(
        blank=True,
        help_text="Optional intro text displayed in the hero area.",
    )
    body: StreamField = StreamField(
        BodyStreamBlock(),
        blank=True,
        null=True,
        use_json_field=True,
        help_text="Add content blocks to build your page layout.",
    )

    content_panels = Page.content_panels + [
        FieldPanel("hero_intro"),
        FieldPanel("body"),
    ]

    promote_panels = SeoFieldsMixin.promote_panels + OpenGraphMixin.open_graph_panels
    settings_panels = (
        Page.settings_panels + DesktopStickyCTAMixin.desktop_sticky_cta_panels
    )

    # NOTE: parent_page_types is intentionally NOT set here.
    # Wagtail's default (inherited from Page) allows ANY parent page type.
    # Client projects should restrict via their HomePage's subpage_types.
    # Empty list would mean "no parents allowed" (i.e., can't be created).

    # StandardPage is a leaf content page - no child pages allowed
    subpage_types: list[str] = []

    # v0.6 rendering contract: themes own page templates under theme/
    template: str = "theme/standard_page.html"

    class Meta:
        verbose_name = "Standard Page"
        verbose_name_plural = "Standard Pages"

    @property
    def has_hero_block(self) -> bool:
        """Return True because StandardPage hero is template-owned."""
        return True

    @property
    def header_transparent_at_top(self) -> bool:
        """Return True when the header should be transparent at the top."""
        return True
