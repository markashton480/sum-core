"""
Name: Wagtail Trash Command Tests
Path: core/sum_core/wagtail_trash/tests/test_commands.py
Purpose: Tests for cleanup_trash management command.
Family: SUM Platform Core - Testing
"""

from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone
from sum_core.wagtail_trash.models import TrashedPageInfo
from sum_core.wagtail_trash.services import TrashService


class TestCleanupTrashCommand:
    """Tests for the cleanup_trash management command."""

    def test_cleanup_deletes_old_items(self, site_with_pages, trash_can, admin_user):
        """C-CT-01: Command deletes items older than specified days."""
        service = TrashService()

        # Trash a page and backdate it
        page = site_with_pages["about"]
        service.trash_page(page, user=admin_user)
        trash_info = page.trash_info
        trash_info.trashed_at = timezone.now() - timedelta(days=10)
        trash_info.save()

        # Run command with 5 days threshold
        out = StringIO()
        call_command("cleanup_trash", "--days=5", stdout=out)

        # Item should be deleted
        assert TrashedPageInfo.objects.count() == 0
        assert "Successfully deleted 1" in out.getvalue()

    def test_cleanup_keeps_recent_items(self, site_with_pages, trash_can, admin_user):
        """C-CT-02: Command keeps items newer than specified days."""
        service = TrashService()

        # Trash a page (recent)
        page = site_with_pages["about"]
        service.trash_page(page, user=admin_user)

        # Run command with 30 days threshold
        out = StringIO()
        call_command("cleanup_trash", "--days=30", stdout=out)

        # Item should still exist
        assert TrashedPageInfo.objects.count() == 1
        assert "No items older than" in out.getvalue()

    def test_cleanup_dry_run(self, site_with_pages, trash_can, admin_user):
        """C-CT-03: Dry run shows but doesn't delete."""
        service = TrashService()

        # Trash a page and backdate it
        page = site_with_pages["about"]
        service.trash_page(page, user=admin_user)
        trash_info = page.trash_info
        trash_info.trashed_at = timezone.now() - timedelta(days=10)
        trash_info.save()

        # Run command with dry-run
        out = StringIO()
        call_command("cleanup_trash", "--days=5", "--dry-run", stdout=out)

        # Item should still exist
        assert TrashedPageInfo.objects.count() == 1
        assert "DRY RUN" in out.getvalue()
        assert page.title in out.getvalue()

    def test_cleanup_default_30_days(self, site_with_pages, trash_can, admin_user):
        """C-CT-04: Default threshold is 30 days."""
        service = TrashService()

        # Trash a page and backdate it 35 days
        page = site_with_pages["about"]
        service.trash_page(page, user=admin_user)
        trash_info = page.trash_info
        trash_info.trashed_at = timezone.now() - timedelta(days=35)
        trash_info.save()

        # Run command without --days
        out = StringIO()
        call_command("cleanup_trash", stdout=out)

        # Item should be deleted
        assert TrashedPageInfo.objects.count() == 0

    def test_cleanup_multiple_items(self, site_with_pages, trash_can, admin_user):
        """C-CT-05: Command handles multiple items correctly."""
        service = TrashService()

        # Trash multiple pages with different ages
        about = site_with_pages["about"]
        contact = site_with_pages["contact"]
        blog = site_with_pages["blog"]

        service.trash_page(about, user=admin_user)
        service.trash_page(contact, user=admin_user)
        service.trash_page(blog, user=admin_user)

        # Backdate only about and contact
        about.trash_info.trashed_at = timezone.now() - timedelta(days=15)
        about.trash_info.save()
        contact.trash_info.trashed_at = timezone.now() - timedelta(days=15)
        contact.trash_info.save()

        # blog is recent, keep it
        assert TrashedPageInfo.objects.count() == 3

        # Run command with 10 days threshold
        out = StringIO()
        call_command("cleanup_trash", "--days=10", stdout=out)

        # Only blog should remain
        assert TrashedPageInfo.objects.count() == 1
        assert "Successfully deleted 2" in out.getvalue()


class TestCleanupTrashValidation:
    """Regression tests for --days validation (#1356 defect 3)."""

    def test_cleanup_rejects_negative_days(
        self, site_with_pages, trash_can, admin_user
    ):
        """C-CV-01: --days=-1 raises CommandError, does not delete anything."""
        service = TrashService()
        page = site_with_pages["about"]
        service.trash_page(page, user=admin_user)

        with pytest.raises(CommandError, match="positive number"):
            call_command("cleanup_trash", "--days=-1")

        # Nothing deleted
        assert TrashedPageInfo.objects.count() == 1

    def test_cleanup_rejects_zero_days(self, site_with_pages, trash_can, admin_user):
        """C-CV-02: --days=0 raises CommandError."""
        service = TrashService()
        page = site_with_pages["about"]
        service.trash_page(page, user=admin_user)

        with pytest.raises(CommandError, match="positive number"):
            call_command("cleanup_trash", "--days=0")

        assert TrashedPageInfo.objects.count() == 1
