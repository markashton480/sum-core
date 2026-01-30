"""
Name: Linking Analyzer
Path: core/sum_core/seo_engine/analyzers/linking_analyzer.py
Purpose: Smart internal linking analyzer for SEO optimization.
Family: SEO Engine
Dependencies: Django, Wagtail, InternalLinkSuggestion

Analyzes pages for internal linking opportunities by:
- Finding related pages based on keyword overlap
- Calculating relevance scores for potential links
- Detecting orphan pages with no incoming links
- Suggesting natural anchor text for links
- Generating and prioritizing link suggestions
"""

from __future__ import annotations

import re

from django.db import transaction
from sum_core.seo_engine.suggestions import InternalLinkSuggestion, SuggestionStatus
from wagtail.models import Page, Site

# Relevance scoring weights
TITLE_MATCH_WEIGHT = 0.6  # Weight for exact title keyword matches
DESCRIPTION_MATCH_WEIGHT = 0.5  # Weight for description keyword matches
PARTIAL_MATCH_WEIGHT = 0.2  # Weight for partial/fuzzy matches

# Common stop words to filter out during keyword extraction
STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "has",
    "he",
    "in",
    "is",
    "it",
    "its",
    "of",
    "on",
    "that",
    "the",
    "to",
    "was",
    "will",
    "with",
    "you",
    "your",
    "our",
    "we",
    "us",
    "this",
    "these",
    "those",
    "their",
    "when",
    "where",
    "which",
    "who",
    "why",
    "how",
    "all",
    "each",
    "every",
    "both",
    "few",
    "more",
    "most",
    "other",
    "some",
    "such",
    "no",
    "nor",
    "not",
    "only",
    "own",
    "same",
    "so",
    "than",
    "too",
    "very",
    "can",
    "just",
    "should",
    "now",
}

# Generic service keywords - common across many service businesses
# These receive lower weight in relevance scoring
GENERIC_KEYWORDS = {
    "professional",
    "expert",
    "quality",
    "services",
    "service",
    "installation",
    "repair",
    "maintenance",
    "new",
    "best",
    "company",
    "business",
    "local",
    "near",
    "me",
    "area",
    "residential",
    "commercial",
    "licensed",
    "certified",
    "guaranteed",
    "warranty",
    "emergency",
    "24",
    "7",
    # Common web/meta keywords
    "page",
    "seo",
    "home",
    "about",
    "contact",
    "title",
    "description",
    "test",
    "testing",
    "e2e",
    "standard",
}


# Related word mappings (stemming-like relationships)
RELATED_WORDS = {
    "roof": {"roof", "roofing", "roofs"},
    "roofing": {"roof", "roofing", "roofs"},
    "roofs": {"roof", "roofing", "roofs"},
    "service": {"service", "services"},
    "services": {"service", "services"},
    "repair": {"repair", "repairs", "repairing"},
    "repairs": {"repair", "repairs", "repairing"},
    "install": {"install", "installation", "installing"},
    "installation": {"install", "installation", "installing"},
}


