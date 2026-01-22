"""
Name: Pages Wagtail hooks
Path: core/sum_core/pages/wagtail_hooks.py
Purpose: Register admin viewsets for page listings.
Family: Pages, Admin UX.
Dependencies: Wagtail hooks, page listing viewsets.
"""

from __future__ import annotations

from sum_core.pages.wagtail_admin import BlogViewSetGroup
from wagtail import hooks
from wagtail.admin.rich_text.converters.html_to_contentstate import (
    InlineStyleElementHandler,
)
from wagtail.admin.rich_text.editors.draftail.features import InlineStyleFeature


@hooks.register("register_admin_viewset")
def register_blog_viewset_group() -> BlogViewSetGroup:
    """Register the Blog viewset group in Wagtail admin."""
    return BlogViewSetGroup()


@hooks.register("register_rich_text_features")
def register_accent_feature(features) -> None:
    """Register a richtext Accent inline style for controlled emphasis."""
    feature_name = "accent"
    accent_type = "ACCENT"
    control = {
        "type": accent_type,
        "label": "Accent",
        "description": "Accent color",
    }

    features.register_editor_plugin(
        "draftail",
        feature_name,
        InlineStyleFeature(control),
    )
    features.register_converter_rule(
        "contentstate",
        feature_name,
        {
            "from_database_format": {
                'span[data-rt-accent="1"]': InlineStyleElementHandler(accent_type)
            },
            "to_database_format": {
                "style_map": {
                    accent_type: {
                        "element": "span",
                        "props": {"data-rt-accent": "1"},
                    }
                }
            },
        },
    )
