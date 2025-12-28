"""
Name: Blocks Package Init
Path: core/sum_core/blocks/__init__.py
Purpose: Namespace for reusable block definitions within sum_core.
Family: Imported by sum_core consumers and test_project when implementing page content.
Dependencies: PageStreamBlock from base module.
"""

from .base import PageStreamBlock
from .content import (
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
    TableOfContentsItemBlock,
    TimelineBlock,
    TimelineItemBlock,
    TrustStripBlock,
)
from .forms import ContactFormBlock, DynamicFormBlock, QuoteRequestFormBlock
from .gallery import FeaturedCaseStudyBlock, GalleryBlock, GalleryImageBlock
from .hero import HeroCTABlock, HeroGradientBlock, HeroImageBlock
from .links import LINK_TYPE_CHOICES, UniversalLinkBlock, UniversalLinkValue
from .process_faq import FAQBlock, ProcessStepsBlock
from .services import ServiceCardItemBlock, ServiceCardsBlock, ServiceDetailBlock
from .testimonials import TestimonialBlock, TestimonialsBlock
from .trust import StatItemBlock, StatsBlock
from .trust import TrustStripBlock as TrustStripLogosBlock
from .trust import TrustStripItemBlock

__all__ = [
    "PageStreamBlock",
    "HeroImageBlock",
    "HeroGradientBlock",
    "HeroCTABlock",
    "HeroBlock",
    "TrustStripBlock",
    "TrustStripLogosBlock",
    "TrustStripItemBlock",
    "FeaturesListBlock",
    "ComparisonBlock",
    "ManifestoBlock",
    "PortfolioBlock",
    "ServiceCardsBlock",
    "ServiceCardItemBlock",
    "ServiceDetailBlock",
    "TestimonialsBlock",
    "TestimonialBlock",
    "GalleryBlock",
    "GalleryImageBlock",
    "FeaturedCaseStudyBlock",
    "StatItemBlock",
    "StatsBlock",
    "ProcessStepsBlock",
    "FAQBlock",
    "TimelineBlock",
    "TimelineItemBlock",
    "RichTextContentBlock",
    "PageHeaderBlock",
    "EditorialHeaderBlock",
    "TableOfContentsBlock",
    "TableOfContentsItemBlock",
    "LegalSectionBlock",
    "QuoteBlock",
    "SocialProofQuoteBlock",
    "ImageBlock",
    "ButtonGroupBlock",
    "SpacerBlock",
    "DividerBlock",
    "ContactFormBlock",
    "DynamicFormBlock",
    "QuoteRequestFormBlock",
    "UniversalLinkBlock",
    "UniversalLinkValue",
    "LINK_TYPE_CHOICES",
]
