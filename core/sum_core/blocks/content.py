"""
Name: Content Blocks
Path: core/sum_core/blocks/content.py
Purpose: Define StructBlocks for rich content sections (Hero, Features, Portfolio, etc.).
Family: Used by StreamFields in pages.
"""

from django.core.exceptions import ValidationError
from django.utils.text import slugify
from sum_core.blocks.links import CtaLinkBlock
from sum_core.utils.links import validate_safe_link
from wagtail import blocks
from wagtail.blocks import StructBlockValidationError
from wagtail.images.blocks import ImageChooserBlock


class ButtonBlock(blocks.StructBlock):
    label = blocks.CharBlock(required=True)
    link = blocks.CharBlock(
        required=False, max_length=255, validators=[validate_safe_link]
    )
    page = blocks.PageChooserBlock(required=False)
    style = blocks.ChoiceBlock(
        choices=[
            ("btn-primary", "Primary"),
            ("btn-outline", "Outline"),
        ],
        default="btn-primary",
    )

    class Meta:
        template = "sum_core/blocks/button.html"
        icon = "placeholder"
        label = "Button"


class HeroBlock(blocks.StructBlock):
    status_text = blocks.CharBlock(
        required=False, help_text="e.g. Available for Q1 2025"
    )
    title = blocks.TextBlock(
        required=True,
        help_text="Main heading. Use html tags like <span class='italic-accent'> for styling.",
    )
    description = blocks.TextBlock(required=True)
    primary_cta = ButtonBlock(required=False)
    secondary_cta = ButtonBlock(required=False)
    image = ImageChooserBlock(required=True)
    float_card_label = blocks.CharBlock(
        required=False, help_text="e.g. Est. Annual Savings"
    )
    float_card_value = blocks.CharBlock(required=False, help_text="e.g. £2,450")

    class Meta:
        template = "sum_core/blocks/hero.html"
        icon = "image"
        label = "Hero Section"


class TrustItemBlock(blocks.StructBlock):
    text = blocks.CharBlock(required=True)

    class Meta:
        icon = "tick"
        label = "Trust Item"


class TrustStripBlock(blocks.StructBlock):
    items = blocks.ListBlock(TrustItemBlock())

    class Meta:
        template = "sum_core/blocks/trust_strip.html"
        icon = "list-ul"
        label = "Trust Strip"


class FeatureBlock(blocks.StructBlock):
    icon = blocks.CharBlock(required=False, help_text="Emoji or text icon")
    title = blocks.CharBlock(required=True)
    description = blocks.TextBlock(required=True)

    class Meta:
        icon = "tick-inverse"
        label = "Feature"


class FeaturesListBlock(blocks.StructBlock):
    heading = blocks.CharBlock(required=True)
    intro = blocks.TextBlock(required=False)
    features = blocks.ListBlock(FeatureBlock())

    class Meta:
        template = "sum_core/blocks/features_list.html"
        icon = "list-ul"
        label = "Features List"


class ComparisonBlock(blocks.StructBlock):
    accent_text = blocks.CharBlock(
        required=False, help_text="Small italic text above title"
    )
    title = blocks.CharBlock(required=True)
    description = blocks.TextBlock(required=True)
    image_before = ImageChooserBlock(required=True, help_text="Background/Before image")
    image_after = ImageChooserBlock(required=True, help_text="Foreground/After image")

    class Meta:
        template = "sum_core/blocks/comparison.html"
        icon = "image"
        label = "Comparison Slider"


