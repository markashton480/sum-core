"""
Name: Wagtail Trash Service Tests
Path: core/sum_core/wagtail_trash/tests/test_services.py
Purpose: Unit tests for TrashService business logic.
Family: SUM Platform Core - Testing
"""

import pytest
from sum_core.wagtail_trash.models import TrashCan, TrashedPageInfo
from sum_core.wagtail_trash.services import (
    RestoreError,
    TrashError,
    TrashService,
    empty_trash,
    get_trashed_pages,
    permanent_delete,
    restore_page,
    trash_page,
)
from wagtail.models import Page


class TestTrashPageBasic:
    """Tests for TrashService.trash_page() basic functionality."""

    def test_trash_page_returns_trash_info(self, site_with_pages, admin_user):
        """S-TP-01: trash_page returns TrashedPageInfo."""
        service = TrashService()
        page = site_with_pages["about"]

        result = service.trash_page(page, user=admin_user)

        assert isinstance(result, TrashedPageInfo)

    def test_trash_page_moves_to_trash(self, site_with_pages, admin_user):
        """S-TP-02: Page is moved under TrashCan."""
        service = TrashService()
        page = site_with_pages["about"]

        service.trash_page(page, user=admin_user)

        page.refresh_from_db()
        assert page.get_parent().specific_class == TrashCan

    def test_trash_page_stores_original_parent(self, site_with_pages, admin_user):
        """S-TP-03: Original parent is stored in trash info."""
        service = TrashService()
        page = site_with_pages["about"]
        original_parent = page.get_parent()

        result = service.trash_page(page, user=admin_user)

        assert result.original_parent == original_parent

    def test_trash_page_stores_original_slug(self, site_with_pages, admin_user):
        """S-TP-04: Original slug is stored in trash info."""
        service = TrashService()
        page = site_with_pages["about"]

        result = service.trash_page(page, user=admin_user)

        assert result.original_slug == "about"

    def test_trash_page_modifies_slug(self, site_with_pages, admin_user):
        """S-TP-05: Page slug is modified to include __trashed__."""
        service = TrashService()
        page = site_with_pages["about"]

        service.trash_page(page, user=admin_user)

        page.refresh_from_db()
        assert "__trashed__" in page.slug

    def test_trash_page_stores_trashed_by(self, site_with_pages, admin_user):
        """S-TP-06: User who trashed is recorded."""
        service = TrashService()
        page = site_with_pages["about"]

        result = service.trash_page(page, user=admin_user)

        assert result.trashed_by == admin_user

    def test_trash_page_records_descendant_count(self, site_with_pages, admin_user):
        """S-TP-07: Descendant count is recorded."""
        service = TrashService()
        page = site_with_pages["blog"]  # Has 2 children

        result = service.trash_page(page, user=admin_user)

        assert result.descendant_count == 2


class TestTrashPageErrors:
    """Tests for TrashService.trash_page() error handling."""

    def test_trash_page_rejects_root_page(self, site_with_pages, admin_user):
        """S-TP-08: Cannot trash root page (depth 1)."""
        service = TrashService()
        root = Page.objects.get(depth=1)

        with pytest.raises(TrashError, match="root page"):
            service.trash_page(root, user=admin_user)

    def test_trash_page_rejects_site_root(self, site_with_pages, admin_user):
        """S-TP-09: Cannot trash site root page (depth 2)."""
        service = TrashService()
        home = site_with_pages["home"]

        with pytest.raises(TrashError, match="root page"):
            service.trash_page(home, user=admin_user)

    def test_trash_page_rejects_already_trashed(self, trashed_page, admin_user):
        """S-TP-10: Cannot trash a page already in trash."""
        service = TrashService()

        with pytest.raises(TrashError, match="already in trash"):
            service.trash_page(trashed_page, user=admin_user)

    def test_trash_page_rejects_trash_can(self, trash_can, admin_user):
        """S-TP-11: Cannot trash the TrashCan itself."""
        service = TrashService()

        with pytest.raises(TrashError, match="TrashCan"):
            service.trash_page(trash_can, user=admin_user)


