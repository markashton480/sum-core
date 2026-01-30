"""
Name: Leads admin (Wagtail)
Path: core/sum_core/leads/wagtail_admin.py
Purpose: Provide Wagtail admin UI for Lead list/detail, status updates, and CSV export.
Family: Lead management, operations workflows.
Dependencies: Wagtail admin APIs, Lead model, attribution fields.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from typing import Any

import django_filters
from django import forms
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q, QuerySet
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import path
from django.utils import timezone
from django.utils.html import format_html, mark_safe
from django.utils.translation import gettext_lazy as _
from sum_core.leads.constants import SCORE_HIGH_THRESHOLD, SCORE_MEDIUM_THRESHOLD
from sum_core.leads.models import Lead, LeadSource, LeadSourceRule
from sum_core.leads.panels import LeadActivityTimelinePanel, LeadNotesPanel
from wagtail.admin.filters import WagtailFilterSet
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.admin.ui.tables import Column, DateColumn, TitleColumn
from wagtail.admin.views import generic
from wagtail.admin.views.generic.models import InspectView
from wagtail.admin.viewsets.base import ViewSet, ViewSetGroup
from wagtail.admin.viewsets.model import ModelViewSet
from wagtail.permissions import ModelPermissionPolicy
from wagtail.snippets.views.snippets import SnippetViewSet


class AssignedToFilter(django_filters.ChoiceFilter):
    """
    Custom filter for assigned_to that includes an "Unassigned" option.

    Allows filtering by specific users or showing only unassigned leads.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("empty_label", _("All"))
        kwargs.setdefault("label", _("Assigned To"))
        super().__init__(*args, **kwargs)

    @property
    def field(self) -> Any:
        """Lazy evaluation of choices to avoid database queries at import time."""
        if not hasattr(self, "_field"):
            # Get all users who have been assigned to leads
            user_ids = Lead.objects.exclude(assigned_to__isnull=True).values_list(
                "assigned_to", flat=True
            )
            users = get_user_model().objects.filter(id__in=user_ids)

            # Build choices: [("unassigned", "Unassigned"), (user_id, "User Name"), ...]
            choices = [("unassigned", _("Unassigned"))]
            choices.extend(
                [
                    (str(user.id), user.get_full_name() or user.username)
                    for user in users
                ]
            )

            self.extra["choices"] = choices
            self._field = super().field
        return self._field

    def filter(self, qs: Any, value: str | None) -> Any:
        """Apply the filter based on selected value."""
        if value == "unassigned":
            return qs.filter(assigned_to__isnull=True)
        if value:
            return qs.filter(assigned_to_id=value)
        return qs


class DateRangeFilter(django_filters.ChoiceFilter):
    """
    Custom filter for date ranges with predefined options.

    Provides Today, This Week, This Month, and Custom Range options.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        choices = [
            ("today", _("Today")),
            ("this_week", _("This Week")),
            ("this_month", _("This Month")),
        ]
        kwargs.setdefault("choices", choices)
        kwargs.setdefault("empty_label", _("All Time"))
        kwargs.setdefault("label", _("Date Range"))
        super().__init__(*args, **kwargs)

    def filter(self, qs: Any, value: str | None) -> Any:
        """Apply the filter based on selected date range."""
        if not value:
            return qs

        today_start = timezone.make_aware(
            datetime.combine(date.today(), datetime.min.time())
        )

        if value == "today":
            return qs.filter(submitted_at__gte=today_start)
        elif value == "this_week":
            week_start = today_start - timedelta(days=today_start.weekday())
            return qs.filter(submitted_at__gte=week_start)
        elif value == "this_month":
            month_start = today_start.replace(day=1)
            return qs.filter(submitted_at__gte=month_start)

        return qs


class QuickFilters(django_filters.ChoiceFilter):
    """
    Quick filter shortcuts for common lead views.

    Provides "New this week", "My leads", and "Unassigned" shortcuts.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        choices = [
            ("new_this_week", _("New this week")),
            ("my_leads", _("My leads")),
            ("unassigned", _("Unassigned")),
        ]
        kwargs.setdefault("choices", choices)
        kwargs.setdefault("empty_label", _("All Leads"))
        kwargs.setdefault("label", _("Quick Filters"))
        super().__init__(*args, **kwargs)

    def filter(self, qs: Any, value: str | None) -> Any:
        """Apply the quick filter based on selected value."""
        if not value:
            return qs

        today_start = timezone.make_aware(
            datetime.combine(date.today(), datetime.min.time())
        )
        week_start = today_start - timedelta(days=today_start.weekday())

        if value == "new_this_week":
            return qs.filter(status=Lead.Status.NEW, submitted_at__gte=week_start)
        elif value == "my_leads":
            # Filter by current user if request is available
            request = getattr(self.parent, "request", None)
            if request and request.user.is_authenticated:
                return qs.filter(assigned_to=request.user)
            return qs
        elif value == "unassigned":
            return qs.filter(assigned_to__isnull=True)

        return qs


