"""
Name: SEO Engine Signal Handlers
Path: core/sum_core/seo_engine/signals.py
Purpose: Connect to Wagtail signals to trigger SEO analysis on page publish.
Family: SEO Engine, signals.
Dependencies: Wagtail signals, SEO tasks.
"""

from __future__ import annotations

import logging

from wagtail.models import Page
from wagtail.signals import page_published

logger = logging.getLogger(__name__)


def _on_page_published(sender, **kwargs) -> None:
    """
    Signal handler for page_published event (SEO Engine).

    Triggers asynchronous SEO analysis when a page is published.

    Args:
        sender: The sender of the signal (Page class).
        **kwargs: Signal arguments including 'instance' (the published page).
    """
    from sum_core.seo_engine.tasks import analyze_page

    instance = kwargs.get("instance")
    if not isinstance(instance, Page):
        return

    page = instance
    logger.info(
        "Page published, queuing SEO analysis",
        extra={"page_id": page.id, "page_title": page.title},
    )

    # Queue the analysis task (gracefully handle Celery unavailability)
    # In eager mode, call the task directly to avoid broker connection issues
    try:
        from django.conf import settings

        if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
            # Run synchronously in dev/test mode
            analyze_page(page.id)
        else:
            # Queue for async execution in production
            analyze_page.delay(page.id)
    except Exception as e:
        logger.warning(
            "Could not queue SEO analysis - Celery broker unavailable",
            extra={"page_id": page.id, "error": str(e)},
        )


# Connect signal with dispatch_uid for idempotency
# Note: function is named _on_page_published to match test expectations
# Multiple signal handlers may have this same function name (e.g. pages/cache.py, navigation/cache.py)
# The test will iterate through all receivers and check the dispatch_uid
page_published.connect(_on_page_published, dispatch_uid="seo_engine_page_published")
