"""
Name: Wagtail Trash Hook Tests
Path: core/sum_core/wagtail_trash/tests/test_hooks.py
Purpose: Integration tests for Wagtail admin hooks.
Family: SUM Platform Core - Testing
"""

import pytest
from django.test import Client
from django.urls import reverse
from sum_core.wagtail_trash.models import TrashedPageInfo
from wagtail.models import Page


@pytest.fixture
def admin_client(db, admin_user):
    """Create an authenticated admin client."""
    client = Client()
    client.force_login(admin_user)
    return client


class TestDeletionInterception:
    """Tests for the before_delete_page hook."""

    def test_delete_page_moves_to_trash(self, admin_client, site_with_pages, trash_can):
        """H-DI-01: Deleting via admin moves page to trash instead."""
        page = site_with_pages["about"]
        page_id = page.pk
        delete_url = reverse("wagtailadmin_pages:delete", args=[page_id])

        # POST to delete (confirm deletion)
        response = admin_client.post(delete_url)

        # Page should still exist
        assert Page.objects.filter(pk=page_id).exists()

        # But should be in trash (has trash_info)
        page.refresh_from_db()
        assert TrashedPageInfo.objects.filter(page_id=page_id).exists()

        # Should redirect
        assert response.status_code == 302

    def test_delete_shows_success_message(
        self, admin_client, site_with_pages, trash_can
    ):
        """H-DI-02: Success message shown after trashing."""
        page = site_with_pages["contact"]
        delete_url = reverse("wagtailadmin_pages:delete", args=[page.pk])

        response = admin_client.post(delete_url, follow=True)

        # Check for success message containing "trash"
        messages = list(response.context["messages"])
        assert any("trash" in str(m).lower() for m in messages)


class TestRootProtection:
    """Tests for the root page protection hook."""

    def test_delete_root_page_blocked(self, admin_client, site_with_pages):
        """H-RP-01: Root page (depth 2) cannot be deleted."""
        home = site_with_pages["home"]
        delete_url = reverse("wagtailadmin_pages:delete", args=[home.pk])

        response = admin_client.post(delete_url, follow=True)

        # Page should still exist
        assert Page.objects.filter(pk=home.pk).exists()

        # Should have error message
        messages = list(response.context["messages"])
        assert any(
            "protected" in str(m).lower() or "cannot" in str(m).lower()
            for m in messages
        )

    def test_delete_wagtail_root_blocked(self, admin_client, site_root):
        """H-RP-02: Wagtail root (depth 1) cannot be deleted."""
        delete_url = reverse("wagtailadmin_pages:delete", args=[site_root.pk])

        admin_client.post(delete_url)

        # Page should still exist
        assert Page.objects.filter(pk=site_root.pk).exists()


class TestLargeTreeWarning:
    """Tests for the large tree warning hook."""

    def test_warning_shown_for_large_tree(self, admin_client, site_with_pages):
        """H-LTW-01: Warning shown when deleting page with 5+ children."""
        blog = site_with_pages["blog"]

        # Add more children to reach 5
        for i in range(3, 8):
            child = Page(title=f"Post {i}", slug=f"post-{i}")
            blog.add_child(instance=child)

        delete_url = reverse("wagtailadmin_pages:delete", args=[blog.pk])

        # GET to see confirmation page
        response = admin_client.get(delete_url)

        # Should have warning message
        messages = list(response.context["messages"])
        assert any(
            "warning" in str(m).lower() or "child" in str(m).lower() for m in messages
        )


class TestTrashCanExclusion:
    """Tests for excluding TrashCan from explorer."""

    def test_trashcan_hidden_from_explorer(
        self, admin_client, site_with_pages, trash_can
    ):
        """H-TCE-01: TrashCan not visible in page explorer."""
        home = site_with_pages["home"]
        explore_url = reverse("wagtailadmin_explore", args=[home.pk])

        response = admin_client.get(explore_url)

        # TrashCan slug should not appear in page listing
        # (The word "Trash" may appear in menu, but not the __trash__ slug)
        content = response.content.decode()
        assert "__trash__" not in content


class TestTrashMenuRegistration:
    """Tests for the Trash menu item."""

    def test_trash_menu_exists(self, admin_client, site_with_pages):
        """H-TM-01: Trash menu item appears in admin."""
        # Access any admin page to get the menu
        response = admin_client.get(reverse("wagtailadmin_home"))

        # Check that Trash link is present
        content = response.content.decode()
        assert reverse("wagtail_trash_index") in content or "Trash" in content


