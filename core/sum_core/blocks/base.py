"""
Name: Base Block Definitions
Path: core/sum_core/blocks/base.py
Purpose: Core block infrastructure and canonical page StreamField definition for sum_core.
Family: Imported by page models and block implementations across sum_core.
Dependencies: Wagtail blocks, rich text utilities.
"""

import itertools

from sum_core.blocks.content import (
    ArticleSectionBlock,
    ButtonGroupBlock,
    CallToActionBlock,
    ComparisonBlock,
    DividerBlock,
    EditorialHeaderBlock,
    FeaturesListBlock,
    FounderLetterBlock,
    HeroBlock,
    ImageBlock,
    InPlainEnglishBlock,
    LeadParagraphBlock,
    LegalSectionBlock,
    ManifestoBlock,
    NumberedStepsBlock,
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
from sum_core.blocks.forms import (
    ContactFormBlock,
    DynamicFormBlock,
    LeadMagnetBlock,
    QuoteRequestFormBlock,
)
from sum_core.blocks.gallery import (
    FeaturedCaseStudyBlock,
    GalleryBlock,
    ProvenancePlateBlock,
)
from sum_core.blocks.hero import HeroGradientBlock, HeroImageBlock
from sum_core.blocks.process_faq import FAQBlock, ProcessStepsBlock
from sum_core.blocks.services import (
    AccreditationsAndWarrantyBlock,
    CenteredCTASectionBlock,
    ProcessTimelineBlock,
    ProcessTimelineLeadMagnetBlock,
    ServiceCardsBlock,
    ServiceDetailBlock,
    ServiceIconGridBlock,
    ValuePropositionBlock,
)
from sum_core.blocks.testimonials import TestimonialsBlock
from sum_core.blocks.trust import StatsBlock
from sum_core.blocks.trust import TrustStripBlock as TrustStripLogosBlock
from sum_core.pages.chrome import HEADER_BLOCK_TYPES
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
    service_icon_grid = ServiceIconGridBlock(group="Sections")
    accreditations_and_warranty = AccreditationsAndWarrantyBlock(group="Sections")
    value_proposition = ValuePropositionBlock(group="Sections")
    process_timeline = ProcessTimelineBlock(group="Sections")
    process_timeline_lead_magnet = ProcessTimelineLeadMagnetBlock(
        group="Legacy Sections"
    )
    centered_cta_section = CenteredCTASectionBlock(group="Sections")
    testimonials = TestimonialsBlock(group="Sections")
    gallery = GalleryBlock(group="Sections")
    featured_case_study = FeaturedCaseStudyBlock(group="Sections")
    provenance_plate = ProvenancePlateBlock(group="Sections")
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
    founder_letter = FounderLetterBlock(group="Sections")
    in_plain_english = InPlainEnglishBlock(group="Sections")
    timeline = TimelineBlock(group="Sections")

    # Content Blocks
    page_header = PageHeaderBlock(group="Page Content")
    lead_paragraph = LeadParagraphBlock(group="Page Content")
    article_section = ArticleSectionBlock(group="Page Content")
    editorial_header = EditorialHeaderBlock(group="Page Content")
    table_of_contents = TableOfContentsBlock(group="Page Content")
    legal_section = LegalSectionBlock(group="Page Content")
    content = RichTextContentBlock(group="Page Content")
    quote = QuoteBlock(group="Page Content")
    social_proof_quote = SocialProofQuoteBlock(group="Page Content")
    image_block = ImageBlock(group="Page Content")
    buttons = ButtonGroupBlock(group="Page Content")
    numbered_steps = NumberedStepsBlock(group="Page Content")
    spacer = SpacerBlock(group="Page Content")
    divider = DividerBlock(group="Page Content")
    call_to_action = CallToActionBlock(group="Page Content")

    # Forms
    contact_form = ContactFormBlock(group="Forms")
    quote_request_form = QuoteRequestFormBlock(group="Forms")
    dynamic_form = DynamicFormBlock(group="Forms")
    lead_magnet = LeadMagnetBlock(group="Forms")

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
        template="sum_core/blocks/rich_text.html",
    )

    class Meta:
        """Meta configuration for PageStreamBlock."""

        icon = "doc-full"
        label = "Content Block"
        label_format = "Content: {label}"


class BodyStreamBlock(PageStreamBlock):
    """StreamBlock for page bodies without hero/header blocks."""

    def grouped_child_blocks(self):
        """Return chooser-visible blocks without mutating stored block defs."""
        visible_blocks = [
            block
            for name, block in self.child_blocks.items()
            if name not in HEADER_BLOCK_TYPES
        ]
        visible_blocks = sorted(visible_blocks, key=lambda block: block.meta.group)
        return itertools.groupby(visible_blocks, key=lambda block: block.meta.group)
