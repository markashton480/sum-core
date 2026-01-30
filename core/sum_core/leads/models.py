"""
Name: Lead persistence & attribution
Path: core/sum_core/leads/models.py
Purpose: Store all inbound leads reliably ("no lost leads" invariant) with attribution tracking.
Family: Lead management, forms, integrations, admin visibility, reporting.
Dependencies: Django ORM, Wagtail Page model.
"""

from __future__ import annotations

from django.conf import settings
from django.core.cache import cache
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils import timezone
from wagtail.models import Page

SCORE_SKIP_FIELDS = {"email_status", "webhook_status", "zapier_status"}
LEAD_SOURCE_RULE_CACHE_KEY = "lead_source_rules:active"


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
    DISABLED = "disabled", "Disabled"


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

    # Lead assignment
    assigned_to: models.ForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_leads",
        help_text="User assigned to handle this lead.",
    )

    # Lead scoring
    score: models.IntegerField = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        db_index=True,
        help_text="Lead priority score (0-100)",
    )
    score_updated_at: models.DateTimeField = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When score was last calculated",
    )

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

    # Dynamic form admin notification status
    form_notification_status: models.CharField = models.CharField(
        max_length=20,
        choices=EmailStatus.choices,
        default=EmailStatus.DISABLED,
        help_text="Status of dynamic form admin notification delivery.",
    )
    form_notification_sent_at: models.DateTimeField = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the dynamic form admin notification was sent.",
    )
    form_notification_last_error: models.TextField = models.TextField(
        blank=True,
        help_text="Last error message for dynamic form admin notification.",
    )
    form_notification_attempts: models.PositiveIntegerField = (
        models.PositiveIntegerField(
            default=0,
            help_text="Number of dynamic form admin notification attempts.",
        )
    )

    # Dynamic form auto-reply status
    auto_reply_status: models.CharField = models.CharField(
        max_length=20,
        choices=EmailStatus.choices,
        default=EmailStatus.DISABLED,
        help_text="Status of dynamic form auto-reply delivery.",
    )
    auto_reply_sent_at: models.DateTimeField = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the dynamic form auto-reply was sent.",
    )
    auto_reply_last_error: models.TextField = models.TextField(
        blank=True,
        help_text="Last error message for dynamic form auto-reply.",
    )
    auto_reply_attempts: models.PositiveIntegerField = models.PositiveIntegerField(
        default=0,
        help_text="Number of dynamic form auto-reply attempts.",
    )

    # Dynamic form webhook status
    form_webhook_status: models.CharField = models.CharField(
        max_length=20,
        choices=WebhookStatus.choices,
        default=WebhookStatus.DISABLED,
        help_text="Status of dynamic form webhook delivery.",
    )
    form_webhook_sent_at: models.DateTimeField = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the dynamic form webhook was sent.",
    )
    form_webhook_last_error: models.TextField = models.TextField(
        blank=True,
        help_text="Last error message for dynamic form webhook delivery.",
    )
    form_webhook_attempts: models.PositiveIntegerField = models.PositiveIntegerField(
        default=0,
        help_text="Number of dynamic form webhook attempts.",
    )
    form_webhook_last_status_code: models.PositiveSmallIntegerField = (
        models.PositiveSmallIntegerField(
            null=True,
            blank=True,
            help_text="HTTP status code from last dynamic form webhook attempt.",
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

    def save(self, *args, **kwargs):
        """Override save to calculate score before saving."""
        from .scoring import calculate_lead_score

        # Skip score recalculation if only updating specific fields
        update_fields = kwargs.get("update_fields")
        should_recalculate = update_fields is None or not set(update_fields).issubset(
            SCORE_SKIP_FIELDS
        )
        if should_recalculate:
            self.score = calculate_lead_score(self)
            self.score_updated_at = timezone.now()
            if update_fields is not None:
                update_fields = list(update_fields)
                for field in ("score", "score_updated_at"):
                    if field not in update_fields:
                        update_fields.append(field)
                kwargs["update_fields"] = update_fields

        super().save(*args, **kwargs)

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


@receiver(post_save, sender=LeadSourceRule)
@receiver(post_delete, sender=LeadSourceRule)
def _clear_lead_source_rule_cache(*_args, **_kwargs) -> None:
    cache.delete(LEAD_SOURCE_RULE_CACHE_KEY)


class LeadNote(models.Model):
    """Timestamped note attached to a lead for audit trail."""

    lead: models.ForeignKey = models.ForeignKey(
        Lead,
        on_delete=models.CASCADE,
        related_name="notes",
    )
    author: models.ForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="lead_notes",
    )
    content: models.TextField = models.TextField(
        help_text="Note content (plain text).",
    )
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Lead Note"
        verbose_name_plural = "Lead Notes"
        indexes = [
            models.Index(fields=["lead", "-created_at"]),
        ]

    def __str__(self) -> str:
        author_name = self.author.get_full_name() if self.author else "Unknown"
        return f"Note by {author_name} on {self.created_at:%Y-%m-%d}"


class ActivityType(models.TextChoices):
    """Types of tracked activities on leads."""

    STATUS_CHANGE = "status_change", "Status Changed"
    ASSIGNMENT_CHANGE = "assignment_change", "Assignment Changed"
    NOTE_ADDED = "note_added", "Note Added"
    CREATED = "created", "Lead Created"


class LeadActivity(models.Model):
    """Audit trail for all changes to a lead."""

    lead: models.ForeignKey = models.ForeignKey(
        Lead,
        on_delete=models.CASCADE,
        related_name="activities",
    )
    actor: models.ForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lead_activities",
        help_text="User who performed the action (null for system actions).",
    )
    action_type: models.CharField = models.CharField(
        max_length=30,
        choices=ActivityType.choices,
    )
    old_value: models.JSONField = models.JSONField(
        null=True,
        blank=True,
        help_text="Previous value (JSON for flexibility).",
    )
    new_value: models.JSONField = models.JSONField(
        null=True,
        blank=True,
        help_text="New value (JSON for flexibility).",
    )
    description: models.CharField = models.CharField(
        max_length=255,
        blank=True,
        help_text="Human-readable description of the activity.",
    )
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Lead Activity"
        verbose_name_plural = "Lead Activities"
        indexes = [
            models.Index(fields=["lead", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.get_action_type_display()} on Lead #{self.lead_id}"