class TestTrashViews:
    """Tests for the trash admin views."""

    def test_trash_index_view(self, admin_client, trashed_page):
        """V-TI-01: Trash index shows trashed pages."""
        response = admin_client.get(reverse("wagtail_trash_index"))

        assert response.status_code == 200
        content = response.content.decode()
        assert trashed_page.title in content

    def test_restore_view_get(self, admin_client, trashed_page):
        """V-RV-01: Restore view shows confirmation."""
        url = reverse("wagtail_trash_restore", args=[trashed_page.pk])

        response = admin_client.get(url)

        assert response.status_code == 200
        content = response.content.decode()
        assert trashed_page.title in content
        assert "Restore" in content

    def test_restore_view_post(self, admin_client, trashed_page, site_with_pages):
        """V-RV-02: Restore view actually restores page."""
        page_pk = trashed_page.pk
        url = reverse("wagtail_trash_restore", args=[page_pk])

        response = admin_client.post(url)

        # Page should be restored (no more trash_info)
        assert not TrashedPageInfo.objects.filter(page_id=page_pk).exists()

        # Should redirect
        assert response.status_code == 302

    def test_delete_view_get(self, admin_client, trashed_page):
        """V-DV-01: Delete view shows confirmation."""
        url = reverse("wagtail_trash_delete", args=[trashed_page.pk])

        response = admin_client.get(url)

        assert response.status_code == 200
        content = response.content.decode()
        assert trashed_page.title in content
        assert "cannot be undone" in content.lower()

    def test_delete_view_post(self, admin_client, trashed_page):
        """V-DV-02: Delete view permanently deletes page."""
        page_pk = trashed_page.pk
        url = reverse("wagtail_trash_delete", args=[page_pk])

        response = admin_client.post(url)

        # Page should be gone
        assert not Page.objects.filter(pk=page_pk).exists()

        # Should redirect to trash index
        assert response.status_code == 302

    def test_empty_view_get(self, admin_client, trashed_page):
        """V-EV-01: Empty view shows confirmation."""
        response = admin_client.get(reverse("wagtail_trash_empty"))

        assert response.status_code == 200
        content = response.content.decode()
        assert "Empty" in content

    def test_empty_view_post(self, admin_client, trashed_page):
        """V-EV-02: Empty view deletes all trashed pages."""
        response = admin_client.post(reverse("wagtail_trash_empty"))

        # Trash should be empty
        assert TrashedPageInfo.objects.count() == 0

        # Should redirect
        assert response.status_code == 302


class TestEmptyTrashValidation:
    """Regression tests for empty-trash input validation (#1356 defect 2)."""

    def test_invalid_days_does_not_delete(self, admin_client, trashed_page):
        """V-ETV-01: Non-numeric older_than_days with empty_option=old rejects."""
        url = reverse("wagtail_trash_empty")
        response = admin_client.post(
            url,
            {"empty_option": "old", "older_than_days": "not-a-number"},
            follow=True,
        )

        # Nothing should be deleted
        assert TrashedPageInfo.objects.count() == 1
        # Error message should be present
        msgs = list(response.context["messages"])
        assert any(
            "invalid" in str(m).lower() or "positive" in str(m).lower() for m in msgs
        )

    def test_negative_days_does_not_delete(self, admin_client, trashed_page):
        """V-ETV-02: Negative older_than_days with empty_option=old rejects."""
        url = reverse("wagtail_trash_empty")
        admin_client.post(
            url,
            {"empty_option": "old", "older_than_days": "-5"},
            follow=True,
        )

        assert TrashedPageInfo.objects.count() == 1

    def test_zero_days_does_not_delete(self, admin_client, trashed_page):
        """V-ETV-03: Zero older_than_days with empty_option=old rejects."""
        url = reverse("wagtail_trash_empty")
        admin_client.post(
            url,
            {"empty_option": "old", "older_than_days": "0"},
            follow=True,
        )

        assert TrashedPageInfo.objects.count() == 1

    def test_empty_option_all_still_works(self, admin_client, trashed_page):
        """V-ETV-04: empty_option=all still empties trash normally."""
        url = reverse("wagtail_trash_empty")
        response = admin_client.post(
            url,
            {"empty_option": "all", "older_than_days": ""},
        )

        assert TrashedPageInfo.objects.count() == 0
        assert response.status_code == 302

    def test_unknown_empty_option_does_not_delete(self, admin_client, trashed_page):
        """V-ETV-05: Unknown empty_option rejects without deleting."""
        url = reverse("wagtail_trash_empty")
        response = admin_client.post(
            url,
            {"empty_option": "invalid-option", "older_than_days": ""},
            follow=True,
        )

        assert TrashedPageInfo.objects.count() == 1
        msgs = list(response.context["messages"])
        assert any("invalid" in str(m).lower() for m in msgs)

    def test_missing_empty_option_defaults_to_all(self, admin_client, trashed_page):
        """V-ETV-06: Missing empty_option defaults to 'all' (safe)."""
        url = reverse("wagtail_trash_empty")
        response = admin_client.post(url, {})

        # Default is "all" which is a valid whitelisted option
        assert TrashedPageInfo.objects.count() == 0
        assert response.status_code == 302
