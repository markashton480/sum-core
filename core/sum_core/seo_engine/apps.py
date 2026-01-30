"""
Name: SEO Engine AppConfig
Path: core/sum_core/seo_engine/apps.py
Purpose: Django app configuration for seo_engine.
Family: SEO Engine
Dependencies: Django apps framework.
"""

from __future__ import annotations

from django.apps import AppConfig


class SeoEngineConfig(AppConfig):
    """Django app configuration for seo_engine."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "sum_core.seo_engine"
    verbose_name = "SEO Engine"

    def ready(self) -> None:
        """Hook for app initialization."""
        # Import signals to ensure they are connected
        from . import signals  # noqa: F401
        from . import wagtail_admin  # noqa: F401
