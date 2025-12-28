"""
Name: Legal Page Model
Path: core/sum_core/pages/legal.py
Purpose: LegalPage model for terms/privacy-style content with section-based TOC.
Family: SUM Platform – Page Types
Dependencies: Wagtail Page model, sum_core.blocks.content.LegalSectionBlock
"""

from __future__ import annotations

from django.db import models
from sum_core.blocks.content import LegalSectionBlock
from sum_core.pages.mixins import BreadcrumbMixin, OpenGraphMixin, SeoFieldsMixin
from wagtail.admin.panels import FieldPanel
from wagtail.fields import StreamField
from wagtail.models import Page


class LegalPage(SeoFieldsMixin, OpenGraphMixin, BreadcrumbMixin, Page):
    """
    Structured legal content page with sections that drive the table of contents.
    """

    last_updated = models.DateField(
        null=True,
        blank=True,
        help_text="Optional date displayed near the page title.",
    )

    sections: StreamField = StreamField(
        [("section", LegalSectionBlock())],
        blank=True,
        null=True,
        use_json_field=True,
        help_text="Add sections with anchors, headings, and body copy.",
    )

    content_panels = Page.content_panels + [
        FieldPanel("last_updated"),
        FieldPanel("sections"),
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

    # LegalPage is a leaf page - no child pages allowed
    subpage_types: list[str] = []

    # v0.6 rendering contract: themes own page templates under theme/
    template: str = "theme/legal_page.html"

    class Meta:
        verbose_name = "Legal Page"
        verbose_name_plural = "Legal Pages"

    @property
    def has_hero_block(self) -> bool:
        """Treat LegalPage as having a hero section for theme layout."""
        return True
