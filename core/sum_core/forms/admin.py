"""
Name: Form configuration admin
Path: core/sum_core/forms/admin.py
Purpose: Django admin interface for FormConfiguration model.
Family: Forms, Admin.
Dependencies: Django admin.
"""

from __future__ import annotations

from django.contrib import admin
from sum_core.forms.models import FormConfiguration


@admin.register(FormConfiguration)
class FormConfigurationAdmin(admin.ModelAdmin):
    """Admin interface for per-site form configuration."""

    list_display = [
        "site",
        "honeypot_field_name",
        "rate_limit_per_ip_per_hour",
        "min_seconds_to_submit",
        "lead_notification_email",
    ]
    list_filter = ["site"]
    search_fields = ["site__hostname", "lead_notification_email"]

    fieldsets = [
        (
            "Site",
            {
                "fields": ["site"],
            },
        ),
        (
            "Spam Protection",
            {
                "fields": [
                    "honeypot_field_name",
                    "rate_limit_per_ip_per_hour",
                    "min_seconds_to_submit",
                ],
                "description": "Configure anti-spam measures for form submissions.",
            },
        ),
        (
            "Notifications",
            {
                "fields": ["lead_notification_email"],
                "description": "Configure where lead notifications are sent.",
            },
        ),
        (
            "Defaults",
            {
                "fields": ["default_form_type"],
                "description": "Default values for form submissions.",
            },
        ),
    ]
