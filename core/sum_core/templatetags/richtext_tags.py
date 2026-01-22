"""
Name: Rich text template tags
Path: core/sum_core/templatetags/richtext_tags.py
Purpose: Provide rich text helpers for inline rendering.
Family: Templates.
Dependencies: Wagtail richtext renderer.
"""

from __future__ import annotations

import re

from django import template
from django.utils.safestring import mark_safe
from wagtail.templatetags.wagtailcore_tags import richtext

register = template.Library()


@register.filter(name="richtext_inline")
def richtext_inline(value) -> str:
    """Render richtext without a wrapping paragraph when possible."""
    if not value:
        return ""

    html = str(richtext(value)).strip()
    match = re.fullmatch(r"<p>(.*)</p>", html, flags=re.S)
    if match:
        html = match.group(1).strip()
    return mark_safe(html)
