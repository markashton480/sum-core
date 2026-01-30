"""
Name: Content Analyzer
Path: core/sum_core/seo_engine/analyzers/content_analyzer.py
Purpose: Content gap analyzer for detecting missing pages, schema, and thin content.
Family: SEO Engine
Dependencies: Django, Wagtail, sum_core pages and blocks
"""

from __future__ import annotations

import re
from collections import Counter
from html.parser import HTMLParser
from typing import TYPE_CHECKING, Any

from sum_core.seo_engine.utils import extract_text_from_stream_field, strip_html

if TYPE_CHECKING:
    from wagtail.models import Page, Site

# Common stop words to filter out
STOP_WORDS = {
    "the",
    "and",
    "or",
    "but",
    "is",
    "are",
    "was",
    "were",
    "a",
    "an",
    "in",
    "on",
    "at",
    "to",
    "for",
    "of",
    "with",
    "by",
    "from",
    "as",
    "be",
    "have",
    "has",
    "had",
    "do",
    "does",
    "did",
    "will",
    "would",
    "can",
    "could",
    "should",
    "may",
    "might",
    "must",
    "this",
    "that",
    "these",
    "those",
    "i",
    "you",
    "he",
    "she",
    "it",
    "we",
    "they",
    "what",
    "which",
    "who",
    "when",
    "where",
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
    "just",
    "our",
    "your",
    "their",
}


# Common UK cities/locations to detect
LOCATION_KEYWORDS = {
    "london",
    "manchester",
    "birmingham",
    "leeds",
    "liverpool",
    "sheffield",
    "bristol",
    "cardiff",
    "edinburgh",
    "glasgow",
    "newcastle",
    "nottingham",
    "southampton",
    "leicester",
    "coventry",
}


# Service-related keywords
SERVICE_KEYWORDS = {
    "plumbing",
    "electrical",
    "hvac",
    "heating",
    "roofing",
    "carpentry",
    "painting",
    "maintenance",
    "installation",
    "repair",
}


