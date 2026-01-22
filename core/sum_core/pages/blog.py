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
from django.utils.text import slugify
from modelcluster.contrib.taggit import ClusterTaggableManager
from modelcluster.fields import ParentalKey
from sum_core.blocks import BlogPostStreamBlock, LeadMagnetBlock
from sum_core.pages.cache import (
    BLOG_CATEGORIES_CACHE_TTL_SECONDS,
    get_blog_categories_cache_key,
)
from sum_core.pages.mixins import (
    BreadcrumbMixin,
    DesktopStickyCTAMixin,
    OpenGraphMixin,
    SeoFieldsMixin,
)
from taggit.models import Tag, TaggedItemBase
from wagtail import blocks
from wagtail.admin.panels import (
    FieldPanel,
    MultiFieldPanel,
    ObjectList,
    PageChooserPanel,
    TabbedInterface,
)
from wagtail.fields import RichTextField, StreamField
from wagtail.models import Page, Site
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
    add_to_admin_menu = False
    menu_item_is_registered = True
    list_display = ["name", "slug"]
    search_fields = ["name", "description"]
    panels = Category.panels


class BlogPromoSnippet(models.Model):
    """Snippet for the BlogPostPage sidebar promo card."""

    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="blog_promos",
        help_text="Optional site restriction for this promo.",
    )
    eyebrow = models.CharField(max_length=80, blank=True)
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True)
    link_text = models.CharField(max_length=80, blank=True)
    link_page = models.ForeignKey(
        Page,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    link_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=False)

    panels = [
        FieldPanel("site"),
        FieldPanel("is_active"),
        FieldPanel("eyebrow"),
        FieldPanel("title"),
        FieldPanel("body"),
        FieldPanel("link_text"),
        FieldPanel("link_page"),
        FieldPanel("link_url"),
    ]

    class Meta:
        verbose_name = "Blog promo"
        verbose_name_plural = "Blog promos"

    def __str__(self) -> str:
        return str(self.title)

    def clean(self) -> None:
        super().clean()
        if self.link_page and self.link_url:
            raise ValidationError({"link_page": "Choose a page or URL, not both."})
        if self.link_text and not (self.link_page or self.link_url):
            raise ValidationError(
                {"link_text": "Provide a link target for the link text."}
            )
        if not self.is_active:
            return
        existing = BlogPromoSnippet.objects.filter(is_active=True)
        if self.site_id:
            existing = existing.filter(site=self.site_id)
        else:
            existing = existing.filter(site__isnull=True)
        if self.pk:
            existing = existing.exclude(pk=self.pk)
        if existing.exists():
            raise ValidationError(
                {"is_active": "Only one active blog promo is allowed per site."}
            )

    def get_link_url(self) -> str:
        if self.link_page:
            return self.link_page.url or ""
        return self.link_url

    @classmethod
    def get_active_for_site(cls, site: Site | None) -> BlogPromoSnippet | None:
        if site is not None:
            promo = cls.objects.filter(is_active=True, site=site).first()
            if promo:
                return promo
        return cls.objects.filter(is_active=True, site__isnull=True).first()


class BlogPromoSnippetViewSet(SnippetViewSet):
    """Wagtail snippet viewset for blog promos."""

    model = BlogPromoSnippet
    icon = "pick"
    menu_label = "Blog Promo"
    add_to_admin_menu = False
    menu_item_is_registered = True
    list_display = ["title", "site", "is_active"]
    list_filter = ["is_active", "site"]
    search_fields = ["title", "body", "eyebrow"]
    panels = BlogPromoSnippet.panels


class BlogPostPageTag(TaggedItemBase):
    """Tag relationship for BlogPostPage."""

    content_object = ParentalKey(
        "sum_core_pages.BlogPostPage",
        related_name="tagged_items",
        on_delete=models.CASCADE,
    )


class BlogSidebarStreamBlock(blocks.StreamBlock):
    """Sidebar block(s) for blog article templates."""

    lead_magnet = LeadMagnetBlock()

    class Meta:
        max_num = 1


