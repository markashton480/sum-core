"""
Name: Navigation App Config
Path: core/sum_core/navigation/apps.py
Purpose: Django AppConfig for the navigation application.
Family: Navigation System (Phase 1: Foundation)
Dependencies: django.apps
"""

from django.apps import AppConfig


class NavigationConfig(AppConfig):
    """Configuration for the navigation app."""

    name = "sum_core.navigation"
    label = "sum_core_navigation"
    verbose_name = "Navigation"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        """Import cache module to register signal handlers."""
        # Import cache module to ensure signal handlers are registered
        import sum_core.navigation.cache  # noqa: F401
