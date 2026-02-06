"""
Name: Wagtail Trash Model Tests
Path: core/sum_core/wagtail_trash/tests/test_models.py
Purpose: Unit tests for TrashCan and TrashedPageInfo models.
Family: SUM Platform Core - Testing
"""

import pytest
from django.http import Http404
from sum_core.wagtail_trash.models import TrashCan, TrashedPageInfo
from wagtail.models import Site


class TestTrashCan:
    """Tests for TrashCan model."""

    def test_trashcan_created_with_correct_slug(self, default_site):
        """TrashCan is created with __trash__ slug."""
        trash = TrashCan.get_or_create_for_site(default_site)
        assert trash.slug == TrashCan.TRASH_SLUG
        assert trash.slug == "__trash__"

    def test_trashcan_is_not_live(self, default_site):
        """TrashCan is created as unpublished."""
        trash = TrashCan.get_or_create_for_site(default_site)
        assert not trash.live

    def test_trashcan_hidden_from_menus(self, default_site):
        """TrashCan is hidden from navigation menus."""
        trash = TrashCan.get_or_create_for_site(default_site)
        assert not trash.show_in_menus

    def test_trashcan_created_as_child_of_site_root(self, default_site):
        """TrashCan is created directly under the site root page."""
        trash = TrashCan.get_or_create_for_site(default_site)
        assert trash.get_parent() == default_site.root_page

    def test_trashcan_get_or_create_returns_existing(self, default_site):
        """get_or_create_for_site returns existing TrashCan."""
        trash1 = TrashCan.get_or_create_for_site(default_site)
        trash2 = TrashCan.get_or_create_for_site(default_site)
        assert trash1.pk == trash2.pk

    def test_trashcan_serve_raises_404(self, trash_can):
        """TrashCan.serve() raises Http404."""
        from django.test import RequestFactory

        request = RequestFactory().get("/")
        with pytest.raises(Http404):
            trash_can.serve(request)

    def test_trashcan_get_url_parts_returns_none(self, trash_can):
        """TrashCan.get_url_parts() returns None."""
        assert trash_can.get_url_parts() is None

    def test_trashcan_get_default_returns_trash(self, default_site, trash_can):
        """TrashCan.get_default() returns trash for default site."""
        result = TrashCan.get_default()
        assert result is not None
        assert result.pk == trash_can.pk

    def test_trashcan_get_default_returns_none_without_site(self, db):
        """TrashCan.get_default() returns None when no default site."""
        Site.objects.filter(is_default_site=True).update(is_default_site=False)
        result = TrashCan.get_default()
        assert result is None

    def test_trashcan_get_or_create_raises_for_site_without_root(
        self, db, default_site
    ):
        """get_or_create_for_site raises ValueError for site without root."""
        from unittest.mock import Mock

        # Mock the site to have no root_page
        mock_site = Mock(spec=Site)
        mock_site.root_page = None

        with pytest.raises(ValueError, match="has no root page"):
            TrashCan.get_or_create_for_site(mock_site)

    def test_trashcan_is_not_creatable(self):
        """TrashCan cannot be created manually via admin."""
        assert TrashCan.is_creatable is False