class BlogIndexPage(
    DesktopStickyCTAMixin, SeoFieldsMixin, OpenGraphMixin, BreadcrumbMixin, Page
):
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
    featured_post = models.ForeignKey(
        "sum_core_pages.BlogPostPage",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="Optional featured post pinned to the top of the listing.",
    )
    sidebar_subscribe = StreamField(
        BlogSidebarStreamBlock(),
        blank=True,
        use_json_field=True,
        help_text="Optional lead magnet shown in the blog article sidebar.",
    )

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
        FieldPanel("posts_per_page"),
        PageChooserPanel("featured_post", "sum_core_pages.BlogPostPage"),
        MultiFieldPanel(
            [FieldPanel("sidebar_subscribe")],
            heading="Sidebar",
        ),
    ]

    promote_panels = SeoFieldsMixin.promote_panels + OpenGraphMixin.open_graph_panels
    settings_panels = (
        Page.settings_panels + DesktopStickyCTAMixin.desktop_sticky_cta_panels
    )

    # NOTE: parent_page_types is intentionally NOT set here.
    # Wagtail's default (inherited from Page) allows ANY parent page type.
    # Client projects should restrict via their HomePage's subpage_types.
    subpage_types: list[str] = ["sum_core_pages.BlogPostPage"]

    # v0.6 rendering contract: themes own page templates under theme/
    template: str = "theme/blog_index_page.html"

    class Meta:
        verbose_name = "Blog Index Page"
        verbose_name_plural = "Blog Index Pages"

    @property
    def header_transparent_at_top(self) -> bool:
        """Return True when the header should be transparent at the top."""
        return True

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
        search_query = (query_params.get("q") or "").strip()
        tag_slug = (query_params.get("tag") or "").strip()
        selected_category = None
        selected_tag = None
        show_featured = not search_query and not category_slug and not tag_slug
        explicit_featured = self.featured_post if show_featured else None

        if search_query:
            posts = posts.filter(
                Q(title__icontains=search_query) | Q(excerpt__icontains=search_query)
            )

        if category_slug:
            try:
                selected_category = Category.objects.get(slug=category_slug)
                posts = posts.filter(category=selected_category)
            except Category.DoesNotExist:
                selected_category = None

        if tag_slug:
            try:
                selected_tag = Tag.objects.get(slug=tag_slug)
                posts = posts.filter(tags__slug=tag_slug)
            except Tag.DoesNotExist:
                selected_tag = None

        if explicit_featured is not None:
            if all_posts.filter(pk=explicit_featured.pk).exists():
                posts = posts.exclude(pk=explicit_featured.pk)
            else:
                explicit_featured = None

        paginator = Paginator(posts, self.posts_per_page)
        page_num = query_params.get("page", 1)
        paginated_posts = paginator.get_page(page_num)

        featured_post = None
        archive_posts = list(paginated_posts)
        if paginated_posts.number == 1 and show_featured:
            if explicit_featured is not None:
                featured_post = explicit_featured
            elif archive_posts:
                featured_post = archive_posts[0]
                archive_posts = archive_posts[1:]

        filtered_posts_count = posts.count()
        if explicit_featured is not None:
            filtered_posts_count += 1
        visible_posts_count = len(archive_posts) + (1 if featured_post else 0)
        if paginated_posts.number > 1:
            visible_posts_count += (paginated_posts.number - 1) * self.posts_per_page

        context["posts"] = paginated_posts
        context["featured_post"] = featured_post
        context["archive_posts"] = archive_posts
        context["search_query"] = search_query
        context["total_posts_count"] = all_posts.count()
        context["filtered_posts_count"] = filtered_posts_count
        context["visible_posts_count"] = visible_posts_count
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
        context["selected_tag"] = selected_tag
        return context


class BlogPostPage(
    DesktopStickyCTAMixin, SeoFieldsMixin, OpenGraphMixin, BreadcrumbMixin, Page
):
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
    tags = ClusterTaggableManager(
        through=BlogPostPageTag,
        blank=True,
        help_text="Optional tags for the article.",
    )
    body: StreamField = StreamField(
        BlogPostStreamBlock(),
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
        FieldPanel("tags"),
        FieldPanel("author_name"),
        FieldPanel("body"),
    ]

    promote_panels = (
        SeoFieldsMixin.promote_panels
        + OpenGraphMixin.open_graph_panels
        + [
            MultiFieldPanel(
                [FieldPanel("reading_time", read_only=True)],
                heading="Metadata",
            )
        ]
    )
    settings_panels = (
        Page.settings_panels + DesktopStickyCTAMixin.desktop_sticky_cta_panels
    )

    edit_handler = TabbedInterface(
        [
            ObjectList(content_panels, heading="Content"),
            ObjectList(promote_panels, heading="Promote"),
            ObjectList(settings_panels, heading="Settings"),
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

        parts: list[str] = []

        for block in self.body:
            value = getattr(block, "value", None)
            if value is None:
                continue

            text_candidates: list[str] = []

            if block.block_type == "numbered_steps":
                for step in value.get("steps", []):
                    title = step.get("title")
                    description = step.get("description")
                    if title:
                        text_candidates.append(str(title))
                    if description:
                        text_candidates.append(str(description))
            elif block.block_type in {
                "lead_paragraph",
                "article_section",
                "call_to_action",
            }:
                for key in (
                    "eyebrow",
                    "heading",
                    "subheading",
                    "subheading_secondary",
                    "body",
                ):
                    item = value.get(key)
                    if item:
                        text_candidates.append(str(getattr(item, "source", item)))
            elif block.block_type in {
                "rich_text",
                "content",
                "quote",
                "social_proof_quote",
                "editorial_header",
                "page_header",
                "legal_section",
                "manifesto",
            }:
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

    @property
    def header_transparent_at_top(self) -> bool:
        """Return True when the header should be transparent at the top."""
        return True

    def _extract_toc_entries(self) -> list[dict[str, str]]:
        if not self.body:
            return []

        entries: list[dict[str, str]] = []

        for block in self.body:
            if block.block_type == "article_section":
                value = getattr(block, "value", None)
                if not value:
                    continue
                heading_text = strip_tags(value.get("heading") or "")
                if not heading_text:
                    continue
                anchor = value.get("anchor") or slugify(heading_text)
                entries.append({"anchor": anchor, "label": heading_text})

        return entries

    def get_read_next_posts(self) -> models.QuerySet[BlogPostPage]:
        parent = self.get_parent()
        if parent is None:
            return BlogPostPage.objects.none()
        return (
            BlogPostPage.objects.child_of(parent)
            .live()
            .public()
            .filter(published_date__lte=timezone.now())
            .exclude(pk=self.pk)
            .select_related("category", "featured_image")
            .prefetch_related("featured_image__renditions")
            .order_by("-published_date")[:3]
        )

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        site = self.get_site()
        body_blocks = list(self.body) if self.body else []
        cta_index = next(
            (
                index
                for index, block in enumerate(body_blocks)
                if block.block_type == "call_to_action"
            ),
            None,
        )
        if cta_index is not None:
            context["body_before_tags"] = body_blocks[:cta_index]
            context["body_after_tags"] = body_blocks[cta_index:]
        else:
            context["body_before_tags"] = body_blocks
            context["body_after_tags"] = []
        context["toc_entries"] = self._extract_toc_entries()
        context["read_next_posts"] = list(self.get_read_next_posts())
        context["promo_snippet"] = BlogPromoSnippet.get_active_for_site(site)
        return context
