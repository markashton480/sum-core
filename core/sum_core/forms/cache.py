"""
Name: Form Definition Cache
Path: core/sum_core/forms/cache.py
Purpose: Cache helpers and signal-based invalidation for FormDefinition lookups.
Family: Forms, Caching.
Dependencies: django.core.cache, django.db.models.signals
"""

from __future__ import annotations

from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

FORM_DEFINITION_CACHE_PREFIX = "form_definition"
FORM_DEFINITION_VERSION_PREFIX = "form_definition_version"
FORM_DEFINITION_CACHE_TTL_SECONDS = 1800
FORM_DEFINITION_VERSION_TTL_SECONDS = 3600


def get_form_definition_version_key(site_id: int, form_definition_id: int) -> str:
    return f"{FORM_DEFINITION_VERSION_PREFIX}:{site_id}:{form_definition_id}"


def get_form_definition_cache_key(
    site_id: int, form_definition_id: int, version: str
) -> str:
    return f"{FORM_DEFINITION_CACHE_PREFIX}:{site_id}:{form_definition_id}:{version}"


def get_form_definition_cache_version(
    site_id: int, form_definition_id: int
) -> str | None:
    version = cache.get(get_form_definition_version_key(site_id, form_definition_id))
    if version is None:
        return None
    return str(version)


def ensure_form_definition_cache_version(site_id: int, form_definition_id: int) -> str:
    version_key = get_form_definition_version_key(site_id, form_definition_id)
    if cache.add(version_key, 1, timeout=FORM_DEFINITION_VERSION_TTL_SECONDS):
        return "1"
    version = cache.get(version_key)
    return str(version) if version is not None else "1"


def bump_form_definition_cache_version(site_id: int, form_definition_id: int) -> str:
    version_key = get_form_definition_version_key(site_id, form_definition_id)
    if cache.add(version_key, 1, timeout=FORM_DEFINITION_VERSION_TTL_SECONDS):
        return "1"
    try:
        return str(cache.incr(version_key))
    except ValueError:
        cache.set(version_key, 1, timeout=FORM_DEFINITION_VERSION_TTL_SECONDS)
        return "1"


@receiver(post_save, dispatch_uid="form_definition_cache_version_save")
def _on_form_definition_save(sender, instance, **kwargs) -> None:
    from sum_core.forms.models import FormDefinition

    if sender is FormDefinition and instance.pk:
        bump_form_definition_cache_version(instance.site_id, instance.pk)


@receiver(post_delete, dispatch_uid="form_definition_cache_version_delete")
def _on_form_definition_delete(sender, instance, **kwargs) -> None:
    from sum_core.forms.models import FormDefinition

    if sender is FormDefinition and instance.pk:
        bump_form_definition_cache_version(instance.site_id, instance.pk)
