"""
Name: Schema Analyzer
Path: core/sum_core/seo_engine/analyzers/schema.py
Purpose: Auto-detect and recommend Schema.org markup from page content.
Family: SEO Engine
Dependencies: Wagtail Page, Django utilities
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.utils.html import strip_tags
from wagtail.models import Page


@dataclass
class SchemaRecommendation:
    """
    A single schema recommendation detected from page content.

    Attributes:
        schema_type: Schema.org type (e.g., "FAQPage", "Service", "Person", "Review")
        data: JSON-LD structured data with @context and @type
        confidence: Confidence score from 0.0 to 1.0
    """

    schema_type: str
    data: dict[str, Any]
    confidence: float


class SchemaAnalyzer:
    """
    Analyzes page content to detect schema opportunities.

    Scans StreamField body content for known block types and extracts
    structured data suitable for Schema.org markup.
    """

    def __init__(self, page: Page) -> None:
        """
        Initialize analyzer for a given page.

        Args:
            page: Wagtail Page instance to analyze
        """
        self.page = page

    def analyze(self) -> list[SchemaRecommendation]:
        """
        Analyze the page and return all schema recommendations.

        Returns:
            List of SchemaRecommendation objects detected from page content
        """
        recommendations: list[SchemaRecommendation] = []

        # Ensure page has a body field
        if not hasattr(self.page, "body") or not self.page.body:
            return recommendations

        # Detect different schema types
        faq_rec = self._detect_faq()
        if faq_rec:
            recommendations.append(faq_rec)

        service_recs = self._detect_services()
        recommendations.extend(service_recs)

        person_recs = self._detect_team_members()
        recommendations.extend(person_recs)

        review_recs = self._detect_testimonials()
        recommendations.extend(review_recs)

        return recommendations

    def _has_required_fields(self, schema_type: str, data: dict[str, Any]) -> bool:
        """
        Validate required Schema.org fields are present.

        Returns:
            True if schema has required fields, else False.
        """
        requirements: dict[str, list[str]] = {
            "FAQPage": ["mainEntity"],
            "Service": ["name", "description"],
            "Person": ["name"],
            "Review": ["author", "reviewBody"],
        }
        required_fields = requirements.get(schema_type, [])
        for field in required_fields:
            value = data.get(field)
            if value is None:
                return False
            if isinstance(value, list) and not value:
                return False
        return True

    def _detect_faq(self) -> SchemaRecommendation | None:
        """
        Detect FAQ blocks and generate FAQPage schema.

        Returns:
            SchemaRecommendation for FAQPage if FAQ blocks found, else None
        """
        if not hasattr(self.page, "body") or not self.page.body:
            return None

        all_questions: list[dict[str, Any]] = []

        for block in self.page.body:
            if block.block_type == "faq":
                items = block.value.get("items", [])
                for item in items:
                    question = item.get("question", "").strip()
                    raw_answer = item.get("answer", "")

                    if not question:
                        continue

                    # Handle RichText or str for answer
                    if hasattr(raw_answer, "source"):
                        answer_text = strip_tags(raw_answer.source)
                    else:
                        answer_text = strip_tags(str(raw_answer))

                    all_questions.append(
                        {
                            "@type": "Question",
                            "name": question,
                            "acceptedAnswer": {
                                "@type": "Answer",
                                "text": answer_text,
                            },
                        }
                    )

        if not all_questions:
            return None

        data = {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": all_questions,
        }

        if not self._has_required_fields("FAQPage", data):
            return None

        return SchemaRecommendation(
            schema_type="FAQPage",
            data=data,
            confidence=0.9,
        )

    def _detect_services(self) -> list[SchemaRecommendation]:
        """
        Detect service blocks and generate Service schemas.

        Returns:
            List of SchemaRecommendation objects for each detected service
        """
        if not hasattr(self.page, "body") or not self.page.body:
            return []

        recommendations: list[SchemaRecommendation] = []

        for block in self.page.body:
            # Handle ServiceCardsBlock
            if block.block_type == "service_cards":
                cards = block.value.get("cards", [])
                for card in cards:
                    title = card.get("title", "").strip()
                    if not title:
                        continue

                    raw_description = card.get("description", "")
                    if hasattr(raw_description, "source"):
                        description = strip_tags(raw_description.source)
                    else:
                        description = strip_tags(str(raw_description))

                    data: dict[str, Any] = {
                        "@context": "https://schema.org",
                        "@type": "Service",
                        "name": title,
                        "description": description,
                    }

                    if not self._has_required_fields("Service", data):
                        continue

                    # Add price range if available
                    price_range = card.get("price_range", "").strip()
                    if price_range:
                        data["priceRange"] = price_range

                    recommendations.append(
                        SchemaRecommendation(
                            schema_type="Service",
                            data=data,
                            confidence=0.85,
                        )
                    )

            # Handle ServiceDetailBlock
            elif block.block_type == "service_detail":
                raw_heading = block.value.get("heading", "")
                if hasattr(raw_heading, "source"):
                    heading = strip_tags(raw_heading.source)
                else:
                    heading = strip_tags(str(raw_heading))

                if not heading:
                    continue

                raw_body = block.value.get("body", "")
                if hasattr(raw_body, "source"):
                    body = strip_tags(raw_body.source)
                else:
                    body = strip_tags(str(raw_body))

                data = {
                    "@context": "https://schema.org",
                    "@type": "Service",
                    "name": heading,
                    "description": body,
                }

                if not self._has_required_fields("Service", data):
                    continue

                recommendations.append(
                    SchemaRecommendation(
                        schema_type="Service",
                        data=data,
                        confidence=0.85,
                    )
                )

        return recommendations

    def _detect_team_members(self) -> list[SchemaRecommendation]:
        """
        Detect team member blocks and generate Person schemas.

        Returns:
            List of SchemaRecommendation objects for each team member
        """
        if not hasattr(self.page, "body") or not self.page.body:
            return []

        recommendations: list[SchemaRecommendation] = []

        for block in self.page.body:
            if block.block_type == "team_members":
                members = block.value.get("members", [])
                for member in members:
                    name = member.get("name", "").strip()
                    if not name:
                        continue

                    role = member.get("role", "").strip()
                    bio = member.get("bio", "").strip()

                    data: dict[str, Any] = {
                        "@context": "https://schema.org",
                        "@type": "Person",
                        "name": name,
                        "jobTitle": role,
                    }

                    if not self._has_required_fields("Person", data):
                        continue

                    if bio:
                        data["description"] = bio

                    recommendations.append(
                        SchemaRecommendation(
                            schema_type="Person",
                            data=data,
                            confidence=0.9,
                        )
                    )

        return recommendations

    def _detect_testimonials(self) -> list[SchemaRecommendation]:
        """
        Detect testimonial blocks and generate Review schemas.

        Returns:
            List of SchemaRecommendation objects for each testimonial
        """
        if not hasattr(self.page, "body") or not self.page.body:
            return []

        recommendations: list[SchemaRecommendation] = []

        for block in self.page.body:
            if block.block_type == "testimonials":
                testimonials = block.value.get("testimonials", [])
                for testimonial in testimonials:
                    quote = testimonial.get("quote", "").strip()
                    author_name = testimonial.get("author_name", "").strip()

                    if not quote or not author_name:
                        continue

                    # Build author Person object
                    author_data: dict[str, Any] = {
                        "@type": "Person",
                        "name": author_name,
                    }

                    # Add company/affiliation if available
                    company = testimonial.get("company", "").strip()
                    if company:
                        author_data["affiliation"] = company

                    data: dict[str, Any] = {
                        "@context": "https://schema.org",
                        "@type": "Review",
                        "author": author_data,
                        "reviewBody": quote,
                    }

                    if not self._has_required_fields("Review", data):
                        continue

                    # Add rating if available
                    rating = testimonial.get("rating")
                    if rating is not None:
                        data["reviewRating"] = {
                            "@type": "Rating",
                            "ratingValue": rating,
                            "bestRating": 5,
                        }

                    recommendations.append(
                        SchemaRecommendation(
                            schema_type="Review",
                            data=data,
                            confidence=0.85,
                        )
                    )

        return recommendations
