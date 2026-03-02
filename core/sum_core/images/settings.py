"""
Name: Image Optimization Settings
Path: core/sum_core/images/settings.py
Purpose: Validate and expose image optimization settings with profile overrides.
Family: sum_core image optimization.
Dependencies: django.conf.settings, django.test.signals.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from functools import lru_cache
from typing import Any

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.dispatch import receiver
from django.test.signals import setting_changed
from sum_core.images.profiles import (
    DEFAULT_IMAGE_PROFILES,
    REQUIRED_PROFILE_NAMES,
    ImageProfile,
    clamp_quality,
    sanitize_widths,
)


@dataclass(frozen=True)
class ImageOptimizationSettings:
    enabled: bool
    profiles: dict[str, ImageProfile]
    pregenerate_on_upload: bool
    pregenerate_on_attach: bool
    pregenerate_on_publish: bool
    pregenerate_upload_profiles: tuple[str, ...]
    pregenerate_attach_profiles: tuple[str, ...]
    pregenerate_sync_in_tests: bool
    pregenerate_lock_seconds: int


def _validate_profile_name_list(
    raw: Any, setting_name: str, profiles: set[str]
) -> tuple[str, ...]:
    if not isinstance(raw, list | tuple):
        raise ImproperlyConfigured(f"{setting_name} must be a list of profile names.")

    normalized: list[str] = []
    for name in raw:
        if not isinstance(name, str):
            raise ImproperlyConfigured(
                f"{setting_name} must contain only string profile names."
            )
        if name not in profiles:
            raise ImproperlyConfigured(
                f"Unknown profile '{name}' in {setting_name}. Known profiles: {sorted(profiles)}"
            )
        if name not in normalized:
            normalized.append(name)

    return tuple(normalized)


def _validate_ratio(raw_ratio: Any, profile_name: str) -> tuple[int, int] | None:
    if raw_ratio is None:
        return None
    if (
        not isinstance(raw_ratio, list | tuple)
        or len(raw_ratio) != 2
        or not all(isinstance(item, int) and item > 0 for item in raw_ratio)
    ):
        raise ImproperlyConfigured(
            f"Profile '{profile_name}' ratio must be [width, height] with positive integers."
        )
    return int(raw_ratio[0]), int(raw_ratio[1])


def _build_profiles_from_settings() -> dict[str, ImageProfile]:
    raw_overrides = getattr(settings, "SUM_CORE_IMAGE_PROFILE_OVERRIDES", {})
    if not isinstance(raw_overrides, dict):
        raise ImproperlyConfigured(
            "SUM_CORE_IMAGE_PROFILE_OVERRIDES must be a dictionary."
        )

    profiles = {name: profile for name, profile in DEFAULT_IMAGE_PROFILES.items()}

    unknown_required = set(REQUIRED_PROFILE_NAMES) - set(profiles)
    if unknown_required:
        raise ImproperlyConfigured(
            f"Missing required image profiles: {sorted(unknown_required)}"
        )

    for profile_name, override in raw_overrides.items():
        if profile_name not in profiles:
            raise ImproperlyConfigured(
                f"Unknown profile '{profile_name}' in SUM_CORE_IMAGE_PROFILE_OVERRIDES."
            )
        if not isinstance(override, dict):
            raise ImproperlyConfigured(
                f"Override for profile '{profile_name}' must be a dictionary."
            )

        profile = profiles[profile_name]

        widths = (
            sanitize_widths(override["widths"], profile_name)
            if "widths" in override
            else profile.widths
        )
        sizes = str(override.get("sizes", profile.sizes))
        base_filter = override.get("base_filter", profile.base_filter)
        if base_filter not in {"width-", "fill-"}:
            raise ImproperlyConfigured(
                f"Profile '{profile_name}' base_filter must be 'width-' or 'fill-'."
            )

        fallback_format = override.get("fallback_format", profile.fallback_format)
        if fallback_format not in {"jpeg", "png"}:
            raise ImproperlyConfigured(
                f"Profile '{profile_name}' fallback_format must be 'jpeg' or 'png'."
            )

        loading = override.get("loading", profile.loading)
        if loading not in {"lazy", "eager"}:
            raise ImproperlyConfigured(
                f"Profile '{profile_name}' loading must be 'lazy' or 'eager'."
            )

        fetchpriority = override.get("fetchpriority", profile.fetchpriority)
        if fetchpriority not in {"high", "auto"}:
            raise ImproperlyConfigured(
                f"Profile '{profile_name}' fetchpriority must be 'high' or 'auto'."
            )

        webp_quality = (
            clamp_quality(
                override["webp_quality"],
                f"SUM_CORE_IMAGE_PROFILE_OVERRIDES['{profile_name}']['webp_quality']",
            )
            if "webp_quality" in override
            else profile.webp_quality
        )

        fallback_quality = (
            clamp_quality(
                override["fallback_quality"],
                f"SUM_CORE_IMAGE_PROFILE_OVERRIDES['{profile_name}']['fallback_quality']",
            )
            if "fallback_quality" in override
            else profile.fallback_quality
        )

        ratio = _validate_ratio(override.get("ratio", profile.ratio), profile_name)
        webp_enabled = bool(override.get("webp_enabled", profile.webp_enabled))

        profiles[profile_name] = replace(
            profile,
            widths=widths,
            sizes=sizes,
            base_filter=base_filter,
            webp_quality=webp_quality,
            fallback_format=fallback_format,
            fallback_quality=fallback_quality,
            loading=loading,
            fetchpriority=fetchpriority,
            ratio=ratio,
            webp_enabled=webp_enabled,
        )

    return profiles


@lru_cache(maxsize=1)
def get_image_optimization_settings() -> ImageOptimizationSettings:
    profiles = _build_profiles_from_settings()
    profile_names = set(profiles)

    lock_seconds_raw = getattr(settings, "SUM_CORE_IMAGE_PREGENERATE_LOCK_SECONDS", 180)
    if not isinstance(lock_seconds_raw, int) or lock_seconds_raw < 1:
        raise ImproperlyConfigured(
            "SUM_CORE_IMAGE_PREGENERATE_LOCK_SECONDS must be a positive integer."
        )

    return ImageOptimizationSettings(
        enabled=bool(getattr(settings, "SUM_CORE_IMAGE_OPTIMIZATION_ENABLED", True)),
        profiles=profiles,
        pregenerate_on_upload=bool(
            getattr(settings, "SUM_CORE_IMAGE_PREGENERATE_ON_UPLOAD", True)
        ),
        pregenerate_on_attach=bool(
            getattr(settings, "SUM_CORE_IMAGE_PREGENERATE_ON_ATTACH", True)
        ),
        pregenerate_on_publish=bool(
            getattr(settings, "SUM_CORE_IMAGE_PREGENERATE_ON_PUBLISH", True)
        ),
        pregenerate_upload_profiles=_validate_profile_name_list(
            getattr(
                settings,
                "SUM_CORE_IMAGE_PREGENERATE_UPLOAD_PROFILES",
                [
                    "hero_full",
                    "card_landscape",
                    "content_inline",
                    "logo",
                    "og_social",
                ],
            ),
            "SUM_CORE_IMAGE_PREGENERATE_UPLOAD_PROFILES",
            profile_names,
        ),
        pregenerate_attach_profiles=_validate_profile_name_list(
            getattr(
                settings,
                "SUM_CORE_IMAGE_PREGENERATE_ATTACH_PROFILES",
                [
                    "hero_full",
                    "hero_block",
                    "card_landscape",
                    "content_inline",
                    "og_social",
                ],
            ),
            "SUM_CORE_IMAGE_PREGENERATE_ATTACH_PROFILES",
            profile_names,
        ),
        pregenerate_sync_in_tests=bool(
            getattr(settings, "SUM_CORE_IMAGE_PREGENERATE_SYNC_IN_TESTS", False)
        ),
        pregenerate_lock_seconds=lock_seconds_raw,
    )


@receiver(setting_changed)
def _clear_cached_image_settings(*, setting: str, **kwargs) -> None:
    if setting.startswith("SUM_CORE_IMAGE_"):
        get_image_optimization_settings.cache_clear()
