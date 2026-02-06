"""
Name: Wagtail Trash Package
Path: core/sum_core/wagtail_trash/__init__.py
Purpose: Soft-delete trash system for Wagtail pages with restore capabilities.
Family: SUM Platform Core - Page Management

This package provides:
- TrashCan: Hidden container page for trashed pages
- TrashedPageInfo: Metadata for page restoration
- TrashService: Business logic for trash operations
- Admin UI for managing trashed pages

Usage:
    from sum_core.wagtail_trash.services import (
        trash_page,
        restore_page,
        permanent_delete,
        empty_trash,
        get_trashed_pages,
    )

    # Trash a page
    info = trash_page(page, user=request.user)

    # Restore a page
    restored_page = restore_page(page, user=request.user)

    # Permanently delete
    permanent_delete(page)

    # Empty all trash
    count = empty_trash()
"""
