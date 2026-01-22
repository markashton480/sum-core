"""
Name: Banners App Config
Path: core/sum_core/banners/apps.py
Purpose: Django AppConfig for alert banner snippets.
"""

from django.apps import AppConfig


class BannersConfig(AppConfig):
    """Configuration for the banners app."""

    name = "sum_core.banners"
    label = "sum_core_banners"
    verbose_name = "Banners"
    default_auto_field = "django.db.models.BigAutoField"
