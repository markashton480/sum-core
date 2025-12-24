"""
Name: Home App Config
Path: core/sum_core/test_project/home/apps.py
Purpose: Configure the test project's home app for Wagtail.
Family: Used only by the sum_core.test_project for development and testing.
Dependencies: Django, Wagtail.
"""

from __future__ import annotations

from django.apps import AppConfig


class HomeConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "home"
