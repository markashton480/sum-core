"""
Name: Blog admin listing
Path: core/sum_core/pages/wagtail_admin.py
Purpose: Custom Wagtail listing for BlogPostPage with category filtering.
Family: Pages, Admin UX.
Dependencies: Wagtail page listing viewset, BlogPostPage model.
"""

from __future__ import annotations

from sum_core.pages.blog import BlogPostPage
from wagtail.admin.filters import WagtailFilterSet
from wagtail.admin.ui.tables import Column, DateColumn
from wagtail.admin.ui.tables.pages import (
    BulkActionsColumn,
    PageStatusColumn,
    PageTitleColumn,
)
from wagtail.admin.viewsets.pages import PageListingViewSet


class BlogPostPageFilterSet(WagtailFilterSet):
    class Meta:
        model = BlogPostPage
        fields = [
            "category",
            "live",
            "published_date",
        ]


class BlogPostPageListingViewSet(PageListingViewSet):
    model = BlogPostPage
    icon = "doc-full"
    menu_label = "Blog Posts"
    menu_name = "blog-posts"
    menu_order = 210
    add_to_admin_menu = True
    filterset_class = BlogPostPageFilterSet

    columns = [
        BulkActionsColumn("bulk_actions"),
        PageTitleColumn(
            "title",
            label="Title",
            sort_key="title",
            classname="title",
        ),
        Column(
            "category",
            label="Category",
            sort_key="category",
            width="15%",
        ),
        DateColumn(
            "published_date",
            label="Published",
            sort_key="published_date",
            width="12%",
        ),
        Column(
            "reading_time",
            label="Read min",
            sort_key="reading_time",
            width="10%",
        ),
        PageStatusColumn(
            "status",
            label="Status",
            sort_key="live",
            width="12%",
        ),
    ]
