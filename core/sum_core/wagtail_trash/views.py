"""
Name: Wagtail Trash Admin Views
Path: core/sum_core/wagtail_trash/views.py
Purpose: Admin views for trash management (listing, restore, delete, empty).
Family: SUM Platform Core - Page Management
Dependencies: Django views, Wagtail admin
"""

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.db.models import Prefetch, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from wagtail.models import Page

from .models import TrashedPageInfo
from .services import RestoreError, TrashError, TrashService


@staff_member_required
def trash_index(request):
    """
    Display list of trashed pages with actions.

    GET /admin/trash/

    Template Context:
        pages: List of dicts with page, trash_info, can_restore, descendant_count
        total_count: Number of root trashed items
        total_with_descendants: Including all children
        old_items_count: Items > 30 days old
    """
    thirty_days_ago = timezone.now() - timezone.timedelta(days=30)

    # Get trash info records with prefetched related data
    # Use stored descendant_count instead of querying per page
    trash_infos = (
        TrashedPageInfo.objects.select_related("page", "original_parent", "trashed_by")
        .prefetch_related(
            Prefetch(
                "page__content_type",
            )
        )
        .order_by("-trashed_at")
    )

    # Calculate totals from full queryset (efficient aggregate queries)
    total_count = trash_infos.count()
    old_items_count = trash_infos.filter(trashed_at__lt=thirty_days_ago).count()
    # Sum all descendant counts from the entire queryset, not just current page
    total_descendants = (
        trash_infos.aggregate(total=Sum("descendant_count"))["total"] or 0
    )

    # Paginate the queryset BEFORE processing
    paginator = Paginator(trash_infos, 50)
    page_number = request.GET.get("p", 1)
    page_obj = paginator.get_page(page_number)

    # Build page data only for current page
    pages_data = []

    for trash_info in page_obj.object_list:
        # Use base page, not .specific (avoids N+1 query for specific page types)
        # Template uses page.specific_class.get_verbose_name which works on base Page
        page = trash_info.page
        descendant_count = trash_info.descendant_count

        # Use the model's can_restore which checks the full trash tree ancestry
        can_restore = trash_info.can_restore()

        pages_data.append(
            {
                "page": page,
                "trash_info": trash_info,
                "can_restore": can_restore,
                "descendant_count": descendant_count,
            }
        )

    context = {
        "page_obj": page_obj,
        "pages": pages_data,
        "total_count": total_count,
        "total_with_descendants": total_count + total_descendants,
        "old_items_count": old_items_count,
    }

    return render(request, "wagtail_trash/index.html", context)


@staff_member_required
def restore_page_view(request, page_id):
    """
    Restore a page from trash.

    GET: Show confirmation with page details
    POST: Perform restore and redirect

    GET /admin/trash/restore/<page_id>/
    POST /admin/trash/restore/<page_id>/
    """
    page = get_object_or_404(Page, pk=page_id)
    page = page.specific

    # Check if page is in trash
    try:
        trash_info = page.trash_info
    except TrashedPageInfo.DoesNotExist:
        messages.error(request, f"'{page.title}' is not in trash.")
        return redirect("wagtail_trash_index")

    if request.method == "POST":
        service = TrashService()

        # Check for alternate parent from form
        target_parent_id = request.POST.get("target_parent")
        target_parent = None
        if target_parent_id:
            try:
                target_parent = Page.objects.get(pk=target_parent_id)
            except Page.DoesNotExist:
                messages.error(request, "Selected parent page does not exist.")
                return redirect("wagtail_trash_restore", page_id=page_id)

            # Permission check: ensure user can add children to target parent
            user_perms = target_parent.permissions_for_user(request.user)
            if not user_perms.can_add_subpage():
                messages.error(
                    request,
                    "You do not have permission to restore pages to that location.",
                )
                return redirect("wagtail_trash_restore", page_id=page_id)
        else:
            # Restoring to original parent - check permissions there too
            original_parent = trash_info.original_parent
            if original_parent:
                user_perms = original_parent.permissions_for_user(request.user)
                if not user_perms.can_add_subpage():
                    messages.error(
                        request,
                        "You do not have permission to restore pages to the original location.",
                    )
                    return redirect("wagtail_trash_restore", page_id=page_id)

        try:
            restored_page = service.restore_page(
                page, user=request.user, target_parent=target_parent
            )
            messages.success(
                request, f"'{restored_page.title}' has been restored successfully."
            )
            # Redirect to the restored page's parent explorer
            parent = restored_page.get_parent()
            if parent:
                return redirect("wagtailadmin_explore", parent.pk)
            return redirect("wagtailadmin_explore_root")
        except RestoreError as e:
            messages.error(request, str(e))
            return redirect("wagtail_trash_restore", page_id=page_id)

    # GET: Show confirmation page
    # Use stored descendant_count for efficiency
    descendant_count = trash_info.descendant_count

    context = {
        "page": page,
        "trash_info": trash_info,
        "descendant_count": descendant_count,
        "can_restore": trash_info.can_restore(),
        "original_parent": trash_info.original_parent,
        "page_title": f"Restore '{page.title}'",
    }

    return render(request, "wagtail_trash/restore_confirm.html", context)