class ContentAnalyzer:
    """
    Analyzes page content to detect gaps in content and schema.

    Detects:
    - Missing pages (services, locations mentioned without dedicated pages)
    - Missing schema (FAQ, testimonials, services not in proper blocks)
    - Thin content (low word count, poor text-to-markup ratio)
    """

    def __init__(self, site: Site | None, page: Page) -> None:
        """
        Initialize the content analyzer.

        Args:
            site: The Wagtail Site instance
            page: The Page to analyze
        """
        self.site = site
        self.page = page

    def analyze(self) -> list[dict[str, Any]]:
        """
        Analyze the page and return a list of content gap dictionaries.

        Returns:
            List of gap dictionaries with keys:
            - gap_type: "missing_page" | "missing_schema" | "thin_content"
            - title: Brief title
            - description: Detailed description
            - confidence_score: Float 0-1
            - source_page_id: Optional page ID
        """
        gaps = []

        # Detect missing pages
        gaps.extend(self._detect_missing_service_pages())
        gaps.extend(self._detect_missing_location_pages())

        # Detect missing schema
        gaps.extend(self._detect_missing_faq_schema())
        gaps.extend(self._detect_missing_testimonial_schema())
        gaps.extend(self._detect_missing_service_schema())

        # Detect thin content
        thin_content_gap = self._detect_thin_content()
        if thin_content_gap:
            gaps.append(thin_content_gap)

        return gaps

    def _extract_keywords(self) -> list[str]:
        """
        Extract keywords from page title and body content.

        Returns:
            List of keywords (stop words filtered out)
        """
        keywords = []

        # Extract from title
        if self.page.title:
            title_words = re.findall(r"\b\w+\b", str(self.page.title).lower())
            keywords.extend([word for word in title_words if word not in STOP_WORDS])

        # Extract from body
        body_text = self._extract_body_text()
        body_words = re.findall(r"\b\w+\b", body_text.lower())
        keywords.extend([word for word in body_words if word not in STOP_WORDS])

        return keywords

    def _extract_keywords_with_frequency(self) -> dict[str, int]:
        """
        Extract keywords with their frequency counts.

        Returns:
            Dictionary mapping keyword to count
        """
        keywords = self._extract_keywords()
        return dict(Counter(keywords))

    def _extract_body_text(self) -> str:
        """Extract plain text from StreamField body."""
        if not hasattr(self.page, "body"):
            return ""

        extra_fields = [
            getattr(self.page, "intro", None),
            getattr(self.page, "hero_intro", None),
        ]

        return extract_text_from_stream_field(self.page.body, extra_fields=extra_fields)

    def _detect_missing_service_pages(self) -> list[dict[str, Any]]:
        """Detect service mentions without dedicated ServicePage."""
        gaps = []
        keyword_freq = self._extract_keywords_with_frequency()

        # Check for service-related keywords
        for service_kw in SERVICE_KEYWORDS:
            if service_kw in keyword_freq:
                count = keyword_freq[service_kw]

                # Check if ServicePage exists for this service
                # Import here to avoid circular imports
                from sum_core.pages.services import ServicePage

                existing_page = (
                    ServicePage.objects.live()
                    .filter(title__icontains=service_kw)
                    .first()
                )

                if not existing_page:
                    # Calculate confidence based on frequency
                    confidence = min(0.5 + (count * 0.1), 1.0)

                    gaps.append(
                        {
                            "gap_type": "missing_page",
                            "title": f"Create {service_kw.title()} Service Page",
                            "description": f"The page mentions '{service_kw}' {count} time(s) but no dedicated ServicePage exists. Consider creating a service page to better organize this content.",
                            "confidence_score": confidence,
                            "source_page_id": self.page.id,
                        }
                    )

        return gaps

    def _detect_missing_location_pages(self) -> list[dict[str, Any]]:
        """Detect location mentions without LocationPage."""
        gaps = []
        keyword_freq = self._extract_keywords_with_frequency()

        # Check for location keywords
        for location_kw in LOCATION_KEYWORDS:
            if location_kw in keyword_freq:
                count = keyword_freq[location_kw]

                # Note: LocationPage doesn't exist in current codebase,
                # so we'll suggest creating one whenever we detect location mentions
                confidence = min(0.5 + (count * 0.1), 1.0)

                gaps.append(
                    {
                        "gap_type": "missing_page",
                        "title": f"Create {location_kw.title()} Location Page",
                        "description": f"The page mentions '{location_kw}' {count} time(s). Consider creating a location-specific page to better serve users searching for services in {location_kw.title()}.",
                        "confidence_score": confidence,
                        "source_page_id": self.page.id,
                    }
                )

        return gaps

    def _detect_missing_faq_schema(self) -> list[dict[str, Any]]:
        """Detect FAQ-like content not using FAQBlock."""
        gaps = []

        # Check if page already has FAQ block
        has_faq_block = False
        if hasattr(self.page, "body") and self.page.body:
            for block in self.page.body:
                if block.block_type == "faq":
                    has_faq_block = True
                    break

        if has_faq_block:
            return gaps

        # Detect question patterns in content
        body_text = self._extract_body_text()

        # Count questions (lines ending with ?)
        question_count = len(re.findall(r"\?", body_text))

        # Also check HTML for h3 tags with questions
        html_content = self._extract_body_html()
        parser = _H3QuestionParser()
        try:
            parser.feed(html_content)
        except Exception:
            h3_questions = 0
        else:
            h3_questions = parser.question_count

        # If we detect multiple questions, suggest FAQ block
        if question_count >= 3 or h3_questions >= 2:
            confidence = min(0.7 + (h3_questions * 0.1), 1.0)

            gaps.append(
                {
                    "gap_type": "missing_schema",
                    "title": "Use FAQ Block for Q&A Content",
                    "description": f"This page contains {question_count} questions but doesn't use the structured FAQ block. Using FAQBlock improves SEO and enables rich schema markup.",
                    "confidence_score": confidence,
                    "source_page_id": self.page.id,
                }
            )

        return gaps

    def _detect_missing_testimonial_schema(self) -> list[dict[str, Any]]:
        """Detect testimonial/review text not in TestimonialsBlock."""
        gaps = []

        # Check if page already has testimonials block
        has_testimonial_block = False
        if hasattr(self.page, "body") and self.page.body:
            for block in self.page.body:
                if block.block_type == "testimonials":
                    has_testimonial_block = True
                    break

        if has_testimonial_block:
            return gaps

        # Detect testimonial patterns
        body_text = self._extract_body_text()

        # Count quote marks and testimonial indicators
        quote_count = body_text.count('"')
        testimonial_indicators = [
            r"\bsaid\b",
            r"\btestimonial\b",
            r"\breview\b",
            r"\bcustomer\b.*\bsaid\b",
        ]

        indicator_matches = sum(
            len(re.findall(pattern, body_text, re.IGNORECASE))
            for pattern in testimonial_indicators
        )

        # If we detect testimonial patterns, suggest block
        if quote_count >= 4 or indicator_matches >= 2:
            confidence = min(0.7 + (indicator_matches * 0.1), 1.0)

            gaps.append(
                {
                    "gap_type": "missing_schema",
                    "title": "Use Testimonials Block for Customer Reviews",
                    "description": "This page contains customer testimonial or review content but doesn't use the structured Testimonials block. Using TestimonialsBlock enables schema markup for better SEO.",
                    "confidence_score": confidence,
                    "source_page_id": self.page.id,
                }
            )

        return gaps

    def _detect_missing_service_schema(self) -> list[dict[str, Any]]:
        """Detect service lists not using ServiceCardsBlock."""
        gaps = []

        # Check if page already has service block
        has_service_block = False
        if hasattr(self.page, "body") and self.page.body:
            for block in self.page.body:
                if block.block_type in ("service_cards", "service_detail"):
                    has_service_block = True
                    break

        if has_service_block:
            return gaps

        # Count service keyword mentions
        keyword_freq = self._extract_keywords_with_frequency()
        service_mentions = sum(keyword_freq.get(kw, 0) for kw in SERVICE_KEYWORDS)

        # If significant service mentions without service block, suggest it
        if service_mentions >= 5:
            confidence = min(0.6 + (service_mentions * 0.02), 0.9)

            gaps.append(
                {
                    "gap_type": "missing_schema",
                    "title": "Use Service Blocks for Service Listings",
                    "description": f"This page mentions services {service_mentions} times but doesn't use structured service blocks. Consider using ServiceCardsBlock or ServiceDetailBlock for better organization and schema markup.",
                    "confidence_score": confidence,
                    "source_page_id": self.page.id,
                }
            )

        return gaps

    def _detect_thin_content(self) -> dict[str, Any] | None:
        """Detect pages with insufficient content."""
        # Count words
        body_text = self._extract_body_text()
        word_count = len(body_text.split())

        # If under 300 words, flag as thin content
        if word_count < 300:
            confidence = 0.8 if word_count < 150 else 0.6

            return {
                "gap_type": "thin_content",
                "title": "Thin Content Detected",
                "description": f"This page has only {word_count} words. Pages with less than 300 words may be considered thin content by search engines. Consider adding more detailed, valuable content.",
                "confidence_score": confidence,
                "source_page_id": self.page.id,
            }

        return None

    def _calculate_content_ratio(self) -> float:
        """
        Calculate content-to-code ratio (text vs markup).

        Returns:
            Float between 0 and 1 representing text/total ratio
        """
        html_content = self._extract_body_html()
        if not html_content:
            return 0.0

        text_content = strip_html(html_content)

        # Avoid division by zero
        total_length = len(html_content)
        if total_length == 0:
            return 0.0

        text_length = len(text_content)
        ratio = text_length / total_length

        return ratio

    def _extract_body_html(self) -> str:
        """Extract raw HTML from StreamField body."""
        if not hasattr(self.page, "body"):
            return ""

        extra_fields = [
            getattr(self.page, "intro", None),
            getattr(self.page, "hero_intro", None),
        ]

        return extract_text_from_stream_field(
            self.page.body, extra_fields=extra_fields, include_html=True
        )


class _H3QuestionParser(HTMLParser):
    """Parse HTML to count H3 tags containing question marks."""

    def __init__(self) -> None:
        super().__init__()
        self._in_h3 = False
        self._buffer: list[str] = []
        self.question_count = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "h3":
            self._in_h3 = True
            self._buffer = []

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "h3" and self._in_h3:
            text = "".join(self._buffer)
            if "?" in text:
                self.question_count += 1
            self._in_h3 = False
            self._buffer = []

    def handle_data(self, data: str) -> None:
        if self._in_h3:
            self._buffer.append(data)
