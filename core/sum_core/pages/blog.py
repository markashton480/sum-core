"""
Name: Blog Snippets
Path: core/sum_core/pages/blog.py
Purpose: Strategy models and admin representations for blog-related taxonomy.
Family: Pages.
"""

from __future__ import annotations

from typing import cast

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.html import strip_tags
from sum_core.blocks import PageStreamBlock
from sum_core.pages.cache import (
    BLOG_CATEGORIES_CACHE_TTL_SECONDS,
    get_blog_categories_cache_key,
)
from sum_core.pages.mixins import BreadcrumbMixin, OpenGraphMixin, SeoFieldsMixin
from wagtail.admin.panels import (
    FieldPanel,
    MultiFieldPanel,
    ObjectList,
    TabbedInterface,
)
from wagtail.fields import RichTextField, StreamField
from wagtail.models import Page
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet


class Category(models.Model):
    """
    Blog post category (single-level taxonomy).

    Allows content editors to group posts without hierarchical parents.
    """

    name = models.CharField(
        max_length=100,
        help_text="Category name (e.g., 'News', 'Tutorials', 'Case Studies')",
    )
    slug = models.SlugField(
        max_length=100,
        unique=True,
        help_text="URL-friendly identifier",
    )
    description = models.TextField(
        blank=True,
        help_text="Optional category description for SEO",
    )

    panels = [
        FieldPanel("name"),
        FieldPanel("slug"),
        FieldPanel("description"),
    ]

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def __str__(self) -> str:
        return str(self.name)


class CategorySnippetViewSet(SnippetViewSet):
    """Wagtail snippet viewset for blog categories."""

    model = Category
    icon = "list-ul"
    menu_label = "Blog Categories"
    list_display = ["name", "slug"]
    search_fields = ["name", "description"]
    panels = Category.panels


register_snippet(CategorySnippetViewSet)


class BlogIndexPage(SeoFieldsMixin, OpenGraphMixin, BreadcrumbMixin, Page):
    """
    Blog listing page that displays blog posts with pagination and filtering.

    URL: /blog/
    """

    intro = RichTextField(
        blank=True,
        help_text="Optional intro text displayed above the post listing.",
    )
    posts_per_page = models.IntegerField(
        default=10,
        help_text="Number of posts to display per page.",
        validators=[MinValueValidator(1)],
    )

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
        FieldPanel("posts_per_page"),
    ]

    promote_panels = (
        SeoFieldsMixin.seo_panels
        + OpenGraphMixin.open_graph_panels
        + Page.promote_panels
    )

    # Allow clients to decide placement via their root page subpage_types.
    parent_page_types: list[str] = ["wagtailcore.Page"]
    subpage_types: list[str] = ["sum_core_pages.BlogPostPage"]

    # v0.6 rendering contract: themes own page templates under theme/
    template: str = "theme/blog_index_page.html"

    class Meta:
        verbose_name = "Blog Index Page"
        verbose_name_plural = "Blog Index Pages"

    def get_posts(self) -> models.QuerySet[BlogPostPage]:
        """Return live BlogPostPage children ordered by published date."""
        return (
            BlogPostPage.objects.child_of(self)
            .live()
            .public()
            .select_related("category", "featured_image")
            .prefetch_related("featured_image__renditions")
            .filter(published_date__lte=timezone.now())
            .order_by("-published_date")
        )

    def get_posts_by_category(
        self, category: Category
    ) -> models.QuerySet[BlogPostPage]:
        """Return blog posts filtered by category."""
        return self.get_posts().filter(category=category)

    def clean(self) -> None:
        """Ensure only one BlogIndexPage exists per site."""
        super().clean()

        site = self.get_site()
        if site is None:
            parent = self.get_parent()
            if parent:
                site = parent.get_site()

        queryset = BlogIndexPage.objects.all()
        if site is not None and getattr(site, "root_page", None) is not None:
            queryset = queryset.descendant_of(site.root_page, inclusive=True)

        if queryset.exclude(pk=self.pk).exists():
            raise ValidationError(
                {"title": "Only one BlogIndexPage is allowed per site."}
            )

    def save(self, *args, **kwargs):
        """Enforce singleton validation even for programmatic saves."""
        should_clean = kwargs.pop("clean", True)
        if should_clean:
            self.clean()
        super().save(*args, **kwargs)

    def get_context(self, request, *args, **kwargs):
        """
        Add pagination and category filtering to template context.

        Query params:
        - category: category slug to filter
        - page: 1-based page number
        If request is None, defaults to first page with no filter.
        Categories are annotated with post_count for listing use.
        """
        context = super().get_context(request, *args, **kwargs)

        all_posts = self.get_posts()
        posts = all_posts
        query_params = request.GET if request is not None else {}
        category_slug = query_params.get("category")
        selected_category = None

        if category_slug:
            try:
                selected_category = Category.objects.get(slug=category_slug)
                posts = posts.filter(category=selected_category)
            except Category.DoesNotExist:
                selected_category = None

        paginator = Paginator(posts, self.posts_per_page)
        page_num = query_params.get("page", 1)
        paginated_posts = paginator.get_page(page_num)

        context["posts"] = paginated_posts
        categories = cache.get(get_blog_categories_cache_key(self))
        if categories is None:
            # Counts are for public posts only; restricted posts are excluded.
            categories = list(
                Category.objects.annotate(
                    post_count=Count(
                        "blog_posts",
                        filter=Q(
                            blog_posts__path__startswith=self.path,
                            blog_posts__depth=self.depth + 1,
                            blog_posts__live=True,
                            blog_posts__published_date__lte=timezone.now(),
                            blog_posts__view_restrictions__isnull=True,
                        ),
                    )
                )
            )
            cache.set(
                get_blog_categories_cache_key(self),
                categories,
                timeout=BLOG_CATEGORIES_CACHE_TTL_SECONDS,
            )
        context["categories"] = categories
        context["selected_category"] = selected_category
        return context


