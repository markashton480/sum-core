"""
Name: Blocks Package Init
Path: core/sum_core/blocks/__init__.py
Purpose: Namespace for reusable block definitions within sum_core.
Family: Imported by sum_core consumers and test_project when implementing page content.
Dependencies: PageStreamBlock from base module.
"""

from .base import BodyStreamBlock, PageStreamBlock
from .blog import BlogPostStreamBlock
from .content import (
    ArticleSectionBlock,
    ButtonBlock,
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
    LongformArticleBlock,
    LongformHeadingAnchorOverrideBlock,
    ManifestoBlock,
    NumberedStepsBlock,
    PageHeaderBlock,
    PortfolioBlock,
    QuoteBlock,
    RichTextContentBlock,
    SocialProofQuoteBlock,
    SpacerBlock,
    TableOfContentsBlock,
    TableOfContentsItemBlock,
    TeamMemberBlock,
    TeamMemberItemBlock,
    TimelineBlock,
    TimelineItemBlock,
)
from .content import TrustStripBlock as TextTrustStripBlock
from .forms import (
    ContactFormBlock,
    DynamicFormBlock,
    LeadMagnetBlock,
    QuoteRequestFormBlock,
)
from .gallery import (
    FeaturedCaseStudyBlock,
    GalleryBlock,
    GalleryImageBlock,
    ProvenancePlateBlock,
)
from .hero import HeroCTABlock, HeroGradientBlock, HeroImageBlock
from .links import (
    LINK_TYPE_CHOICES,
    CtaLinkBlock,
    UniversalLinkBlock,
    UniversalLinkValue,
)
from .process_faq import FAQBlock, ProcessStepsBlock
from .services import (
    AccreditationPolicyCardBlock,
    AccreditationsAndWarrantyBlock,
    CenteredCTASectionBlock,
    ProcessTimelineBlock,
    ProcessTimelineLeadMagnetBlock,
    ServiceCardItemBlock,
    ServiceCardsBlock,
    ServiceDetailBlock,
    ServiceIconGridBlock,
    ServiceIconGridItemBlock,
    ValuePropositionBlock,
    ValuePropositionStatBlock,
)
from .testimonials import TestimonialBlock, TestimonialsBlock
from .trust import StatItemBlock, StatsBlock
from .trust import TrustStripBlock as TrustStripLogosBlock
from .trust import TrustStripItemBlock

__all__ = [
    "PageStreamBlock",
    "BodyStreamBlock",
    "BlogPostStreamBlock",
    "HeroImageBlock",
    "HeroGradientBlock",
    "HeroCTABlock",
    "HeroBlock",
    "TextTrustStripBlock",
    "TrustStripLogosBlock",
    "TrustStripItemBlock",
    "FeaturesListBlock",
    "ComparisonBlock",
    "FounderLetterBlock",
    "ManifestoBlock",
    "InPlainEnglishBlock",
    "PortfolioBlock",
    "ServiceCardsBlock",
    "ServiceCardItemBlock",
    "ServiceDetailBlock",
    "AccreditationsAndWarrantyBlock",
    "AccreditationPolicyCardBlock",
    "CenteredCTASectionBlock",
    "ServiceIconGridBlock",
    "ServiceIconGridItemBlock",
    "ProcessTimelineBlock",
    "ProcessTimelineLeadMagnetBlock",
    "ValuePropositionBlock",
    "ValuePropositionStatBlock",
    "TestimonialsBlock",
    "TestimonialBlock",
    "GalleryBlock",
    "GalleryImageBlock",
    "FeaturedCaseStudyBlock",
    "ProvenancePlateBlock",
    "StatItemBlock",
    "StatsBlock",
    "ProcessStepsBlock",
    "FAQBlock",
    "TimelineBlock",
    "TimelineItemBlock",
    "RichTextContentBlock",
    "LeadParagraphBlock",
    "LongformArticleBlock",
    "LongformHeadingAnchorOverrideBlock",
    "ArticleSectionBlock",
    "NumberedStepsBlock",
    "CallToActionBlock",
    "PageHeaderBlock",
    "EditorialHeaderBlock",
    "TableOfContentsBlock",
    "TableOfContentsItemBlock",
    "TeamMemberBlock",
    "TeamMemberItemBlock",
    "LegalSectionBlock",
    "QuoteBlock",
    "SocialProofQuoteBlock",
    "ImageBlock",
    "ButtonBlock",
    "ButtonGroupBlock",
    "SpacerBlock",
    "DividerBlock",
    "ContactFormBlock",
    "DynamicFormBlock",
    "QuoteRequestFormBlock",
    "LeadMagnetBlock",
    "UniversalLinkBlock",
    "UniversalLinkValue",
    "LINK_TYPE_CHOICES",
    "CtaLinkBlock",
]