class PortfolioItemBlock(blocks.StructBlock):
    image = ImageChooserBlock(required=True)
    alt_text = blocks.CharBlock(
        required=True, max_length=255, help_text="Alt text for accessibility."
    )
    title = blocks.CharBlock(required=True)
    category = blocks.CharBlock(
        required=False,
        max_length=50,
        help_text="Optional filter label, e.g. Residential, Commercial.",
    )
    location = blocks.CharBlock(required=False, help_text="e.g. Kensington, London")
    services = blocks.CharBlock(
        required=False, help_text="e.g. Design • Build • Install"
    )
    constraint = blocks.CharBlock(max_length=100, required=False)
    material = blocks.CharBlock(max_length=100, required=False)
    outcome = blocks.CharBlock(max_length=100, required=False)
    link_url = blocks.CharBlock(
        required=False,
        max_length=255,
        validators=[validate_safe_link],
        help_text="Link to full project case study",
    )

    class Meta:
        icon = "image"
        label = "Project Item"


class PortfolioBlock(blocks.StructBlock):
    eyebrow = blocks.CharBlock(required=False, help_text="Small label above heading")
    heading = blocks.RichTextBlock(
        required=True,
        features=["bold", "italic"],
        help_text="Main heading. Use italics for accent styling.",
    )
    intro = blocks.TextBlock(required=False, help_text="Short lead text")
    view_all_link = blocks.CharBlock(
        required=False,
        max_length=255,
        validators=[validate_safe_link],
        label="View All Link",
    )
    view_all_label = blocks.CharBlock(
        required=False, max_length=50, label="View All Label"
    )
    items = blocks.ListBlock(PortfolioItemBlock(), min_num=1, max_num=12)

    def get_context(self, value, parent_context=None):
        context = super().get_context(value, parent_context=parent_context)
        items = list(value.get("items", []))
        categories = []
        for item in items:
            category = (item.get("category") or "").strip()
            if category and category not in categories:
                categories.append(category)

        request = parent_context.get("request") if parent_context else None
        active_category = ""
        if request:
            active_category = request.GET.get("category", "").strip()

        if active_category:
            filtered_items = [
                item
                for item in items
                if (item.get("category") or "").strip()
                and slugify((item.get("category") or "").strip()) == active_category
            ]
        else:
            filtered_items = items

        context.update(
            {
                "categories": categories,
                "active_category": active_category,
                "filtered_items": filtered_items,
            }
        )
        return context

    class Meta:
        template = "sum_core/blocks/portfolio.html"
        icon = "grip"
        label = "Portfolio Gallery"


class TeamMemberItemBlock(blocks.StructBlock):
    photo = ImageChooserBlock(
        required=True, help_text="Team member headshot or portrait."
    )
    alt_text = blocks.CharBlock(
        required=True, max_length=255, help_text="Alt text for accessibility."
    )
    name = blocks.CharBlock(required=True, help_text="Full name.")
    role = blocks.CharBlock(required=False, help_text="Role or title.")
    bio = blocks.TextBlock(required=False, help_text="Short bio (1-2 sentences).")
    overlay_quote = blocks.CharBlock(
        required=False,
        help_text="Optional short overlay quote displayed on the photo.",
    )

    class Meta:
        icon = "user"
        label = "Team Member"


class TeamMemberBlock(blocks.StructBlock):
    eyebrow = blocks.CharBlock(
        max_length=100, required=False, help_text="Small label above heading"
    )
    heading = blocks.RichTextBlock(
        required=False,
        features=["bold", "italic"],
        help_text="Section heading. Use italics for accent styling.",
    )
    badge_label = blocks.CharBlock(
        required=False,
        max_length=100,
        help_text="Optional badge label, e.g. Combined Experience.",
    )
    badge_value = blocks.CharBlock(
        required=False,
        max_length=100,
        help_text="Optional badge value, e.g. 142 Years.",
    )
    members = blocks.ListBlock(TeamMemberItemBlock(), min_num=1, max_num=12)

    class Meta:
        template = "sum_core/blocks/team_members.html"
        icon = "group"
        label = "Team Members"


