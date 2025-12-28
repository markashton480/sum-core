"""
Name: Pages Wagtail hooks
Path: core/sum_core/pages/wagtail_hooks.py
Purpose: Register admin viewsets for page listings.
Family: Pages, Admin UX.
Dependencies: Wagtail hooks, page listing viewsets.
"""

from __future__ import annotations

from sum_core.pages.wagtail_admin import BlogPostPageListingViewSet
from wagtail import hooks


@hooks.register("register_admin_viewset")
def register_blog_post_listing_viewset() -> BlogPostPageListingViewSet:
    """Register the BlogPostPage listing in Wagtail admin."""
    return BlogPostPageListingViewSet("blog-posts")