class TestTrashPageWithDescendants:
    """Tests for trashing pages with descendants."""

    def test_trash_page_moves_descendants(self, site_with_pages, admin_user):
        """S-TP-12: Descendants are moved with parent."""
        service = TrashService()
        blog = site_with_pages["blog"]
        post1 = site_with_pages["post1"]

        service.trash_page(blog, user=admin_user)

        post1.refresh_from_db()
        # Post1 should still be under blog
        assert post1.get_parent().pk == blog.pk

    def test_descendants_do_not_get_trash_info(self, site_with_pages, admin_user):
        """S-TP-13: Only root trashed page gets TrashedPageInfo."""
        service = TrashService()
        blog = site_with_pages["blog"]
        post1 = site_with_pages["post1"]

        service.trash_page(blog, user=admin_user)

        post1.refresh_from_db()
        assert not TrashedPageInfo.objects.filter(page=post1).exists()


class TestRestorePageBasic:
    """Tests for TrashService.restore_page() basic functionality."""

    def test_restore_page_moves_back(self, trashed_page, site_with_pages, admin_user):
        """S-RP-01: Page is moved back to original parent."""
        service = TrashService()

        result = service.restore_page(trashed_page, user=admin_user)

        result.refresh_from_db()
        assert result.get_parent() == site_with_pages["home"]

    def test_restore_page_restores_slug(self, trashed_page, admin_user):
        """S-RP-02: Original slug is restored."""
        service = TrashService()

        result = service.restore_page(trashed_page, user=admin_user)

        assert result.slug == "about"

    def test_restore_page_deletes_trash_info(self, trashed_page, admin_user):
        """S-RP-03: TrashedPageInfo is deleted after restore."""
        service = TrashService()
        page_pk = trashed_page.pk

        service.restore_page(trashed_page, user=admin_user)

        assert not TrashedPageInfo.objects.filter(page_id=page_pk).exists()

    def test_restore_page_to_alternate_parent(
        self, trashed_page, site_with_pages, admin_user
    ):
        """S-RP-04: Can restore to a different parent."""
        service = TrashService()
        blog = site_with_pages["blog"]

        result = service.restore_page(trashed_page, user=admin_user, target_parent=blog)

        result.refresh_from_db()
        assert result.get_parent() == blog


class TestRestorePageSlugConflicts:
    """Tests for slug conflict resolution during restore."""

    def test_restore_page_resolves_slug_conflict(
        self, site_with_pages, trash_can, admin_user
    ):
        """S-RP-05: Slug conflict is resolved by appending number."""
        service = TrashService()
        about = site_with_pages["about"]
        home = site_with_pages["home"]

        # Trash the about page
        service.trash_page(about, user=admin_user)

        # Create a new page with the same slug
        new_about = Page(title="About (New)", slug="about")
        home.add_child(instance=new_about)

        # Restore should create about-1
        about.refresh_from_db()
        result = service.restore_page(about, user=admin_user)

        assert result.slug == "about-1"


class TestRestorePageErrors:
    """Tests for TrashService.restore_page() error handling."""

    def test_restore_page_rejects_non_trashed(self, site_with_pages, admin_user):
        """S-RP-06: Cannot restore a page not in trash."""
        service = TrashService()
        page = site_with_pages["about"]

        with pytest.raises(RestoreError, match="not in trash"):
            service.restore_page(page, user=admin_user)

    def test_restore_page_rejects_descendant(
        self, site_with_pages, trash_can, admin_user
    ):
        """S-RP-07: Cannot restore a descendant directly."""
        service = TrashService()
        blog = site_with_pages["blog"]
        post1 = site_with_pages["post1"]

        # Trash blog (includes post1)
        service.trash_page(blog, user=admin_user)

        post1.refresh_from_db()
        with pytest.raises(RestoreError, match="descendant"):
            service.restore_page(post1, user=admin_user)

    def test_restore_page_requires_parent_when_original_gone(
        self, trashed_page, admin_user
    ):
        """S-RP-08: Error when original parent is gone and no target specified."""
        service = TrashService()

        # Remove original parent reference
        trash_info = trashed_page.trash_info
        trash_info.original_parent = None
        trash_info.save()

        with pytest.raises(RestoreError, match="Original parent"):
            service.restore_page(trashed_page, user=admin_user)


