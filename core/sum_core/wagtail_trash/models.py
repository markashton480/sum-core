"""
Name: Wagtail Trash Models
Path: core/sum_core/wagtail_trash/models.py
Purpose: Data models for TrashCan container and TrashedPageInfo metadata.
Family: SUM Platform Core - Page Management
Dependencies: Wagtail Page model, Django models
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.conf import settings
from django.db import models
from django.http import Http404
from django.utils import timezone
from wagtail.models import Page, Site

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from django.http import HttpRequest


class TrashCan(Page):
    """
    A hidden page that serves as the container for trashed pages.

    One per site, created automatically on first use. Returns 404 on frontend
    access. Hidden from page explorer and page choosers.
    """

    # Wagtail configuration - restrict page creation/hierarchy
    subpage_types: list[str] = []  # No manual children (all pages can be moved here)
    parent_page_types: list[str] = []  # Can't be created manually via UI
    is_creatable = False  # Hidden from page type selection
    show_in_menus_default = False

    # Internal slug for identification
    TRASH_SLUG = "__trash__"

    class Meta:
        verbose_name = "Trash"
        verbose_name_plural = "Trash"

    def serve(self, request: HttpRequest, *args, **kwargs):
        """Return 404 for any frontend access."""
        raise Http404("Trash is not accessible")

    def get_url_parts(self, request=None):
        """Return None to prevent URL generation."""
        return None

    @classmethod
    def get_or_create_for_site(cls, site: Site) -> TrashCan:
        """
        Get or create the trash can for a given site.

        Args:
            site: The Wagtail site to get/create trash for.

        Returns:
            TrashCan instance for the site.

        Raises:
            ValueError: If site has no root page.
        """
        from django.db import IntegrityError, transaction

        root = site.root_page
        if not root:
            raise ValueError(f"Site {site} has no root page")

        # Try to find existing trash can under this specific site root
        existing = cls.objects.filter(
            slug=cls.TRASH_SLUG,
            depth=root.depth + 1,
            path__startswith=root.path,
        ).first()
        if existing:
            return existing

        # Create new trash can as child of site root
        # Use transaction to handle race condition where another process
        # creates the TrashCan between our check and create
        try:
            with transaction.atomic():
                trash = cls(
                    title="Trash",
                    slug=cls.TRASH_SLUG,
                    live=False,  # Not published
                    show_in_menus=False,
                )
                root.add_child(instance=trash)
                return trash
        except IntegrityError:
            # Another process created it concurrently, fetch and return it
            return cls.objects.get(
                slug=cls.TRASH_SLUG,
                depth=root.depth + 1,
                path__startswith=root.path,
            )

    @classmethod
    def get_default(cls) -> TrashCan | None:
        """
        Get the trash can for the default site.

        Returns:
            TrashCan instance or None if no default site.
        """
        site = Site.objects.filter(is_default_site=True).first()
        if not site:
            return None
        return cls.get_or_create_for_site(site)


class TrashedPageInfo(models.Model):
    """
    Stores metadata needed to restore a trashed page.

    Created when a page is moved to trash, deleted on restore or permanent delete.
    Only created for the root of a trashed tree (not for descendants).
    """

    # Relationships
    page = models.OneToOneField(
        Page,
        on_delete=models.CASCADE,
        related_name="trash_info",
        help_text="The page that was trashed.",
    )
    original_parent = models.ForeignKey(
        Page,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="trashed_children",
        help_text="The parent page before trashing (for restoration).",
    )
    trashed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="trashed_pages",
        help_text="User who performed the trash operation.",
    )

    # Restoration data
    original_path = models.CharField(
        max_length=255,
        help_text="URL path before trashing.",
    )
    original_slug = models.CharField(
        max_length=255,
        help_text="Slug before modification for trash.",
    )

    # Audit data
    trashed_at = models.DateTimeField(
        default=timezone.now,
        help_text="When the page was trashed.",
    )
    descendant_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of descendant pages trashed with this page.",
    )

    class Meta:
        ordering = ["-trashed_at"]
        verbose_name = "Trashed Page Info"
        verbose_name_plural = "Trashed Page Info"
        indexes = [
            models.Index(fields=["trashed_at"]),
            models.Index(fields=["original_parent"]),
        ]

    def __str__(self) -> str:
        return f"TrashInfo: {self.page.title} (trashed {self.trashed_at})"

    def can_restore(self) -> bool:
        """
        Check if the page can be restored to its original location.

        Returns:
            True if original parent exists and is not inside the trash tree.
        """
        # Use FK id to avoid query just to check existence
        if self.original_parent_id is None:
            return False

        # Check if original parent still exists
        try:
            parent = self.original_parent  # Use FK directly (may be cached)
        except Page.DoesNotExist:
            return False

        # Check parent is not anywhere inside a trash tree.
        # A parent could be a descendant of a trashed page without having its
        # own trash_info, so we must check ancestors for TrashCan.
        for ancestor in parent.get_ancestors(inclusive=True):
            if ancestor.specific_class == TrashCan:
                return False

        return True

    def get_restore_parent(self) -> Page | None:
        """
        Get the parent page for restoration.

        Returns:
            Original parent if available and not trashed, otherwise None.
        """
        if self.can_restore():
            return self.original_parent
        return None

    @classmethod
    def get_trashed_root_pages(cls) -> QuerySet[Page]:
        """
        Get all top-level trashed pages (not descendants).

        Returns:
            QuerySet of Page instances that have TrashedPageInfo.
        """
        return Page.objects.filter(trash_info__isnull=False).select_related(
            "trash_info", "trash_info__trashed_by", "trash_info__original_parent"
        )