class BlogPostPage(SeoFieldsMixin, OpenGraphMixin, BreadcrumbMixin, Page):
    """
    Individual blog post/article.

    URL: /blog/<slug>/
    Template: theme/blog_post_page.html
    """

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="blog_posts",
        help_text="Blog post category",
    )
    published_date = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text="Date this post was published",
    )
    featured_image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Featured image displayed at top of post",
    )
    excerpt = models.TextField(
        blank=True,
        max_length=500,
        help_text="Short excerpt for listings (auto-generated if blank)",
    )
    body: StreamField = StreamField(
        PageStreamBlock(),  # Includes DynamicFormBlock for CTAs
        blank=False,
        use_json_field=True,
        help_text="Article content with optional form CTAs",
    )
    author_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Author name (optional - no multi-author system)",
    )
    reading_time = models.PositiveIntegerField(
        default=1,
        help_text="Estimated reading time in minutes (auto-calculated)",
    )

    content_panels = Page.content_panels + [
        FieldPanel("category"),
        FieldPanel("published_date"),
        FieldPanel("featured_image"),
        FieldPanel("excerpt"),
        FieldPanel("author_name"),
        FieldPanel("body"),
    ]

    promote_panels = (
        SeoFieldsMixin.seo_panels
        + OpenGraphMixin.open_graph_panels
        + Page.promote_panels
        + [
            MultiFieldPanel(
                [FieldPanel("reading_time", read_only=True)],
                heading="Metadata",
            )
        ]
    )

    edit_handler = TabbedInterface(
        [
            ObjectList(content_panels, heading="Content"),
            ObjectList(promote_panels, heading="Promote"),
            ObjectList(Page.settings_panels, heading="Settings"),
        ]
    )

    parent_page_types = ["sum_core_pages.BlogIndexPage"]
    subpage_types: list[str] = []
    template: str = "theme/blog_post_page.html"

    def save(self, *args, **kwargs):
        """Auto-calculate reading time before saving."""
        self.reading_time = self.calculate_reading_time()
        super().save(*args, **kwargs)

    def calculate_reading_time(self) -> int:
        """
        Calculate reading time based on word count.

        Assumes 200 words per minute average reading speed.
        Minimum 1 minute.
        """
        body_text = self._get_body_text()
        word_count = len(body_text.split())
        minutes = max(1, round(word_count / 200))
        return minutes

    def get_excerpt(self) -> str:
        """
        Return excerpt if provided, otherwise generate from body.

        Strips HTML and truncates to ~150 characters.
        """
        if self.excerpt:
            return str(self.excerpt)

        body_text = self._get_body_text()
        if not body_text:
            return ""

        if len(body_text) > 150:
            return body_text[:147] + "..."
        return body_text

    def _get_body_text(self) -> str:
        """Return a plain-text representation of the body StreamField."""
        if not self.body:
            return ""

        text_blocks = {
            "rich_text",
            "content",
            "quote",
            "social_proof_quote",
            "editorial_header",
            "page_header",
            "legal_section",
            "manifesto",
        }
        parts: list[str] = []

        for block in self.body:
            if block.block_type not in text_blocks:
                continue

            value = getattr(block, "value", None)
            text_candidates: list[str] = []

            if value is None:
                continue

            if hasattr(value, "source"):
                text_candidates.append(str(getattr(value, "source")))
            elif hasattr(value, "get"):
                for key in ("body", "quote", "heading", "eyebrow"):
                    item = value.get(key)
                    if item:
                        text_candidates.append(str(getattr(item, "source", item)))
            elif value:
                text_candidates.append(str(value))

            if text_candidates:
                parts.append(" ".join(text_candidates))

        return cast(str, strip_tags(" ".join(parts)))

    class Meta:
        verbose_name = "Blog Post"
        verbose_name_plural = "Blog Posts"
