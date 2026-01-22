"""
Name: HomePage Model
Path: core/sum_core/pages/home.py
Purpose: Provide a HomePage type with template-owned hero, SEO fields, and one-per-site enforcement.
Family: SUM Platform Core Pages
Dependencies: Wagtail Page model, sum_core.pages.mixins, sum_core.blocks.base.BodyStreamBlock
"""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models
from modelcluster.fields import ParentalKey
from sum_core.blocks import BodyStreamBlock
from sum_core.pages.mixins import (
    BreadcrumbMixin,
    DesktopStickyCTAMixin,
    OpenGraphMixin,
    SeoFieldsMixin,
)
from sum_core.utils.links import validate_safe_link
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.fields import RichTextField, StreamField
from wagtail.models import Orderable, Page


class HomePage(
    DesktopStickyCTAMixin, SeoFieldsMixin, OpenGraphMixin, BreadcrumbMixin, Page
):
    """
    Homepage with template-owned hero, SEO fields, and one-per-site enforcement.

    The hero is defined via dedicated model fields (not in StreamField) so it cannot be
    accidentally deleted by editors. The body uses BodyStreamBlock which excludes hero blocks.
    """

    # Hero fields (template-owned)
    hero_status = models.CharField(
        blank=True,
        max_length=120,
        help_text="Optional eyebrow/status line above the hero heading.",
    )
    hero_headline = RichTextField(
        blank=True,
        features=["italic", "bold"],
        help_text="Main hero heading. Use Italic for accent emphasis.",
    )
    hero_subheadline = models.TextField(
        blank=True,
        help_text="Optional supporting copy shown alongside the hero heading.",
    )
    hero_image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Hero background image.",
    )
    hero_image_alt = models.CharField(
        blank=True,
        max_length=255,
        help_text="Alt text for the hero image.",
    )
    hero_overlay_opacity = models.CharField(
        max_length=16,
        choices=[
            ("none", "None"),
            ("light", "Light"),
            ("medium", "Medium"),
            ("strong", "Strong"),
        ],
        default="medium",
        help_text="Overlay darkness level for text readability.",
    )
    hero_layout = models.CharField(
        max_length=16,
        choices=[
            ("full", "Full width"),
            ("split", "Split layout"),
        ],
        default="full",
        help_text="Hero section layout style.",
    )
    hero_floating_card_label = models.CharField(
        blank=True,
        max_length=50,
        help_text="Optional floating card label text.",
    )
    hero_floating_card_value = models.CharField(
        blank=True,
        max_length=50,
        help_text="Optional floating card value text.",
    )

    # Body StreamField (excludes hero blocks)
    body: StreamField = StreamField(
        BodyStreamBlock(),
        blank=True,
        null=True,
        use_json_field=True,
        help_text="Add content blocks to build your homepage layout.",
    )

    content_panels = Page.content_panels + [
        MultiFieldPanel(
            [
                FieldPanel("hero_status"),
                FieldPanel("hero_headline"),
                FieldPanel("hero_subheadline"),
                FieldPanel("hero_image"),
                FieldPanel("hero_image_alt"),
                FieldPanel("hero_overlay_opacity"),
                FieldPanel("hero_layout"),
                FieldPanel("hero_floating_card_label"),
                FieldPanel("hero_floating_card_value"),
                InlinePanel("hero_ctas", label="Hero CTAs", max_num=2),
            ],
            heading="Hero Section",
        ),
        FieldPanel("body"),
    ]

    promote_panels = SeoFieldsMixin.promote_panels + OpenGraphMixin.open_graph_panels
    settings_panels = (
        Page.settings_panels + DesktopStickyCTAMixin.desktop_sticky_cta_panels
    )

    # HomePage can only be created under the root page
    parent_page_types: list[str] = ["wagtailcore.Page"]

    # HomePage can have child pages - explicitly list allowed types
    subpage_types: list[str] = [
        "sum_core_pages.StandardPage",
        "sum_core_pages.ServiceIndexPage",
        "sum_core_pages.BlogIndexPage",
        "sum_core_pages.PortfolioIndexPage",
        "sum_core_pages.LegalPage",
    ]

    # v0.6 rendering contract: themes own page templates under theme/
    template: str = "theme/home_page.html"

    class Meta:
        verbose_name = "Home Page"
        verbose_name_plural = "Home Pages"

    @classmethod
    def can_create_at(cls, parent: Page) -> bool:
        """Enforce root-only creation for HomePage."""
        return bool(parent.is_root() and super().can_create_at(parent))

    def clean(self) -> None:
        """Validate that only one HomePage exists in the database."""
        super().clean()
        if HomePage.objects.exclude(pk=self.pk).exists():
            raise ValidationError(
                {"title": "Only one HomePage is allowed in the database."}
            )

    @property
    def has_hero_block(self) -> bool:
        """Return True because HomePage hero is template-owned."""
        return True

    @property
    def header_transparent_at_top(self) -> bool:
        """Return True when the header should be transparent at the top."""
        return True


class HomePageHeroCTA(Orderable):
    """CTA button for the HomePage hero section."""

    page = ParentalKey(
        HomePage,
        related_name="hero_ctas",
        on_delete=models.CASCADE,
    )
    label = models.CharField(
        max_length=50,
        help_text="Button text (e.g., 'Get Started', 'Learn More').",
    )
    url = models.CharField(
        max_length=255,
        validators=[validate_safe_link],
        help_text="URL or anchor (e.g., '/contact/' or '#contact').",
    )
    style = models.CharField(
        max_length=16,
        choices=[
            ("primary", "Primary"),
            ("outline", "Outline"),
        ],
        default="primary",
        help_text="Button visual style.",
    )
    open_in_new_tab = models.BooleanField(
        default=False,
        help_text="Open link in a new browser tab.",
    )

    panels = [
        FieldPanel("label"),
        FieldPanel("url"),
        FieldPanel("style"),
        FieldPanel("open_in_new_tab"),
    ]

    class Meta(Orderable.Meta):
        verbose_name = "Hero CTA"
        verbose_name_plural = "Hero CTAs"
