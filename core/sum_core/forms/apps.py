"""
Name: Forms app config
Path: core/sum_core/forms/apps.py
Purpose: Django app configuration for form handling module.
Family: Forms, Platform Configuration.
Dependencies: Django.
"""

from __future__ import annotations

from django.apps import AppConfig


class FormsConfig(AppConfig):
    """Configuration for the sum_core.forms application."""

    name = "sum_core.forms"
    label = "sum_core_forms"
    verbose_name = "Form Configuration"
