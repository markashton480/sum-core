"""
Name: SEO Engine Celery Tasks
Path: core/sum_core/seo_engine/tasks.py
Purpose: Asynchronous SEO analysis tasks for pages.
Family: SEO Engine, async processing.
Dependencies: Celery, Django ORM, Wagtail Page model.
"""

from __future__ import annotations

import logging

from celery import shared_task
from django.db import DatabaseError, OperationalError, transaction
from django.utils import timezone
from wagtail.models import Page

logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 3
RETRY_BACKOFF = 60  # Base backoff in seconds (60, 120, 240)


def analyze_page_content(page: Page) -> tuple[dict, int]:
    """
    Perform SEO analysis on a page using all available analyzers.

    Args:
        page: The Wagtail Page instance to analyze.

    Returns:
        Tuple of (analysis_data dict, health_score int).
    """
    from sum_core.seo_engine.analyzers import (
        ContentAnalyzer,
        HealthAnalyzer,
        KeywordAnalyzer,
        SchemaAnalyzer,
    )

    # Get the site for the page
    site = page.get_site()

    # Initialize all analyzers
    schema_analyzer = SchemaAnalyzer(page)
    health_analyzer = HealthAnalyzer(page)
    content_analyzer = ContentAnalyzer(site, page)
    keyword_analyzer = KeywordAnalyzer(site)

    # Run all analyzers
    schema_results = schema_analyzer.analyze()
    health_result = health_analyzer.analyze()
    content_gaps = content_analyzer.analyze()
    keyword_result = keyword_analyzer.analyze(page)

    # Collect all results in analysis_data
    analysis_data = {
        "schema": [
            {
                "schema_type": rec.schema_type,
                "data": rec.data,
                "confidence": rec.confidence,
            }
            for rec in schema_results
        ],
        "health": {
            "score": health_result.score,
            "breakdown": health_result.breakdown,
            "recommendations": health_result.recommendations,
        },
        "content": content_gaps,  # Use "content" key for test compatibility
        "keywords": {
            "current_title": keyword_result.current_title,
            "current_description": keyword_result.current_description,
            "suggested_title": keyword_result.suggested_title,
            "suggested_description": keyword_result.suggested_description,
            "title_needs_location": keyword_result.title_needs_location,
            "description_needs_location": keyword_result.description_needs_location,
            "should_suggest": keyword_result.should_suggest,
            "importance": keyword_result.importance,
            "page_type": keyword_result.page_type,
        },
    }

    # Use health analyzer's score as the overall health score
    health_score = health_result.score

    return analysis_data, health_score


@shared_task(bind=True, max_retries=MAX_RETRIES, default_retry_delay=RETRY_BACKOFF)
def analyze_page(self, page_id: int) -> None:
    """
    Analyze a page for SEO issues and create/update PageSEOAnalysis record.

    This task is idempotent and concurrency-safe - uses select_for_update()
    to prevent race conditions when calculating version numbers.

    Args:
        page_id: The ID of the Page to analyze.
    """
    from sum_core.seo_engine.analyzers import LinkingAnalyzer
    from sum_core.seo_engine.models import PageSEOAnalysis

    try:
        # Get the specific page type (not base Page) to access body field
        try:
            page = Page.objects.get(id=page_id).specific
        except Page.DoesNotExist:
            logger.warning(
                "Page not found for SEO analysis, skipping",
                extra={"page_id": page_id},
            )
            return

        # Perform analysis
        analysis_data, health_score = analyze_page_content(page)

        # Update or create analysis record (idempotent, concurrency-safe)
        with transaction.atomic():
            # Use select_for_update to prevent race conditions
            existing = (
                PageSEOAnalysis.objects.select_for_update(nowait=False)
                .filter(page=page)
                .first()
            )
            next_version = (existing.version + 1) if existing else 1

            # Use update_or_create with computed version
            analysis, created = PageSEOAnalysis.objects.update_or_create(
                page=page,
                defaults={
                    "analysis_data": analysis_data,
                    "health_score": health_score,
                    "version": next_version,
                    "analyzed_at": timezone.now(),
                },
            )

            if created:
                logger.info(
                    "Created SEO analysis for page",
                    extra={
                        "page_id": page_id,
                        "health_score": health_score,
                    },
                )
            else:
                logger.info(
                    "Updated SEO analysis for page",
                    extra={
                        "page_id": page_id,
                        "version": analysis.version,
                        "health_score": health_score,
                    },
                )

        # Generate and save link suggestions
        site = page.get_site()
        linking_analyzer = LinkingAnalyzer(site)
        linking_analyzer.analyze(page, save=True)

    except (DatabaseError, OperationalError) as exc:
        logger.error(
            "SEO analysis failed due to transient database error",
            extra={"page_id": page_id, "error": str(exc)},
            exc_info=True,
        )
        raise
