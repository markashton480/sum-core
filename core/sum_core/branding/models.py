"""
Name: Branding Site Settings
Path: core/sum_core/branding/models.py
Purpose: Provides Wagtail SiteSettings for branding and business configuration shared across client sites.
Family: Used by template tags and frontend templates (branding_css, branding_fonts, base layouts).
Dependencies: Django models, Wagtail settings framework, wagtailimages, Django cache.
"""

from __future__ import annotations

from typing import Any

from django.core.cache import cache
from django.db import models
from sum_core.branding.panels import FormFieldPanel
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.contrib.settings.models import BaseSiteSetting, register_setting


@register_setting
class SiteSettings(BaseSiteSetting):
    primary_color = models.CharField(
        max_length=7,
        blank=True,
        help_text="Primary brand colour in hex format (e.g. #0055ff).",
    )
    secondary_color = models.CharField(
        max_length=7,
        blank=True,
        help_text="Secondary brand colour in hex format (e.g. #f97316).",
    )
    accent_color = models.CharField(
        max_length=7,
        blank=True,
        help_text="Accent brand colour in hex format (e.g. #10b981).",
    )
    background_color = models.CharField(
        max_length=7,
        blank=True,
        help_text="Background colour for pages (e.g. #ffffff).",
    )
    text_color = models.CharField(
        max_length=7,
        blank=True,
        help_text="Default text colour (e.g. #0f172a).",
    )
    surface_color = models.CharField(
        max_length=7,
        blank=True,
        help_text="Surface colour for cards and panels (e.g. #f8fafc).",
    )
    surface_elevated_color = models.CharField(
        max_length=7,
        blank=True,
        help_text="Elevated surface colour for layered elements.",
    )
    text_light_color = models.CharField(
        max_length=7,
        blank=True,
        help_text="Subtle text colour for muted labels.",
    )
    header_logo = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    footer_logo = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    favicon = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    og_default_image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Default image for social sharing (Open Graph).",
    )
    heading_font = models.CharField(
        max_length=100,
        blank=True,
        help_text="Google Fonts family name for headings.",
    )
    body_font = models.CharField(
        max_length=100,
        blank=True,
        help_text="Google Fonts family name for body text.",
    )
    company_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Company or brand name displayed across the site.",
    )
    established_year = models.IntegerField(null=True, blank=True)
    tagline = models.CharField(
        max_length=255,
        blank=True,
        help_text="Short tagline or strapline.",
    )
    phone_number = models.CharField(
        max_length=50,
        blank=True,
        help_text="Primary contact phone number.",
    )
    email = models.EmailField(
        blank=True,
        help_text="Primary contact email address.",
    )
    address = models.TextField(
        blank=True,
        help_text="Postal address displayed in footers or contact sections.",
    )
    business_hours = models.TextField(
        blank=True,
        help_text="Business hours text (free-form).",
    )
    facebook_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)
    youtube_url = models.URLField(blank=True)
    tiktok_url = models.URLField(blank=True)

    gtm_container_id = models.CharField(
        max_length=20,
        blank=True,
        help_text="Google Tag Manager Container ID (e.g. GTM-XXXXXX).",
    )
    ga_measurement_id = models.CharField(
        max_length=20,
        blank=True,
        help_text="Google Analytics 4 Measurement ID (e.g. G-XXXXXXXXXX).",
    )
    cookie_banner_enabled = models.BooleanField(
        default=False,
        help_text=(
            "When enabled, analytics load only after a visitor accepts the banner; "
            "when disabled, analytics load immediately."
        ),
    )
    cookie_consent_version = models.CharField(
        max_length=20,
        default="1",
        help_text=(
            "Increment this version when consent text changes to trigger a new prompt."
        ),
    )
    privacy_policy_page = models.ForeignKey(
        "wagtailcore.Page",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Optional link to your privacy policy page.",
    )
    cookie_policy_page = models.ForeignKey(
        "wagtailcore.Page",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Optional link to your cookie policy page.",
    )
    terms_page = models.ForeignKey(
        "wagtailcore.Page",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Optional link to your terms page.",
    )

    robots_txt = models.TextField(
        blank=True,
        help_text=(
            "Custom robots.txt content. If blank, defaults to allowing all bots. "
            "Sitemap reference will be added automatically."
        ),
    )

    # Zapier Integration (M4-007)
    zapier_enabled = models.BooleanField(
        default=False,
        help_text="Enable Zapier webhook integration for new leads.",
    )
    zapier_webhook_url = models.URLField(
        blank=True,
        help_text="Zapier webhook URL for lead notifications.",
    )

    # Email Notification Settings (M4-011)
    notification_from_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Name used in the 'From' header (e.g. 'ACME Corp Leads').",
    )
    notification_from_email = models.EmailField(
        blank=True,
        help_text="Email address used in the 'From' header (e.g. leads@acme.com).",
    )
    notification_reply_to_email = models.EmailField(
        blank=True,
        help_text="Email address for the 'Reply-To' header (e.g. sales@acme.com).",
    )
    notification_subject_prefix = models.CharField(
        max_length=50,
        blank=True,
        help_text="Optional prefix for the email subject (e.g. '[New Lead]').",
    )

    panels = [
        MultiFieldPanel(
            [
                FieldPanel("header_logo"),
                FieldPanel("footer_logo"),
                FieldPanel("favicon"),
                FieldPanel("og_default_image"),
            ],
            heading="Logos & Favicon",
        ),
        MultiFieldPanel(
            [
                # FormFieldPanel is used for form-only fields not backed by model fields.
                # theme_preset is defined in SiteSettingsAdminForm and pre-populates
                # colours and fonts when a preset is selected.
                FormFieldPanel("theme_preset"),
            ],
            heading="Theme Preset",
        ),
        MultiFieldPanel(
            [
                FieldPanel("primary_color"),
                FieldPanel("secondary_color"),
                FieldPanel("accent_color"),
                FieldPanel("background_color"),
                FieldPanel("surface_color"),
                FieldPanel("surface_elevated_color"),
                FieldPanel("text_color"),
                FieldPanel("text_light_color"),
            ],
            heading="Brand Colours",
        ),
        MultiFieldPanel(
            [
                FieldPanel("heading_font"),
                FieldPanel("body_font"),
            ],
            heading="Typography",
        ),
        MultiFieldPanel(
            [
                FieldPanel("company_name"),
                FieldPanel("established_year"),
                FieldPanel("tagline"),
                FieldPanel("phone_number"),
                FieldPanel("email"),
                FieldPanel("address"),
                FieldPanel("business_hours"),
            ],
            heading="Business Info",
        ),
        MultiFieldPanel(
            [
                FieldPanel("facebook_url"),
                FieldPanel("instagram_url"),
                FieldPanel("linkedin_url"),
                FieldPanel("twitter_url"),
                FieldPanel("youtube_url"),
                FieldPanel("tiktok_url"),
            ],
            heading="Social Links",
        ),
        MultiFieldPanel(
            [
                FieldPanel("gtm_container_id"),
                FieldPanel("ga_measurement_id"),
            ],
            heading="Analytics",
        ),
        MultiFieldPanel(
            [
                FieldPanel("cookie_banner_enabled"),
                FieldPanel("cookie_consent_version"),
                FieldPanel("privacy_policy_page"),
                FieldPanel("cookie_policy_page"),
                FieldPanel("terms_page"),
            ],
            heading="Consent & Legal",
        ),
        MultiFieldPanel(
            [
                FieldPanel("robots_txt"),
            ],
            heading="Technical SEO",
        ),
        MultiFieldPanel(
            [
                FieldPanel("zapier_enabled"),
                FieldPanel("zapier_webhook_url"),
            ],
            heading="Zapier Integration",
        ),
        MultiFieldPanel(
            [
                FieldPanel("notification_from_name"),
                FieldPanel("notification_from_email"),
                FieldPanel("notification_reply_to_email"),
                FieldPanel("notification_subject_prefix"),
            ],
            heading="Email Notifications",
        ),
    ]

    class Meta:
        verbose_name = "Site settings"
        verbose_name_plural = "Site settings"

    def __str__(self) -> str:  # pragma: no cover - admin display helper
        return self.company_name or "Site settings"

    def _invalidate_branding_cache(self) -> None:
        cache.delete(f"branding_css:{self.site_id}")
        cache.delete(f"branding_fonts:{self.site_id}")

    def save(self, *args: Any, **kwargs: Any) -> None:
        super().save(*args, **kwargs)
        self._invalidate_branding_cache()

    def delete(self, *args: Any, **kwargs: Any) -> None:
        site_id = self.site_id
        super().delete(*args, **kwargs)
        cache.delete(f"branding_css:{site_id}")
        cache.delete(f"branding_fonts:{site_id}")
