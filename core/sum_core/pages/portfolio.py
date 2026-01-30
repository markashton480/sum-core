"""
Name: Portfolio Page Models
Path: core/sum_core/pages/portfolio.py
Purpose: Portfolio index and case study page models.
Family: SUM Platform – Page Types
Dependencies: Wagtail Page model, sum_core.blocks.base.PageStreamBlock
"""

from __future__ import annotations

from django.db import models
from django.utils.text import slugify
from sum_core.blocks import BodyStreamBlock
from sum_core.pages.mixins import (
    BreadcrumbMixin,
    DesktopStickyCTAMixin,
    OpenGraphMixin,
    SeoFieldsMixin,
)
from sum_core.utils.links import validate_safe_link
from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField, StreamField
from wagtail.models import Page


class PortfolioIndexPage(
    DesktopStickyCTAMixin, SeoFieldsMixin, OpenGraphMixin, BreadcrumbMixin, Page
):
    """
    Portfolio landing page that lists child case studies.

    URL: /portfolio/
    """

    intro = RichTextField(
        blank=True,
        help_text="Optional intro text displayed in the portfolio header.",
    )
    hero_heading = RichTextField(
        blank=True,
        features=["italic", "bold", "accent"],
        help_text="Hero heading copy; supports italic/bold/accent emphasis.",
    )
    featured_case_study = models.ForeignKey(
        "sum_core_pages.CaseStudyPage",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Optional featured case study highlighted above the grid.",
    )
    portfolio_quote = models.TextField(
        blank=True,
        help_text="Optional quote displayed within the portfolio grid.",
    )
    cta_eyebrow = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional eyebrow text for the portfolio CTA section.",
    )
    cta_heading = models.CharField(
        max_length=255,
        blank=True,
        help_text="Main heading for the portfolio CTA section.",
    )
    cta_primary_label = models.CharField(
        max_length=100,
        blank=True,
        help_text="Label for the primary CTA button.",
    )
    cta_primary_link = models.CharField(
        max_length=255,
        blank=True,
        help_text="URL or anchor for the primary CTA button.",
        validators=[validate_safe_link],
    )
    cta_secondary_label = models.CharField(
        max_length=100,
        blank=True,
        help_text="Label for the secondary CTA button.",
    )
    cta_secondary_link = models.CharField(
        max_length=255,
        blank=True,
        help_text="URL or anchor for the secondary CTA button.",
        validators=[validate_safe_link],
    )

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
        FieldPanel("hero_heading"),
        FieldPanel("featured_case_study"),
        FieldPanel("portfolio_quote"),
        FieldPanel("cta_eyebrow"),
        FieldPanel("cta_heading"),
        FieldPanel("cta_primary_label"),
        FieldPanel("cta_primary_link"),
        FieldPanel("cta_secondary_label"),
        FieldPanel("cta_secondary_link"),
    ]

    promote_panels = SeoFieldsMixin.promote_panels + OpenGraphMixin.open_graph_panels
    settings_panels = (
        Page.settings_panels + DesktopStickyCTAMixin.desktop_sticky_cta_panels
    )

    # NOTE: parent_page_types is intentionally NOT set here.
    # Wagtail's default (inherited from Page) allows ANY parent page type.
    # Client projects should restrict via their HomePage's subpage_types.
    subpage_types: list[str] = ["sum_core_pages.CaseStudyPage"]

    # v0.6 rendering contract: themes own page templates under theme/
    template: str = "theme/portfolio_index_page.html"

    class Meta:
        verbose_name = "Portfolio Index Page"
        verbose_name_plural = "Portfolio Index Pages"

    @property
    def header_transparent_at_top(self) -> bool:
        """Return True when the header should be transparent at the top."""
        return True

    def get_case_studies(self) -> models.QuerySet[CaseStudyPage]:
        """Return live CaseStudyPage children ordered by project date."""
        return (
            CaseStudyPage.objects.child_of(self)
            .live()
            .public()
            .order_by("-project_date", "-first_published_at")
        )

    def _get_filter_values(
        self, case_studies: models.QuerySet[CaseStudyPage]
    ) -> tuple[list[str], list[str]]:
        categories = sorted(
            {
                value.strip()
                for value in case_studies.values_list("category", flat=True)
                if value and value.strip()
            }
        )
        types = sorted(
            {
                value.strip()
                for value in case_studies.values_list("project_type", flat=True)
                if value and value.strip()
            }
        )
        return categories, types

    def get_context(self, request, *args, **kwargs):
        """
        Add case studies, featured item, and filters to template context.

        Query params:
        - category: slugified category filter (used to seed client-side state)
        - type: slugified project type filter (used to seed client-side state)
        """
        context = super().get_context(request, *args, **kwargs)
        case_studies = self.get_case_studies()
        categories, types = self._get_filter_values(case_studies)
        category_slugs = {slugify(category) for category in categories if category}
        type_slugs = {slugify(value) for value in types if value}

        query_params = request.GET if request is not None else {}
        selected_category = slugify(query_params.get("category", "").strip())
        selected_type = slugify(query_params.get("type", "").strip())

        if selected_category and selected_category not in category_slugs:
            selected_category = ""
        if selected_type and selected_type not in type_slugs:
            selected_type = ""

        featured_case_study = None
        if self.featured_case_study_id:
            featured_case_study = case_studies.filter(
                pk=self.featured_case_study_id
            ).first()
        if featured_case_study is not None:
            case_studies = case_studies.exclude(pk=featured_case_study.pk)

        context.update(
            {
                "case_studies": case_studies,
                "featured_case_study": featured_case_study,
                "categories": categories,
                "types": types,
                "selected_category": selected_category,
                "selected_type": selected_type,
            }
        )
        return context


