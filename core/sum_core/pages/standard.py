"""
Name: Standard Page Model
Path: core/sum_core/pages/standard.py
Purpose: A reusable general-purpose content page using StreamField with PageStreamBlock.
Family: SUM Platform – Page Types
Dependencies: Wagtail Page model, sum_core.blocks.base.PageStreamBlock
"""

from __future__ import annotations

from sum_core.blocks.base import PageStreamBlock
from sum_core.pages.mixins import BreadcrumbMixin, OpenGraphMixin, SeoFieldsMixin
from wagtail.admin.panels import FieldPanel
from wagtail.fields import StreamField
from wagtail.models import Page


class StandardPage(SeoFieldsMixin, OpenGraphMixin, BreadcrumbMixin, Page):
    """
    General-purpose content page for About, FAQ, Terms, Service Overview, etc.

    Uses the same PageStreamBlock as HomePage, allowing editors to compose pages
    from the full set of available blocks (hero, trust strip, testimonials,
    services, content blocks, etc.) without developer involvement.
    """

    body: StreamField = StreamField(
        PageStreamBlock(),
        blank=True,
        null=True,
        use_json_field=True,
        help_text="Add content blocks to build your page layout.",
    )

    content_panels = Page.content_panels + [
        FieldPanel("body"),
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

    # StandardPage is a leaf content page - no child pages allowed
    subpage_types: list[str] = []

    # v0.6 rendering contract: themes own page templates under theme/
    template: str = "theme/standard_page.html"

    class Meta:
        verbose_name = "Standard Page"
        verbose_name_plural = "Standard Pages"

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
