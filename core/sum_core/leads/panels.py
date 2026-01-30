"""
Name: Lead custom panels
Path: core/sum_core/leads/panels.py
Purpose: Custom Wagtail admin panels for Lead detail view.
Family: Lead management, admin UI.
Dependencies: Wagtail admin panels.
"""

from __future__ import annotations

from typing import Any

from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.functional import cached_property
from wagtail.admin.panels import Panel


class LeadActivityTimelinePanel(Panel):
    """
    Custom panel that displays lead activity timeline.

    Shows all activities (status changes, assignments, notes) in reverse
    chronological order with human-readable timestamps.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.heading = "Activity Timeline"

    class BoundPanel(Panel.BoundPanel):
        """Bound instance of the activity timeline panel."""

        template_name = "sum_core/admin/lead_activity_timeline.html"

        @cached_property
        def activities(self) -> Any:
            """Get all activities for this lead, ordered newest first."""
            if self.instance and self.instance.pk:
                return self.instance.activities.select_related("actor").all()
            return []

        def get_context_data(self, parent_context: dict | None = None) -> dict:
            """Add activities to template context."""
            context = super().get_context_data(parent_context)
            context["activities"] = self.activities
            return context

        def render_html(self, parent_context: dict | None = None) -> str:
            """Render the activity timeline."""
            context = self.get_context_data(parent_context)
            return render_to_string(self.template_name, context)


class LeadNotesPanel(Panel):
    """
    Custom panel that displays lead notes and allows adding new ones.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.heading = "Notes"

    class BoundPanel(Panel.BoundPanel):
        """Bound instance of the notes panel."""

        template_name = "sum_core/admin/lead_notes_panel.html"

        @cached_property
        def notes(self) -> Any:
            """Get all notes for this lead."""
            if self.instance and self.instance.pk:
                return self.instance.notes.select_related("author").all()
            return []

        def get_context_data(self, parent_context: dict | None = None) -> dict:
            """Add notes and add_note_url to template context."""
            context = super().get_context_data(parent_context)
            context["notes"] = self.notes

            if self.instance and self.instance.pk:
                context["add_note_url"] = reverse(
                    "lead_add_note", args=[self.instance.pk]
                )
            else:
                context["add_note_url"] = None

            return context

        def render_html(self, parent_context: dict | None = None) -> str:
            """Render the notes panel."""
            context = self.get_context_data(parent_context)
            return render_to_string(self.template_name, context)
