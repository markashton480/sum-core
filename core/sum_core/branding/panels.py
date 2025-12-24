"""
Name: Custom Admin Panels
Path: core/sum_core/branding/panels.py
Purpose: Provide custom Wagtail panels for non-model form fields.
Family: Used by branding.models to display form-only fields in the admin.
Dependencies: Wagtail admin panels.
"""

from __future__ import annotations

from typing import Any

from django.utils.functional import cached_property
from wagtail.admin.panels import FieldPanel


class FormFieldPanel(FieldPanel):
    """
    A panel for rendering form-only fields (not model fields).

    Use this for extra fields defined on the form class that aren't
    backed by a model field. The field will be included in the form
    and rendered in the admin, but won't be saved to the database.
    """

    def clone_kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = super().clone_kwargs()
        return kwargs

    class BoundPanel(FieldPanel.BoundPanel):
        @cached_property
        def bound_field(self) -> Any:
            """Get the bound field from the form."""
            if self.field_name in self.form.fields:
                return self.form[self.field_name]
            return None

        def is_shown(self) -> bool:
            """Show the panel if the field exists in the form."""
            return self.bound_field is not None
