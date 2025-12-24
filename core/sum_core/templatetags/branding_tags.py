"""
Name: sum_core Branding Tags Shim
Path: core/sum_core/templatetags/branding_tags.py
Purpose: Expose branding template tags at the app root for `{% load branding_tags %}`.
Family: Django template libraries.
Dependencies: sum_core.branding.templatetags.branding_tags.
"""

from __future__ import annotations

from sum_core.branding.templatetags.branding_tags import *  # noqa: F401,F403
