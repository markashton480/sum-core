"""
Name: Image Task Dispatch
Path: core/sum_core/images/dispatch.py
Purpose: Queue (or sync-run) image pregeneration from signals/commands.
Family: sum_core image optimization.
Dependencies: Django settings, Celery task wrapper.
"""

from __future__ import annotations

import logging

from django.conf import settings
from sum_core.images.settings import get_image_optimization_settings
from sum_core.images.tasks import (
    pregenerate_profiles_for_image,
    run_pregeneration_for_image,
)

logger = logging.getLogger("sum_core.images")


def dispatch_pregeneration(
    *,
    image_id: int,
    profiles: list[str],
    reason: str,
) -> None:
    """Dispatch image pregeneration with a safe sync mode for tests."""
    if image_id <= 0:
        return

    image_settings = get_image_optimization_settings()

    try:
        should_run_sync = image_settings.pregenerate_sync_in_tests and getattr(
            settings, "CELERY_TASK_ALWAYS_EAGER", False
        )

        if should_run_sync:
            run_pregeneration_for_image(
                image_id=image_id,
                profiles=profiles,
                reason=reason,
            )
            return

        pregenerate_profiles_for_image.delay(
            image_id=image_id,
            profiles=profiles,
            reason=reason,
        )
    except Exception as exc:
        logger.warning(
            "Failed to dispatch image pregeneration",
            extra={
                "image_id": image_id,
                "profiles": profiles,
                "reason": reason,
                "duration_ms": 0,
                "generated_count": 0,
                "failure_count": 0,
                "error_type": type(exc).__name__,
            },
        )


def dispatch_pregeneration_for_images(
    *,
    image_ids: set[int] | list[int],
    profiles: list[str],
    reason: str,
) -> None:
    for image_id in sorted(set(image_ids)):
        dispatch_pregeneration(image_id=image_id, profiles=profiles, reason=reason)
