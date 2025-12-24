"""
Name: Lead persistence & attribution
Path: core/sum_core/leads/models.py
Purpose: Store all inbound leads reliably ("no lost leads" invariant) with attribution tracking.
Family: Lead management, forms, integrations, admin visibility, reporting.
Dependencies: Django ORM, Wagtail Page model.
"""

from __future__ import annotations

from django.db import models
from wagtail.models import Page


class LeadSource(models.TextChoices):
    """Derived lead source categories matching SSOT 8.2."""

    GOOGLE_ADS = "google_ads", "Google Ads"
    META_ADS = "meta_ads", "Meta Ads"
    BING_ADS = "bing_ads", "Bing Ads"
    SEO = "seo", "SEO"
    DIRECT = "direct", "Direct"
    REFERRAL = "referral", "Referral"
    OFFLINE = "offline", "Offline"
    UNKNOWN = "unknown", "Unknown"


class EmailStatus(models.TextChoices):
    """Status of email notification delivery."""

    PENDING = "pending", "Pending"
    IN_PROGRESS = "in_progress", "In progress"
    SENT = "sent", "Sent"
    FAILED = "failed", "Failed"


class WebhookStatus(models.TextChoices):
    """Status of webhook notification delivery."""

    PENDING = "pending", "Pending"
    IN_PROGRESS = "in_progress", "In progress"
    SENT = "sent", "Sent"
    FAILED = "failed", "Failed"
    DISABLED = "disabled", "Disabled"


class ZapierStatus(models.TextChoices):
    """Status of Zapier webhook delivery (M4-007)."""

    PENDING = "pending", "Pending"
    IN_PROGRESS = "in_progress", "In progress"
    SENT = "sent", "Sent"
    FAILED = "failed", "Failed"
    DISABLED = "disabled", "Disabled"


class Lead(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "New"
        CONTACTED = "contacted", "Contacted"
        QUOTED = "quoted", "Quoted"
        WON = "won", "Won"
        LOST = "lost", "Lost"

    # Core contact fields
    name: models.CharField = models.CharField(max_length=100)
    email: models.EmailField = models.EmailField()
    phone: models.CharField = models.CharField(
        max_length=20,
        blank=True,
    )
    message: models.TextField = models.TextField()

    # Form metadata
    form_type: models.CharField = models.CharField(
        max_length=50,
        help_text="Form identifier (e.g. 'contact', 'quote').",
    )
    form_data: models.JSONField = models.JSONField(default=dict)

    source_page: models.ForeignKey = models.ForeignKey(
        Page,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="leads",
    )

    # Attribution fields (SSOT 8.1)
    utm_source: models.CharField = models.CharField(
        max_length=100,
        blank=True,
        help_text="UTM source parameter (e.g. 'google', 'facebook').",
    )
    utm_medium: models.CharField = models.CharField(
        max_length=100,
        blank=True,
        help_text="UTM medium parameter (e.g. 'cpc', 'email').",
    )
    utm_campaign: models.CharField = models.CharField(
        max_length=100,
        blank=True,
        help_text="UTM campaign parameter.",
    )
    utm_term: models.CharField = models.CharField(
        max_length=100,
        blank=True,
        help_text="UTM term parameter (keywords).",
    )
    utm_content: models.CharField = models.CharField(
        max_length=100,
        blank=True,
        help_text="UTM content parameter (ad variant).",
    )
    landing_page_url: models.URLField = models.URLField(
        max_length=500,
        blank=True,
        help_text="First page URL the visitor landed on.",
    )
    page_url: models.URLField = models.URLField(
        max_length=500,
        blank=True,
        help_text="Page URL where form was submitted.",
    )
    referrer_url: models.URLField = models.URLField(
        max_length=500,
        blank=True,
        help_text="HTTP referer header value.",
    )

    # Derived source fields (computed from attribution)
    lead_source: models.CharField = models.CharField(
        max_length=50,
        blank=True,
        choices=LeadSource.choices,
        help_text="Derived source category (e.g. 'google_ads', 'seo').",
    )
    lead_source_detail: models.TextField = models.TextField(
        blank=True,
        help_text="Additional source details for debugging/reporting.",
    )

    # Status workflow
    submitted_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    status: models.CharField = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
    )
    is_archived: models.BooleanField = models.BooleanField(default=False)

    # Email notification status
    email_status: models.CharField = models.CharField(
        max_length=20,
        choices=EmailStatus.choices,
        default=EmailStatus.PENDING,
        help_text="Status of email notification delivery.",
    )
    email_sent_at: models.DateTimeField = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the email notification was successfully sent.",
    )
    email_last_error: models.TextField = models.TextField(
        blank=True,
        help_text="Last error message if email delivery failed.",
    )
    email_attempts: models.PositiveIntegerField = models.PositiveIntegerField(
        default=0,
        help_text="Number of email delivery attempts.",
    )

    # Webhook notification status
    webhook_status: models.CharField = models.CharField(
        max_length=20,
        choices=WebhookStatus.choices,
        default=WebhookStatus.PENDING,
        help_text="Status of webhook notification delivery.",
    )
    webhook_sent_at: models.DateTimeField = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the webhook notification was successfully sent.",
    )
    webhook_last_error: models.TextField = models.TextField(
        blank=True,
        help_text="Last error message if webhook delivery failed.",
    )
    webhook_attempts: models.PositiveIntegerField = models.PositiveIntegerField(
        default=0,
        help_text="Number of webhook delivery attempts.",
    )
    webhook_last_status_code: models.PositiveSmallIntegerField = (
        models.PositiveSmallIntegerField(
            null=True,
            blank=True,
            help_text="HTTP status code from last webhook attempt.",
        )
    )

    # Zapier webhook status (M4-007)
    zapier_status: models.CharField = models.CharField(
        max_length=20,
        choices=ZapierStatus.choices,
        default=ZapierStatus.PENDING,
        help_text="Status of Zapier webhook delivery.",
    )
    zapier_last_attempt_at: models.DateTimeField = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the Zapier webhook was last attempted.",
    )
    zapier_attempt_count: models.PositiveIntegerField = models.PositiveIntegerField(
        default=0,
        help_text="Number of Zapier delivery attempts.",
    )
    zapier_last_error: models.TextField = models.TextField(
        blank=True,
        help_text="Last error message if Zapier delivery failed (truncated).",
    )

    class Meta:
        ordering = ["-submitted_at"]
        permissions = [
            ("export_lead", "Can export leads to CSV"),
        ]

    def __str__(self) -> str:
        return f"{self.name} <{self.email}> ({self.form_type})"


