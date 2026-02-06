"""
Name: Wagtail Trash App Config
Path: core/sum_core/wagtail_trash/apps.py
Purpose: Django AppConfig for the wagtail_trash application.
Family: SUM Platform Core - Page Management
Dependencies: django.apps
"""

from django.apps import AppConfig


class WagtailTrashConfig(AppConfig):
    """Configuration for the wagtail_trash app."""

    name = "sum_core.wagtail_trash"
    label = "wagtail_trash"
    verbose_name = "Wagtail Trash"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        """Import wagtail_hooks to register hooks on app ready."""
        import sum_core.wagtail_trash.wagtail_hooks  # noqa: F401