class TestPermanentDelete:
    """Tests for TrashService.permanent_delete()."""

    def test_permanent_delete_removes_page(self, trashed_page):
        """S-PD-01: Page is permanently deleted."""
        service = TrashService()
        page_pk = trashed_page.pk

        service.permanent_delete(trashed_page)

        assert not Page.objects.filter(pk=page_pk).exists()

    def test_permanent_delete_removes_trash_info(self, trashed_page):
        """S-PD-02: TrashedPageInfo is removed with page."""
        service = TrashService()
        page_pk = trashed_page.pk

        service.permanent_delete(trashed_page)

        assert not TrashedPageInfo.objects.filter(page_id=page_pk).exists()

    def test_permanent_delete_rejects_non_trashed(self, site_with_pages):
        """S-PD-03: Cannot permanently delete non-trashed page."""
        service = TrashService()
        page = site_with_pages["about"]

        with pytest.raises(TrashError, match="not in trash"):
            service.permanent_delete(page)


class TestEmptyTrash:
    """Tests for TrashService.empty_trash()."""

    def test_empty_trash_deletes_all(self, trashed_page):
        """S-ET-01: All trashed pages are deleted."""
        service = TrashService()

        count = service.empty_trash()

        assert count == 1
        assert TrashedPageInfo.objects.count() == 0

    def test_empty_trash_with_age_filter(self, site_with_pages, trash_can, admin_user):
        """S-ET-02: Only old items are deleted when days specified."""
        from datetime import timedelta

        from django.utils import timezone

        service = TrashService()
        page = site_with_pages["about"]

        # Trash a page and backdate it
        service.trash_page(page, user=admin_user)
        trash_info = page.trash_info
        trash_info.trashed_at = timezone.now() - timedelta(days=10)
        trash_info.save()

        # Trash another page (recent)
        contact = site_with_pages["contact"]
        service.trash_page(contact, user=admin_user)

        # Empty only items older than 5 days
        count = service.empty_trash(older_than_days=5)

        assert count == 1
        assert TrashedPageInfo.objects.count() == 1

    def test_empty_trash_returns_count(self, site_with_pages, trash_can, admin_user):
        """S-ET-03: Returns count of deleted root pages."""
        service = TrashService()

        service.trash_page(site_with_pages["about"], user=admin_user)
        service.trash_page(site_with_pages["contact"], user=admin_user)

        count = service.empty_trash()

        assert count == 2


class TestGetTrashedPages:
    """Tests for TrashService.get_trashed_pages()."""

    def test_get_trashed_pages_returns_trashed(self, trashed_page):
        """S-GTP-01: Returns pages that are trashed."""
        service = TrashService()

        result = service.get_trashed_pages()

        page_pks = list(result.values_list("pk", flat=True))
        assert trashed_page.pk in page_pks

    def test_get_trashed_pages_excludes_non_trashed(
        self, site_with_pages, trashed_page
    ):
        """S-GTP-02: Does not return non-trashed pages."""
        service = TrashService()

        result = service.get_trashed_pages()

        page_pks = list(result.values_list("pk", flat=True))
        assert site_with_pages["blog"].pk not in page_pks


