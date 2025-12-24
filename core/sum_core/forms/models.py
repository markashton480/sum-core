"""
Name: Form configuration model
Path: core/sum_core/forms/models.py
Purpose: Per-site form settings for spam protection, rate limiting, and notifications.
Family: Forms, Leads, Spam Protection.
Dependencies: Django ORM, Wagtail Site.
"""

from __future__ import annotations

from django.db import models
from wagtail.models import Site


class FormConfiguration(models.Model):
    """
    Per-site form configuration for spam protection and behaviour.

    Each Wagtail Site can have its own FormConfiguration to control:
    - Honeypot field name
    - Rate limiting thresholds
    - Minimum submission time (anti-bot timing check)
    - Notification email address
    """

    site = models.OneToOneField(
        Site,
        on_delete=models.CASCADE,
        related_name="form_configuration",
        help_text="The site this configuration applies to.",
    )

    # Spam protection: Honeypot
    honeypot_field_name = models.CharField(
        max_length=50,
        default="company",
        help_text="Name of the honeypot field. If filled, submission is rejected as spam.",
    )

    # Spam protection: Rate limiting
    rate_limit_per_ip_per_hour = models.PositiveIntegerField(
        default=20,
        help_text="Maximum form submissions allowed per IP address per hour.",
    )

    # Spam protection: Timing
    min_seconds_to_submit = models.PositiveIntegerField(
        default=3,
        help_text="Minimum seconds between form render and submission. Faster submissions are rejected.",
    )

    # Notifications
    lead_notification_email = models.EmailField(
        blank=True,
        help_text="Email address for lead notifications. If blank, falls back to environment variable.",
    )

    # Presentation metadata
    default_form_type = models.CharField(
        max_length=50,
        blank=True,
        help_text="Default form type if not specified in submission.",
    )

    class Meta:
        verbose_name = "Form Configuration"
        verbose_name_plural = "Form Configurations"

    def __str__(self) -> str:
        return f"Form Configuration for {self.site.hostname}"

    @classmethod
    def get_for_site(cls, site: Site) -> FormConfiguration:
        """
        Get or create FormConfiguration for a site.

        Returns the existing configuration or a new instance with defaults.
        The returned instance is always saved to the database.
        """
        from typing import cast

        config, _created = cls.objects.get_or_create(site=site)
        return cast(FormConfiguration, config)

    @classmethod
    def get_defaults(cls) -> dict:
        """Return default configuration values for use when no config exists."""
        return {
            "honeypot_field_name": "company",
            "rate_limit_per_ip_per_hour": 20,
            "min_seconds_to_submit": 3,
        }
