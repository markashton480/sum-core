"""
Name: Lead admin
Path: core/sum_core/leads/admin.py
Purpose: Provide admin visibility into Lead records and LeadSourceRule configuration.
Family: Lead management, admin visibility, attribution.
Dependencies: Django admin, sum_core.leads.models.Lead, sum_core.leads.models.LeadSourceRule.
"""

from __future__ import annotations

import json

from django.contrib import admin
from django.utils.html import format_html
from django.utils.text import Truncator
from sum_core.leads.models import Lead, LeadSourceRule


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    date_hierarchy = "submitted_at"
    list_display = (
        "submitted_at",
        "name",
        "email",
        "form_type",
        "lead_source",
        "status",
        "is_archived",
    )
    list_filter = (
        "form_type",
        "lead_source",
        "status",
        "is_archived",
        "submitted_at",
    )
    search_fields = ("name", "email", "phone", "message", "utm_campaign")

    readonly_fields = (
        "submitted_at",
        "name",
        "email",
        "phone",
        "message",
        "form_type",
        "source_page",
        "formatted_form_data",
        # Attribution fields (read-only as they're captured at submission)
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "landing_page_url",
        "page_url",
        "referrer_url",
        "lead_source",
        "lead_source_detail",
    )

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "submitted_at",
                    "status",
                    "is_archived",
                )
            },
        ),
        (
            "Contact",
            {"fields": ("name", "email", "phone", "message")},
        ),
        (
            "Form",
            {"fields": ("form_type", "source_page", "formatted_form_data")},
        ),
        (
            "Attribution",
            {
                "fields": (
                    "lead_source",
                    "lead_source_detail",
                    "utm_source",
                    "utm_medium",
                    "utm_campaign",
                    "utm_term",
                    "utm_content",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "URLs",
            {
                "fields": (
                    "landing_page_url",
                    "page_url",
                    "referrer_url",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(description="Form data")
    def formatted_form_data(self, obj: Lead) -> str:
        pretty = json.dumps(obj.form_data or {}, indent=2, sort_keys=True)
        return str(format_html("<pre style='white-space: pre-wrap'>{}</pre>", pretty))

    @admin.display(description="Message")
    def short_message(self, obj: Lead) -> str:
        return str(Truncator(obj.message).chars(60))


@admin.register(LeadSourceRule)
class LeadSourceRuleAdmin(admin.ModelAdmin):
    list_display = (
        "priority",
        "name",
        "utm_source",
        "utm_medium",
        "referrer_contains",
        "derived_source",
        "is_active",
    )
    list_display_links = ("name",)
    list_filter = ("is_active", "derived_source")
    list_editable = ("priority", "is_active")
    search_fields = ("name", "utm_source", "utm_medium", "referrer_contains")
    ordering = ("priority", "id")

    fieldsets = (
        (
            "Rule Identity",
            {
                "fields": ("name", "priority", "is_active"),
            },
        ),
        (
            "Matching Conditions",
            {
                "fields": ("utm_source", "utm_medium", "referrer_contains"),
                "description": (
                    "All non-empty fields must match for this rule to apply. "
                    "Matches are case-insensitive. Leave fields blank to skip that condition."
                ),
            },
        ),
        (
            "Derived Values",
            {
                "fields": ("derived_source", "derived_source_detail"),
            },
        ),
    )
