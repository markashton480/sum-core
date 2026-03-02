"""
Name: Blog Snippets
Path: core/sum_core/pages/blog.py
Purpose: Strategy models and admin representations for blog-related taxonomy.
Family: Pages.
"""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from html.parser import HTMLParser
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


@dataclass
class LongformHeading:
    """Parsed heading metadata extracted from longform rich text."""

    level: int
    text: str
    explicit_anchor: str | None = None


@dataclass
class BlogBodyAnalysis:
    """Cached analysis output for blog body anchor and TOC rendering."""

    toc_entries: list[dict[str, str]]
    article_section_anchors: dict[str, str]
    longform_rendered_html: dict[str, str]


class LongformHeadingParser(HTMLParser):
    """Extract H2/H3 heading text (and optional ID) from HTML."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.headings: list[LongformHeading] = []
        self._depth = 0
        self._current_level: int | None = None
        self._current_anchor: str | None = None
        self._text_chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._depth == 0 and tag in {"h2", "h3"}:
            self._depth = 1
            self._current_level = int(tag[1])
            attrs_dict = dict(attrs)
            self._current_anchor = attrs_dict.get("id")
            self._text_chunks = []
            return

        if self._depth > 0:
            self._depth += 1

    def handle_endtag(self, tag: str) -> None:
        if self._depth == 0:
            return

        self._depth -= 1
        if self._depth != 0:
            return

        if self._current_level is None:
            return

        heading_text = " ".join("".join(self._text_chunks).split())
        self.headings.append(
            LongformHeading(
                level=self._current_level,
                text=heading_text,
                explicit_anchor=self._current_anchor,
            )
        )
        self._current_level = None
        self._current_anchor = None
        self._text_chunks = []

    def handle_data(self, data: str) -> None:
        if self._depth > 0:
            self._text_chunks.append(data)


class HeadingAnchorInjector(HTMLParser):
    """Inject precomputed IDs into H2/H3 tags while preserving HTML output."""

    def __init__(self, anchors: list[str]) -> None:
        super().__init__(convert_charrefs=False)
        self._anchors = anchors
        self._parts: list[str] = []
        self._anchor_index = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"h2", "h3"} and self._anchor_index < len(self._anchors):
            anchor = self._anchors[self._anchor_index]
            self._anchor_index += 1
            self._parts.append(self._render_start_tag(tag, attrs, anchor))
            return

        self._parts.append(
            self.get_starttag_text() or self._render_start_tag(tag, attrs)
        )

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._parts.append(
            self.get_starttag_text() or self._render_start_tag(tag, attrs, closed=True)
        )

    def handle_endtag(self, tag: str) -> None:
        self._parts.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        self._parts.append(data)

    def handle_entityref(self, name: str) -> None:
        self._parts.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        self._parts.append(f"&#{name};")

    def handle_comment(self, data: str) -> None:
        self._parts.append(f"<!--{data}-->")

    def handle_decl(self, decl: str) -> None:
        self._parts.append(f"<!{decl}>")

    def handle_pi(self, data: str) -> None:
        self._parts.append(f"<?{data}>")

    def get_html(self) -> str:
        return "".join(self._parts)

    def _render_start_tag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
        anchor: str | None = None,
        *,
        closed: bool = False,
    ) -> str:
        final_attrs = [(name, value) for name, value in attrs if name.lower() != "id"]
        if anchor:
            final_attrs.append(("id", anchor))

        rendered_attrs = []
        for name, value in final_attrs:
            if value is None:
                rendered_attrs.append(f" {name}")
            else:
                rendered_attrs.append(f' {name}="{escape(value, quote=True)}"')
        suffix = " /" if closed else ""
        return f"<{tag}{''.join(rendered_attrs)}{suffix}>"


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
        # NOTE: Best-effort validation only; concurrent activations can race.
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
        # NOTE: Best-effort validation only; concurrent page creations can race.

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
                "longform_article",
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

        raw_body_html = " ".join(parts).replace("><", "> <")
        plain_text = strip_tags(raw_body_html)
        return cast(str, " ".join(plain_text.split()))

    def _normalize_anchor(self, raw_anchor: str | None) -> str:
        """Return a normalized anchor ID or an empty string."""
        if not raw_anchor:
            return ""
        return slugify(str(raw_anchor).strip().lstrip("#"))

    def _normalize_heading_key(self, heading_text: str | None) -> str:
        """Return a case-insensitive heading key for override matching."""
        if not heading_text:
            return ""
        return " ".join(strip_tags(str(heading_text)).split()).casefold()

    def _build_unique_anchor(
        self, raw_anchor: str | None, used_anchors: set[str]
    ) -> str:
        """Return a deterministic unique anchor and reserve it in used_anchors."""
        base_anchor = self._normalize_anchor(raw_anchor) or "section"
        candidate = base_anchor
        index = 2
        while candidate in used_anchors:
            candidate = f"{base_anchor}-{index}"
            index += 1
        used_anchors.add(candidate)
        return candidate

    def _get_block_id(self, block, index: int) -> str:
        block_id = getattr(block, "id", None)
        if block_id:
            return str(block_id)
        return f"idx-{index}"

    def _get_richtext_source(self, value) -> str:
        if value is None:
            return ""
        source = getattr(value, "source", None)
        if source is not None:
            return str(source)
        return str(value)

    def _collect_longform_override_map(
        self, override_items
    ) -> dict[tuple[str, int], str]:
        """Build map of (normalized heading, occurrence) -> explicit anchor."""
        overrides: dict[tuple[str, int], str] = {}
        for item in override_items or []:
            heading_key = self._normalize_heading_key(item.get("heading"))
            occurrence = int(item.get("occurrence") or 1)
            anchor = self._normalize_anchor(item.get("anchor"))
            if not heading_key or occurrence < 1 or not anchor:
                continue
            overrides[(heading_key, occurrence)] = anchor
        return overrides

    def _analyze_blog_body(self) -> BlogBodyAnalysis:
        """Analyze body once to produce TOC entries and render-safe anchors."""
        cached = getattr(self, "_blog_body_analysis_cache", None)
        if cached is not None:
            return cached

        if not self.body:
            empty_analysis = BlogBodyAnalysis(
                toc_entries=[],
                article_section_anchors={},
                longform_rendered_html={},
            )
            self._blog_body_analysis_cache = empty_analysis
            return empty_analysis

        used_anchors: set[str] = set()
        toc_entries: list[dict[str, str]] = []
        article_section_anchors: dict[str, str] = {}
        longform_rendered_html: dict[str, str] = {}

        for index, block in enumerate(self.body):
            block_id = self._get_block_id(block, index)
            value = getattr(block, "value", None)
            if value is None:
                continue

            if block.block_type == "article_section":
                heading_text = " ".join(strip_tags(value.get("heading") or "").split())
                if not heading_text:
                    continue

                anchor = self._build_unique_anchor(
                    value.get("anchor") or heading_text,
                    used_anchors,
                )
                article_section_anchors[block_id] = anchor
                toc_entries.append({"anchor": anchor, "label": heading_text})
                continue

            if block.block_type != "longform_article":
                continue

            longform_html = self._get_richtext_source(value.get("body"))
            parser = LongformHeadingParser()
            parser.feed(longform_html)
            parser.close()
            headings = parser.headings

            heading_occurrences: dict[str, int] = {}
            override_map = self._collect_longform_override_map(
                value.get("anchor_overrides")
            )
            resolved_heading_anchors: list[str] = []

            for heading in headings:
                heading_key = self._normalize_heading_key(heading.text)
                if heading_key:
                    heading_occurrences[heading_key] = (
                        heading_occurrences.get(heading_key, 0) + 1
                    )
                occurrence = heading_occurrences.get(heading_key, 1)

                override_anchor = override_map.get((heading_key, occurrence))
                anchor = self._build_unique_anchor(
                    override_anchor or heading.explicit_anchor or heading.text,
                    used_anchors,
                )
                resolved_heading_anchors.append(anchor)

                if heading.text:
                    toc_entries.append(
                        {
                            "anchor": anchor,
                            "label": heading.text,
                            "level": f"h{heading.level}",
                        }
                    )

            injector = HeadingAnchorInjector(resolved_heading_anchors)
            injector.feed(longform_html)
            injector.close()
            longform_rendered_html[block_id] = injector.get_html()

        analysis = BlogBodyAnalysis(
            toc_entries=toc_entries,
            article_section_anchors=article_section_anchors,
            longform_rendered_html=longform_rendered_html,
        )
        self._blog_body_analysis_cache = analysis
        return analysis

    class Meta:
        verbose_name = "Blog Post"
        verbose_name_plural = "Blog Posts"

    @property
    def header_transparent_at_top(self) -> bool:
        """Return True when the header should be transparent at the top."""
        return True

    def _extract_toc_entries(self) -> list[dict[str, str]]:
        return self._analyze_blog_body().toc_entries

    def get_blog_block_anchor(self, block_id: str | None) -> str | None:
        """Return computed anchor for blog article_section block IDs."""
        if not block_id:
            return None
        return self._analyze_blog_body().article_section_anchors.get(str(block_id))

    def get_longform_block_html(self, block_id: str | None) -> str | None:
        """Return rendered longform HTML with injected heading IDs."""
        if not block_id:
            return None
        return self._analyze_blog_body().longform_rendered_html.get(str(block_id))

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
