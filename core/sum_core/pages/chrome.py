"""
Chrome-related helpers for page models.
"""

from __future__ import annotations

HERO_BLOCK_TYPES = (
    "hero_image",
    "hero_gradient",
    "hero",
)

HEADER_BLOCK_TYPES = HERO_BLOCK_TYPES + ("page_header",)


def first_block_is_hero(stream_value: object | None) -> bool:
    """Return True when the first StreamField block is a hero block."""
    if not stream_value:
        return False

    for block in stream_value:
        return block.block_type in HERO_BLOCK_TYPES
    return False


def streamfield_has_header_block(stream_value: object | None) -> bool:
    """Return True when a StreamField contains header/hero block types."""
    if not stream_value:
        return False
    for block in stream_value:
        if block.block_type in HEADER_BLOCK_TYPES:
            return True
    return False
