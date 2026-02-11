"""
Name: SEO Health Analyzer
Path: core/sum_core/seo_engine/analyzers/health.py
Purpose: Analyzes page SEO health with scoring and recommendations.
Family: SEO Engine
Dependencies: Wagtail pages, HTML parsing

Scoring Categories:
    - meta_title (15 points): Optimal 50-60 chars
    - meta_description (15 points): Optimal 150-160 chars
    - heading_structure (20 points): H1 presence, logical hierarchy
    - content_length (25 points): 300+ words, 1000+ optimal
    - image_alt_text (15 points): All images have alt
    - internal_linking (10 points): 2+ internal links

Total: 100 points
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from html import escape
from html.parser import HTMLParser

from sum_core.seo_engine.utils import extract_text_from_stream_field

logger = logging.getLogger(__name__)


@dataclass
class HealthScore:
    """SEO health score result."""

    score: int  # Overall score 0-100
    breakdown: dict[str, int]  # Category scores
    recommendations: list[str]  # Actionable suggestions


class HeadingParser(HTMLParser):
    """Parse HTML to extract heading tags."""

    def __init__(self):
        super().__init__()
        self.headings = []

    def handle_starttag(self, tag, attrs):
        if tag in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            self.headings.append(tag)


class LinkParser(HTMLParser):
    """Parse HTML to extract internal links."""

    def __init__(self):
        super().__init__()
        self.internal_links = 0

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            attrs_dict = dict(attrs)
            href = attrs_dict.get("href") or ""
            # Internal links start with / but not //
            if href.startswith("/") and not href.startswith("//"):
                self.internal_links += 1


class HealthAnalyzer:
    """Analyzes page SEO health and provides scoring."""

    # Scoring weights (out of 100)
    WEIGHTS = {
        "meta_title": 15,
        "meta_description": 15,
        "heading_structure": 20,
        "content_length": 25,
        "image_alt_text": 15,
        "internal_linking": 10,
    }

    def __init__(self, page):
        """Initialize analyzer with a page."""
        self.page = page

    def analyze(self) -> HealthScore:
        """Analyze page and return health score."""
        breakdown = {
            "meta_title": self._score_meta_title(),
            "meta_description": self._score_meta_description(),
            "heading_structure": self._score_heading_structure(),
            "content_length": self._score_content_length(),
            "image_alt_text": self._score_image_alt_text(),
            "internal_linking": self._score_internal_links(),
        }

        # Calculate weighted overall score
        overall_score = 0
        for category, score in breakdown.items():
            weight = self.WEIGHTS[category]
            overall_score += int((score / 100) * weight)

        recommendations = self._generate_recommendations(breakdown)

        return HealthScore(
            score=overall_score, breakdown=breakdown, recommendations=recommendations
        )

    def _score_meta_title(self) -> int:
        """Score meta title length (optimal 50-60 chars)."""
        # Handle None values explicitly
        seo_title = getattr(self.page, "seo_title", None)
        page_title = getattr(self.page, "title", None)
        title = seo_title or page_title or ""
        length = len(title)

        if length == 0:
            return 0
        elif 50 <= length <= 60:
            return 100
        elif 30 <= length < 50:
            # Gradually increase from 60 to 100
            return 60 + int((length - 30) * 2)
        elif 60 < length <= 70:
            # Gradually decrease from 100 to 75
            return 100 - int((length - 60) * 2.5)
        elif length < 30:
            # Too short: 0-60
            return max(0, int(length * 2))
        else:
            # Too long (>70): 75 down to 50
            excess = min(length - 70, 30)
            return max(50, 75 - int(excess * 0.83))

    def _score_meta_description(self) -> int:
        """Score meta description length (optimal 150-160 chars)."""
        # Handle None values explicitly
        description = getattr(self.page, "search_description", None) or ""
        length = len(description)

        if length == 0:
            return 0
        elif 150 <= length <= 160:
            return 100
        elif 100 <= length < 150:
            # Gradually increase from 50 to 100
            return 50 + int(length - 100)
        elif 160 < length <= 180:
            # Gradually decrease from 100 to 75
            return 100 - int((length - 160) * 1.25)
        elif length < 100:
            # Too short: scale from 0 to 50
            return max(0, int(length * 0.5))
        else:
            # Too long (>180): 75 down to 50
            excess = min(length - 180, 40)
            return max(50, 75 - int(excess * 0.625))

    def _score_heading_structure(self) -> int:
        """Score heading structure and hierarchy."""
        headings = self._extract_headings()
        if not headings:
            return 0

        score = 0

        # Check for H1 presence (critical)
        h1_count = headings.count("h1")
        if h1_count == 0:
            # Missing H1 is heavily penalized
            score = 30
        elif h1_count == 1:
            # Perfect
            score = 60
        else:
            # Multiple H1s - minor penalty
            score = 50

        # Check hierarchy (only add bonus if we have exactly one H1)
        if len(headings) > 1 and h1_count == 1:
            hierarchy_good = True
            prev_level = int(headings[0][1])
            for heading in headings[1:]:
                curr_level = int(heading[1])
                # Check if hierarchy jumps more than 1 level
                if curr_level - prev_level > 1:
                    hierarchy_good = False
                    break
                prev_level = curr_level

            if hierarchy_good:
                # Bonus for good hierarchy
                score = min(100, score + 40)
            else:
                # Penalty for poor hierarchy
                score = max(score, score + 10)
        elif len(headings) > 1 and h1_count != 1:
            # Multiple H1s or no H1: check hierarchy but only add small bonus
            hierarchy_good = True
            prev_level = int(headings[0][1])
            for heading in headings[1:]:
                curr_level = int(heading[1])
                if curr_level - prev_level > 1:
                    hierarchy_good = False
                    break
                prev_level = curr_level

            if not hierarchy_good:
                # Additional penalty for poor hierarchy
                score = max(score, score + 10)

        return score

    def _score_content_length(self) -> int:
        """Score content length (thin content detection)."""
        html_content = self._extract_html_from_body()
        if not html_content:
            return 0

        # Strip HTML tags and count words
        text = re.sub(r"<[^>]+>", " ", html_content)
        words = text.split()
        word_count = len(words)

        if word_count == 0:
            return 0
        elif word_count < 300:
            # Thin content: scale from 0 to 40
            return min(40, int(word_count / 300 * 40))
        elif word_count < 1000:
            # Adequate content: scale from 40 to 90
            return 40 + int((word_count - 300) / 700 * 50)
        else:
            # Good content: 90-100
            return min(100, 90 + int((word_count - 1000) / 1000 * 10))

    def _score_image_alt_text(self) -> int:
        """Score image alt text presence."""
        if not hasattr(self.page, "body") or not self.page.body:
            return 100  # No images = neutral/high score

        total_images = 0
        images_with_alt = 0

        for block in self.page.body:
            block_type = block.block_type
            if block_type == "image_block":
                total_images += 1
                value = block.value
                if isinstance(value, dict):
                    alt_text = value.get("alt_text", "")
                    if alt_text and alt_text.strip():
                        images_with_alt += 1

        if total_images == 0:
            return 100  # No images = not penalized

        # Calculate percentage
        percentage = images_with_alt / total_images
        return int(percentage * 100)

    def _score_internal_links(self) -> int:
        """Score internal link count (orphan detection)."""
        html_content = self._extract_html_from_body()
        if not html_content:
            return 0

        # Parse internal links
        parser = LinkParser()
        try:
            parser.feed(html_content)
        except Exception as e:
            logger.warning("HTML parsing failed", extra={"error": str(e)})
            # Handle malformed HTML gracefully
            pass

        link_count = parser.internal_links

        if link_count == 0:
            return 30  # Orphan page
        elif link_count == 1:
            return 60  # Partial credit
        else:
            # 2+ links = good
            return min(100, 80 + link_count * 5)

    def _extract_html_from_body(self) -> str:
        """Extract HTML content from body StreamField."""
        # Support test injection of HTML (for testing H1 handling)
        if hasattr(self.page, "_test_html"):
            return self.page._test_html

        if not hasattr(self.page, "body"):
            return ""

        if not self.page.body:
            return ""

        extra_fields = [
            getattr(self.page, "intro", None),
            getattr(self.page, "hero_intro", None),
        ]

        return extract_text_from_stream_field(
            self.page.body, extra_fields=extra_fields, include_html=True
        )

    def _extract_headings(self) -> list[str]:
        """Extract heading tags from body HTML plus template-rendered SEO H1."""
        html_content = self._extract_html_from_body() or ""

        # SEO H1 is rendered in templates, not StreamField body, so include it for analysis.
        seo_h1 = getattr(self.page, "seo_h1", None) or ""

        if seo_h1.strip():
            html_content = f"<h1>{escape(seo_h1)}</h1>{html_content}"

        if not html_content:
            return []

        parser = HeadingParser()
        try:
            parser.feed(html_content)
        except Exception as e:
            logger.warning("HTML parsing failed", extra={"error": str(e)})

        return parser.headings

    def _generate_recommendations(self, breakdown: dict[str, int]) -> list[str]:
        """Generate actionable recommendations based on scores."""
        recommendations = []

        if breakdown["meta_title"] < 70:
            seo_title = getattr(self.page, "seo_title", None)
            page_title = getattr(self.page, "title", None)
            title = seo_title or page_title or ""
            title_length = len(title)
            if title_length == 0:
                recommendations.append("Add a meta title (optimal: 50-60 characters)")
            elif title_length < 50:
                recommendations.append(
                    "Meta title is too short. Aim for 50-60 characters."
                )
            elif title_length > 60:
                recommendations.append(
                    "Meta title is too long. Keep it between 50-60 characters."
                )

        if breakdown["meta_description"] < 70:
            description = getattr(self.page, "search_description", None) or ""
            desc_length = len(description)
            if desc_length == 0:
                recommendations.append(
                    "Add a meta description (optimal: 150-160 characters)"
                )
            elif desc_length < 150:
                recommendations.append(
                    "Meta description is too short. Aim for 150-160 characters."
                )
            elif desc_length > 160:
                recommendations.append(
                    "Meta description is too long. Keep it between 150-160 characters."
                )

        if breakdown["heading_structure"] < 70:
            headings = self._extract_headings()
            h1_count = headings.count("h1")
            if h1_count == 0:
                recommendations.append(
                    "Add a single H1 heading to establish page topic."
                )
            elif h1_count > 1:
                recommendations.append(
                    "Use only one H1 heading per page for better SEO."
                )
            else:
                recommendations.append(
                    "Improve heading hierarchy (H1→H2→H3). Don't skip levels."
                )

        if breakdown["content_length"] < 70:
            recommendations.append(
                "Add more content. Aim for at least 300 words (1000+ is optimal)."
            )

        if breakdown["image_alt_text"] < 70:
            recommendations.append(
                "Add descriptive alt text to all images for accessibility and SEO."
            )

        if breakdown["internal_linking"] < 70:
            recommendations.append(
                "Add 2-3 internal links to related pages to improve site structure."
            )

        return recommendations