@staff_member_required
def permanent_delete_view(request, page_id):
    """
    Permanently delete a page from trash.

    GET: Show confirmation with clear warning
    POST: Perform permanent delete

    GET /admin/trash/delete/<page_id>/
    POST /admin/trash/delete/<page_id>/
    """
    page = get_object_or_404(Page, pk=page_id)
    page = page.specific

    # Verify page is in trash
    service = TrashService()
    is_in_trash = service.is_in_trash(page)

    if not is_in_trash:
        messages.error(
            request,
            f"'{page.title}' is not in trash. Use the standard delete function.",
        )
        return redirect("wagtail_trash_index")

    if request.method == "POST":
        page_title = page.title
        try:
            service.permanent_delete(page)
            messages.success(request, f"'{page_title}' has been permanently deleted.")
        except TrashError as e:
            messages.error(request, str(e))
        return redirect("wagtail_trash_index")

    # GET: Show confirmation page
    # Get descendant count from trash_info if available, else query
    try:
        descendant_count = page.trash_info.descendant_count
    except TrashedPageInfo.DoesNotExist:
        descendant_count = page.get_descendants().count()

    context = {
        "page": page,
        "descendant_count": descendant_count,
        "page_title": f"Permanently delete '{page.title}'",
    }

    return render(request, "wagtail_trash/delete_confirm.html", context)


@staff_member_required
def empty_trash_view(request):
    """
    Empty the entire trash or items older than specified days.

    GET: Show confirmation with counts
    POST: Perform empty and redirect

    GET /admin/trash/empty/
    POST /admin/trash/empty/
    """
    service = TrashService()

    if request.method == "POST":
        empty_option = request.POST.get("empty_option", "all")
        older_than_days = None

        if empty_option not in ("all", "old"):
            messages.error(request, "Invalid empty option selected.")
            return redirect("wagtail_trash_empty")

        if empty_option == "old":
            # When age-filtered deletion is requested, require a valid positive int
            raw_days = request.POST.get("older_than_days", "")
            try:
                parsed_days = int(raw_days)
                if parsed_days <= 0:
                    raise ValueError("days must be positive")
                older_than_days = parsed_days
            except (ValueError, TypeError):
                messages.error(
                    request,
                    "Invalid number of days. Please enter a positive whole number.",
                )
                return redirect("wagtail_trash_empty")

        count = service.empty_trash(older_than_days=older_than_days)

        if older_than_days:
            messages.success(
                request,
                f"Permanently deleted {count} items older than {older_than_days} days.",
            )
        else:
            messages.success(
                request, f"Trash emptied. Permanently deleted {count} items."
            )
        return redirect("wagtail_trash_index")

    # GET: Show confirmation page
    trashed_pages = service.get_trashed_pages()
    total_count = trashed_pages.count()

    # Count old items
    thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
    old_items_count = TrashedPageInfo.objects.filter(
        trashed_at__lt=thirty_days_ago
    ).count()

    context = {
        "total_count": total_count,
        "old_items_count": old_items_count,
        "page_title": "Empty Trash",
    }

    return render(request, "wagtail_trash/empty_confirm.html", context)
