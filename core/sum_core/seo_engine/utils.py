"""SEO engine utilities for content extraction."""

# StreamField text extraction helpers.

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from html import unescape
from typing import Any


def extract_text_from_stream_field(
    body: Any,
    *,
    extra_fields: Iterable[Any] | None = None,
    include_html: bool = False,
) -> str:
    """Extract text from a StreamField-like value.

    Args:
        body: StreamField value or iterable of blocks.
        extra_fields: Page-level fields to include (e.g., intro, hero_intro).
        include_html: If True, return HTML content instead of plain text.

    Returns:
        Extracted text or HTML concatenated from blocks.
    """
    if not body:
        return ""

    text_parts: list[str] = []

    if isinstance(body, Iterable) and not isinstance(body, str | bytes):
        for block in body:
            block_value = _unwrap_stream_block(block)
            text_parts.extend(
                _extract_text_from_value(block_value, include_html=include_html)
            )
    else:
        text_parts.extend(_extract_text_from_value(body, include_html=include_html))

    if extra_fields:
        for value in extra_fields:
            if value:
                text_parts.extend(
                    _extract_text_from_value(value, include_html=include_html)
                )

    return " ".join(part for part in text_parts if part)


_METADATA_KEYS_TO_SKIP = frozenset({"align", "layout", "variant"})
_PREFERRED_TEXT_KEYS = frozenset(
    {
        "body",
        "content",
        "text",
        "title",
        "description",
        "heading",
        "intro",
        "summary",
        "lead",
        "quote",
        "caption",
        "label",
        "status_text",
    }
)


def _unwrap_stream_block(value: Any) -> Any:
    if (
        isinstance(value, Sequence)
        and not isinstance(value, str | bytes)
        and len(value) == 2
        and isinstance(value[0], str)
    ):
        return value[1]
    return value


def _extract_text_from_value(value: Any, *, include_html: bool) -> list[str]:
    if value is None:
        return []

    value = _unwrap_stream_block(value)

    if hasattr(value, "block_type") and hasattr(value, "value"):
        nested_value = getattr(value, "value", None)
        return _extract_text_from_value(nested_value, include_html=include_html)

    if hasattr(value, "source"):
        source = getattr(value, "source", None)

        if isinstance(source, str):
            html = source
        else:
            # Delegate to the recursive extractor when the source is not a string
            return _extract_text_from_value(source, include_html=include_html)

        return [html if include_html else strip_html(html)]

    if isinstance(value, str):
        return [value if include_html else strip_html(value)]

    if isinstance(value, Mapping):
        mapping_parts: list[str] = []
        preferred_items: list[Any] = []
        nested_iterables: list[Any] = []
        fallback_items: list[Any] = []
        for key, item in value.items():
            if isinstance(key, str) and key.lower() in _METADATA_KEYS_TO_SKIP:
                continue
            normalized_key = key.lower() if isinstance(key, str) else None
            if normalized_key and normalized_key in _PREFERRED_TEXT_KEYS:
                preferred_items.append(item)
            elif isinstance(item, Iterable) and not isinstance(item, str | bytes):
                # Always recurse into nested iterables (lists like 'cards', 'items')
                nested_iterables.append(item)
            else:
                fallback_items.append(item)

        # Process preferred text keys first
        items_to_process = preferred_items or fallback_items
        # Always process nested iterables (they contain child content)
        items_to_process = list(items_to_process) + nested_iterables

        for item in items_to_process:
            mapping_parts.extend(
                _extract_text_from_value(item, include_html=include_html)
            )
        return mapping_parts

    if isinstance(value, Iterable) and not isinstance(value, str | bytes):
        iterable_parts: list[str] = []
        for item in value:
            iterable_parts.extend(
                _extract_text_from_value(item, include_html=include_html)
            )
        return iterable_parts

    return []


def strip_html(value: str) -> str:
    """Strip HTML tags and normalize whitespace."""
    if not value:
        return ""
    text = re.sub(r"<[^>]+>", " ", value)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([.,!?;:])", r"\1", text)
    return unescape(text).strip()