class TimelineItemBlock(blocks.StructBlock):
    date_label = blocks.CharBlock(
        required=True,
        help_text="Short date label for the milestone (e.g. 2020, Q3 2024)",
    )
    heading = blocks.CharBlock(required=True, help_text="Milestone heading")
    body = blocks.RichTextBlock(
        required=True,
        features=["bold", "italic", "link", "ol", "ul"],
        help_text="Supporting copy for the milestone",
    )
    image = ImageChooserBlock(required=False, help_text="Optional supporting image")
    alt_text = blocks.CharBlock(
        required=False,
        max_length=255,
        help_text="Alt text for the image (required if image is set).",
    )

    class Meta:
        icon = "date"
        label = "Timeline Item"

    def clean(self, value):
        cleaned = super().clean(value)
        image = cleaned.get("image")
        alt_text = (cleaned.get("alt_text") or "").strip()
        if image and not alt_text:
            raise StructBlockValidationError(
                block_errors={
                    "alt_text": ValidationError("Alt text is required with an image.")
                }
            )
        if not image:
            cleaned["alt_text"] = ""
        return cleaned


class TimelineBlock(blocks.StructBlock):
    eyebrow = blocks.CharBlock(
        required=False, help_text="Optional accent label above the heading"
    )
    heading = blocks.RichTextBlock(
        required=False,
        features=["italic", "bold"],
        help_text="Timeline section heading",
    )
    intro = blocks.RichTextBlock(
        required=False,
        features=["bold", "italic", "link"],
        help_text="Short intro or description for the timeline",
    )
    items = blocks.ListBlock(TimelineItemBlock(), min_num=1)

    class Meta:
        template = "sum_core/blocks/timeline.html"
        icon = "time"
        label = "Timeline"
        group = "Sections"


class ManifestoBlock(blocks.StructBlock):
    """
    Centered prose section used for "manifesto"-style content blocks.

    Designed to match Theme A wireframes: eyebrow + heading + rich prose + optional quote.
    """

    eyebrow = blocks.CharBlock(
        max_length=100,
        required=False,
        help_text="Optional accent label above the heading (e.g. “The Manifesto”).",
    )

    heading = blocks.RichTextBlock(
        required=True,
        features=["italic", "bold"],
        help_text="Main heading. Use Italic for accent styling.",
    )

    body = blocks.RichTextBlock(
        required=True,
        features=["bold", "italic", "link", "ol", "ul"],
        help_text="Main prose content. Use paragraphs and lists.",
    )

    quote = blocks.TextBlock(
        required=False,
        help_text="Optional pull quote shown beneath the prose content.",
    )

    class Meta:
        template = "sum_core/blocks/manifesto.html"
        icon = "doc-full"
        label = "Manifesto"


class FounderLetterBlock(blocks.StructBlock):
    """
    Personal founder letter section with portrait, quote heading, and signature.
    """

    image = ImageChooserBlock(required=True, help_text="Founder portrait.")
    alt_text = blocks.CharBlock(
        required=True, max_length=255, help_text="Alt text for the image."
    )
    image_name = blocks.CharBlock(required=True, help_text="Name shown on image badge.")
    image_role = blocks.CharBlock(required=True, help_text="Role shown on image badge.")
    quote_heading = blocks.RichTextBlock(
        required=True,
        features=["italic", "bold"],
        help_text="Large quote-style heading.",
    )
    body = blocks.RichTextBlock(
        required=True,
        features=["bold", "italic", "link", "ol", "ul"],
        help_text="Founder letter body content.",
    )
    signature_name = blocks.CharBlock(
        required=False, help_text="Signature name shown beneath the letter."
    )
    signature_label = blocks.CharBlock(
        required=False, help_text="Optional secondary label under the signature."
    )

    class Meta:
        template = "sum_core/blocks/founder_letter.html"
        icon = "user"
        label = "Founder Letter"


