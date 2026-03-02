"""
Name: Image Reference Extraction
Path: core/sum_core/images/extraction.py
Purpose: Extract referenced Wagtail image IDs from model fields and stream values.
Family: sum_core image optimization.
Dependencies: Django models, Wagtail page/image APIs.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from django.db import models
from wagtail.fields import StreamField
from wagtail.images import get_image_model

IMAGE_KEY_HINTS = {
    "image",
    "image_id",
    "featured_image",
    "hero_image",
    "logo",
    "photo",
    "avatar",
    "favicon",
    "og_image",
    "og_default_image",
    "supporting_image",
}


def _is_image_fk(field: models.Field) -> bool:
    remote_field = getattr(field, "remote_field", None)
    if remote_field is None:
        return False

    image_model = get_image_model()
    related_model = getattr(remote_field, "model", None)
    if related_model is None:
        return False

    return (
        related_model == image_model
        or getattr(related_model, "_meta", None) == getattr(image_model, "_meta", None)
        or getattr(getattr(related_model, "_meta", None), "label_lower", "")
        == image_model._meta.label_lower
    )


def _collect_value_candidates(
    value: Any,
    *,
    key_hint: str | None,
    candidates: set[int],
) -> None:
    image_model = get_image_model()

    if value is None:
        return

    if isinstance(value, image_model):
        if value.id:
            candidates.add(int(value.id))
        return

    if isinstance(value, int) and key_hint:
        normalized = key_hint.casefold()
        if normalized in IMAGE_KEY_HINTS or "image" in normalized:
            candidates.add(value)
        return

    if isinstance(value, dict):
        if key_hint:
            normalized_hint = key_hint.casefold()
            if normalized_hint in IMAGE_KEY_HINTS or "image" in normalized_hint:
                nested_id = value.get("id") or value.get("pk")
                if isinstance(nested_id, int) and nested_id > 0:
                    candidates.add(nested_id)
        for key, nested in value.items():
            _collect_value_candidates(
                nested,
                key_hint=str(key),
                candidates=candidates,
            )
        return

    if isinstance(value, list | tuple | set):
        for item in value:
            _collect_value_candidates(item, key_hint=key_hint, candidates=candidates)
        return

    stream_data = getattr(value, "stream_data", None)
    if isinstance(stream_data, Iterable) and not isinstance(
        stream_data, str | bytes | dict
    ):
        for item in stream_data:
            _collect_value_candidates(item, key_hint=key_hint, candidates=candidates)
        return

    if isinstance(value, Iterable) and not isinstance(value, str | bytes | dict):
        for item in value:
            _collect_value_candidates(item, key_hint=key_hint, candidates=candidates)
        return

    stream_value = getattr(value, "value", None)
    if stream_value is not None and stream_value is not value:
        _collect_value_candidates(
            stream_value, key_hint=key_hint, candidates=candidates
        )


def _filter_existing_image_ids(candidates: Iterable[int]) -> set[int]:
    candidate_set = {candidate for candidate in candidates if candidate > 0}
    if not candidate_set:
        return set()

    image_model = get_image_model()
    return set(
        image_model.objects.filter(id__in=candidate_set).values_list("id", flat=True)
    )


def extract_image_ids_from_value(
    value: Any, *, key_hint: str | None = None
) -> set[int]:
    candidates: set[int] = set()
    _collect_value_candidates(value, key_hint=key_hint, candidates=candidates)
    return _filter_existing_image_ids(candidates)


def collect_model_image_ids(
    instance: models.Model, field_names: Iterable[str]
) -> set[int]:
    image_ids: set[int] = set()

    for field_name in field_names:
        id_attr = f"{field_name}_id"
        if hasattr(instance, id_attr):
            raw_fk_id = getattr(instance, id_attr)
            if isinstance(raw_fk_id, int) and raw_fk_id > 0:
                image_ids.add(raw_fk_id)
                continue

        value = getattr(instance, field_name, None)
        image_ids.update(extract_image_ids_from_value(value, key_hint=field_name))

    return _filter_existing_image_ids(image_ids)


def collect_page_image_ids(page: models.Model) -> set[int]:
    image_ids: set[int] = set()

    for field in page._meta.get_fields():
        if isinstance(field, models.Field) and _is_image_fk(field):
            attname = getattr(field, "attname", "")
            if attname:
                raw_fk_id = getattr(page, attname, None)
                if isinstance(raw_fk_id, int) and raw_fk_id > 0:
                    image_ids.add(raw_fk_id)
                continue

        if isinstance(field, StreamField):
            value = getattr(page, field.name, None)
            image_ids.update(extract_image_ids_from_value(value, key_hint=field.name))

    return _filter_existing_image_ids(image_ids)
