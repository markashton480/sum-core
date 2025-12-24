"""
Name: Leads App Config
Path: core/sum_core/leads/apps.py
Purpose: Django AppConfig for the leads application (persistence + admin visibility).
Family: Lead management, forms, integrations, admin visibility.
Dependencies: django.apps.AppConfig
"""

from __future__ import annotations

from django.apps import AppConfig


class LeadsConfig(AppConfig):
    """Configuration for the sum_core.leads app."""

    default_auto_field: str = "django.db.models.BigAutoField"
    name: str = "sum_core.leads"
    label: str = "sum_core_leads"
    verbose_name: str = "Leads"

    def ready(self) -> None:
        """Import Wagtail admin hooks when app is ready."""
        # Import wagtail_admin to register hooks
        from sum_core.leads import wagtail_admin  # noqa: F401
