"""
Name: Lead activity signals
Path: core/sum_core/leads/signals.py
Purpose: Auto-create LeadActivity records on Lead changes.
Family: Lead management, audit trail.
Dependencies: Django signals, sum_core.leads.models.
"""

from __future__ import annotations

import logging
from typing import Any

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from sum_core.leads.models import ActivityType, Lead, LeadActivity, LeadNote

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Lead)
def lead_pre_save(sender: type[Lead], instance: Lead, **kwargs: Any) -> None:
    """Track old values before save for comparison."""
    if instance.pk:
        # If update_fields is provided and none of the tracked fields are being updated, skip
        update_fields = kwargs.get("update_fields")
        tracked_fields = {"status", "assigned_to"}
        if update_fields is not None and not (tracked_fields & set(update_fields)):
            return

        try:
            old = Lead.objects.only("status", "assigned_to").get(pk=instance.pk)
            instance._old_status = old.status
            instance._old_assigned_to = old.assigned_to_id
        except Lead.DoesNotExist:
            # Lead doesn't exist yet, silently skip
            pass


@receiver(post_save, sender=Lead)
def lead_post_save(
    sender: type[Lead], instance: Lead, created: bool, **kwargs: Any
) -> None:
    """Create activity records for lead creation and changes."""
    if created:
        try:
            LeadActivity.objects.create(
                lead=instance,
                action_type=ActivityType.CREATED,
                description=f"Lead created from {instance.form_type} form",
            )
        except Exception:
            logger.exception(
                "Failed to create lead activity for lead creation",
                extra={"lead_id": instance.pk},
            )
    else:
        # Check for status change
        if hasattr(instance, "_old_status") and instance._old_status != instance.status:
            actor = getattr(instance, "_change_actor", None)
            try:
                LeadActivity.objects.create(
                    lead=instance,
                    actor=actor,
                    action_type=ActivityType.STATUS_CHANGE,
                    old_value={"status": instance._old_status},
                    new_value={"status": instance.status},
                    description=(
                        f"Status changed from {instance._old_status} to {instance.status}"
                    ),
                )
            except Exception:
                logger.exception(
                    "Failed to create lead activity for status change",
                    extra={"lead_id": instance.pk},
                )

        # Check for assignment change
        if (
            hasattr(instance, "_old_assigned_to")
            and instance._old_assigned_to != instance.assigned_to_id
        ):
            old_user = (
                f"user {instance._old_assigned_to}"
                if instance._old_assigned_to
                else "unassigned"
            )
            new_user = (
                f"user {instance.assigned_to_id}"
                if instance.assigned_to_id
                else "unassigned"
            )
            try:
                LeadActivity.objects.create(
                    lead=instance,
                    action_type=ActivityType.ASSIGNMENT_CHANGE,
                    old_value={"assigned_to": instance._old_assigned_to},
                    new_value={"assigned_to": instance.assigned_to_id},
                    description=f"Assignment changed from {old_user} to {new_user}",
                )
            except Exception:
                logger.exception(
                    "Failed to create lead activity for assignment change",
                    extra={"lead_id": instance.pk},
                )


@receiver(post_save, sender=LeadNote)
def lead_note_post_save(
    sender: type[LeadNote], instance: LeadNote, created: bool, **kwargs: Any
) -> None:
    """Create activity record when a note is added to a lead."""
    if created:
        author_name = instance.author.get_full_name() if instance.author else "Unknown"
        # Truncate note content for preview (max 200 chars)
        note_preview = instance.content[:200]
        is_truncated = len(instance.content) > 200
        try:
            LeadActivity.objects.create(
                lead=instance.lead,
                actor=instance.author,
                action_type=ActivityType.NOTE_ADDED,
                new_value={
                    "note_id": instance.pk,
                    "note_preview": note_preview,
                    "is_truncated": is_truncated,
                },
                description=f"Note added by {author_name}",
            )
        except Exception:
            logger.exception(
                "Failed to create lead activity for note",
                extra={"lead_id": instance.lead_id},
            )
