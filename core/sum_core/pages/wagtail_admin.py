"""
Name: Blog admin listing
Path: core/sum_core/pages/wagtail_admin.py
Purpose: Custom Wagtail listing for BlogPostPage with category filtering.
Family: Pages, Admin UX.
Dependencies: Wagtail page listing viewset, BlogPostPage model.
"""

from __future__ import annotations

from django.db.utils import OperationalError, ProgrammingError
from django.urls import reverse
from django.utils.functional import cached_property
from sum_core.pages.blog import (
    BlogIndexPage,
    BlogPostPage,
    BlogPromoSnippetViewSet,
    CategorySnippetViewSet,
)
from wagtail.admin.filters import WagtailFilterSet
from wagtail.admin.menu import MenuItem
from wagtail.admin.ui.tables import Column, DateColumn
from wagtail.admin.ui.tables.pages import (
    BulkActionsColumn,
    PageStatusColumn,
    PageTitleColumn,
)
from wagtail.admin.viewsets.base import ViewSet, ViewSetGroup
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
    name = "blog-posts"
    icon = "doc-full"
    menu_label = "Blog Posts"
    menu_name = "blog-posts"
    add_to_admin_menu = False
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


class BlogIndexMenuItem(MenuItem):
    def is_shown(self, request):
        return bool(self.url)


class BlogIndexPageViewSet(ViewSet):
    name = "blog-settings"
    menu_label = "Blog Settings"
    menu_name = "blog-settings"
    menu_icon = "cog"
    menu_item_class = BlogIndexMenuItem
    add_to_admin_menu = False

    def get_urlpatterns(self):
        return []

    @cached_property
    def menu_url(self):
        try:
            blog_index = BlogIndexPage.objects.first()
        except (OperationalError, ProgrammingError):
            return ""
        if blog_index is None:
            return ""
        return reverse("wagtailadmin_pages:edit", args=(blog_index.pk,))


class BlogViewSetGroup(ViewSetGroup):
    menu_label = "Blog"
    menu_name = "blog"
    menu_icon = "doc-full-inverse"
    menu_order = 210
    items = (
        BlogIndexPageViewSet,
        BlogPostPageListingViewSet,
        CategorySnippetViewSet,
        BlogPromoSnippetViewSet,
    )