class InPlainEnglishBlock(blocks.StructBlock):
    """
    Callout box for values, principles, or plain-language summaries.
    """

    label = blocks.CharBlock(
        required=False,
        max_length=100,
        default="In Plain English",
        help_text="Optional callout label.",
    )
    heading = blocks.CharBlock(required=False, help_text="Optional heading.")
    body = blocks.RichTextBlock(
        required=True,
        features=["bold", "italic", "link"],
        help_text="Callout body copy.",
    )
    icon = blocks.ChoiceBlock(
        choices=[
            ("info", "Info"),
            ("quote", "Quote"),
            ("none", "None"),
        ],
        default="info",
        required=False,
        help_text="Select the callout icon style.",
    )

    class Meta:
        template = "sum_core/blocks/in_plain_english.html"
        icon = "doc-full"
        label = "In Plain English"


# --- M2-008 New Content Blocks ---


class PageHeaderBlock(blocks.StructBlock):
    """
    Interior page header with optional eyebrow, heading, and intro.
    """

    eyebrow = blocks.CharBlock(
        required=False, help_text="Optional label above the heading."
    )
    heading = blocks.RichTextBlock(
        required=False,
        features=["italic", "bold"],
        help_text="Main heading. Use italics for accent styling.",
    )
    intro = blocks.TextBlock(required=False, help_text="Short supporting intro text.")

    class Meta:
        icon = "title"
        label = "Page Header"
        template = "sum_core/blocks/page_header.html"


class RichTextContentBlock(blocks.StructBlock):
    """
    A flexible block for general content sections.
    """

    align = blocks.ChoiceBlock(
        choices=[
            ("left", "Left"),
            ("center", "Center"),
        ],
        default="left",
        required=False,
    )

    body = blocks.RichTextBlock(
        features=["h2", "h3", "h4", "bold", "italic", "link", "ol", "ul", "hr"],
        required=True,
    )

    class Meta:
        icon = "doc-full"
        label = "Content (Rich Text)"
        template = "sum_core/blocks/content_richtext.html"


class LeadParagraphBlock(blocks.StructBlock):
    """
    Lead paragraph for editorial content.
    """

    body = blocks.RichTextBlock(
        features=["bold", "italic", "link"],
        required=True,
        help_text="Lead paragraph copy. Use italics to highlight opening phrases.",
    )

    class Meta:
        icon = "pilcrow"
        label = "Lead Paragraph"
        template = "sum_core/blocks/lead_paragraph.html"


class ArticleSectionBlock(blocks.StructBlock):
    """
    Editorial section with optional eyebrow/heading and body copy.
    """

    anchor = blocks.RegexBlock(
        regex=r"^[a-z][a-z0-9-]*$",
        required=False,
        help_text=(
            "Optional anchor ID used for in-page links (lowercase letters, "
            "numbers, and hyphens only)."
        ),
    )

    align = blocks.ChoiceBlock(
        choices=[
            ("left", "Left"),
            ("center", "Center"),
        ],
        default="left",
        required=False,
    )

    eyebrow = blocks.CharBlock(required=False, help_text="Optional eyebrow label.")

    heading = blocks.RichTextBlock(
        required=False,
        features=["italic", "bold"],
        help_text="Section heading. Use italics for accent styling.",
    )

    subheading = blocks.TextBlock(
        required=False,
        help_text="Optional subheading line under the main heading.",
    )

    subheading_secondary = blocks.TextBlock(
        required=False,
        help_text="Optional second subheading line.",
    )

    drop_cap = blocks.BooleanBlock(
        required=False,
        default=False,
        help_text="Style the first paragraph with a drop cap.",
    )

    body = blocks.RichTextBlock(
        features=["h3", "h4", "bold", "italic", "link", "ol", "ul", "hr"],
        required=True,
    )

    class Meta:
        icon = "doc-full-inverse"
        label = "Article Section"
        template = "sum_core/blocks/article_section.html"


class NumberedStepItemBlock(blocks.StructBlock):
    """
    Single step for numbered protocol lists.
    """

    title = blocks.CharBlock(required=True)
    description = blocks.TextBlock(required=True)

    class Meta:
        icon = "list-ol"
        label = "Step"


