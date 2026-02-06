"""
Name: Wagtail Trash Services
Path: core/sum_core/wagtail_trash/services.py
Purpose: Business logic for trash operations with atomic transactions.
Family: SUM Platform Core - Page Management
Dependencies: Django transactions, Wagtail Page model
"""

from __future__ import annotations

import threading
import time
from typing import TYPE_CHECKING

from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone
from wagtail.models import Page, Site

from .models import TrashCan, TrashedPageInfo

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser


class TrashError(Exception):
    """Base exception for trash operations."""

    pass


class RestoreError(TrashError):
    """Raised when a page cannot be restored."""

    pass


class TrashService:
    """
    Service class for all trash operations.

    All public methods are atomic (wrapped in database transactions).
    """

    def get_trash_can(self, page: Page | None = None) -> TrashCan:
        """
        Get or create the trash can for the site that owns the given page.

        Falls back to the default site when no page is provided.

        Args:
            page: Optional page used to determine the owning site.

        Returns:
            TrashCan instance

        Raises:
            TrashError: If no suitable site is found
        """
        site = None
        if page is not None:
            # Determine owning site by finding the site whose root_page path
            # is the longest prefix of this page's path.  This works for site
            # roots at any depth, not just depth 2.
            ancestor_ids = set(
                page.get_ancestors(inclusive=True).values_list("pk", flat=True)
            )
            if ancestor_ids:
                # Pick the site whose root is deepest among page's ancestors
                site = (
                    Site.objects.filter(root_page_id__in=ancestor_ids)
                    .order_by("-root_page__depth")
                    .first()
                )

        if site is None:
            site = Site.objects.filter(is_default_site=True).first()

        if not site:
            raise TrashError("No default site configured")
        return TrashCan.get_or_create_for_site(site)

    def is_in_trash(self, page: Page) -> bool:
        """Check if a page is currently in the trash (under TrashCan)."""
        # Check if page has trash_info (is a root trashed page)
        if hasattr(page, "trash_info") and page.trash_info is not None:
            return True

        # Check if any ancestor is a TrashCan
        for ancestor in page.get_ancestors():
            if ancestor.specific_class == TrashCan:
                return True

        return False

    def _is_protected(self, page: Page) -> bool:
        """Check if a page is protected from deletion (root pages, depth <= 2)."""
        return page.depth <= 2

    def _generate_trash_slug(self, slug: str, page_id: int) -> str:
        """Generate a unique slug for a trashed page."""
        timestamp = int(time.time() * 1000)
        return f"{slug}__trashed__{page_id}_{timestamp}"

    def _resolve_slug_conflict(self, slug: str, parent: Page) -> str:
        """
        Resolve slug conflicts when restoring.

        If the slug already exists under the parent, append -1, -2, etc.
        Uses a single query to fetch all potentially conflicting slugs.
        """
        original_slug = slug

        # Fetch all potentially conflicting slugs in a single query
        existing_slugs = set(
            parent.get_children()
            .filter(slug__startswith=original_slug)
            .values_list("slug", flat=True)
        )

        # If the original slug is unused, return it as-is
        if original_slug not in existing_slugs:
            return original_slug

        # Find the first available "<original_slug>-<n>" in memory
        # Safety limit to prevent infinite loop in pathological cases
        max_attempts = 1000
        for counter in range(1, max_attempts + 1):
            candidate = f"{original_slug}-{counter}"
            if candidate not in existing_slugs:
                return candidate

        raise TrashError(
            f"Unable to resolve slug conflict for '{original_slug}' "
            f"after {max_attempts} attempts."
        )

    @transaction.atomic
    def trash_page(
        self,
        page: Page,
        user: AbstractUser | None = None,
    ) -> TrashedPageInfo:
        """
        Move a page to trash.

        Args:
            page: The page to trash
            user: User performing the action (for audit)

        Returns:
            TrashedPageInfo with restoration metadata

        Raises:
            TrashError: If page cannot be trashed (root page, already trashed, etc.)

        Side Effects:
            - Page slug modified to avoid conflicts: "{slug}__trashed__{page_id}_{timestamp}"
            - Page moved to TrashCan in page tree
            - TrashedPageInfo record created
        """
        # Get the specific page instance
        page = page.specific

        # Validate page can be trashed
        if self._is_protected(page):
            raise TrashError(f"Cannot trash root page '{page.title}' (depth <= 2)")

        if isinstance(page, TrashCan):
            raise TrashError("Cannot trash the TrashCan itself")

        if self.is_in_trash(page):
            raise TrashError(f"Page '{page.title}' is already in trash")

        # Get trash can for the page's owning site
        trash_can = self.get_trash_can(page=page)

        # Store original metadata before moving
        original_parent = page.get_parent()
        original_slug = page.slug
        original_path = page.url_path
        descendant_count = page.get_descendants().count()

        # Modify slug to avoid conflicts (include page ID for uniqueness)
        page.slug = self._generate_trash_slug(original_slug, page.pk)
        page.save(update_fields=["slug"])

        # Move page to trash (includes descendants automatically)
        page.move(trash_can, pos="last-child")

        # Create trash info record
        trash_info = TrashedPageInfo.objects.create(
            page=page,
            original_parent=original_parent,
            trashed_by=user,
            original_path=original_path,
            original_slug=original_slug,
            descendant_count=descendant_count,
        )

        return trash_info

    @transaction.atomic
    def restore_page(
        self,
        page: Page,
        user: AbstractUser | None = None,
        *,
        target_parent: Page | None = None,
    ) -> Page:
        """
        Restore a page from trash.

        Args:
            page: The trashed page to restore
            user: User performing the action
            target_parent: Where to restore (None = original location)

        Returns:
            The restored page

        Raises:
            RestoreError: If page not in trash or cannot be restored

        Side Effects:
            - Page slug restored (with conflict resolution if needed)
            - Page moved to target parent in page tree
            - TrashedPageInfo record deleted
        """
        # Get the specific page instance
        page = page.specific

        # Validate page is in trash
        if not self.is_in_trash(page):
            raise RestoreError(f"Page '{page.title}' is not in trash")

        # Get trash info (only root trashed pages have this)
        try:
            trash_info = page.trash_info
        except TrashedPageInfo.DoesNotExist:
            # This is a descendant of a trashed page, not a root
            raise RestoreError(
                f"Page '{page.title}' is a descendant of a trashed page. "
                "Restore the parent page instead."
            )

        # Determine restore location
        if target_parent is None:
            target_parent = trash_info.get_restore_parent()
            if target_parent is None:
                raise RestoreError(
                    f"Original parent no longer exists for '{page.title}'. "
                    "Please specify a target_parent."
                )

        # Validate target parent is not in trash
        if self.is_in_trash(target_parent):
            raise RestoreError(
                f"Cannot restore to '{target_parent.title}' which is in trash"
            )

        # Resolve slug conflicts
        original_slug = trash_info.original_slug
        new_slug = self._resolve_slug_conflict(original_slug, target_parent)

        # Restore slug
        page.slug = new_slug
        page.save(update_fields=["slug"])

        # Move page back to original location
        page.move(target_parent, pos="last-child")

        # Delete trash info
        trash_info.delete()

        # Refresh from database
        page.refresh_from_db()
        return page

    @transaction.atomic
    def permanent_delete(self, page: Page) -> None:
        """
        Permanently delete a page from trash.

        Args:
            page: The trashed page to delete

        Raises:
            TrashError: If page is not in trash

        Side Effects:
            - Page and all descendants permanently deleted
            - TrashedPageInfo record cascade deleted
        """
        # Get the specific page instance
        page = page.specific

        # Validate page is in trash
        if not self.is_in_trash(page):
            raise TrashError(
                f"Page '{page.title}' is not in trash. "
                "Use this method only for trashed pages."
            )

        # Delete the page (cascades to TrashedPageInfo and descendants)
        page.delete()

    @transaction.atomic
    def empty_trash(self, older_than_days: int | None = None) -> int:
        """
        Empty the trash (permanently delete all or old items).

        Args:
            older_than_days: If set, only delete items older than this

        Returns:
            Number of root pages deleted (not counting descendants)
        """
        queryset = TrashedPageInfo.objects.all()

        if older_than_days is not None:
            cutoff = timezone.now() - timezone.timedelta(days=older_than_days)
            queryset = queryset.filter(trashed_at__lt=cutoff)

        count = 0
        for trash_info in queryset:
            try:
                page = trash_info.page
                page.delete()
                count += 1
            except Page.DoesNotExist:
                # Page already deleted, just clean up the trash_info
                trash_info.delete()
                count += 1

        return count

    def get_trashed_pages(self) -> QuerySet[Page]:
        """
        Get all top-level trashed pages (not descendants).

        Returns:
            QuerySet of specific page instances
        """
        return TrashedPageInfo.get_trashed_root_pages()


# Module-level convenience functions
_service = None
_service_lock = threading.Lock()


def _get_service() -> TrashService:
    """Get or create the singleton TrashService instance (thread-safe)."""
    global _service
    if _service is None:
        with _service_lock:
            # Double-check locking pattern
            if _service is None:
                _service = TrashService()
    return _service


def trash_page(
    page: Page, user: AbstractUser | None = None, **kwargs
) -> TrashedPageInfo:
    """Move a page to trash. See TrashService.trash_page for details."""
    return _get_service().trash_page(page, user, **kwargs)


def restore_page(page: Page, user: AbstractUser | None = None, **kwargs) -> Page:
    """Restore a page from trash. See TrashService.restore_page for details."""
    return _get_service().restore_page(page, user, **kwargs)


def permanent_delete(page: Page) -> None:
    """Permanently delete a page from trash. See TrashService.permanent_delete."""
    return _get_service().permanent_delete(page)


def empty_trash(older_than_days: int | None = None) -> int:
    """Empty the trash. See TrashService.empty_trash for details."""
    return _get_service().empty_trash(older_than_days)


def get_trashed_pages() -> QuerySet[Page]:
    """Get all trashed pages. See TrashService.get_trashed_pages for details."""
    return _get_service().get_trashed_pages()
