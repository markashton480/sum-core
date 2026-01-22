"""
Link validation helpers shared across pages and blocks.
"""

from __future__ import annotations

from urllib.parse import urlsplit

from django.core.exceptions import ValidationError


def validate_safe_link(value: str) -> None:
    if not value:
        return
    trimmed = value.strip()
    if trimmed.startswith("//"):
        raise ValidationError("Relative URLs must start with '/' or '#'.")
    if trimmed.startswith(("#", "/")):
        return
    parsed = urlsplit(trimmed)
    scheme = parsed.scheme.lower()
    if scheme in {"http", "https", "mailto", "tel"}:
        return
    if scheme:
        raise ValidationError("Unsupported or unsafe URL scheme.")
    if parsed.netloc:
        raise ValidationError("Relative URLs must start with '/' or '#'.")
    raise ValidationError("Relative URLs must start with '/' or '#'.")
