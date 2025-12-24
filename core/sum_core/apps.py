"""
Name: SumCoreConfig
Path: core/sum_core/apps.py
Purpose: Django application configuration for the sum_core shared core app.
Family: Referenced by INSTALLED_APPS in client projects and sum_core.test_project.
Dependencies: django.apps.AppConfig

Required INSTALLED_APPS for client projects:

    INSTALLED_APPS = [
        # ... Django and Wagtail apps ...
        "sum_core",
        "sum_core.pages",
        "sum_core.navigation",
        "sum_core.leads",
        "sum_core.forms",
        "sum_core.analytics",
        "sum_core.seo",          # Required for SEO template tags
        # ... your project apps ...
    ]

Note: sum_core.seo MUST be included for the {% seo_tags %} template tags to work.
See test_project/test_project/settings.py for a complete reference configuration.
"""

from django.apps import AppConfig


class SumCoreConfig(AppConfig):
    default_auto_field: str = "django.db.models.BigAutoField"
    name: str = "sum_core"

    def ready(self) -> None:
        """Wire up custom admin forms after all models are loaded."""
        from sum_core.branding.forms import SiteSettingsAdminForm
        from sum_core.branding.models import SiteSettings

        SiteSettings.base_form_class = SiteSettingsAdminForm
