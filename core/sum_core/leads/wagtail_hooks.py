"""
Name: Leads Wagtail hooks
Path: core/sum_core/leads/wagtail_hooks.py
Purpose: Register Leads admin viewsets in Wagtail so "Leads" appears in the admin UI.
Family: Lead management, admin UX.
Dependencies: Wagtail hooks, leads admin viewsets.
"""

from django.contrib import messages
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseForbidden,
    HttpResponseNotAllowed,
    HttpResponseRedirect,
    JsonResponse,
)
from django.shortcuts import get_object_or_404
from django.templatetags.static import static
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.http import url_has_allowed_host_and_scheme
from sum_core.leads.analytics_views import lead_analytics_dashboard
from sum_core.leads.bulk_actions import UpdateStatusBulkAction
from sum_core.leads.models import Lead, LeadNote
from sum_core.leads.wagtail_admin import LeadsViewSetGroup
from wagtail import hooks


@hooks.register("register_admin_viewset")
def register_leads_viewset_group() -> LeadsViewSetGroup:
    """Register the Leads ViewSet Group with Wagtail admin."""
    return LeadsViewSetGroup()


@hooks.register("insert_global_admin_css")
def global_admin_css() -> str:
    """Load admin CSS overrides to fix sticky footer overlap on edit forms."""
    return format_html(
        '<link rel="stylesheet" href="{}">',
        static("sum_core/css/admin_overrides.css"),
    )


@hooks.register("insert_global_admin_js")
def global_admin_js() -> str:
    """Load inline status editing JS globally (it checks for elements before running)."""
    return format_html(
        '<script src="{}"></script>',
        static("sum_core/js/inline_status_edit.js"),
    )


# Register bulk action directly (not via a function)
hooks.register("register_bulk_action", UpdateStatusBulkAction)


@hooks.register("register_admin_urls")
def register_lead_note_urls():
    """Register custom URL for adding notes to leads."""
    return [
        path(
            "leads/lead/<int:pk>/add_note/",
            add_lead_note_view,
            name="lead_add_note",
        ),
        path(
            "leads/analytics/",
            lead_analytics_dashboard,
            name="lead_analytics",
        ),
    ]


def add_lead_note_view(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Handle POST request to add a note to a lead.

    Author is automatically set to the current user.
    Redirects back to the lead edit page.
    """
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    # Defense-in-depth: verify user is authenticated
    if not request.user.is_authenticated:
        return HttpResponseForbidden("Authentication required.")

    lead = get_object_or_404(Lead, pk=pk)

    # Permission check - user must have change permission
    if not request.user.has_perm("sum_core_leads.change_lead"):
        return HttpResponseForbidden("You do not have permission to add notes.")

    content = request.POST.get("content", "").strip()
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    if content:
        # Create the note with the current user as author
        note = LeadNote.objects.create(
            lead=lead,
            author=request.user,
            content=content,
        )
        if is_ajax:
            return JsonResponse(
                {
                    "success": True,
                    "note_id": note.id,
                    "message": "Note added successfully.",
                }
            )
        messages.success(request, "Note added successfully.")
    else:
        if is_ajax:
            return JsonResponse(
                {"success": False, "error": "Note content cannot be empty."}, status=400
            )
        messages.error(request, "Note content cannot be empty.")
    # Redirect back to the lead edit page (namespace is 'lead' singular, based on model name)
    # Check for next parameter or referer, with validation to prevent open redirect
    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER")
    if next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return HttpResponseRedirect(next_url)
    return HttpResponseRedirect(reverse("lead:edit", args=[pk]))
