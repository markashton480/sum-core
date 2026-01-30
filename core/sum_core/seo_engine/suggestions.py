"""
Name: InternalLinkSuggestion Model
Path: core/sum_core/seo_engine/suggestions.py
Purpose: Store internal link recommendations with status tracking.
Family: SEO Engine
Dependencies: Django ORM, Wagtail Page model.
"""

from __future__ import annotations

from django.db import models
from wagtail.models import Page


class SuggestionStatus(models.TextChoices):
    """Status choices for internal link suggestions."""

    PENDING = "pending", "Pending"
    ACCEPTED = "accepted", "Accepted"
    DISMISSED = "dismissed", "Dismissed"


class InternalLinkSuggestion(models.Model):
    """
    Internal link recommendation from source page to target page.

    Tracks suggested links with relevance scores and status workflow.
    Prevents duplicate suggestions with unique constraint on (source, target).
    """

    source_page = models.ForeignKey(
        Page,
        on_delete=models.CASCADE,
        related_name="outgoing_link_suggestions",
        help_text="The page where the link should be added.",
    )

    target_page = models.ForeignKey(
        Page,
        on_delete=models.CASCADE,
        related_name="incoming_link_suggestions",
        help_text="The page being suggested as link target.",
    )

    @property
    def source_page_specific(self):
        """Return the specific page type for source_page."""
        return self.source_page.specific

    @property
    def target_page_specific(self):
        """Return the specific page type for target_page."""
        return self.target_page.specific

    anchor_text = models.CharField(
        max_length=200,
        help_text="Suggested anchor text for the link.",
    )

    relevance_score = models.FloatField(
        default=0.0,
        help_text="Relevance score (0.0-1.0).",
    )

    status = models.CharField(
        max_length=20,
        choices=SuggestionStatus.choices,
        default=SuggestionStatus.PENDING,
        help_text="Current status of this suggestion.",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this suggestion was created.",
    )

    class Meta:
        verbose_name = "Internal Link Suggestion"
        verbose_name_plural = "Internal Link Suggestions"
        constraints = [
            models.UniqueConstraint(
                fields=["source_page", "target_page"],
                name="unique_source_target_link_suggestion",
            ),
        ]
        ordering = ["-relevance_score", "-created_at"]

    def __str__(self) -> str:
        return (
            f"Link: {self.source_page.title} → {self.target_page.title} ({self.status})"
        )

    @property
    def confidence(self) -> float:
        """Alias for relevance_score for backward compatibility."""
        return self.relevance_score

    def accept(self) -> None:
        """Mark this suggestion as accepted."""
        self.status = SuggestionStatus.ACCEPTED
        self.save(update_fields=["status"])

    def dismiss(self) -> None:
        """Mark this suggestion as dismissed."""
        self.status = SuggestionStatus.DISMISSED
        self.save(update_fields=["status"])
