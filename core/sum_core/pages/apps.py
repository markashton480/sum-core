"""
Name: Pages App Config
Path: core/sum_core/pages/apps.py
Purpose: Django AppConfig for the sum_core pages module containing reusable page types.
Family: SUM Platform – Page Types
Dependencies: django.apps.AppConfig
"""

from __future__ import annotations

from django.apps import AppConfig


class PagesConfig(AppConfig):
    """Configuration for the sum_core.pages app."""

    default_auto_field: str = "django.db.models.BigAutoField"
    name: str = "sum_core.pages"
    label: str = "sum_core_pages"
    verbose_name: str = "SUM Core Pages"

    def ready(self) -> None:
        """Import cache module to register signal handlers."""
        import sum_core.pages.cache  # noqa: F401