class TestTrashedPageInfo:
    """Tests for TrashedPageInfo model."""

    def test_trashed_page_info_created(self, trashed_page):
        """TrashedPageInfo is created when page is trashed."""
        assert hasattr(trashed_page, "trash_info")
        info = trashed_page.trash_info
        assert info is not None

    def test_trashed_page_info_stores_original_parent(
        self, trashed_page, site_with_pages
    ):
        """TrashedPageInfo stores the original parent page."""
        info = trashed_page.trash_info
        assert info.original_parent == site_with_pages["home"]

    def test_trashed_page_info_stores_original_slug(self, trashed_page):
        """TrashedPageInfo stores the original slug."""
        info = trashed_page.trash_info
        assert info.original_slug == "about"

    def test_trashed_page_info_stores_original_path(self, trashed_page):
        """TrashedPageInfo stores the original URL path."""
        info = trashed_page.trash_info
        assert "about" in info.original_path

    def test_trashed_page_info_stores_trashed_by(self, trashed_page, admin_user):
        """TrashedPageInfo stores who trashed the page."""
        info = trashed_page.trash_info
        assert info.trashed_by == admin_user

    def test_trashed_page_info_has_trashed_at(self, trashed_page):
        """TrashedPageInfo records when page was trashed."""
        info = trashed_page.trash_info
        assert info.trashed_at is not None

    def test_can_restore_returns_true_when_parent_exists(self, trashed_page):
        """can_restore() returns True when original parent exists."""
        info = trashed_page.trash_info
        assert info.can_restore() is True

    def test_can_restore_returns_false_when_parent_deleted(self, trashed_page):
        """can_restore() returns False when original parent reference is gone."""
        info = trashed_page.trash_info

        # Simulate parent deletion by setting to None
        # (In real deletion, SET_NULL on FK would do this)
        TrashedPageInfo.objects.filter(pk=info.pk).update(original_parent=None)
        info.refresh_from_db()

        assert info.can_restore() is False

    def test_can_restore_returns_false_when_parent_is_none(self, trashed_page):
        """can_restore() returns False when original_parent is None."""
        info = trashed_page.trash_info
        info.original_parent = None
        info.save()

        assert info.can_restore() is False

    def test_get_restore_parent_returns_parent_when_available(
        self, trashed_page, site_with_pages
    ):
        """get_restore_parent() returns original parent when available."""
        info = trashed_page.trash_info
        assert info.get_restore_parent() == site_with_pages["home"]

    def test_get_restore_parent_returns_none_when_unavailable(self, trashed_page):
        """get_restore_parent() returns None when parent unavailable."""
        info = trashed_page.trash_info
        info.original_parent = None
        info.save()

        assert info.get_restore_parent() is None

    def test_get_trashed_root_pages_returns_trashed(self, trashed_page):
        """get_trashed_root_pages() returns pages with trash_info."""
        result = TrashedPageInfo.get_trashed_root_pages()
        page_ids = list(result.values_list("pk", flat=True))
        assert trashed_page.pk in page_ids

    def test_get_trashed_root_pages_excludes_non_trashed(self, site_with_pages):
        """get_trashed_root_pages() excludes pages without trash_info."""
        result = TrashedPageInfo.get_trashed_root_pages()
        page_ids = list(result.values_list("pk", flat=True))
        assert site_with_pages["blog"].pk not in page_ids

    def test_str_representation(self, trashed_page):
        """TrashedPageInfo has meaningful string representation."""
        info = trashed_page.trash_info
        assert "TrashInfo" in str(info)
        assert trashed_page.title in str(info)

    def test_ordering_by_trashed_at_descending(self, db, site_with_pages, admin_user):
        """TrashedPageInfo is ordered by trashed_at descending."""
        from datetime import timedelta

        from django.utils import timezone

        now = timezone.now()

        # Create TrashedPageInfo records at different times
        # Note: We test ordering without moving pages (just metadata records)
        contact = site_with_pages["contact"]
        post1 = site_with_pages["post1"]

        # Older trash info (2 days ago)
        info_old = TrashedPageInfo.objects.create(
            page=contact,
            original_parent=site_with_pages["home"],
            original_slug="contact",
            original_path="/contact/",
            trashed_by=admin_user,
            trashed_at=now - timedelta(days=2),
        )

        # Newer trash info (1 day ago)
        info_new = TrashedPageInfo.objects.create(
            page=post1,
            original_parent=site_with_pages["blog"],
            original_slug="post-1",
            original_path="/blog/post-1/",
            trashed_by=admin_user,
            trashed_at=now - timedelta(days=1),
        )

        # Verify ordering (newest first)
        infos = list(TrashedPageInfo.objects.all())
        assert len(infos) >= 2
        assert infos[0].pk == info_new.pk
        assert infos[1].pk == info_old.pk
        assert infos[0].trashed_at > infos[1].trashed_at


class TestTrashCanMultiSite:
    """Regression tests for multi-site trash isolation (#1356 defect 1)."""

    def test_separate_trash_cans_per_site(self, default_site, second_site):
        """Each site gets its own TrashCan, not a shared one."""
        trash1 = TrashCan.get_or_create_for_site(default_site)
        trash2 = TrashCan.get_or_create_for_site(second_site["site"])

        assert trash1.pk != trash2.pk
        assert trash1.get_parent().pk == default_site.root_page.pk
        assert trash2.get_parent().pk == second_site["home"].pk

    def test_get_or_create_returns_correct_trash_for_each_site(
        self, default_site, second_site
    ):
        """Repeated calls return the correct trash can for each site."""
        trash1a = TrashCan.get_or_create_for_site(default_site)
        trash2a = TrashCan.get_or_create_for_site(second_site["site"])
        trash1b = TrashCan.get_or_create_for_site(default_site)
        trash2b = TrashCan.get_or_create_for_site(second_site["site"])

        assert trash1a.pk == trash1b.pk
        assert trash2a.pk == trash2b.pk
        assert trash1a.pk != trash2a.pk


class TestCanRestoreInTrashParent:
    """Regression tests for can_restore false positive (#1356 defect 4)."""

    def test_can_restore_false_when_parent_is_descendant_inside_trash(
        self, site_with_pages, trash_can, admin_user
    ):
        """can_restore returns False when original parent is inside trash tree."""
        from sum_core.wagtail_trash.services import TrashService

        service = TrashService()
        blog = site_with_pages["blog"]
        post1 = site_with_pages["post1"]
        contact = site_with_pages["contact"]

        # Trash blog (takes post1 and post2 as descendants)
        service.trash_page(blog, user=admin_user)

        # Trash contact separately, but manually set its original_parent
        # to post1 (a descendant inside trash with no trash_info record)
        service.trash_page(contact, user=admin_user)
        post1.refresh_from_db()
        contact_info = contact.trash_info
        contact_info.original_parent = post1
        contact_info.save()

        assert contact_info.can_restore() is False

    def test_can_restore_true_when_parent_is_not_in_trash(
        self, trashed_page, site_with_pages
    ):
        """can_restore returns True when original parent is live (not in trash)."""
        info = trashed_page.trash_info
        assert info.original_parent == site_with_pages["home"]
        assert info.can_restore() is True
