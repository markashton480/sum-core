"""
Name: Image Optimization Signals
Path: core/sum_core/images/signals.py
Purpose: Trigger image pregeneration on upload, attach/update, and publish events.
Family: sum_core image optimization.
Dependencies: Django signals, Wagtail signals/models.
"""

from __future__ import annotations

import logging
from typing import Any

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from sum_core.images.dispatch import dispatch_pregeneration_for_images
from sum_core.images.extraction import collect_model_image_ids, collect_page_image_ids
from sum_core.images.settings import get_image_optimization_settings
from wagtail.images import get_image_model
from wagtail.models import Page
from wagtail.signals import page_published

logger = logging.getLogger("sum_core.images")

ATTACH_FIELD_MAP: dict[str, tuple[str, ...]] = {
    "sum_core.pages.home.HomePage": ("hero_image", "og_image", "body"),
    "sum_core.pages.blog.BlogPostPage": ("featured_image", "og_image", "body"),
    "sum_core.pages.services.ServicePage": ("featured_image", "og_image", "body"),
    "sum_core.branding.models.SiteSettings": (
        "header_logo",
        "footer_logo",
        "favicon",
        "og_default_image",
    ),
}


def _tracked_fields_for_instance(instance: Any) -> tuple[str, ...] | None:
    model_class = instance.__class__
    label = f"{model_class.__module__}.{model_class.__name__}"
    return ATTACH_FIELD_MAP.get(label)


@receiver(post_save, dispatch_uid="sum_core_images_upload_trigger")
def _on_image_upload(sender, instance, created: bool, **kwargs) -> None:
    image_model = get_image_model()
    if sender is not image_model:
        return

    image_settings = get_image_optimization_settings()
    if not created or not image_settings.pregenerate_on_upload:
        return

    dispatch_pregeneration_for_images(
        image_ids={int(instance.id)},
        profiles=list(image_settings.pregenerate_upload_profiles),
        reason="upload",
    )


@receiver(pre_save, dispatch_uid="sum_core_images_attach_pre_save")
def _capture_previous_attach_state(sender, instance, **kwargs) -> None:
    tracked_fields = _tracked_fields_for_instance(instance)
    if tracked_fields is None:
        return

    if not getattr(instance, "pk", None):
        instance._sum_core_previous_image_ids = set()
        return

    try:
        previous = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        previous_ids: set[int] = set()
    else:
        previous_ids = collect_model_image_ids(previous, tracked_fields)

    instance._sum_core_previous_image_ids = previous_ids


@receiver(post_save, dispatch_uid="sum_core_images_attach_post_save")
def _on_attach_model_save(sender, instance, created: bool, **kwargs) -> None:
    tracked_fields = _tracked_fields_for_instance(instance)
    if tracked_fields is None:
        return

    image_settings = get_image_optimization_settings()
    if not image_settings.pregenerate_on_attach:
        return

    previous_ids = getattr(instance, "_sum_core_previous_image_ids", set())
    current_ids = collect_model_image_ids(instance, tracked_fields)

    image_ids = current_ids if created else current_ids - set(previous_ids)
    if not image_ids:
        return

    dispatch_pregeneration_for_images(
        image_ids=image_ids,
        profiles=list(image_settings.pregenerate_attach_profiles),
        reason="attach",
    )


@receiver(page_published, dispatch_uid="sum_core_images_publish_trigger")
def _on_page_published(sender, instance: Page, **kwargs) -> None:
    if not isinstance(instance, Page):
        return

    image_settings = get_image_optimization_settings()
    if not image_settings.pregenerate_on_publish:
        return

    page = instance.specific if hasattr(instance, "specific") else instance
    image_ids = collect_page_image_ids(page)
    if not image_ids:
        return

    dispatch_pregeneration_for_images(
        image_ids=image_ids,
        profiles=list(image_settings.pregenerate_attach_profiles),
        reason="publish",
    )

    logger.info(
        "Queued image pregeneration from page publish",
        extra={
            "image_id": 0,
            "profiles": list(image_settings.pregenerate_attach_profiles),
            "reason": "publish",
            "duration_ms": 0,
            "generated_count": 0,
            "failure_count": 0,
        },
    )
