"""
Name: Alert Banner Models
Path: core/sum_core/banners/models.py
Purpose: Define alert banner snippet for global notifications.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.snippets.models import register_snippet


class AlertBannerQuerySet(models.QuerySet):
    def active(self) -> AlertBannerQuerySet:
        now = timezone.now()
        return (
            self.filter(
                is_active=True,
            )
            .filter(models.Q(start_date__isnull=True) | models.Q(start_date__lte=now))
            .filter(models.Q(end_date__isnull=True) | models.Q(end_date__gte=now))
        )


@register_snippet
class AlertBanner(models.Model):
    message = models.CharField(max_length=200)
    link_text = models.CharField(max_length=50, blank=True)
    link_url = models.URLField(blank=True)
    background_color = models.CharField(
        max_length=20,
        choices=[
            ("bg-primary", "Primary"),
            ("bg-secondary", "Secondary"),
            ("bg-accent", "Accent"),
        ],
        default="bg-primary",
    )
    is_active = models.BooleanField(default=False)
    start_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Banner will not show before this date/time.",
    )
    end_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Banner will not show after this date/time.",
    )
    dismissible = models.BooleanField(
        default=True,
        help_text="Allow users to dismiss this banner.",
    )

    objects = AlertBannerQuerySet.as_manager()

    panels = [
        FieldPanel("message"),
        MultiFieldPanel(
            [
                FieldPanel("link_text"),
                FieldPanel("link_url"),
            ],
            heading="Optional Link",
        ),
        FieldPanel("background_color"),
        FieldPanel("dismissible"),
        MultiFieldPanel(
            [
                FieldPanel("is_active"),
                FieldPanel("start_date"),
                FieldPanel("end_date"),
            ],
            heading="Scheduling",
        ),
    ]

    class Meta:
        verbose_name = "Alert Banner"
        verbose_name_plural = "Alert Banners"

    def __str__(self) -> str:
        return self.message[:60]

    def clean(self) -> None:
        errors = {}

        if self.start_date and self.end_date and self.end_date < self.start_date:
            errors["end_date"] = ValidationError(
                "End date must be after the start date."
            )

        if self.link_text and not self.link_url:
            errors["link_url"] = ValidationError(
                "Add a URL when link text is provided."
            )
        elif self.link_url and not self.link_text:
            errors["link_text"] = ValidationError(
                "Add link text when a URL is provided."
            )

        if errors:
            raise ValidationError(errors)

        super().clean()
