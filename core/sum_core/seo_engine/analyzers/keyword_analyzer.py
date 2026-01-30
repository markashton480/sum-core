"""
Name: Keyword Analyzer
Path: core/sum_core/seo_engine/analyzers/keyword_analyzer.py
Purpose: Local keyword injection analyzer for SEO optimization.
Family: SEO Engine
Dependencies: Django, Wagtail, SiteSettings

Analyzes pages for local keyword optimization opportunities by:
- Extracting location from SiteSettings.address
- Detecting missing location keywords in page titles and descriptions
- Generating optimized suggestions that respect SEO character limits
- Providing page-type-aware recommendations with importance levels
"""

from __future__ import annotations

from dataclasses import dataclass

from wagtail.models import Page, Site


@dataclass
class KeywordSuggestions:
    """
    Results from keyword analysis with optimization suggestions.

    Attributes:
        current_title: Page's current SEO title
        current_description: Page's current meta description
        suggested_title: Optimized title with location keyword (if needed)
        suggested_description: Optimized description with location keyword (if needed)
        title_needs_location: Whether title is missing location
        description_needs_location: Whether description is missing location
        should_suggest: Whether suggestions should be made for this page type
        importance: Priority level (high/medium/low)
        page_type: Type of page being analyzed
    """

    current_title: str
    current_description: str
    suggested_title: str | None
    suggested_description: str | None
    title_needs_location: bool
    description_needs_location: bool
    should_suggest: bool
    importance: str  # "high", "medium", or "low"
    page_type: str


