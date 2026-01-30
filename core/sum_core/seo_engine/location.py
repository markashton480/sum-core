"""
Name: Location Page Models
Path: core/sum_core/seo_engine/location.py
Purpose: Service area configuration and location page models for automated location-based SEO pages.
Family: SEO Engine
Dependencies: Django ORM, Wagtail Page model, PostgreSQL ArrayField
"""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models
from sum_core.blocks.base import BodyStreamBlock
from sum_core.pages.mixins import (
    BreadcrumbMixin,
    DesktopStickyCTAMixin,
    OpenGraphMixin,
    SeoFieldsMixin,
)
from wagtail.admin.panels import FieldPanel
from wagtail.fields import StreamField
from wagtail.models import Page


class AreaType(models.TextChoices):
    """Choices for service area definition types."""

    TOWNS = "towns", "List of Towns"
    POSTCODES = "postcodes", "Postcode Prefixes"
    RADIUS = "radius", "Radius from Point"


class GenerationStatus(models.TextChoices):
    """Status of location page generation."""

    PENDING = "pending", "Pending"
    IN_PROGRESS = "in_progress", "In Progress"
    COMPLETE = "complete", "Complete"
    FAILED = "failed", "Failed"


class ServiceAreaConfig(models.Model):
    """
    Configuration for defining service areas and generating location pages.

    Supports three types of area definition:
    - towns: Explicit list of town/city names
    - postcodes: List of postcode prefixes
    - radius: Radius (in miles) from a central point (lat/lng)

    Provides template configuration for generating unique location pages.
    """

    service_page = models.OneToOneField(
        "wagtailcore.Page",
        on_delete=models.CASCADE,
        related_name="service_area_config",
        help_text="The ServicePage this area configuration belongs to.",
    )

    area_type = models.CharField(
        max_length=20,
        choices=AreaType.choices,
        help_text="How the service area is defined.",
    )

    # Towns-based configuration
    towns_list = models.JSONField(
        blank=True,
        null=True,
        default=list,
        help_text="List of town/city names (for area_type='towns').",
    )

    # Postcode-based configuration
    postcode_prefixes = models.JSONField(
        blank=True,
        null=True,
        default=list,
        help_text="List of postcode prefixes (for area_type='postcodes').",
    )

    # Radius-based configuration
    center_latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        help_text="Center point latitude (for area_type='radius').",
    )

    center_longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        help_text="Center point longitude (for area_type='radius').",
    )

    radius_miles = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Radius in miles from center point (for area_type='radius').",
    )

    # Template configuration
    title_template = models.CharField(
        max_length=255,
        blank=True,
        default="{service} in {location}",
        help_text="Template for page titles. Placeholders: {service}, {location}",
    )

    meta_template = models.TextField(
        blank=True,
        default="Expert {service} in {location}. Professional service.",
        help_text="Template for meta descriptions. Placeholders: {service}, {location}",
    )

    content_template = models.TextField(
        blank=True,
        default="We provide {service} in {location}.",
        help_text="Template for page content. Placeholders: {service}, {location}, {postcodes}",
    )

    include_schema = models.BooleanField(
        default=True,
        help_text="Include LocalBusiness schema markup in generated pages.",
    )

    # Generation tracking
    generation_status = models.CharField(
        max_length=20,
        choices=GenerationStatus.choices,
        default=GenerationStatus.PENDING,
        help_text="Current status of page generation.",
    )

    pages_generated = models.IntegerField(
        default=0, help_text="Number of location pages generated."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Service Area Configuration"
        verbose_name_plural = "Service Area Configurations"

    def __str__(self):
        return f"Service Area for {self.service_page.title}"

    def clean(self):
        """Validate that required fields are present for the chosen area_type."""
        super().clean()

        if self.area_type == AreaType.TOWNS:
            if not self.towns_list or len(self.towns_list) == 0:
                raise ValidationError(
                    {"towns_list": "towns_list is required when area_type is 'towns'."}
                )

        elif self.area_type == AreaType.POSTCODES:
            if not self.postcode_prefixes or len(self.postcode_prefixes) == 0:
                raise ValidationError(
                    {
                        "postcode_prefixes": "postcode_prefixes is required when area_type is 'postcodes'."
                    }
                )

        elif self.area_type == AreaType.RADIUS:
            if self.center_latitude is None:
                raise ValidationError(
                    {
                        "center_latitude": "center_latitude is required when area_type is 'radius'."
                    }
                )
            if self.center_longitude is None:
                raise ValidationError(
                    {
                        "center_longitude": "center_longitude is required when area_type is 'radius'."
                    }
                )
            if self.radius_miles is None:
                raise ValidationError(
                    {
                        "radius_miles": "radius_miles is required when area_type is 'radius'."
                    }
                )


class LocationPage(
    DesktopStickyCTAMixin, SeoFieldsMixin, OpenGraphMixin, BreadcrumbMixin, Page
):
    """
    Auto-generated location-specific service page.

    Created by LocationGenerator based on ServiceAreaConfig.
    Contains location-specific content with LocalBusiness schema markup.
    """

    location_name = models.CharField(
        max_length=255, help_text="The specific location this page represents."
    )

    config = models.ForeignKey(
        ServiceAreaConfig,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="location_pages",
        help_text="The ServiceAreaConfig that generated this page.",
    )

    body: StreamField = StreamField(
        BodyStreamBlock(),
        blank=True,
        null=True,
        use_json_field=True,
        help_text="Location-specific content.",
    )

    # Schema.org LocalBusiness data
    schema_address_locality = models.CharField(
        max_length=255, blank=True, help_text="City/town for LocalBusiness schema."
    )

    schema_latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        help_text="Latitude for LocalBusiness schema.",
    )

    schema_longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        help_text="Longitude for LocalBusiness schema.",
    )

    content_panels = Page.content_panels + [
        FieldPanel("location_name"),
        FieldPanel("body"),
    ]

    promote_panels = SeoFieldsMixin.promote_panels + OpenGraphMixin.open_graph_panels
    settings_panels = (
        Page.settings_panels + DesktopStickyCTAMixin.desktop_sticky_cta_panels
    )

    # LocationPage must be created under ServicePage
    parent_page_types: list[str] = ["sum_core_pages.ServicePage"]

    # LocationPage is a leaf page - no children allowed
    subpage_types: list[str] = []

    template: str = "theme/service_page.html"

    class Meta:
        verbose_name = "Location Page"
        verbose_name_plural = "Location Pages"
        unique_together = [("config", "location_name")]

    def get_schema_data(self) -> dict:
        """
        Generate LocalBusiness schema.org JSON-LD data for this location page.

        Returns:
            dict: Schema.org LocalBusiness structured data
        """
        schema = {
            "@context": "https://schema.org",
            "@type": "LocalBusiness",
            "name": self.title,
            "description": self.search_description or "",
            "url": self.get_full_url(),
        }

        if self.schema_address_locality:
            schema["address"] = {
                "@type": "PostalAddress",
                "addressLocality": self.schema_address_locality,
            }

        if self.schema_latitude and self.schema_longitude:
            schema["geo"] = {
                "@type": "GeoCoordinates",
                "latitude": str(self.schema_latitude),
                "longitude": str(self.schema_longitude),
            }

        return schema

    def get_parent(self):
        """Override to return specific parent page instance."""
        parent = super().get_parent()
        if parent:
            return parent.specific
        return parent

    def __eq__(self, other):
        """Allow comparison with Page objects based on PK."""
        if isinstance(other, Page):
            return self.pk == other.pk and self.pk is not None
        return super().__eq__(other)

    def __hash__(self):
        """Maintain hash consistency with __eq__."""
        return hash(self.pk) if self.pk else super().__hash__()

    @property
    def is_published(self) -> bool:
        """Convenience property for checking if page is published (live)."""
        return self.live

    @property
    def has_hero_block(self) -> bool:
        """Return True because LocationPage hero is template-owned."""
        return True

    @property
    def header_transparent_at_top(self) -> bool:
        """Return True when the header should be transparent at the top."""
        return True
