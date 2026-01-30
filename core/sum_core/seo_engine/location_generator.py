"""
Name: Location Page Generator
Path: core/sum_core/seo_engine/location_generator.py
Purpose: Generate location-specific service pages based on ServiceAreaConfig.
Family: SEO Engine
Dependencies: Django ORM, Wagtail Page model, location models
"""

from __future__ import annotations

import logging
import re
from typing import Any

from django.db import transaction
from django.utils.text import slugify
from wagtail.models import Page

from .location import GenerationStatus, LocationPage, ServiceAreaConfig

logger = logging.getLogger(__name__)


class LocationGenerator:
    """
    Generates LocationPage instances based on ServiceAreaConfig.

    Handles:
    - Preview of pages to be generated
    - Batch generation with template interpolation
    - Regeneration after template changes
    - Cleanup of generated pages
    """

    def __init__(self, config: ServiceAreaConfig):
        """
        Initialize generator with a ServiceAreaConfig.

        Args:
            config: The ServiceAreaConfig to generate pages from
        """
        self.config = config
        self.service_page = config.service_page.specific

    def _get_locations(self) -> list[str]:
        """
        Get list of location names based on area_type.

        Returns:
            List of location names to generate pages for
        """
        if self.config.area_type == "towns":
            return self.config.towns_list or []
        elif self.config.area_type == "postcodes":
            # For postcodes, use the prefix as the location name for now
            # In production, you'd lookup actual town names for each postcode
            return self.config.postcode_prefixes or []
        elif self.config.area_type == "radius":
            # For radius, you'd need a geocoding service to get locations within radius
            # For now, return empty list (will be extended in future)
            return []
        return []

    def _interpolate_template(
        self, template: str, location: str, extra_context: dict[str, Any] | None = None
    ) -> str:
        """
        Interpolate template placeholders with actual values.

        Args:
            template: Template string with placeholders
            location: Location name
            extra_context: Additional context variables

        Returns:
            Interpolated string
        """
        context = {
            "service": self.service_page.title,
            "location": location,
        }

        if extra_context:
            context.update(extra_context)

        # Handle postcode placeholder specially
        if "{postcodes}" in template:
            if self.config.area_type == "postcodes":
                postcodes_str = ", ".join(self.config.postcode_prefixes or [])
                context["postcodes"] = postcodes_str
            else:
                context["postcodes"] = ""

        result = template
        for key, value in context.items():
            result = result.replace(f"{{{key}}}", str(value))
        # Match placeholders like {name}, {company_name} - \w includes underscores
        unresolved = re.findall(r"{\w+}", result)
        if unresolved:
            logger.warning(
                "Unrecognized placeholders remain after interpolation",
                extra={
                    "unresolved": sorted(set(unresolved)),
                    "template": template,
                },
            )
        return result

    def _sanitize_slug(self, text: str) -> str:
        """
        Sanitize text for use in URL slugs.

        Handles special characters like &, apostrophes, periods.

        Args:
            text: Text to sanitize

        Returns:
            URL-safe slug
        """
        # Replace " & " (with spaces) with just space (will be slugified to -)
        text = text.replace(" & ", " ")
        # Replace & with nothing
        text = text.replace("&", "")
        # Remove apostrophes
        text = text.replace("'", "")
        # Remove periods
        text = text.replace(".", "")
        # Use Django's slugify for the rest
        return slugify(text)

    def _generate_slug(self, location: str) -> str:
        """
        Generate unique slug for a location page.

        Args:
            location: Location name

        Returns:
            Unique slug for the page
        """
        service_slug = self._sanitize_slug(self.service_page.title)
        location_slug = self._sanitize_slug(location)
        return f"{service_slug}-{location_slug}"

    def _get_or_create_body_content(self, location: str) -> list:
        """
        Generate body content for location page.

        Args:
            location: Location name

        Returns:
            StreamField-compatible body content
        """
        # Interpolate content template
        content = self._interpolate_template(
            self.config.content_template or "We provide {service} in {location}.",
            location,
        )

        # Wrap in paragraph tags for rich_text block
        html_content = f"<p>{content}</p>"

        # Return as a list with a single rich_text block
        return [{"type": "rich_text", "value": html_content}]

    def preview_pages(self) -> list[dict[str, str]]:
        """
        Preview pages that would be generated without creating them.

        Returns:
            List of dicts with title, slug, and meta_description for each page
        """
        locations = self._get_locations()
        preview = []

        for location in locations:
            title = self._interpolate_template(
                self.config.title_template or "{service} in {location}", location
            )

            slug = self._generate_slug(location)

            meta_description = self._interpolate_template(
                self.config.meta_template
                or "Expert {service} in {location}. Professional service.",
                location,
            )

            preview.append(
                {"title": title, "slug": slug, "meta_description": meta_description}
            )

        return preview

    def generate_pages(self, batch_size: int = 100) -> list[LocationPage]:
        """
        Generate LocationPage instances for all locations in service area.

        If pages already exist, returns existing pages instead of creating duplicates.

        Args:
            batch_size: Maximum number of pages to generate at once (for future pagination)

        Returns:
            List of generated/existing LocationPage instances
        """
        locations = self._get_locations()
        pages = []

        # Check if pages already exist
        existing_pages = {
            page.location_name: page
            for page in LocationPage.objects.filter(config=self.config)
        }

        if existing_pages and len(existing_pages) == len(locations):
            # All pages already exist, return them
            self.config.generation_status = GenerationStatus.COMPLETE
            self.config.pages_generated = len(existing_pages)
            self.config.save()
            return list(existing_pages.values())

        # Update status to in_progress
        self.config.generation_status = GenerationStatus.IN_PROGRESS
        self.config.save()

        for location in locations:
            # Check if page already exists
            if location in existing_pages:
                pages.append(existing_pages[location])
                continue

            # Generate new page
            title = self._interpolate_template(
                self.config.title_template or "{service} in {location}", location
            )

            slug = self._generate_slug(location)

            meta_description = self._interpolate_template(
                self.config.meta_template
                or "Expert {service} in {location}. Professional service.",
                location,
            )

            body_content = self._get_or_create_body_content(location)

            # Create the LocationPage
            page = LocationPage(
                title=title,
                slug=slug,
                location_name=location,
                config=self.config,
                search_description=meta_description,
                body=body_content,
            )

            # Add schema data if enabled
            if self.config.include_schema:
                page.schema_address_locality = location

            # Add as child of service page
            # Try to add child; if tree is corrupted, refresh service_page and retry
            try:
                with transaction.atomic():
                    self.service_page.add_child(instance=page)
            except (AttributeError, TypeError):
                # Tree may be corrupted from improper deletions
                # Refresh service_page from database
                self.service_page = Page.objects.get(id=self.service_page.id).specific
                with transaction.atomic():
                    self.service_page.add_child(instance=page)

            # Publish the page
            revision = page.save_revision()
            revision.publish()

            # Refresh from database to get updated publish status
            page.refresh_from_db()

            pages.append(page)

        # Update generation tracking
        self.config.generation_status = GenerationStatus.COMPLETE
        self.config.pages_generated = len(pages)
        self.config.save()

        return pages

    def regenerate_pages(self) -> list[LocationPage]:
        """
        Regenerate all location pages, updating existing pages with new template data.

        Returns:
            List of regenerated LocationPage instances
        """
        # First, delete existing pages
        self.cleanup_generated_pages()

        # Refresh service page from database after cleanup
        self.service_page.refresh_from_db()

        # Then generate fresh pages
        return self.generate_pages()

    def cleanup_generated_pages(self) -> int:
        """
        Delete all LocationPage instances generated by this config.

        Returns:
            Number of pages deleted
        """
        pages = LocationPage.objects.filter(config=self.config)
        count = pages.count()

        # Delete all pages
        for page in pages:
            page.delete()

        # Reset generation tracking
        self.config.generation_status = GenerationStatus.PENDING
        self.config.pages_generated = 0
        self.config.save()

        return count