class ScoreRangeFilter(django_filters.ChoiceFilter):
    """
    Custom filter for lead score ranges.

    Provides three-tier filtering:
    - High: 70+
    - Medium: 30-69
    - Low: 0-29
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        choices = [
            ("high", _("High (70+)")),
            ("medium", _("Medium (30-69)")),
            ("low", _("Low (0-29)")),
        ]
        kwargs.setdefault("choices", choices)
        kwargs.setdefault("empty_label", _("All Scores"))
        kwargs.setdefault("label", _("Score Range"))
        super().__init__(*args, **kwargs)

    def filter(self, qs: Any, value: str | None) -> Any:
        """Apply the score range filter based on selected value."""
        if value == "high":
            return qs.filter(score__gte=SCORE_HIGH_THRESHOLD)
        elif value == "medium":
            return qs.filter(
                score__gte=SCORE_MEDIUM_THRESHOLD, score__lt=SCORE_HIGH_THRESHOLD
            )
        elif value == "low":
            return qs.filter(score__lt=SCORE_MEDIUM_THRESHOLD)
        return qs


class LeadFilterSet(WagtailFilterSet):
    """
    Custom filterset for Lead model with enhanced filtering capabilities.

    Provides:
    - Multi-select status filter
    - Multi-select lead source filter
    - Assigned to filter with "Unassigned" option
    - Date range filters (Today, This Week, This Month)
    - Quick filter shortcuts
    - Score range filter (High/Medium/Low)
    """

    status = django_filters.MultipleChoiceFilter(
        choices=Lead.Status.choices,
        widget=forms.CheckboxSelectMultiple,
        label=_("Status"),
    )
    lead_source = django_filters.MultipleChoiceFilter(
        choices=LeadSource.choices,
        widget=forms.CheckboxSelectMultiple,
        label=_("Source"),
    )
    assigned_to = AssignedToFilter(field_name="assigned_to")
    date_range = DateRangeFilter(field_name="submitted_at")
    quick_filter = QuickFilters(method="filter_quick")
    score_range = ScoreRangeFilter(field_name="score")

    class Meta:
        model = Lead
        fields = [
            "status",
            "lead_source",
            "assigned_to",
            "date_range",
            "quick_filter",
            "score_range",
        ]

    def filter_quick(self, queryset: Any, name: str, value: str) -> Any:
        """Custom filter method for quick filters."""
        # The QuickFilters class handles the actual filtering
        return queryset


class LeadIndexView(generic.IndexView):
    """
    Custom IndexView for Lead with enhanced search including JSON field content.

    Extends Wagtail's IndexView to add search capability for form_data JSON field.
    """

    @property
    def media(self) -> forms.Media:
        return forms.Media(js=["sum_core/js/inline_status_edit.js"])

    def filter_queryset(self, queryset: QuerySet) -> QuerySet:
        """Apply search filtering including form_data JSON field."""
        queryset = super().filter_queryset(queryset)
        search_query = self.request.GET.get("q", "").strip()
        if search_query:
            q_objects = Q()
            if hasattr(self, "search_fields") and self.search_fields:
                for field in self.search_fields:
                    q_objects |= Q(**{f"{field}__icontains": search_query})
            q_objects |= Q(form_data__icontains=search_query)
            queryset = queryset.filter(q_objects).distinct()
        return queryset


class ScoreColumn(Column):
    """Custom column for displaying lead score with color coding."""

    def get_cell_context_data(
        self, instance: Lead, parent_context: dict[str, Any]
    ) -> dict[str, Any]:
        """Add score badge HTML to cell context."""
        context = super().get_cell_context_data(instance, parent_context)
        score = instance.score
        if score >= SCORE_HIGH_THRESHOLD:
            badge_class, label = "w-status w-status--primary", "High"
        elif score >= SCORE_MEDIUM_THRESHOLD:
            badge_class, label = "w-status", "Medium"
        else:
            badge_class, label = "w-status w-status--secondary", "Low"

        context["value"] = format_html(
            '<span class="{}">{}</span>',
            badge_class,
            label,
        )
        return context


class InlineStatusColumn(Column):
    """Custom column for inline status editing with dropdown."""

    def get_cell_context_data(
        self, instance: Lead, parent_context: dict[str, Any]
    ) -> dict[str, Any]:
        """Add inline status dropdown to cell context."""
        context = super().get_cell_context_data(instance, parent_context)

        options = []
        for status_value, status_label in Lead.Status.choices:
            selected = "selected" if status_value == instance.status else ""
            options.append(
                f'<option value="{status_value}" {selected}>{status_label}</option>'
            )

        context["value"] = format_html(
            '<select class="inline-status-select" data-lead-id="{}" data-original-value="{}">{}</select>',
            instance.pk,
            instance.status,
            mark_safe("".join(options)),
        )
        return context


class LeadInspectView(InspectView):
    """
    Customized InspectView for Lead detail redesign.
    Two-column layout, action buttons, and activity timeline.
    """

    template_name = "sum_core/admin/lead_inspect.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        lead = self.object

        # Parse form data JSON safely
        form_data_items = []
        if isinstance(lead.form_data, dict):
            form_data_items = [
                {"label": k.replace("_", " ").title(), "value": v}
                for k, v in lead.form_data.items()
                if v is not None and k not in ["g-recaptcha-response"]
            ]
        context["form_data_items"] = form_data_items

        # Previous enquiries (same email, excluding current, most recent first)
        previous_enquiries = (
            Lead.objects.filter(email=lead.email)
            .exclude(id=lead.id)
            .order_by("-submitted_at")
            .only("id", "submitted_at")[:5]
        )
        context["previous_enquiries"] = previous_enquiries

        # Activities for timeline
        context["activities"] = lead.activities.select_related("actor").all()

        # Notes for dedicated list
        context["notes"] = (
            lead.notes.select_related("author").all().order_by("-created_at")
        )

        # Add assignable users for the inline dropdown
        user_model = get_user_model()
        context["assignable_users"] = user_model.objects.filter(
            is_active=True, is_staff=True
        ).order_by("first_name", "username")

        # Pass status choices for the inline dropdown
        context["status_choices"] = Lead.Status.choices

        return context


class LeadViewSet(ModelViewSet):
    """
    Wagtail admin ViewSet for Lead management.

    Provides:
    - List view with search, filters, and columns
    - Detail view with grouped sections
    - Status update capability (permission-gated)
    - CSV export (permission-gated)
    """

    model = Lead
    icon = "mail"
    menu_label = "All Leads"
    menu_order = 200
    add_to_admin_menu = False
    add_to_settings_menu = False
    exclude_from_explorer = False
    copy_view_enabled = False
    inspect_view_enabled = True
    inspect_view_class = LeadInspectView
    inspect_template_name = "sum_core/admin/lead_inspect.html"
    edit_template_name = "sum_core/admin/lead_edit.html"
    create_template_name = "sum_core/admin/lead_edit.html"
    index_view_class = LeadIndexView
    filterset_class = LeadFilterSet

    class Media:
        css = {
            "all": [
                # Fix for save button overlap in Edit view
                "sum_core/css/admin_overrides.css",
                "sum_core/css/admin_leads.css",
            ]
        }
        js = [
            "sum_core/js/lead_inspect.js",
            "sum_core/js/inline_status_edit.js",
        ]

    list_display = [
        TitleColumn(
            "name",
            label="Name",
            url_name="lead:inspect",
        ),
        DateColumn("submitted_at", label="Submitted", width="12%"),
        Column("email", label="Email", width="20%"),
        Column("form_type", label="Form", width="10%"),
        ScoreColumn("score", label="Score", width="10%"),
        InlineStatusColumn("status", label="Status", width="12%"),
    ]

    search_fields = ["name", "email", "phone", "message"]

    ordering = ["-submitted_at"]

    # Detail view panels - organized for usability:
    # 1. Actionable fields first (status, assignment)
    # 2. Contact info (read-only but important)
    # 3. Notes (interactive)
    # 4. Activity timeline
    # 5. Technical/debug info (collapsed)
    panels = [
        # Workflow - what sales reps change often
        MultiFieldPanel(
            [
                FieldPanel("status"),
                FieldPanel("assigned_to"),
            ],
            heading="Workflow",
        ),
        # Contact Details - read-only reference
        MultiFieldPanel(
            [
                FieldPanel("name"),
                FieldPanel("email"),
                FieldPanel("phone"),
                FieldPanel("message", read_only=True),
            ],
            heading="Contact Details",
        ),
        # Notes panel (keep existing)
        LeadNotesPanel(),
        # Activity timeline (keep existing)
        LeadActivityTimelinePanel(),
        # Lead Information - context, collapsed
        MultiFieldPanel(
            [
                FieldPanel("lead_source", read_only=True),
                FieldPanel("form_type", read_only=True),
                FieldPanel("source_page", read_only=True),
                FieldPanel("submitted_at", read_only=True),
                FieldPanel("score", read_only=True),
                FieldPanel("is_archived"),  # Keep but in collapsed section
            ],
            heading="Lead Information",
            classname="collapsible collapsed",
        ),
    ]

    def get_base_queryset(self) -> Any:
        """Base queryset for list/export operations."""
        return self.model.objects.all().select_related("source_page", "assigned_to")

    @property
    def permission_policy(self) -> ModelPermissionPolicy:
        """Custom permission policy for edit/export controls."""
        return LeadPermissionPolicy(self.model)

    def get_urlpatterns(self) -> list:
        """Add CSV export and status update URL patterns."""
        urlpatterns = super().get_urlpatterns()
        return list(urlpatterns) + [
            path("export/", self.export_csv_view, name="export"),
            path(
                "<int:pk>/update-status/", self.update_status_view, name="update_status"
            ),
            path(
                "<int:pk>/update-assignment/",
                self.update_assignment_view,
                name="update_assignment",
            ),
        ]

    def export_csv_view(self, request: HttpRequest) -> HttpResponse:
        """
        Export filtered leads to CSV.

        Only accessible to users with 'export_lead' permission.
        """
        from sum_core.leads.services import build_lead_csv, can_user_export_leads

        # Permission check
        if not can_user_export_leads(request.user):
            return HttpResponseForbidden("You do not have permission to export leads.")

        queryset = self._get_export_queryset(request)

        # Generate CSV
        csv_content = build_lead_csv(queryset)

        # Return as downloadable file
        response = HttpResponse(csv_content, content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="leads_export.csv"'
        return response

    def _get_export_queryset(self, request: HttpRequest) -> Any:
        """
        Build the queryset for CSV export, matching the admin list's filtering/search.

        This uses Wagtail's IndexView queryset pipeline (ordering → filters → search)
        so that exported CSV matches the currently applied list view state.
        """
        index_view = self.index_view_class()
        index_view.request = request
        index_view.model = self.model
        index_view.queryset = self.get_base_queryset()
        index_view.list_display = self.list_display
        index_view.filterset_class = self.filterset_class
        index_view.search_fields = self.search_fields
        index_view.search_backend_name = self.search_backend_name
        index_view.index_url_name = self.get_url_name("index")
        index_view.index_results_url_name = self.get_url_name("index_results")
        if self.ordering:
            index_view.default_ordering = self.ordering

        return index_view.get_queryset()

    def update_status_view(self, request: HttpRequest, pk: int) -> JsonResponse:
        """
        Update lead status via AJAX.

        Accepts JSON: {"status": "<status_value>"}
        Returns JSON: {"success": true, "status": "<new_status>"}
        Creates activity record on successful change.
        """
        if request.method != "POST":
            return JsonResponse({"error": "Method not allowed"}, status=405)

        # Defense-in-depth: verify user is authenticated
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Authentication required"}, status=401)

        # Permission check
        if not request.user.has_perm("sum_core_leads.change_lead"):
            return JsonResponse({"error": "Permission denied"}, status=403)

        # Get lead
        lead = get_object_or_404(Lead, pk=pk)

        # Parse request
        try:
            data = json.loads(request.body)
            new_status = data.get("status")
        except (json.JSONDecodeError, AttributeError):
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        # Validate status
        valid_statuses = [choice[0] for choice in Lead.Status.choices]
        if new_status not in valid_statuses:
            return JsonResponse({"error": "Invalid status value"}, status=400)

        # Check if status actually changed
        old_status = lead.status
        if old_status == new_status:
            # No change - return success without creating activity
            return JsonResponse(
                {"success": True, "status": new_status, "no_change": True}
            )

        # Update status
        with transaction.atomic():
            lead.status = new_status
            lead._change_actor = request.user  # Used by post_save signal
            lead.save(update_fields=["status"])
            # Activity is logged by the post_save signal

        return JsonResponse(
            {
                "success": True,
                "status": new_status,
                "status_display": lead.get_status_display(),
            }
        )

    def update_assignment_view(self, request: HttpRequest, pk: int) -> JsonResponse:
        """
        Update lead assignment via AJAX.

        Accepts JSON: {"assigned_to": "<user_id>"}
        Returns JSON: {"success": true, "assigned_to": "<user_name>"}
        """
        if request.method != "POST":
            return JsonResponse({"error": "Method not allowed"}, status=405)

        if not request.user.is_authenticated:
            return JsonResponse({"error": "Authentication required"}, status=401)

        if not request.user.has_perm("sum_core_leads.change_lead"):
            return JsonResponse({"error": "Permission denied"}, status=403)

        lead = get_object_or_404(Lead, pk=pk)

        try:
            data = json.loads(request.body)
            user_id = data.get("assigned_to")
        except (json.JSONDecodeError, AttributeError):
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        assigned_user = None
        if user_id and user_id != "unassigned":
            user_model = get_user_model()
            assigned_user = get_object_or_404(user_model, pk=user_id)

        if lead.assigned_to == assigned_user:
            return JsonResponse(
                {
                    "success": True,
                    "assigned_to": (
                        assigned_user.get_full_name() or assigned_user.username
                        if assigned_user
                        else "Unassigned"
                    ),
                    "no_change": True,
                }
            )

        with transaction.atomic():
            lead.assigned_to = assigned_user
            lead._change_actor = request.user
            lead.save(update_fields=["assigned_to"])

        return JsonResponse(
            {
                "success": True,
                "assigned_to": (
                    assigned_user.get_full_name() or assigned_user.username
                    if assigned_user
                    else "Unassigned"
                ),
            }
        )


class LeadPermissionPolicy(ModelPermissionPolicy):
    """
    Custom permission policy for Lead model.

    - Editors (change_lead): can view list and detail
    - Admins (change_lead + export_lead): can also update status and export CSV
    """

    def user_has_permission(self, user: Any, action: str) -> bool:
        """Check if user has permission for the given action."""
        if action == "add":
            # No one can add leads through Wagtail admin (they come from forms)
            return False

        if action == "change":
            # Users with change permission can edit status/archive.
            return bool(
                user.has_perm(
                    f"{self.model._meta.app_label}.change_{self.model._meta.model_name}"
                )
            )

        if action == "delete":
            # Leads should not be deleted via the admin.
            return False

        if action == "export":
            # Only users with export_lead can export
            return bool(
                user.has_perm(
                    f"{self.model._meta.app_label}.export_{self.model._meta.model_name}"
                )
            )

        # For index/inspect, allow if user has view or change permission
        return bool(super().user_has_permission(user, action))


# Register the viewset


# Also register LeadSourceRule as a snippet for configuration


class LeadSourceRuleViewSet(SnippetViewSet):
    """ViewSet for LeadSourceRule configuration."""

    model = LeadSourceRule
    icon = "cog"
    menu_label = "Source Rules"
    menu_order = 201
    add_to_admin_menu = False

    list_display = [
        "priority",
        "name",
        "utm_source",
        "utm_medium",
        "referrer_contains",
        "derived_source",
        "is_active",
    ]
    list_filter = ["is_active", "derived_source"]
    search_fields = ["name", "utm_source", "utm_medium", "referrer_contains"]

    panels = [
        MultiFieldPanel(
            [
                FieldPanel("name"),
                FieldPanel("priority"),
                FieldPanel("is_active"),
            ],
            heading="Rule Identity",
        ),
        MultiFieldPanel(
            [
                FieldPanel("utm_source"),
                FieldPanel("utm_medium"),
                FieldPanel("referrer_contains"),
            ],
            heading="Matching Conditions",
        ),
        MultiFieldPanel(
            [
                FieldPanel("derived_source"),
                FieldPanel("derived_source_detail"),
            ],
            heading="Derived Values",
        ),
    ]


class LeadAnalyticsViewSet(ViewSet):
    """ViewSet for Lead Analytics dashboard."""

    name = "lead_analytics"
    icon = "group"
    menu_label = "Analytics"
    menu_order = 300
    add_to_admin_menu = False

    @property
    def menu_url(self) -> str:
        return "/admin/leads/analytics/"


class LeadsViewSetGroup(ViewSetGroup):
    """Group Leads and Lead Source Rules under a single menu."""

    menu_label = "Leads"
    menu_name = "leads"
    menu_icon = "mail"
    menu_order = 200
    items = (
        LeadViewSet,
        LeadSourceRuleViewSet,
        LeadAnalyticsViewSet,
    )