class NumberedStepsBlock(blocks.StructBlock):
    """
    Numbered list of steps for editorial content.
    """

    steps = blocks.ListBlock(NumberedStepItemBlock(), min_num=1, max_num=8)

    class Meta:
        icon = "list-ol"
        label = "Numbered Steps"
        template = "sum_core/blocks/numbered_steps.html"


class EditorialHeaderBlock(blocks.StructBlock):
    """
    A text-heavy header for editorial pages/blog posts.
    """

    anchor = blocks.RegexBlock(
        regex=r"^[a-z][a-z0-9-]*$",
        required=False,
        help_text=(
            "Optional anchor ID used for in-page links (lowercase letters, "
            "numbers, and hyphens only)."
        ),
    )

    align = blocks.ChoiceBlock(
        choices=[
            ("left", "Left"),
            ("center", "Center"),
        ],
        default="center",
        required=False,
    )

    eyebrow = blocks.CharBlock(required=False, help_text="e.g. Case Study")

    heading = blocks.RichTextBlock(
        required=True,
        features=["italic", "bold"],
        help_text="Main title. Use italics for accent styling.",
    )

    class Meta:
        icon = "title"
        label = "Editorial Header"
        template = "sum_core/blocks/content_editorial_header.html"


class QuoteBlock(blocks.StructBlock):
    """
    Editorial quote / pull-quote block.
    """

    quote = blocks.TextBlock(
        label="Quote Text", help_text="Short editorial quote (1-3 sentences)."
    )
    author = blocks.CharBlock(required=False)
    role = blocks.CharBlock(
        required=False, help_text="Role/description, e.g. Property Owner"
    )

    class Meta:
        icon = "openquote"
        label = "Editorial Quote"
        template = "sum_core/blocks/content_quote.html"


class SocialProofQuoteBlock(blocks.StructBlock):
    """
    Editorial quote with optional social proof metadata.
    """

    quote = blocks.TextBlock(
        label="Quote Text", help_text="Editorial quote (1-3 sentences)."
    )
    logo = ImageChooserBlock(required=False, help_text="Optional company logo.")
    author = blocks.CharBlock(required=False)
    role = blocks.CharBlock(required=False)
    company = blocks.CharBlock(required=False)

    class Meta:
        icon = "openquote"
        label = "Social Proof Quote"
        template = "sum_core/blocks/content_social_proof_quote.html"


class ImageBlock(blocks.StructBlock):
    """
    Cinematic image block with caption.
    """

    image = ImageChooserBlock(required=True)
    alt_text = blocks.CharBlock(required=True, max_length=255)
    caption = blocks.CharBlock(
        required=False, help_text="Short caption under the image."
    )
    full_width = blocks.BooleanBlock(
        required=False, default=False, help_text="Stretch to full-width container."
    )

    class Meta:
        icon = "image"
        label = "Image"
        template = "sum_core/blocks/content_image.html"


class ContentButtonBlock(blocks.StructBlock):
    """
    Single button definition for use in ButtonGroupBlock.
    """

    label = blocks.CharBlock()
    url = blocks.CharBlock(max_length=255, validators=[validate_safe_link])
    style = blocks.ChoiceBlock(
        choices=[
            ("primary", "Primary"),
            ("secondary", "Secondary"),
        ],
        default="primary",
    )

    class Meta:
        icon = "link"
        label = "Button"


class ButtonGroupBlock(blocks.StructBlock):
    """
    Group of buttons (CTAs).
    """

    alignment = blocks.ChoiceBlock(
        choices=[
            ("left", "Left"),
            ("center", "Center"),
            ("right", "Right"),
        ],
        default="left",
    )

    buttons = blocks.ListBlock(ContentButtonBlock(), min_num=1, max_num=3)

    class Meta:
        icon = "snippet"
        label = "Button Group"
        template = "sum_core/blocks/content_buttons.html"


