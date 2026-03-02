"""
Name: Image Profile Definitions
Path: core/sum_core/images/profiles.py
Purpose: Define rendition profile schema and platform defaults for image delivery.
Family: sum_core image optimization.
Dependencies: dataclasses, django.core.exceptions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from django.core.exceptions import ImproperlyConfigured

ImageFormat = Literal["jpeg", "png"]
ImageLoading = Literal["lazy", "eager"]
ImageFetchPriority = Literal["high", "auto"]


@dataclass(frozen=True)
class ImageProfile:
    """Typed rendition profile used by template delivery and pregeneration."""

    name: str
    widths: tuple[int, ...]
    sizes: str
    base_filter: Literal["width-", "fill-"]
    webp_quality: int
    fallback_format: ImageFormat
    fallback_quality: int
    loading: ImageLoading
    fetchpriority: ImageFetchPriority
    ratio: tuple[int, int] | None = None
    webp_enabled: bool = True

    def build_base_filter(self, width: int) -> str:
        if self.base_filter == "width-":
            return f"width-{width}"

        if self.ratio is None:
            raise ImproperlyConfigured(
                f"Profile '{self.name}' uses fill- but has no ratio configured."
            )

        ratio_w, ratio_h = self.ratio
        height = max(1, round((width * ratio_h) / ratio_w))
        return f"fill-{width}x{height}"

    def build_fallback_spec(self, width: int) -> str:
        parts = [self.build_base_filter(width), f"format-{self.fallback_format}"]
        if self.fallback_format == "jpeg":
            parts.append(f"jpegquality-{self.fallback_quality}")
        return "|".join(parts)

    def build_webp_spec(self, width: int) -> str:
        return "|".join(
            [
                self.build_base_filter(width),
                "format-webp",
                f"webpquality-{self.webp_quality}",
            ]
        )


REQUIRED_PROFILE_NAMES: tuple[str, ...] = (
    "hero_full",
    "hero_block",
    "card_landscape",
    "card_square",
    "content_inline",
    "logo",
    "avatar",
    "og_social",
)


DEFAULT_IMAGE_PROFILES: dict[str, ImageProfile] = {
    "hero_full": ImageProfile(
        name="hero_full",
        widths=(640, 960, 1280, 1600, 1920),
        sizes="100vw",
        base_filter="width-",
        webp_quality=78,
        fallback_format="jpeg",
        fallback_quality=82,
        loading="eager",
        fetchpriority="high",
    ),
    "hero_block": ImageProfile(
        name="hero_block",
        widths=(480, 768, 1024, 1366),
        sizes="(min-width: 1024px) 50vw, 100vw",
        base_filter="width-",
        webp_quality=78,
        fallback_format="jpeg",
        fallback_quality=82,
        loading="lazy",
        fetchpriority="auto",
    ),
    "card_landscape": ImageProfile(
        name="card_landscape",
        widths=(320, 480, 640, 800, 1200),
        sizes="(min-width: 1280px) 33vw, (min-width: 768px) 50vw, 100vw",
        base_filter="fill-",
        ratio=(4, 3),
        webp_quality=76,
        fallback_format="jpeg",
        fallback_quality=80,
        loading="lazy",
        fetchpriority="auto",
    ),
    "card_square": ImageProfile(
        name="card_square",
        widths=(96, 160, 240, 320, 400, 600),
        sizes="(min-width: 1280px) 20vw, (min-width: 768px) 33vw, 50vw",
        base_filter="fill-",
        ratio=(1, 1),
        webp_quality=78,
        fallback_format="jpeg",
        fallback_quality=82,
        loading="lazy",
        fetchpriority="auto",
    ),
    "content_inline": ImageProfile(
        name="content_inline",
        widths=(480, 768, 1200, 1600, 2400),
        sizes="100vw",
        base_filter="width-",
        webp_quality=80,
        fallback_format="jpeg",
        fallback_quality=84,
        loading="lazy",
        fetchpriority="auto",
    ),
    "logo": ImageProfile(
        name="logo",
        widths=(80, 120, 160, 200, 240, 320),
        sizes="(min-width: 1024px) 200px, 160px",
        base_filter="width-",
        webp_quality=80,
        fallback_format="png",
        fallback_quality=90,
        loading="lazy",
        fetchpriority="auto",
    ),
    "avatar": ImageProfile(
        name="avatar",
        widths=(48, 72, 96, 128, 192, 256),
        sizes="96px",
        base_filter="fill-",
        ratio=(1, 1),
        webp_quality=82,
        fallback_format="jpeg",
        fallback_quality=85,
        loading="lazy",
        fetchpriority="auto",
    ),
    "og_social": ImageProfile(
        name="og_social",
        widths=(1200,),
        sizes="1200px",
        base_filter="fill-",
        ratio=(40, 21),
        webp_quality=80,
        fallback_format="jpeg",
        fallback_quality=84,
        loading="eager",
        fetchpriority="high",
        webp_enabled=False,
    ),
}


def sanitize_widths(raw_widths: Any, profile_name: str) -> tuple[int, ...]:
    if not isinstance(raw_widths, list | tuple):
        raise ImproperlyConfigured(
            f"Profile '{profile_name}' widths must be a list or tuple of positive integers."
        )

    widths: set[int] = set()
    for width in raw_widths:
        if not isinstance(width, int) or width <= 0:
            raise ImproperlyConfigured(
                f"Profile '{profile_name}' widths must contain only positive integers."
            )
        widths.add(width)

    if not widths:
        raise ImproperlyConfigured(
            f"Profile '{profile_name}' must define at least one width."
        )

    return tuple(sorted(widths))


def clamp_quality(value: Any, setting_name: str) -> int:
    if not isinstance(value, int):
        raise ImproperlyConfigured(
            f"{setting_name} must be an integer between 1 and 100."
        )
    return max(1, min(100, value))
