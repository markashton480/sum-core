# Generated for moving HomePage from test_project to sum_core
# Migration creates HomePage and HomePageHeroCTA models

import django.db.models.deletion
import modelcluster.fields
import wagtail.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("sum_core_pages", "0052_merge_20260119_1935"),
        ("wagtailimages", "0026_delete_uploadedimage"),
        ("wagtailcore", "0094_alter_page_locale"),
        ("sum_core_navigation", "0008_alter_headernavigation_menu_items"),
    ]

    operations = [
        migrations.CreateModel(
            name="HomePage",
            fields=[
                (
                    "page_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="wagtailcore.page",
                    ),
                ),
                # SeoFieldsMixin fields
                (
                    "meta_title",
                    models.CharField(
                        blank=True,
                        help_text=(
                            "Optional. Overrides the SEO title when set; otherwise uses the SEO title "
                            'or "{page title} | {site name}".'
                        ),
                        max_length=60,
                    ),
                ),
                (
                    "meta_description",
                    models.TextField(
                        blank=True,
                        help_text=(
                            "Optional. Overrides the search description for SEO snippets "
                            "(recommended max 160 characters)."
                        ),
                        max_length=160,
                    ),
                ),
                (
                    "seo_noindex",
                    models.BooleanField(
                        default=False,
                        help_text="If checked, this page will be hidden from search engines (noindex).",
                        verbose_name="No-Index",
                    ),
                ),
                (
                    "seo_nofollow",
                    models.BooleanField(
                        default=False,
                        help_text="If checked, search engines will not follow links on this page (nofollow).",
                        verbose_name="No-Follow",
                    ),
                ),
                # OpenGraphMixin field
                (
                    "og_image",
                    models.ForeignKey(
                        blank=True,
                        help_text="Optional. If blank, uses the page featured image (if present), otherwise the site default OG image.",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="wagtailimages.image",
                    ),
                ),
                # DesktopStickyCTAMixin fields
                (
                    "desktop_sticky_cta_mode",
                    models.CharField(
                        choices=[
                            ("inherit", "Inherit site default"),
                            ("disabled", "Disabled"),
                            ("custom", "Custom snippet"),
                        ],
                        default="inherit",
                        help_text="Control whether this page uses the site default or a custom CTA.",
                        max_length=20,
                    ),
                ),
                (
                    "desktop_sticky_cta_snippet",
                    models.ForeignKey(
                        blank=True,
                        help_text="Used when mode is set to Custom snippet.",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="sum_core_navigation.desktopstickyctasnippet",
                    ),
                ),
                # Hero fields (template-owned)
                (
                    "hero_status",
                    models.CharField(
                        blank=True,
                        help_text="Optional eyebrow/status line above the hero heading.",
                        max_length=120,
                    ),
                ),
                (
                    "hero_headline",
                    wagtail.fields.RichTextField(
                        blank=True,
                        help_text="Main hero heading. Use Italic for accent emphasis.",
                    ),
                ),
                (
                    "hero_subheadline",
                    models.TextField(
                        blank=True,
                        help_text="Optional supporting copy shown alongside the hero heading.",
                    ),
                ),
                (
                    "hero_image",
                    models.ForeignKey(
                        blank=True,
                        help_text="Hero background image.",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="wagtailimages.image",
                    ),
                ),
                (
                    "hero_image_alt",
                    models.CharField(
                        blank=True,
                        help_text="Alt text for the hero image.",
                        max_length=255,
                    ),
                ),
                (
                    "hero_overlay_opacity",
                    models.CharField(
                        choices=[
                            ("none", "None"),
                            ("light", "Light"),
                            ("medium", "Medium"),
                            ("strong", "Strong"),
                        ],
                        default="medium",
                        help_text="Overlay darkness level for text readability.",
                        max_length=16,
                    ),
                ),
                (
                    "hero_layout",
                    models.CharField(
                        choices=[
                            ("full", "Full width"),
                            ("split", "Split layout"),
                        ],
                        default="full",
                        help_text="Hero section layout style.",
                        max_length=16,
                    ),
                ),
                (
                    "hero_floating_card_label",
                    models.CharField(
                        blank=True,
                        help_text="Optional floating card label text.",
                        max_length=50,
                    ),
                ),
                (
                    "hero_floating_card_value",
                    models.CharField(
                        blank=True,
                        help_text="Optional floating card value text.",
                        max_length=50,
                    ),
                ),
                # Body StreamField - blocks defined by model at runtime
                (
                    "body",
                    wagtail.fields.StreamField(
                        [],
                        blank=True,
                        help_text="Add content blocks to build your homepage layout.",
                        null=True,
                        use_json_field=True,
                    ),
                ),
            ],
            options={
                "verbose_name": "Home Page",
                "verbose_name_plural": "Home Pages",
            },
            bases=(
                "wagtailcore.page",
                models.Model,
            ),
        ),
        migrations.CreateModel(
            name="HomePageHeroCTA",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "sort_order",
                    models.IntegerField(blank=True, editable=False, null=True),
                ),
                (
                    "label",
                    models.CharField(
                        help_text="Button text (e.g., 'Get Started', 'Learn More').",
                        max_length=50,
                    ),
                ),
                (
                    "url",
                    models.CharField(
                        help_text="URL or anchor (e.g., '/contact/' or '#contact').",
                        max_length=255,
                    ),
                ),
                (
                    "style",
                    models.CharField(
                        choices=[
                            ("primary", "Primary"),
                            ("outline", "Outline"),
                        ],
                        default="primary",
                        help_text="Button visual style.",
                        max_length=16,
                    ),
                ),
                (
                    "open_in_new_tab",
                    models.BooleanField(
                        default=False,
                        help_text="Open link in a new browser tab.",
                    ),
                ),
                (
                    "page",
                    modelcluster.fields.ParentalKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="hero_ctas",
                        to="sum_core_pages.homepage",
                    ),
                ),
            ],
            options={
                "verbose_name": "Hero CTA",
                "verbose_name_plural": "Hero CTAs",
                "ordering": ["sort_order"],
                "abstract": False,
            },
        ),
    ]
