"""
Name: Image Delivery Services
Path: core/sum_core/images/services.py
Purpose: Build responsive rendition payloads and pregenerate profile renditions.
Family: sum_core image optimization.
Dependencies: wagtail image renditions, profile/settings registry.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from django.core.exceptions import ImproperlyConfigured
from sum_core.images.profiles import ImageProfile
from sum_core.images.settings import get_image_optimization_settings

logger = logging.getLogger("sum_core.images")


@dataclass(frozen=True)
class RenditionEntry:
    url: str
    width: int
    height: int


@dataclass(frozen=True)
class ResponsiveImagePayload:
    fallback_src: str
    fallback_width: int
    fallback_height: int
    fallback_srcset: str
    webp_srcset: str
    sizes: str
    loading: str
    fetchpriority: str


def is_svg_image(image: Any) -> bool:
    file_name = str(getattr(getattr(image, "file", None), "name", "")).lower()
    title = str(getattr(image, "title", "")).lower()
    return file_name.endswith(".svg") or title.endswith(".svg")


def _build_srcset(entries: list[RenditionEntry]) -> str:
    return ", ".join(f"{entry.url} {entry.width}w" for entry in entries)


def _resolve_profile(profile_name: str) -> ImageProfile:
    image_settings = get_image_optimization_settings()
    profile = image_settings.profiles.get(profile_name)
    if profile is None:
        raise ImproperlyConfigured(
            f"Unknown image profile '{profile_name}'. Known profiles: {sorted(image_settings.profiles)}"
        )
    return profile


def _safe_get_rendition(
    image: Any, spec: str, *, profile_name: str, width: int
) -> RenditionEntry | None:
    try:
        rendition = image.get_rendition(spec)
        return RenditionEntry(
            url=str(rendition.url),
            width=int(rendition.width),
            height=int(rendition.height),
        )
    except Exception as exc:
        logger.warning(
            "Rendition generation failed",
            extra={
                "image_id": getattr(image, "id", None),
                "profile": profile_name,
                "width": width,
                "spec": spec,
                "error_type": type(exc).__name__,
            },
        )
        return None


def _build_payload_from_profile(
    image: Any, profile: ImageProfile
) -> ResponsiveImagePayload:
    fallback_entries: list[RenditionEntry] = []
    webp_entries: list[RenditionEntry] = []

    for width in profile.widths:
        fallback_entry = _safe_get_rendition(
            image,
            profile.build_fallback_spec(width),
            profile_name=profile.name,
            width=width,
        )
        if fallback_entry is not None:
            fallback_entries.append(fallback_entry)

        if profile.webp_enabled:
            webp_entry = _safe_get_rendition(
                image,
                profile.build_webp_spec(width),
                profile_name=profile.name,
                width=width,
            )
            if webp_entry is not None:
                webp_entries.append(webp_entry)

    if fallback_entries:
        primary = fallback_entries[-1]
        return ResponsiveImagePayload(
            fallback_src=primary.url,
            fallback_width=primary.width,
            fallback_height=primary.height,
            fallback_srcset=_build_srcset(fallback_entries),
            webp_srcset=_build_srcset(webp_entries),
            sizes=profile.sizes,
            loading=profile.loading,
            fetchpriority=profile.fetchpriority,
        )

    logger.warning(
        "All fallback renditions failed; falling back to original image URL",
        extra={
            "image_id": getattr(image, "id", None),
            "profile": profile.name,
        },
    )

    return ResponsiveImagePayload(
        fallback_src=str(getattr(getattr(image, "file", None), "url", "")),
        fallback_width=int(getattr(image, "width", 0) or 0),
        fallback_height=int(getattr(image, "height", 0) or 0),
        fallback_srcset="",
        webp_srcset="",
        sizes=profile.sizes,
        loading=profile.loading,
        fetchpriority=profile.fetchpriority,
    )


def build_responsive_payload(image: Any, profile_name: str) -> ResponsiveImagePayload:
    """Return responsive delivery payload for template rendering."""
    profile = _resolve_profile(profile_name)
    image_settings = get_image_optimization_settings()

    if is_svg_image(image) or not image_settings.enabled:
        return ResponsiveImagePayload(
            fallback_src=str(getattr(getattr(image, "file", None), "url", "")),
            fallback_width=int(getattr(image, "width", 0) or 0),
            fallback_height=int(getattr(image, "height", 0) or 0),
            fallback_srcset="",
            webp_srcset="",
            sizes=profile.sizes,
            loading=profile.loading,
            fetchpriority=profile.fetchpriority,
        )

    return _build_payload_from_profile(image, profile)


def resolve_fallback_url(image: Any, profile_name: str) -> str:
    """Return best available fallback URL for URL-only contexts (meta tags, etc.)."""
    payload = build_responsive_payload(image, profile_name)
    return payload.fallback_src


def pregenerate_profile_renditions(
    image: Any,
    profile_name: str,
    *,
    reason: str,
) -> tuple[int, int]:
    """Generate configured renditions for an image/profile pair."""
    image_settings = get_image_optimization_settings()
    if not image_settings.enabled or is_svg_image(image):
        return (0, 0)

    profile = _resolve_profile(profile_name)
    generated_count = 0
    failure_count = 0

    for width in profile.widths:
        specs = [profile.build_fallback_spec(width)]
        if profile.webp_enabled:
            specs.append(profile.build_webp_spec(width))

        for spec in specs:
            try:
                image.get_rendition(spec)
                generated_count += 1
            except Exception as exc:
                failure_count += 1
                logger.warning(
                    "Failed to pregenerate rendition",
                    extra={
                        "image_id": getattr(image, "id", None),
                        "profiles": [profile_name],
                        "reason": reason,
                        "error_type": type(exc).__name__,
                        "spec": spec,
                    },
                )

    return generated_count, failure_count
