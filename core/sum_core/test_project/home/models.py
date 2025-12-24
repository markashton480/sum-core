"""
Name: Test Project Home Page Models
Path: core/sum_core/test_project/home/models.py
Purpose: Provide a HomePage type with StreamField body, SEO fields, and one-per-site enforcement.
Family: Used only by sum_core.test_project; client projects will define their own page types later.
Dependencies: Wagtail Page model, sum_core.pages.mixins, sum_core.blocks.base.PageStreamBlock, sum_core base template.
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
    Homepage for the test project with StreamField body, SEO fields, and one-per-site enforcement.

    Satisfies US-P01 Homepage acceptance criteria:
    - StreamField body accepting all homepage blocks (PageStreamBlock)
    - SEO fields (meta title, meta description) via SeoFieldsMixin
    - Open Graph image via OpenGraphMixin
    - Only one HomePage allowed per site (enforced via clean method)
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

    # HomePage can have child pages - explicitly list allowed types
    subpage_types: list[str] = [
        "sum_core_pages.StandardPage",
        "sum_core_pages.ServiceIndexPage",
    ]

    # v0.6 rendering contract: themes own page templates under theme/
    template: str = "theme/home_page.html"

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

        # StreamField iteration yields blocks that behave like bound blocks
        for block in self.body:
            if block.block_type in hero_block_types:
                return True
        return False
