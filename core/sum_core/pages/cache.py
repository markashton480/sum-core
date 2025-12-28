"""
Name: Blog Category Cache
Path: core/sum_core/pages/cache.py
Purpose: Cache helpers and signal-based invalidation for blog category listings.
Family: Pages, Blog.
Dependencies: django.core.cache, django.db.models.signals, wagtail.signals
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from wagtail.signals import page_published, page_unpublished

if TYPE_CHECKING:
    from sum_core.pages.blog import BlogIndexPage

BLOG_CATEGORIES_CACHE_PREFIX = "blog_categories"
BLOG_CATEGORIES_VERSION_KEY = "blog_categories_version"
BLOG_CATEGORIES_CACHE_TTL_SECONDS = 3600


def get_blog_categories_cache_key(blog_index: BlogIndexPage) -> str:
    version = cache.get(BLOG_CATEGORIES_VERSION_KEY) or "0"
    return f"{BLOG_CATEGORIES_CACHE_PREFIX}:{blog_index.pk}:{blog_index.path}:{version}"


def bump_blog_categories_cache_version() -> None:
    if cache.add(BLOG_CATEGORIES_VERSION_KEY, 1):
        return
    try:
        cache.incr(BLOG_CATEGORIES_VERSION_KEY)
    except ValueError:
        cache.set(BLOG_CATEGORIES_VERSION_KEY, 1)


@receiver(post_save, dispatch_uid="blog_categories_cache_category_save")
def _on_category_save(sender, instance, **kwargs) -> None:
    from sum_core.pages.blog import Category

    if sender is Category:
        bump_blog_categories_cache_version()


@receiver(post_delete, dispatch_uid="blog_categories_cache_category_delete")
def _on_category_delete(sender, instance, **kwargs) -> None:
    from sum_core.pages.blog import Category

    if sender is Category:
        bump_blog_categories_cache_version()


@receiver(post_delete, dispatch_uid="blog_categories_cache_post_delete")
def _on_blog_post_delete(sender, instance, **kwargs) -> None:
    from sum_core.pages.blog import BlogPostPage

    if sender is BlogPostPage:
        bump_blog_categories_cache_version()


@receiver(page_published, dispatch_uid="blog_categories_cache_page_published")
def _on_page_published(sender, instance, **kwargs) -> None:
    from sum_core.pages.blog import BlogIndexPage, BlogPostPage

    if isinstance(instance, BlogIndexPage | BlogPostPage):
        bump_blog_categories_cache_version()


@receiver(page_unpublished, dispatch_uid="blog_categories_cache_page_unpublished")
def _on_page_unpublished(sender, instance, **kwargs) -> None:
    from sum_core.pages.blog import BlogIndexPage, BlogPostPage

    if isinstance(instance, BlogIndexPage | BlogPostPage):
        bump_blog_categories_cache_version()
