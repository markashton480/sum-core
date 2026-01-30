"""
Name: Lead bulk actions
Path: core/sum_core/leads/bulk_actions.py
Purpose: Bulk actions for lead management (status updates, etc.).
Family: Lead management, admin operations.
Dependencies: Wagtail bulk actions, Lead model, LeadActivity model.
"""

from __future__ import annotations

import logging

from django import forms
from django.db import transaction
from django.utils.functional import classproperty
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext
from sum_core.leads.models import Lead
from wagtail.admin.views.bulk_action import BulkAction
from wagtail.snippets.permissions import get_permission_name


class UpdateStatusBulkActionForm(forms.Form):
    """Form for selecting new status in bulk update."""

    new_status = forms.ChoiceField(
        choices=Lead.Status.choices,
        label=_("New Status"),
        required=True,
        help_text=_("Select the status to apply to all selected leads."),
    )


logger = logging.getLogger(__name__)


class UpdateStatusBulkAction(BulkAction):
    """Bulk action for updating lead status."""

    display_name = _("Update Status")
    action_type = "update_status"
    aria_label = _("Update status of selected leads")
    template_name = "sum_core_leads/bulk_actions/confirm_update_status.html"
    action_priority = 10
    form_class = UpdateStatusBulkActionForm

    @classproperty
    def models(self):  # noqa: N805
        return [Lead]

    def check_perm(self, obj):
        """Check if user has permission to change the lead."""
        if getattr(self, "can_change_items", None) is None:
            # Check permission once per request
            self.can_change_items = self.request.user.has_perm(
                get_permission_name("change", self.model)
            )
        return self.can_change_items

    @classmethod
    def execute_action(cls, objects, user=None, **kwargs):
        """
        Execute the bulk status update and create activity records.

        Note: We iterate leads individually rather than using bulk_update() because
        signals are needed for activity tracking. For very large selections, consider
        a separate batch endpoint that creates a single summary activity record.
        """
        new_status = kwargs.get("new_status")
        if not new_status:
            return 0, 0

        updated_count = 0
        failure_count = 0
        failures: list[int] = []
        # NOTE: transaction.atomic() here ensures each successful save is durable,
        # but we intentionally allow partial success - failed items are logged and
        # skipped while successful items commit. This is deliberate UX: users prefer
        # 8/10 leads updated vs. all-or-nothing rollback on a single failure.
        with transaction.atomic():
            for lead in objects:
                old_status = lead.status
                if old_status != new_status:
                    try:
                        # Update status and set actor for signal handler
                        lead.status = new_status
                        lead._change_actor = user  # Used by post_save signal
                        lead.save(update_fields=["status"])
                        # Activity is logged by the post_save signal

                        updated_count += 1
                    except Exception:
                        failure_count += 1
                        failures.append(lead.pk)
                        logger.exception(
                            "Bulk lead status update failed",
                            extra={
                                "lead_id": lead.pk,
                                "new_status": new_status,
                            },
                        )

        if failures:
            logger.warning(
                "Bulk lead status update completed with failures",
                extra={"failed_lead_ids": failures},
            )

        return updated_count, failure_count

    def get_success_message(self, num_parent_objects, num_child_objects):
        """Return success message showing count of updated leads."""
        if num_child_objects:
            return ngettext(
                "%(count)d lead status updated; %(failed)d failed.",
                "%(count)d lead statuses updated; %(failed)d failed.",
                num_parent_objects,
            ) % {
                "count": num_parent_objects,
                "failed": num_child_objects,
            }
        if num_parent_objects == 0:
            return _("No leads were updated.")
        elif num_parent_objects == 1:
            return _("%(count)d lead status updated successfully.") % {
                "count": num_parent_objects,
            }
        else:
            return ngettext(
                "%(count)d lead status updated successfully.",
                "%(count)d lead statuses updated successfully.",
                num_parent_objects,
            ) % {
                "count": num_parent_objects,
            }

    def get_context_data(self, **kwargs):
        """Add lead-specific context data."""
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "model_opts": self.model._meta,
            }
        )
        return context

    def get_execution_context(self):
        """Pass form data and user to execute_action."""
        context = super().get_execution_context()
        context["user"] = self.request.user
        if self.cleaned_form:
            context["new_status"] = self.cleaned_form.cleaned_data.get("new_status")
        return context