class LeadSourceRule(models.Model):
    """
    Configurable rule for deriving lead_source from UTM/referrer fields.

    Rules are evaluated in priority order (lower number = higher priority).
    The first matching rule determines the derived source.

    This allows per-client customization of attribution while SSOT defaults
    remain available as a fallback when no rules match.
    """

    # Rule matching fields (nullable to allow partial matching)
    utm_source: models.CharField = models.CharField(
        max_length=100,
        blank=True,
        help_text="Match leads with this utm_source value (case-insensitive, exact match).",
    )
    utm_medium: models.CharField = models.CharField(
        max_length=100,
        blank=True,
        help_text="Match leads with this utm_medium value (case-insensitive, exact match).",
    )
    referrer_contains: models.CharField = models.CharField(
        max_length=200,
        blank=True,
        help_text="Match leads where referrer_url contains this string (case-insensitive).",
    )

    # Derived output
    derived_source: models.CharField = models.CharField(
        max_length=50,
        choices=LeadSource.choices,
        help_text="The lead_source value to assign when this rule matches.",
    )
    derived_source_detail: models.CharField = models.CharField(
        max_length=200,
        blank=True,
        help_text="Optional detail to add to lead_source_detail.",
    )

    # Rule metadata
    priority: models.PositiveIntegerField = models.PositiveIntegerField(
        default=100,
        help_text="Lower numbers are higher priority. First matching rule wins.",
    )
    is_active: models.BooleanField = models.BooleanField(
        default=True,
        help_text="Inactive rules are skipped during matching.",
    )
    name: models.CharField = models.CharField(
        max_length=100,
        blank=True,
        help_text="Optional descriptive name for this rule.",
    )

    class Meta:
        ordering = ["priority", "id"]
        verbose_name = "Lead Source Rule"
        verbose_name_plural = "Lead Source Rules"

    def __str__(self) -> str:
        parts = []
        if self.utm_source:
            parts.append(f"utm_source={self.utm_source}")
        if self.utm_medium:
            parts.append(f"utm_medium={self.utm_medium}")
        if self.referrer_contains:
            parts.append(f"referrer~{self.referrer_contains}")
        rule_desc = " & ".join(parts) if parts else "(catch-all)"
        name_prefix = f"{self.name}: " if self.name else ""
        return f"{name_prefix}{rule_desc} → {self.derived_source}"

    def matches(self, *, utm_source: str, utm_medium: str, referrer_url: str) -> bool:
        """Check if this rule matches the given attribution values."""
        if not self.is_active:
            return False

        # All non-empty rule fields must match
        if self.utm_source and self.utm_source.lower() != utm_source.lower():
            return False
        if self.utm_medium and self.utm_medium.lower() != utm_medium.lower():
            return False
        if (
            self.referrer_contains
            and self.referrer_contains.lower() not in referrer_url.lower()
        ):
            return False

        return True
