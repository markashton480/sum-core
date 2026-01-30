"""
Name: ContentGap Model
Path: core/sum_core/seo_engine/gaps.py
Purpose: Detect and track content opportunities and missing schema.
Family: SEO Engine
Dependencies: Django ORM, Wagtail Page and Site models.
"""

from __future__ import annotations

from django.db import models
from wagtail.models import Page, Site


class GapType(models.TextChoices):
    """Content gap type choices."""

    MISSING_PAGE = "missing_page", "Missing Page"
    MISSING_SCHEMA = "missing_schema", "Missing Schema"
    THIN_CONTENT = "thin_content", "Thin Content"


class ContentGap(models.Model):
    """
    Content opportunity or missing schema detection.

    Tracks content gaps at site level (or optionally page level).
    Supports dismissal workflow to hide irrelevant suggestions.
    """

    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        related_name="content_gaps",
        help_text="The site this gap belongs to.",
    )

    gap_type = models.CharField(
        max_length=50,
        choices=GapType.choices,
        help_text="Type of content gap detected.",
    )

    title = models.CharField(
        max_length=200,
        help_text="Brief title describing the gap.",
    )

    description = models.TextField(
        help_text="Detailed description and recommendation.",
    )

    confidence_score = models.FloatField(
        default=0.0,
        help_text="Confidence score (0.0-1.0).",
    )

    source_page = models.ForeignKey(
        Page,
        on_delete=models.CASCADE,
        related_name="content_gaps",
        null=True,
        blank=True,
        help_text="Optional source page (for page-level gaps).",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this gap was detected.",
    )

    dismissed = models.BooleanField(
        default=False,
        help_text="Whether this gap has been dismissed.",
    )

    class Meta:
        verbose_name = "Content Gap"
        verbose_name_plural = "Content Gaps"
        ordering = ["-confidence_score", "-created_at"]

    def __str__(self) -> str:
        dismissed_suffix = " (dismissed)" if self.dismissed else ""
        return f"{self.gap_type}: {self.title}{dismissed_suffix}"