class CaseStudyPage(
    DesktopStickyCTAMixin, SeoFieldsMixin, OpenGraphMixin, BreadcrumbMixin, Page
):
    """
    Portfolio case study detail page.

    URL: /portfolio/<slug>/
    """

    client_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Client or project name for this case study.",
    )
    project_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of completion or publication for the project.",
    )
    outcomes = models.TextField(
        blank=True,
        help_text="Optional outcome summary for the project.",
    )
    category = models.CharField(
        max_length=100,
        blank=True,
        help_text="Optional filter category, e.g. Kitchens, Restoration.",
    )
    project_type = models.CharField(
        max_length=100,
        blank=True,
        help_text="Optional filter type label for portfolio filtering.",
    )
    portfolio_number = models.CharField(
        max_length=20,
        blank=True,
        help_text="Optional display number for portfolio highlights.",
    )
    location = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional location label for portfolio metadata.",
    )
    material = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional material label for portfolio metadata.",
    )
    portfolio_summary = models.TextField(
        blank=True,
        help_text="Optional summary used in portfolio grid cards.",
    )
    portfolio_quote = models.TextField(
        blank=True,
        help_text="Optional quote used in portfolio metadata highlights.",
    )
    body: StreamField = StreamField(
        BodyStreamBlock(),
        blank=False,
        use_json_field=True,
        help_text="Case study content.",
    )

    content_panels = Page.content_panels + [
        FieldPanel("client_name"),
        FieldPanel("project_date"),
        FieldPanel("category"),
        FieldPanel("project_type"),
        FieldPanel("outcomes"),
        FieldPanel("portfolio_number"),
        FieldPanel("location"),
        FieldPanel("material"),
        FieldPanel("portfolio_summary"),
        FieldPanel("portfolio_quote"),
        FieldPanel("body"),
    ]

    promote_panels = SeoFieldsMixin.promote_panels + OpenGraphMixin.open_graph_panels
    settings_panels = (
        Page.settings_panels + DesktopStickyCTAMixin.desktop_sticky_cta_panels
    )

    parent_page_types: list[str] = ["sum_core_pages.PortfolioIndexPage"]
    subpage_types: list[str] = []

    template: str = "theme/case_study_page.html"

    class Meta:
        verbose_name = "Case Study Page"
        verbose_name_plural = "Case Study Pages"

    @property
    def header_transparent_at_top(self) -> bool:
        """Return True when the header should be transparent at the top."""
        return True
