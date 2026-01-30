"""
Name: SEO Engine Wagtail Hooks
Path: core/sum_core/seo_engine/wagtail_hooks.py
Purpose: Register dashboard panels and admin viewsets for SEO Engine.
Family: SEO Engine
Dependencies: Wagtail hooks, panels, wagtail_admin module.
"""

from __future__ import annotations

from wagtail import hooks

from .panels import SEODashboardPanel


@hooks.register("construct_homepage_panels")
def add_seo_dashboard_panel(request, panels):
    """Add SEO dashboard panel to Wagtail admin homepage."""
    panels.append(SEODashboardPanel(request))
