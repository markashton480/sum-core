"""
Django AppConfig for the client home app.

Replace 'project_name' with your actual project name after copying.
Both 'name' and 'label' must be updated.
"""
from __future__ import annotations

from django.apps import AppConfig


class HomeConfig(AppConfig):
    """Configuration for the client home app."""

    default_auto_field = "django.db.models.BigAutoField"
    # Update these after renaming project_name:
    name = "project_name.home"
    label = "project_name_home"
    verbose_name = "Home"
