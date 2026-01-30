"""
Name: PageSEOAnalysis Model
Path: core/sum_core/seo_engine/analysis.py
Purpose: Store per-page SEO analysis results and health scores.
Family: SEO Engine
Dependencies: Django ORM, Wagtail Page model.
"""

from __future__ import annotations

from django.db import models
from wagtail.models import Page


class PageSEOAnalysis(models.Model):
    """
    Per-page SEO analysis results with caching.

    Stores analysis data, health score, and version for cache invalidation.
    One analysis record per page (unique constraint).
    """

    page = models.OneToOneField(
        Page,
        on_delete=models.CASCADE,
        related_name="seo_analysis",
        help_text="The page this analysis belongs to.",
    )

    analysis_data = models.JSONField(
        default=dict,
        help_text="Analysis results (issues, metrics, etc.).",
    )

    health_score = models.PositiveIntegerField(
        default=0,
        help_text="SEO health score (0-100).",
    )

    analyzed_at = models.DateTimeField(
        auto_now=True,
        help_text="When this analysis was last updated.",
    )

    version = models.PositiveIntegerField(
        default=1,
        help_text="Cache invalidation version.",
    )

    class Meta:
        verbose_name = "Page SEO Analysis"
        verbose_name_plural = "Page SEO Analyses"

    def __str__(self) -> str:
        return f"SEO Analysis: {self.page.title} (Score: {self.health_score})"