class CallToActionBlock(blocks.StructBlock):
    """
    Reusable editorial CTA with heading, body, and buttons.
    """

    eyebrow = blocks.CharBlock(required=False, help_text="Optional eyebrow label.")
    heading = blocks.RichTextBlock(
        required=True,
        features=["italic", "bold"],
        help_text="CTA heading. Use italics for accent styling.",
    )
    body = blocks.RichTextBlock(
        required=True,
        features=["bold", "italic", "link"],
        help_text="Supporting CTA copy.",
    )
    buttons = blocks.ListBlock(CtaLinkBlock(), min_num=1, max_num=2)

    class Meta:
        icon = "pick"
        label = "Call To Action"
        template = "sum_core/blocks/call_to_action.html"


class SpacerBlock(blocks.StructBlock):
    """
    Vertical spacer for rhythm.
    """

    size = blocks.ChoiceBlock(
        choices=[
            ("small", "Small (24px)"),
            ("medium", "Medium (40px)"),
            ("large", "Large (64px)"),
            ("xlarge", "X-Large (96px)"),
        ],
        default="medium",
    )

    class Meta:
        icon = "horizontalrule"
        label = "Spacer"
        template = "sum_core/blocks/content_spacer.html"


class DividerBlock(blocks.StructBlock):
    """
    Horizontal divider line.
    """

    style = blocks.ChoiceBlock(
        choices=[
            ("muted", "Muted"),
            ("strong", "Strong"),
            ("accent", "Accent"),
        ],
        default="muted",
    )

    class Meta:
        icon = "horizontalrule"
        label = "Divider"
        template = "sum_core/blocks/content_divider.html"


class TableOfContentsItemBlock(blocks.StructBlock):
    """
    Single entry for the TableOfContentsBlock.
    """

    label = blocks.CharBlock(required=True, help_text="Link label shown in the TOC.")
    anchor = blocks.CharBlock(
        required=True,
        help_text="Anchor ID (e.g. terms-intro) that matches a LegalSectionBlock.",
    )

    class Meta:
        icon = "link"
        label = "TOC Item"


class TableOfContentsBlock(blocks.StructBlock):
    """
    Table of contents for legal pages.
    """

    items = blocks.ListBlock(
        TableOfContentsItemBlock(),
        min_num=1,
        help_text="Add links that point to anchors on the same page.",
    )

    class Meta:
        icon = "list-ol"
        label = "Table of Contents"
        template = "sum_core/blocks/table_of_contents.html"


class LegalSectionRichTextBlock(blocks.StructBlock):
    """
    Rich text content inside a legal section.
    """

    body = blocks.RichTextBlock(
        required=True,
        features=["h3", "h4", "bold", "italic", "link", "ol", "ul"],
        help_text="Section content. Use H3/H4 for nested headings; avoid H1/H2.",
    )

    class Meta:
        icon = "doc-full"
        label = "Rich Text"


class LegalSectionContentBlock(blocks.StreamBlock):
    """
    Structured content items inside a legal section.
    """

    rich_text = LegalSectionRichTextBlock()
    in_plain_english = InPlainEnglishBlock()

    class Meta:
        icon = "doc-full"
        label = "Legal Section Content"


class LegalSectionBlock(blocks.StructBlock):
    """
    Anchored legal section with heading and structured content.
    """

    anchor = blocks.RegexBlock(
        regex=r"^[a-z][a-z0-9-]*$",
        required=True,
        error_messages={
            "invalid": "Anchor must start with a letter and contain only lowercase letters, numbers, and hyphens."
        },
        help_text="Anchor ID used for in-page links (lowercase letters, numbers, hyphens only).",
    )
    heading = blocks.CharBlock(required=True, help_text="Section heading.")
    content = LegalSectionContentBlock(
        required=True,
        help_text="Add rich text and callouts for this section.",
    )

    class Meta:
        icon = "doc-full"
        label = "Legal Section"
        template = "sum_core/blocks/legal_section.html"
