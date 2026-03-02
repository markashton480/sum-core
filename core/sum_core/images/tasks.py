"""
Name: Image Pregeneration Tasks
Path: core/sum_core/images/tasks.py
Purpose: Background pregeneration of configured image rendition profiles.
Family: sum_core image optimization.
Dependencies: Celery, Django cache, Wagtail image model.
"""

from __future__ import annotations

import logging
from time import perf_counter

from celery import shared_task
from django.core.cache import cache
from django.db import DatabaseError, OperationalError
from sum_core.images.services import pregenerate_profile_renditions
from sum_core.images.settings import get_image_optimization_settings
from wagtail.images import get_image_model

logger = logging.getLogger("sum_core.images")

MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 30


def _build_lock_key(image_id: int, profiles: tuple[str, ...]) -> str:
    profile_key = ":".join(sorted(profiles))
    return f"sum_core:images:pregenerate:{image_id}:{profile_key}"


def run_pregeneration_for_image(
    *,
    image_id: int,
    profiles: list[str],
    reason: str,
) -> dict[str, int | str]:
    image_settings = get_image_optimization_settings()
    selected_profiles = tuple(dict.fromkeys(profiles))

    lock_key = _build_lock_key(image_id, selected_profiles)
    lock_acquired = cache.add(
        lock_key,
        "1",
        timeout=image_settings.pregenerate_lock_seconds,
    )

    if not lock_acquired:
        logger.info(
            "Skipped image pregeneration due to active lock",
            extra={
                "image_id": image_id,
                "profiles": list(selected_profiles),
                "reason": reason,
                "duration_ms": 0,
                "generated_count": 0,
                "failure_count": 0,
            },
        )
        return {
            "image_id": image_id,
            "generated_count": 0,
            "failure_count": 0,
            "reason": reason,
        }

    started_at = perf_counter()
    generated_count = 0
    failure_count = 0

    try:
        image_model = get_image_model()
        image = image_model.objects.filter(id=image_id).first()
        if image is None:
            logger.warning(
                "Image not found during pregeneration",
                extra={
                    "image_id": image_id,
                    "profiles": list(selected_profiles),
                    "reason": reason,
                    "duration_ms": 0,
                    "generated_count": 0,
                    "failure_count": 0,
                },
            )
            return {
                "image_id": image_id,
                "generated_count": 0,
                "failure_count": 0,
                "reason": reason,
            }

        for profile_name in selected_profiles:
            generated, failed = pregenerate_profile_renditions(
                image,
                profile_name,
                reason=reason,
            )
            generated_count += generated
            failure_count += failed

        duration_ms = round((perf_counter() - started_at) * 1000)
        logger_method = logger.info if failure_count == 0 else logger.warning
        logger_method(
            "Completed image pregeneration",
            extra={
                "image_id": image_id,
                "profiles": list(selected_profiles),
                "reason": reason,
                "duration_ms": duration_ms,
                "generated_count": generated_count,
                "failure_count": failure_count,
            },
        )

        return {
            "image_id": image_id,
            "generated_count": generated_count,
            "failure_count": failure_count,
            "reason": reason,
        }
    finally:
        cache.delete(lock_key)


@shared_task(
    bind=True, max_retries=MAX_RETRIES, default_retry_delay=RETRY_BACKOFF_SECONDS
)
def pregenerate_profiles_for_image(
    self,
    image_id: int,
    profiles: list[str],
    reason: str,
) -> dict[str, int | str]:
    try:
        return run_pregeneration_for_image(
            image_id=image_id,
            profiles=profiles,
            reason=reason,
        )
    except (DatabaseError, OperationalError, OSError) as exc:
        if self.request.retries < MAX_RETRIES:
            raise self.retry(exc=exc)

        logger.error(
            "Image pregeneration exhausted retries",
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
        return {
            "image_id": image_id,
            "generated_count": 0,
            "failure_count": 0,
            "reason": reason,
        }
    except Exception as exc:
        logger.error(
            "Image pregeneration failed",
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
        return {
            "image_id": image_id,
            "generated_count": 0,
            "failure_count": 0,
            "reason": reason,
        }
