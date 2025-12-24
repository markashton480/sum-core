"""
HomePage model for this client project.

Demonstrates how to build a HomePage using sum_core mixins and blocks
as a standalone client project.

Features:
- StreamField body using sum_core's PageStreamBlock
- SEO fields via SeoFieldsMixin
- Open Graph image via OpenGraphMixin
- Breadcrumb support via BreadcrumbMixin
- Only one HomePage allowed per site
"""
from __future__ import annotations

from django.core.exceptions import ValidationError
from sum_core.blocks import PageStreamBlock
from sum_core.pages.mixins import BreadcrumbMixin, OpenGraphMixin, SeoFieldsMixin
from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField, StreamField
from wagtail.models import Page


class HomePage(SeoFieldsMixin, OpenGraphMixin, BreadcrumbMixin, Page):
    """
    Homepage for this client project.

    Uses sum_core mixins for SEO, Open Graph, and breadcrumbs.
    Body content is built using sum_core's PageStreamBlock.
    """

    intro: RichTextField = RichTextField(blank=True)
    body: StreamField = StreamField(
        PageStreamBlock(),
        blank=True,
        null=True,
        use_json_field=True,
        help_text="Add content blocks to build your homepage layout.",
    )

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
        FieldPanel("body"),
    ]

    promote_panels = (
        SeoFieldsMixin.seo_panels
        + OpenGraphMixin.open_graph_panels
        + Page.promote_panels
    )

    # HomePage can only be created under the root page
    parent_page_types: list[str] = ["wagtailcore.Page"]

    # HomePage can have child pages from sum_core
    subpage_types: list[str] = [
        "sum_core_pages.StandardPage",
        "sum_core_pages.ServiceIndexPage",
    ]

    # Use sum_core's home page template
    template: str = "sum_core/home_page.html"

    class Meta:
        verbose_name = "Home Page"
        verbose_name_plural = "Home Pages"

    @classmethod
    def can_create_at(cls, parent: Page) -> bool:
        """
        Enforce root-only creation for HomePage.

        This is used by Wagtail admin UI, but also helps prevent programmatic
        misuse when callers respect the standard Wagtail create APIs.
        """
        return bool(parent.is_root() and super().can_create_at(parent))

    def clean(self) -> None:
        """
        Validate that only one HomePage exists.

        This rule is enforced at the model layer so programmatic creation can't
        bypass it.
        """
        super().clean()

        if HomePage.objects.exclude(pk=self.pk).exists():
            raise ValidationError({"title": "Only one HomePage is allowed per site."})

    @property
    def has_hero_block(self) -> bool:
        """Check if the StreamField body contains any hero blocks."""
        if not self.body:
            return False

        # Check against the block names defined in PageStreamBlock
        hero_block_types = ["hero_image", "hero_gradient", "hero"]

        for block in self.body:
            if block.block_type in hero_block_types:
                return True
        return False
