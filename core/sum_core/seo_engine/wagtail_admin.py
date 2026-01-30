"""
Name: SEO Engine Wagtail Admin
Path: core/sum_core/seo_engine/wagtail_admin.py
Purpose: Wagtail admin integration for SEO analysis and link suggestions.
Family: SEO Engine
Dependencies: Wagtail admin, SEO models.
"""

from __future__ import annotations

from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import path, reverse
from django.utils.functional import cached_property
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST
from wagtail import hooks
from wagtail.admin.panels import FieldPanel
from wagtail.admin.ui.tables import Column, DateColumn
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import IndexView as SnippetIndexView
from wagtail.snippets.views.snippets import InspectView as SnippetInspectView
from wagtail.snippets.views.snippets import SnippetViewSet

from .panels import render_seo_analysis_html


class SEOAnalysisInspectView(SnippetInspectView):
    def get_edit_url(self):
        return None

    def get_delete_url(self):
        return None

    def get_analysis_data_display_value(self):
        return render_seo_analysis_html(self.object)


class SEOAnalysisIndexView(SnippetIndexView):
    @cached_property
    def columns(self):
        from wagtail.admin.views.generic.models import IndexView as GenericIndexView

        # Call grandparent's columns to skip BulkActionsCheckboxColumn
        return GenericIndexView.columns.__get__(self)

    def get_add_url(self):
        return None

    def get_edit_url(self, instance):
        return None

    def get_copy_url(self, instance):
        return None

    def get_delete_url(self, instance):
        return None


class SEOAnalysisViewSet(SnippetViewSet):
    from .models import PageSEOAnalysis

    model = PageSEOAnalysis
    icon = "search"
    menu_label = "SEO Analysis"
    menu_order = 300
    add_to_admin_menu = True
    inspect_view_enabled = True
    index_view_class = SEOAnalysisIndexView
    inspect_view_class = SEOAnalysisInspectView
    add_view_class = None
    edit_view_class = None
    delete_view_class = None

    list_display = [
        "page",
        Column("health_score", label="Score", width="15%"),
        DateColumn("analyzed_at", label="Analyzed", width="20%"),
    ]

    list_filter = ["analyzed_at"]
    search_fields = ["page__title"]

    panels = [
        FieldPanel("page", read_only=True),
        FieldPanel("health_score", read_only=True),
        FieldPanel("analysis_data", read_only=True),
        FieldPanel("analyzed_at", read_only=True),
    ]

    def get_urlpatterns(self):
        return [
            path("", self.index_view, name="list"),
            path("results/", self.index_results_view, name="list_results"),
            path("inspect/<str:pk>/", self.inspect_view, name="inspect"),
            path("usage/<str:pk>/", self.usage_view, name="usage"),
            path("history/<str:pk>/", self.history_view, name="history"),
            path(
                "history-results/<str:pk>/",
                self.history_results_view,
                name="history_results",
            ),
        ]


register_snippet(SEOAnalysisViewSet)


@hooks.register("register_admin_urls")
def register_seo_admin_urls():
    return [
        path(
            "seo/suggestions/<int:suggestion_id>/accept/",
            accept_link_suggestion,
            name="seo_accept_suggestion",
        ),
        path(
            "seo/suggestions/<int:suggestion_id>/dismiss/",
            dismiss_link_suggestion,
            name="seo_dismiss_suggestion",
        ),
    ]


@staff_member_required
@csrf_protect
@require_POST
def accept_link_suggestion(request: HttpRequest, suggestion_id: int) -> HttpResponse:
    from .models import InternalLinkSuggestion

    suggestion = get_object_or_404(InternalLinkSuggestion, pk=suggestion_id)
    if suggestion.status == "pending":
        suggestion.status = "accepted"
        suggestion.save()
    return HttpResponseRedirect(
        reverse("wagtailadmin_pages:edit", args=[suggestion.source_page.id])
    )


@staff_member_required
@csrf_protect
@require_POST
def dismiss_link_suggestion(request: HttpRequest, suggestion_id: int) -> HttpResponse:
    from .models import InternalLinkSuggestion

    suggestion = get_object_or_404(InternalLinkSuggestion, pk=suggestion_id)
    suggestion.status = "dismissed"
    suggestion.save()
    return HttpResponseRedirect(
        reverse("wagtailadmin_pages:edit", args=[suggestion.source_page.id])
    )
