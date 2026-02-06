"""
Name: Wagtail Trash Hooks
Path: core/sum_core/wagtail_trash/wagtail_hooks.py
Purpose: Wagtail admin integration hooks for the trash system.
Family: SUM Platform Core - Page Management
Dependencies: wagtail.hooks

Hooks implemented:
- before_delete_page: Intercept deletion, move to trash instead
- before_delete_page: Block deletion of root pages (depth <= 2)
- before_delete_page: Warn when deleting pages with many children
- register_admin_urls: Register trash management URLs
- register_admin_menu_item: Add "Trash" to sidebar
- construct_explorer_page_queryset: Exclude TrashCan from explorer
"""

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import path, reverse
from wagtail import hooks
from wagtail.admin.menu import MenuItem

from .models import TrashCan
from .services import TrashError, TrashService

# Constants
LARGE_TREE_WARNING_THRESHOLD = 5


@hooks.register("before_delete_page")
def protect_critical_pages(request, page):
    """
    Block deletion of root pages entirely.

    Condition: page.depth <= 2

    Action:
    1. Add error message explaining why
    2. Return redirect to parent explorer
    """
    if page.depth <= 2:
        messages.error(
            request,
            f"Cannot delete '{page.title}': Root pages (depth {page.depth}) are protected.",
        )
        # Redirect to page explorer for the page's parent or root
        parent = page.get_parent()
        if parent:
            return redirect("wagtailadmin_explore", parent.pk)
        return redirect("wagtailadmin_explore_root")


@hooks.register("before_delete_page")
def warn_on_large_tree(request, page):
    """
    Show warning on GET (confirmation page) when deleting large trees.

    Condition: request.method == 'GET' and descendant_count >= 5

    Action: Add warning message (does not block)
    """
    if request.method == "GET":
        descendant_count = page.get_descendants().count()
        if descendant_count >= LARGE_TREE_WARNING_THRESHOLD:
            messages.warning(
                request,
                f"Warning: '{page.title}' has {descendant_count} child pages "
                "that will also be moved to trash.",
            )


@hooks.register("before_delete_page")
def move_to_trash_instead_of_delete(request, page):
    """
    Intercept POST requests to delete and redirect to trash.

    Conditions to intercept:
    - request.method == 'POST'
    - page is not TrashCan
    - page is not already in trash (no trash_info and not under TrashCan)

    On intercept:
    1. Call TrashService.trash_page(page, request.user)
    2. Add success message
    3. Return redirect to parent page explorer

    On error:
    4. Add error message
    5. Return redirect to parent page explorer

    NOTE: Pages already in trash are handled by our custom delete confirmation
    view, not Wagtail's built-in delete. The page listing buttons direct to
    wagtail_trash_delete instead of wagtailadmin_pages:delete.
    """
    # Only intercept POST (actual deletion)
    if request.method != "POST":
        return None

    # Don't intercept if page is TrashCan (use specific_class to avoid DB query)
    if page.specific_class == TrashCan:
        messages.error(request, "The Trash container cannot be deleted.")
        parent = page.get_parent()
        if parent:
            return redirect("wagtailadmin_explore", parent.pk)
        return redirect("wagtailadmin_explore_root")

    # Don't intercept if page is already in trash
    if hasattr(page, "trash_info"):
        # This is a root trashed page - let our custom view handle it
        return None

    # Check if page is under TrashCan (descendant of trashed page)
    # Use specific_class to avoid DB query per ancestor
    for ancestor in page.get_ancestors():
        if ancestor.specific_class == TrashCan:
            # Already in trash, let standard deletion proceed
            return None

    # Move page to trash
    service = TrashService()
    try:
        service.trash_page(page, user=request.user)
        messages.success(
            request,
            f"'{page.title}' has been moved to trash. "
            "You can restore it from the Trash menu.",
        )
    except TrashError as e:
        messages.error(request, str(e))

    # Redirect to parent page explorer
    parent = page.get_parent()
    if parent:
        return redirect("wagtailadmin_explore", parent.pk)
    return redirect("wagtailadmin_explore_root")


@hooks.register("construct_explorer_page_queryset")
def exclude_trash_from_explorer(parent_page, pages, request):
    """
    Exclude TrashCan pages from the page explorer.

    The TrashCan should not appear in the normal page tree navigation.
    Users access it via the dedicated Trash menu instead.
    """
    # Get the TrashCan page type's content type
    from django.contrib.contenttypes.models import ContentType

    trash_ct = ContentType.objects.get_for_model(TrashCan)
    return pages.exclude(content_type=trash_ct)


@hooks.register("register_admin_urls")
def register_trash_admin_urls():
    """Register admin URLs for trash management."""
    from . import views

    return [
        path("trash/", views.trash_index, name="wagtail_trash_index"),
        path(
            "trash/restore/<int:page_id>/",
            views.restore_page_view,
            name="wagtail_trash_restore",
        ),
        path(
            "trash/delete/<int:page_id>/",
            views.permanent_delete_view,
            name="wagtail_trash_delete",
        ),
        path("trash/empty/", views.empty_trash_view, name="wagtail_trash_empty"),
    ]


@hooks.register("register_admin_menu_item")
def register_trash_menu_item():
    """Add Trash menu item to the Wagtail admin sidebar."""
    return MenuItem(
        "Trash",
        reverse("wagtail_trash_index"),
        icon_name="bin",
        order=9000,  # Near the bottom
    )


@hooks.register("construct_page_listing_buttons")
def modify_page_listing_buttons(buttons, page, user, context=None):
    """
    Modify page listing buttons for pages in the trash.

    - For pages in trash: Remove edit/add buttons, keep delete (which goes to our view)
    - The buttons collection is modified in-place
    """
    # Check if page is in trash
    is_in_trash = False
    if hasattr(page, "trash_info"):
        is_in_trash = True
    else:
        # Use specific_class to avoid DB query per ancestor
        for ancestor in page.get_ancestors():
            if ancestor.specific_class == TrashCan:
                is_in_trash = True
                break

    if not is_in_trash:
        return

    # For trashed pages, filter out most buttons except those we want to keep
    buttons_to_remove = []
    for button in buttons:
        # Keep only the 'more' dropdown if present
        if hasattr(button, "dropdown_buttons"):
            # Filter dropdown items
            button.dropdown_buttons = [
                b
                for b in button.dropdown_buttons
                if b.label in ("Delete", "View live", "View draft")
            ]
        elif button.label not in ("Delete", "More"):
            buttons_to_remove.append(button)

    for button in buttons_to_remove:
        buttons.remove(button)
