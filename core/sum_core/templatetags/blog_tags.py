"""
Name: Blog template tags
Path: core/sum_core/templatetags/blog_tags.py
Purpose: Resolve computed blog anchors and rendered longform HTML.
Family: Templates.
"""

from __future__ import annotations

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def blog_block_anchor(page, block_id, fallback: str = "") -> str:
    """
    Return computed anchor for a blog block when available.

    Falls back to the provided anchor for non-blog contexts.
    """
    resolver = getattr(page, "get_blog_block_anchor", None)
    if callable(resolver):
        resolved = resolver(str(block_id) if block_id else None)
        if resolved:
            return str(resolved)
    return fallback


@register.simple_tag
def blog_longform_html(page, block_id):
    """Return longform HTML with injected heading IDs when available."""
    resolver = getattr(page, "get_longform_block_html", None)
    if callable(resolver):
        rendered = resolver(str(block_id) if block_id else None)
        if rendered:
            return mark_safe(rendered)
    return ""
