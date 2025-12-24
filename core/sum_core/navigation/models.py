"""
Name: Navigation Site Settings Models
Path: core/sum_core/navigation/models.py
Purpose: Define HeaderNavigation and FooterNavigation site settings models
         for managing site-wide navigation configuration.
Family: Navigation System (Phase 1: Foundation)
Dependencies: wagtail.contrib.settings, wagtail.fields, wagtail.admin.panels

Models:
    - HeaderNavigation: Site-level settings for header menu items and CTAs
    - FooterNavigation: Site-level settings for footer links and social media
"""

from django.db import models
from sum_core.blocks import UniversalLinkBlock
from sum_core.navigation.blocks import FooterLinkSectionBlock, MenuItemBlock
from wagtail import blocks
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.contrib.settings.models import BaseSiteSetting, register_setting
from wagtail.fields import StreamField

# =============================================================================
# Custom StreamBlocks for Constraints
# =============================================================================


class MenuItemsStreamBlock(blocks.StreamBlock):
    """
    StreamBlock for top-level menu items with max 8 constraint.

    Enforces maximum 8 menu items in the header navigation.
    """

    item = MenuItemBlock()

    class Meta:
        max_num = 8


class FooterSectionsStreamBlock(blocks.StreamBlock):
    """
    StreamBlock for footer link sections with min/max constraints.

    Enforces minimum 2 and maximum 4 footer sections.
    """

    section = FooterLinkSectionBlock()

    class Meta:
        min_num = 2
        max_num = 4


class SingleLinkStreamBlock(blocks.StreamBlock):
    """
    StreamBlock for a single optional link (0-1 items).

    Used for CTA links where only one link is allowed.
    """

    link = UniversalLinkBlock()

    class Meta:
        min_num = 0
        max_num = 1


# =============================================================================
# HeaderNavigation Site Setting
# =============================================================================


@register_setting(icon="list-ul")
class HeaderNavigation(BaseSiteSetting):
    """
    Site-level settings for header navigation.

    Configures:
        - Main navigation menu items (max 8)
        - Phone visibility in header
        - Desktop CTA button
        - Mobile sticky CTA bar

    Admin panels are grouped for better editor UX:
        - Main Navigation: menu_items, show_phone_in_header
        - Header CTA: header_cta_enabled, header_cta_text, header_cta_link
        - Mobile Sticky CTA: mobile_cta_enabled, mobile_cta_phone_enabled,
                           mobile_cta_button_enabled, mobile_cta_button_text,
                           mobile_cta_button_link
    """

    # =========================================================================
    # Main Navigation Fields
    # =========================================================================

    menu_items = StreamField(
        MenuItemsStreamBlock(),
        blank=True,
        use_json_field=True,
        help_text="Top-level menu items (max 8).",
    )

    show_phone_in_header = models.BooleanField(
        default=True,
        help_text="Display phone number in the header.",
    )

    # =========================================================================
    # Header CTA Fields
    # =========================================================================

    header_cta_enabled = models.BooleanField(
        default=True,
        help_text="Enable the header CTA button.",
    )

    header_cta_text = models.CharField(
        max_length=50,
        blank=True,
        default="Get a Quote",
        help_text="Text for the header CTA button (max 50 characters).",
    )

    header_cta_link = StreamField(
        SingleLinkStreamBlock(),
        blank=True,
        use_json_field=True,
        help_text="Link destination for header CTA (optional, max 1).",
    )

    # =========================================================================
    # Mobile Sticky CTA Fields
    # =========================================================================

    mobile_cta_enabled = models.BooleanField(
        default=True,
        help_text="Enable the mobile sticky CTA bar.",
    )

    mobile_cta_phone_enabled = models.BooleanField(
        default=True,
        help_text="Show phone button in mobile CTA bar.",
    )

    mobile_cta_button_enabled = models.BooleanField(
        default=True,
        help_text="Show action button in mobile CTA bar.",
    )

    mobile_cta_button_text = models.CharField(
        max_length=50,
        blank=True,
        default="Get a Quote",
        help_text="Text for mobile CTA button (max 50 characters).",
    )

    mobile_cta_button_link = StreamField(
        SingleLinkStreamBlock(),
        blank=True,
        use_json_field=True,
        help_text="Link destination for mobile CTA button (optional, max 1).",
    )

    # =========================================================================
    # Panels
    # =========================================================================

    panels = [
        MultiFieldPanel(
            [
                FieldPanel("menu_items"),
                FieldPanel("show_phone_in_header"),
            ],
            heading="Main Navigation",
        ),
        MultiFieldPanel(
            [
                FieldPanel("header_cta_enabled"),
                FieldPanel("header_cta_text"),
                FieldPanel("header_cta_link"),
            ],
            heading="Header CTA",
        ),
        MultiFieldPanel(
            [
                FieldPanel("mobile_cta_enabled"),
                FieldPanel("mobile_cta_phone_enabled"),
                FieldPanel("mobile_cta_button_enabled"),
                FieldPanel("mobile_cta_button_text"),
                FieldPanel("mobile_cta_button_link"),
            ],
            heading="Mobile Sticky CTA",
        ),
    ]

    class Meta:
        verbose_name = "Header Navigation"