class TestModuleFunctions:
    """Tests for module-level convenience functions."""

    def test_trash_page_function(self, site_with_pages, admin_user):
        """Module function trash_page works."""
        page = site_with_pages["contact"]

        result = trash_page(page, user=admin_user)

        assert isinstance(result, TrashedPageInfo)

    def test_restore_page_function(self, trashed_page, admin_user):
        """Module function restore_page works."""
        result = restore_page(trashed_page, user=admin_user)

        assert "__trashed__" not in result.slug

    def test_permanent_delete_function(self, trashed_page):
        """Module function permanent_delete works."""
        page_pk = trashed_page.pk

        permanent_delete(trashed_page)

        assert not Page.objects.filter(pk=page_pk).exists()

    def test_empty_trash_function(self, trashed_page):
        """Module function empty_trash works."""
        count = empty_trash()

        assert count == 1

    def test_get_trashed_pages_function(self, trashed_page):
        """Module function get_trashed_pages works."""
        result = get_trashed_pages()

        assert trashed_page.pk in result.values_list("pk", flat=True)


class TestMultiSiteTrashRouting:
    """Regression tests for cross-site trash routing (#1356 defect 1)."""

    def test_trash_page_uses_owning_site_trash(
        self, site_with_pages, second_site, admin_user
    ):
        """S-MS-01: Trashing a page on site 2 uses site 2's trash can."""
        service = TrashService()
        article = second_site["article"]

        service.trash_page(article, user=admin_user)

        article.refresh_from_db()
        trash_parent = article.get_parent()
        assert trash_parent.specific_class == TrashCan
        # Trash can should be under site 2's root, not site 1's
        assert trash_parent.get_parent().pk == second_site["home"].pk

    def test_trash_page_does_not_cross_site_boundaries(
        self, site_with_pages, second_site, admin_user
    ):
        """S-MS-02: Pages from different sites end up in different trash cans."""
        service = TrashService()

        # Trash one page from each site
        about = site_with_pages["about"]
        article = second_site["article"]

        service.trash_page(about, user=admin_user)
        service.trash_page(article, user=admin_user)

        about.refresh_from_db()
        article.refresh_from_db()

        about_trash = about.get_parent()
        article_trash = article.get_parent()

        assert about_trash.pk != article_trash.pk

    def test_get_trash_can_resolves_from_page(self, site_with_pages, second_site):
        """S-MS-03: get_trash_can(page=...) returns the correct site's trash."""
        service = TrashService()
        article = second_site["article"]
        about = site_with_pages["about"]

        trash_for_article = service.get_trash_can(page=article)
        trash_for_about = service.get_trash_can(page=about)

        assert trash_for_article.get_parent().pk == second_site["home"].pk
        assert trash_for_about.get_parent().pk == site_with_pages["home"].pk
        assert trash_for_article.pk != trash_for_about.pk

    def test_get_trash_can_falls_back_to_default_site(self, default_site):
        """S-MS-04: get_trash_can() without page uses default site."""
        service = TrashService()
        trash = service.get_trash_can()
        assert trash.get_parent().pk == default_site.root_page.pk


class TestNestedSiteRoot:
    """Regression tests for nested site roots at depth > 2 (#1358 defect 1)."""

    def test_trash_page_uses_nested_site_trash(
        self, site_with_pages, nested_site, admin_user
    ):
        """S-NS-01: Page under a depth-3 site root uses that site's trash."""
        service = TrashService()
        landing = nested_site["landing"]

        service.trash_page(landing, user=admin_user)

        landing.refresh_from_db()
        trash_parent = landing.get_parent()
        assert trash_parent.specific_class == TrashCan
        assert trash_parent.get_parent().pk == nested_site["home"].pk

    def test_get_trash_can_resolves_nested_site(self, site_with_pages, nested_site):
        """S-NS-02: get_trash_can picks deepest matching site root."""
        service = TrashService()
        landing = nested_site["landing"]

        trash = service.get_trash_can(page=landing)
        assert trash.get_parent().pk == nested_site["home"].pk

    def test_nested_site_does_not_steal_parent_site_pages(
        self, site_with_pages, nested_site, admin_user
    ):
        """S-NS-03: Pages at depth 3 under default site (not nested) stay in default trash."""
        service = TrashService()
        about = site_with_pages["about"]

        service.trash_page(about, user=admin_user)

        about.refresh_from_db()
        trash_parent = about.get_parent()
        assert trash_parent.get_parent().pk == site_with_pages["home"].pk