class LinkingAnalyzer:
    """
    Analyzes pages for internal linking opportunities.

    Detects keyword overlap between pages and suggests internal links
    with natural anchor text to improve site structure and SEO.
    """

    def __init__(self, site: Site):
        """
        Initialize analyzer for a specific site.

        Args:
            site: Wagtail Site instance to analyze
        """
        self.site = site

    def _extract_keywords_separated(self, page: Page) -> tuple[set[str], set[str]]:
        """
        Extract keywords from page title and meta description (internal method).

        Returns separate sets for title and description keywords to allow
        differential weighting (title matches are more important).

        Args:
            page: Wagtail Page instance to extract keywords from

        Returns:
            Tuple of (title_keywords, description_keywords)
        """
        title_keywords = []
        description_keywords = []

        # Extract from title (highest priority)
        if page.title:
            title_keywords.extend(self._tokenize(page.title))

        # Extract from SEO title (also high priority)
        if hasattr(page, "seo_title") and page.seo_title:
            title_keywords.extend(self._tokenize(page.seo_title))

        # Extract from search description
        if hasattr(page, "search_description") and page.search_description:
            description_keywords.extend(self._tokenize(page.search_description))

        # Filter stop words
        title_filtered = set(
            kw.lower() for kw in title_keywords if kw.lower() not in STOP_WORDS
        )
        desc_filtered = set(
            kw.lower() for kw in description_keywords if kw.lower() not in STOP_WORDS
        )

        return (title_filtered, desc_filtered)

    def extract_keywords(self, page: Page) -> list[str]:
        """
        Extract keywords from page title and meta description.

        Args:
            page: Wagtail Page instance to extract keywords from

        Returns:
            List of extracted keywords (filtered, lowercased)
        """
        title_kw, desc_kw = self._extract_keywords_separated(page)
        # Return combined list
        return list(title_kw | desc_kw)

    def _tokenize(self, text: str) -> list[str]:
        """
        Tokenize text into words.

        Args:
            text: Text to tokenize

        Returns:
            List of words (lowercased, alphanumeric only)
        """
        # Remove punctuation and split
        words = re.findall(r"\b\w+\b", text.lower())
        return words

    def _calculate_relevance(
        self,
        source_title_kw: set[str],
        source_desc_kw: set[str],
        target_title_kw: set[str],
        target_desc_kw: set[str],
    ) -> float:
        """
        Calculate relevance score between two pages.

        Uses weighted keyword matching with emphasis on:
        - Topic-specific keywords (non-generic)
        - Title keyword matches
        - Related word families (roof/roofing)

        Generic service keywords (professional, services, etc.) receive
        lower weight to prevent unrelated service pages from matching highly.

        Args:
            source_title_kw: Title keywords from source page
            source_desc_kw: Description keywords from source page
            target_title_kw: Title keywords from target page
            target_desc_kw: Description keywords from target page

        Returns:
            Relevance score (0.0-1.0)
        """
        # Combine all keywords
        source_all = source_title_kw | source_desc_kw
        target_all = target_title_kw | target_desc_kw

        if not source_all or not target_all:
            return 0.0

        # Separate topic-specific keywords from generic ones
        source_specific = source_all - GENERIC_KEYWORDS
        target_specific = target_all - GENERIC_KEYWORDS

        # Calculate intersection
        intersection_all = source_all & target_all
        intersection_specific = source_specific & target_specific

        # Title keyword matches (only count non-generic title matches)
        title_matches = source_title_kw & target_title_kw
        title_specific = title_matches - GENERIC_KEYWORDS

        # Score based on topic-specific keyword overlap
        # This is the primary signal - do pages discuss the same topic?
        if source_specific and target_specific:
            specific_overlap = len(intersection_specific) / max(
                len(source_specific), len(target_specific)
            )
        else:
            specific_overlap = 0.0

        # Title matches on topic-specific words are extremely valuable
        # Each specific title match contributes heavily to the score
        title_score = (
            len(title_specific) * TITLE_MATCH_WEIGHT if title_specific else 0.0
        )

        # Boost for related word matches (e.g., roof/roofing)
        # This helps pages with stem variations to still match well
        related_boost = 0.0
        for source_word in source_all - intersection_all:
            for target_word in target_all - intersection_all:
                source_family = RELATED_WORDS.get(source_word, {source_word})
                target_family = RELATED_WORDS.get(target_word, {target_word})
                if source_family & target_family:
                    related_boost += DESCRIPTION_MATCH_WEIGHT
                    break

        # Combine scores: specific keyword overlap + title emphasis + related words
        # Title-specific matches dominate, ensuring topic relevance
        final_score = (
            (specific_overlap * PARTIAL_MATCH_WEIGHT) + title_score + related_boost
        )

        return min(final_score, 1.0)

    def find_related_pages(self, page: Page) -> list[Page]:
        """
        Find pages with keyword overlap (any relevance > 0).

        Args:
            page: Source page to find related pages for

        Returns:
            List of related pages (excludes self)
        """
        matches = self.find_related_pages_with_scores(page)
        return list(matches.keys())

    def find_related_pages_with_scores(self, page: Page) -> dict[Page, float]:
        """
        Find pages with keyword overlap and their relevance scores.

        Args:
            page: Source page to find related pages for

        Returns:
            Dictionary mapping pages to relevance scores

        Performance Note:
            This method avoids .specific() to prevent extra queries per page.
            Page-level fields are sufficient for keyword extraction.
        """
        # Early return if site is unavailable
        if self.site is None:
            return {}

        source_title_kw, source_desc_kw = self._extract_keywords_separated(page)

        # Get all published pages in the site (excluding self)
        all_pages = Page.objects.live().in_site(self.site).exclude(id=page.id)

        matches: dict[Page, float] = {}

        for candidate in all_pages:
            target_title_kw, target_desc_kw = self._extract_keywords_separated(
                candidate
            )
            score = self._calculate_relevance(
                source_title_kw, source_desc_kw, target_title_kw, target_desc_kw
            )

            if score > 0.0:
                matches[candidate] = score

        return matches

    def find_orphan_pages(self) -> list[Page]:
        """
        Find pages with no incoming internal link suggestions (accepted).

        Returns:
            List of orphan pages, sorted by depth (shallower first)
        """
        # Get all page IDs that have incoming accepted link suggestions
        pages_with_links = (
            InternalLinkSuggestion.objects.filter(status=SuggestionStatus.ACCEPTED)
            .values_list("target_page_id", flat=True)
            .distinct()
        )

        # Get all published pages in the site excluding those with links
        orphan_pages = (
            Page.objects.live()
            .in_site(self.site)
            .exclude(id__in=pages_with_links)
            .specific()
            .order_by("depth", "path")  # Shallower pages first
        )

        return list(orphan_pages)

    def suggest_anchor_text(self, source_page: Page, target_page: Page) -> str:
        """
        Generate natural anchor text for a link from source to target.

        Args:
            source_page: Page where link will be added
            target_page: Page being linked to

        Returns:
            Suggested anchor text (max 200 chars)
        """
        # Default: use target page title
        anchor = target_page.title

        # Look for multi-word phrases from target
        if hasattr(target_page, "seo_title") and target_page.seo_title:
            # Use SEO title if available
            anchor = target_page.seo_title
        else:
            # Build a phrase from title words
            title_words = self._tokenize(target_page.title)
            # Take first 3-4 meaningful words from title
            meaningful = [w for w in title_words if w not in STOP_WORDS][:4]
            if meaningful:
                anchor = " ".join(meaningful).title()

        # Ensure it's within length limit
        if len(anchor) > 200:
            anchor = anchor[:197] + "..."

        # Clean up anchor text
        anchor = anchor.strip()

        # Ensure it's not empty
        if not anchor:
            anchor = target_page.title

        return anchor[:200]

    def generate_suggestions(
        self, page: Page, max_suggestions: int = 10, min_relevance: float = 0.3
    ) -> list[InternalLinkSuggestion]:
        """
        Generate internal link suggestions for a page.

        Args:
            page: Source page to generate suggestions for
            max_suggestions: Maximum number of suggestions to return
            min_relevance: Minimum relevance score threshold

        Returns:
            List of InternalLinkSuggestion instances (unsaved)
        """
        # Find related pages with scores
        matches = self.find_related_pages_with_scores(page)

        # Filter by minimum relevance
        filtered = {
            target: score for target, score in matches.items() if score >= min_relevance
        }

        # Get existing link suggestions for this source page
        existing_targets = set(
            InternalLinkSuggestion.objects.filter(
                source_page=page, status=SuggestionStatus.ACCEPTED
            ).values_list("target_page_id", flat=True)
        )

        # Exclude already-linked targets
        filtered = {
            target: score
            for target, score in filtered.items()
            if target.id not in existing_targets
        }

        # Sort by relevance (descending)
        sorted_matches = sorted(filtered.items(), key=lambda x: x[1], reverse=True)

        # Limit to max_suggestions
        sorted_matches = sorted_matches[:max_suggestions]

        # Create suggestion objects (unsaved)
        suggestions = []
        for target, score in sorted_matches:
            anchor = self.suggest_anchor_text(page, target)
            suggestion = InternalLinkSuggestion(
                source_page=page,
                target_page=target,
                anchor_text=anchor,
                relevance_score=score,
                status=SuggestionStatus.PENDING,
            )
            suggestions.append(suggestion)

        return suggestions

    def analyze(self, page: Page, save: bool = True) -> list[InternalLinkSuggestion]:
        """
        Main analysis method: generate link suggestions for a page.

        Args:
            page: Page to analyze
            save: If True, save suggestions to database

        Returns:
            List of InternalLinkSuggestion instances
        """
        suggestions = self.generate_suggestions(page)

        if save:
            # Save suggestions to database atomically to ensure data consistency
            # Handle duplicates by checking existing suggestions
            with transaction.atomic():
                for suggestion in suggestions:
                    # Check if suggestion already exists by ID
                    # Access the FK ID directly to avoid calling .specific()
                    source_id = suggestion.source_page_id
                    target_id = suggestion.target_page_id
                    existing = InternalLinkSuggestion.objects.filter(
                        source_page_id=source_id, target_page_id=target_id
                    ).first()

                    if not existing:
                        suggestion.save()
                    # If exists, we could update the score, but tests expect no duplicates

        return suggestions
