"""
Name: Base Block Definitions
Path: core/sum_core/blocks/base.py
Purpose: Core block infrastructure and canonical page StreamField definition for sum_core.
Family: Imported by page models and block implementations across sum_core.
Dependencies: Wagtail blocks, rich text utilities.
"""

from sum_core.blocks.content import (
    ButtonGroupBlock,
    ComparisonBlock,
    DividerBlock,
    EditorialHeaderBlock,
    FeaturesListBlock,
    HeroBlock,
    ImageBlock,
    LegalSectionBlock,
    ManifestoBlock,
    PageHeaderBlock,
    PortfolioBlock,
    QuoteBlock,
    RichTextContentBlock,
    SocialProofQuoteBlock,
    SpacerBlock,
    TableOfContentsBlock,
    TeamMemberBlock,
    TimelineBlock,
    TrustStripBlock,
)
from sum_core.blocks.forms import ContactFormBlock, QuoteRequestFormBlock
from sum_core.blocks.gallery import FeaturedCaseStudyBlock, GalleryBlock
from sum_core.blocks.hero import HeroGradientBlock, HeroImageBlock
from sum_core.blocks.process_faq import FAQBlock, ProcessStepsBlock
from sum_core.blocks.services import ServiceCardsBlock, ServiceDetailBlock
from sum_core.blocks.testimonials import TestimonialsBlock
from sum_core.blocks.trust import StatsBlock
from sum_core.blocks.trust import TrustStripBlock as TrustStripLogosBlock
from wagtail import blocks
from wagtail.blocks import StreamBlock


class PageStreamBlock(StreamBlock):
    """
    Canonical StreamBlock for page content fields.

    This block defines the available content blocks that can be used in page
    body fields. It serves as the foundation for building pages through the
    Wagtail admin interface.
    """

    hero_image = HeroImageBlock(group="Hero")
    hero_gradient = HeroGradientBlock(group="Hero")
    service_cards = ServiceCardsBlock(group="Services")
    service_detail = ServiceDetailBlock(group="Services")
    testimonials = TestimonialsBlock(group="Sections")
    gallery = GalleryBlock(group="Sections")
    featured_case_study = FeaturedCaseStudyBlock(group="Sections")
    hero = HeroBlock(group="Legacy Sections")  # Keeping specific hero type separate
    trust_strip = TrustStripBlock(group="Sections")
    trust_strip_logos = TrustStripLogosBlock(group="Sections")
    stats = StatsBlock(group="Sections")
    process = ProcessStepsBlock(group="Sections")
    faq = FAQBlock(group="Sections")
    features = FeaturesListBlock(group="Sections")
    comparison = ComparisonBlock(group="Sections")
    manifesto = ManifestoBlock(group="Sections")
    portfolio = PortfolioBlock(group="Sections")
    team_members = TeamMemberBlock(group="Sections")
    timeline = TimelineBlock(group="Sections")

    # Content Blocks
    page_header = PageHeaderBlock(group="Page Content")
    editorial_header = EditorialHeaderBlock(group="Page Content")
    table_of_contents = TableOfContentsBlock(group="Page Content")
    legal_section = LegalSectionBlock(group="Page Content")
    content = RichTextContentBlock(group="Page Content")
    quote = QuoteBlock(group="Page Content")
    social_proof_quote = SocialProofQuoteBlock(group="Page Content")
    image_block = ImageBlock(group="Page Content")
    buttons = ButtonGroupBlock(group="Page Content")
    spacer = SpacerBlock(group="Page Content")
    divider = DividerBlock(group="Page Content")

    # Forms
    contact_form = ContactFormBlock(group="Forms")
    quote_request_form = QuoteRequestFormBlock(group="Forms")

    rich_text = blocks.RichTextBlock(
        label="Rich Text",
        help_text="Add formatted text content. Use H2-H4 for headings, avoid H1.",
        features=[
            "h2",
            "h3",
            "h4",  # Headings H2-H4 only, no H1
            "bold",
            "italic",  # Text formatting
            "link",  # Links
            "ol",
            "ul",  # Ordered and unordered lists
        ],
        required=False,
    )

    class Meta:
        """Meta configuration for PageStreamBlock."""

        icon = "doc-full"
        label = "Content Block"
        label_format = "Content: {label}"
        template = "sum_core/blocks/rich_text.html"  # Default template for rendering