class KeywordAnalyzer:
    """
    Analyzes pages for local keyword optimization opportunities.

    Detects pages missing location keywords in titles/descriptions
    and suggests optimized alternatives.
    """

    def __init__(self, site: Site):
        """
        Initialize analyzer for a specific site.

        Args:
            site: Wagtail Site instance to analyze
        """
        self.site = site

    def extract_location(self) -> str | None:
        """
        Extract target location from SiteSettings.address.

        Returns:
            Location string (city/town name) or None if not available.
        """
        from sum_core.branding.models import SiteSettings

        # Handle missing site or SiteSettings gracefully
        if not self.site:
            return None

        try:
            settings = SiteSettings.for_site(self.site)
        except SiteSettings.DoesNotExist:
            return None

        if not settings.address:
            return None

        # Parse multi-line address to extract city/town
        # Typically: Line 1 = street, Line 2 = city, Line 3 = postcode
        lines = [line.strip() for line in settings.address.split("\n") if line.strip()]

        if len(lines) < 2:
            # Single line address or too short - return None
            return None

        # City is usually on the second line (before postcode line)
        city = lines[1] if len(lines) >= 2 else None
        return city if city else None

    def analyze(self, page: Page) -> KeywordSuggestions:
        """
        Analyze a page for keyword optimization opportunities.

        Args:
            page: Wagtail Page instance to analyze

        Returns:
            KeywordSuggestions with current values and optimization recommendations
        """
        # Extract location from site settings
        location = self.extract_location()

        # Get page type
        page_type = page.__class__.__name__

        # Determine if this page type should receive suggestions
        should_suggest = self._should_suggest_for_page_type(page_type, location)

        # Get current SEO fields (with fallbacks) - convert to str for type safety
        current_title = str(page.seo_title or page.title)
        current_description = str(page.search_description or "")

        # Check if location is present in current content
        title_has_location = (
            location.lower() in current_title.lower() if location else False
        )
        description_has_location = (
            location.lower() in current_description.lower() if location else False
        )

        # Determine if suggestions are needed
        title_needs_location = should_suggest and not title_has_location
        description_needs_location = should_suggest and not description_has_location

        # Generate suggestions
        suggested_title = None
        suggested_description = None

        if title_needs_location and location:
            suggested_title = self._suggest_title(current_title, location)

        if description_needs_location and location:
            suggested_description = self._suggest_description(
                current_description, str(page.title), location
            )

        # Determine importance
        importance = self._calculate_importance(page_type, location, should_suggest)

        return KeywordSuggestions(
            current_title=current_title,
            current_description=current_description,
            suggested_title=suggested_title,
            suggested_description=suggested_description,
            title_needs_location=title_needs_location,
            description_needs_location=description_needs_location,
            should_suggest=should_suggest,
            importance=importance,
            page_type=page_type,
        )

    def _should_suggest_for_page_type(
        self, page_type: str, location: str | None
    ) -> bool:
        """
        Determine if suggestions should be made for this page type.

        Args:
            page_type: Name of the page class
            location: Extracted location (None if not available)

        Returns:
            True if suggestions should be made, False otherwise
        """
        # No suggestions if no location available
        if not location:
            return False

        # LegalPage should NOT receive suggestions
        if page_type == "LegalPage":
            return False

        # All other page types should receive suggestions
        return True

    def _suggest_title(self, current_title: str, location: str) -> str:
        """
        Generate an optimized title with location keyword.

        Args:
            current_title: Current page title
            location: Location to inject

        Returns:
            Optimized title (max 60 chars)
        """
        # Try to insert location naturally
        # Pattern: "Service in Location"
        location_phrase = f"in {location}"

        # If title already has a separator (|), insert before it
        if "|" in current_title:
            parts = current_title.split("|")
            base = parts[0].strip()
            suffix = "|".join(parts[1:]).strip()

            # Try to fit location before separator
            suggested = f"{base} {location_phrase} | {suffix}"
            if len(suggested) <= 60:
                return suggested

            # If too long, use just base + location
            suggested = f"{base} {location_phrase}"
            if len(suggested) <= 60:
                return suggested

            # If still too long, truncate base
            max_base_len = 60 - len(location_phrase) - 1
            if max_base_len > 10:
                base = base[:max_base_len].rsplit(" ", 1)[
                    0
                ]  # Truncate at word boundary
                return f"{base} {location_phrase}"

        # No separator - append location
        suggested = f"{current_title} {location_phrase}"
        if len(suggested) <= 60:
            return suggested

        # Too long - truncate title intelligently
        max_title_len = 60 - len(location_phrase) - 1
        if max_title_len > 10:
            truncated = current_title[:max_title_len].rsplit(" ", 1)[0]
            return f"{truncated} {location_phrase}"

        # Fallback - just use location
        return f"{location}"

    def _suggest_description(
        self, current_description: str, page_title: str, location: str
    ) -> str:
        """
        Generate an optimized description with location keyword.

        Args:
            current_description: Current meta description
            page_title: Page title (for context if description is empty)
            location: Location to inject

        Returns:
            Optimized description (max 160 chars)
        """
        # Natural location phrases
        location_phrases = [
            f"in {location}",
            f"across {location}",
            f"throughout {location}",
        ]

        # If description is empty, create one from page title
        if not current_description:
            return f"Professional services {location_phrases[0]}."

        # Try to insert location naturally
        # Common pattern: append "in Location" to existing description
        for phrase in location_phrases:
            # Try inserting before the period if exists
            if current_description.endswith("."):
                suggested = f"{current_description[:-1]} {phrase}."
                if len(suggested) <= 160:
                    return suggested

            # Try appending at the end (add period if not there)
            suggested = f"{current_description} {phrase}."
            if len(suggested) <= 160:
                return suggested

        # If all attempts are too long, truncate and append
        phrase = location_phrases[0]
        max_desc_len = 160 - len(phrase) - 2  # -2 for space and period
        if max_desc_len > 20:
            # Truncate at word boundary
            truncated = current_description[:max_desc_len].rsplit(" ", 1)[0]
            # Remove trailing punctuation
            truncated = truncated.rstrip(".,;:")
            return f"{truncated} {phrase}."

        # Fallback - create minimal description
        return f"Services {phrase}."

    def _calculate_importance(
        self, page_type: str, location: str | None, should_suggest: bool
    ) -> str:
        """
        Calculate importance level for suggestions.

        Args:
            page_type: Name of the page class
            location: Extracted location
            should_suggest: Whether suggestions should be made

        Returns:
            "high", "medium", or "low"
        """
        if not should_suggest:
            return "low"

        # ServicePage gets high importance
        if page_type == "ServicePage":
            return "high"

        # BlogPostPage gets medium importance
        if page_type == "BlogPostPage":
            return "medium"

        # All others get medium by default
        return "medium"