# =============================================================================
# FooterNavigation Site Setting
# =============================================================================


@register_setting(icon="doc-full")
class FooterNavigation(BaseSiteSetting):
    """
    Site-level settings for footer navigation.

    Configures:
        - Footer tagline
        - Link sections (min 2, max 4)
        - Service area auto-population toggle
        - Social media links
        - Copyright text

    Admin panels are grouped for better editor UX:
        - Footer Content: tagline, link_sections, auto_service_areas
        - Social Links: social_facebook, social_instagram, etc.
        - Copyright: copyright_text
    """

    # =========================================================================
    # Footer Content Fields
    # =========================================================================

    tagline = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text=(
            "Optional override. Leave blank to use Site Settings tagline. "
            "(max 255 characters)"
        ),
    )

    link_sections = StreamField(
        FooterSectionsStreamBlock(),
        blank=True,
        use_json_field=True,
        help_text="Footer link sections (min 2, max 4 sections).",
    )

    auto_service_areas = models.BooleanField(
        default=False,
        help_text="Automatically populate service areas section (logic TBD).",
    )

    # =========================================================================
    # Social Links Fields
    # =========================================================================
    #
    # Note: TikTok is intentionally NOT included here. TikTok URLs are always
    # sourced from SiteSettings (Branding) to maintain a single source of truth.
    # See navigation/services.py::get_effective_footer_settings for details.
    #

    social_facebook = models.URLField(
        blank=True,
        default="",
        help_text="Optional override. Leave blank to use Site Settings value.",
    )

    social_instagram = models.URLField(
        blank=True,
        default="",
        help_text="Optional override. Leave blank to use Site Settings value.",
    )

    social_linkedin = models.URLField(
        blank=True,
        default="",
        help_text="Optional override. Leave blank to use Site Settings value.",
    )

    social_youtube = models.URLField(
        blank=True,
        default="",
        help_text="Optional override. Leave blank to use Site Settings value.",
    )

    social_x = models.URLField(
        blank=True,
        default="",
        help_text="Optional override. Leave blank to use Site Settings value.",
    )

    # =========================================================================
    # Copyright Fields
    # =========================================================================

    copyright_text = models.CharField(
        max_length=255,
        blank=True,
        default="© {year} {company_name}. All rights reserved.",
        help_text=(
            "Copyright text. Use {year} and {company_name} as placeholders "
            "(max 255 characters)."
        ),
    )

    # =========================================================================
    # Panels
    # =========================================================================

    panels = [
        MultiFieldPanel(
            [
                FieldPanel("tagline"),
                FieldPanel("link_sections"),
                FieldPanel("auto_service_areas"),
            ],
            heading="Footer Content",
        ),
        MultiFieldPanel(
            [
                FieldPanel("social_facebook"),
                FieldPanel("social_instagram"),
                FieldPanel("social_linkedin"),
                FieldPanel("social_youtube"),
                FieldPanel("social_x"),
            ],
            heading="Social Links",
        ),
        MultiFieldPanel(
            [
                FieldPanel("copyright_text"),
            ],
            heading="Copyright",
        ),
    ]

    class Meta:
        verbose_name = "Footer Navigation"
