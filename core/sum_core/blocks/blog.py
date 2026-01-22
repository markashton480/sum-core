"""
Name: Blog Blocks
Path: core/sum_core/blocks/blog.py
Purpose: StreamBlock tailored for blog post authoring.
Family: Blocks.
"""

from __future__ import annotations

import itertools

from sum_core.blocks.content import (
    ArticleSectionBlock,
    CallToActionBlock,
    DividerBlock,
    ImageBlock,
    LeadParagraphBlock,
    NumberedStepsBlock,
    QuoteBlock,
    RichTextContentBlock,
    SocialProofQuoteBlock,
    SpacerBlock,
)
from sum_core.blocks.forms import DynamicFormBlock
from sum_core.pages.chrome import HEADER_BLOCK_TYPES
from wagtail import blocks
from wagtail.blocks import StreamBlock


class BlogPostStreamBlock(StreamBlock):
    """
    StreamBlock for BlogPostPage content.
    """

    lead_paragraph = LeadParagraphBlock(group="Blog")
    article_section = ArticleSectionBlock(group="Blog")
    content = RichTextContentBlock(group="Blog")
    numbered_steps = NumberedStepsBlock(group="Blog")
    quote = QuoteBlock(group="Blog")
    social_proof_quote = SocialProofQuoteBlock(group="Blog")
    image_block = ImageBlock(group="Blog")
    call_to_action = CallToActionBlock(group="Blog")
    spacer = SpacerBlock(group="Blog")
    divider = DividerBlock(group="Blog")
    dynamic_form = DynamicFormBlock(group="Forms")
    rich_text = blocks.RichTextBlock(
        label="Rich Text",
        help_text="Add formatted text content. Use H2-H4 for headings, avoid H1.",
        features=["h2", "h3", "h4", "bold", "italic", "link", "ol", "ul"],
        required=False,
    )

    class Meta:
        icon = "doc-full"
        label = "Blog Content Block"
        label_format = "Blog: {label}"

    def grouped_child_blocks(self):
        """Return chooser-visible blocks without mutating stored block defs."""
        visible_blocks = [
            block
            for name, block in self.child_blocks.items()
            if name not in HEADER_BLOCK_TYPES
        ]
        visible_blocks = sorted(visible_blocks, key=lambda block: block.meta.group)
        return itertools.groupby(visible_blocks, key=lambda block: block.meta.group)
