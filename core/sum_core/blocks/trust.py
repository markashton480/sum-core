"""
Name: Trust & Stats Blocks
Path: core/sum_core/blocks/trust.py
Purpose: StreamField blocks for trust strip logos and numeric stats.
Family: Used by PageStreamBlock and homepage templates.
Dependencies: wagtail.blocks, wagtail.images, sum_core.blocks.base.
"""

from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock


class TrustStripItemBlock(blocks.StructBlock):
    """A single logo/badge item for the trust strip."""

    logo = ImageChooserBlock(
        required=True,
        help_text="Logo image for a certification, association, or partner.",
    )
    alt_text = blocks.CharBlock(
        required=True,
        max_length=255,
        help_text="Descriptive alt text for the logo (accessibility).",
    )
    url = blocks.URLBlock(
        required=False, help_text="Optional URL to link to (e.g. association website)."
    )

    class Meta:
        icon = "image"
        label = "Trust Item"


class TrustStripBlock(blocks.StructBlock):
    """
    Horizontal row of trust logos/badges.

    A thin, understated band with an eyebrow text and 2-8 logos
    for certifications, associations, or partner badges.
    """

    eyebrow = blocks.CharBlock(
        required=False,
        max_length=100,
        help_text="Small text above logos, e.g. 'Trusted by' or 'Certified by'.",
    )
    items = blocks.ListBlock(
        TrustStripItemBlock(),
        min_num=2,
        max_num=8,
        help_text="2-8 logo items for the trust strip.",
    )

    class Meta:
        template = "sum_core/blocks/trust_strip_logos.html"
        icon = "group"
        label = "Trust Strip (Logos)"


class StatItemBlock(blocks.StructBlock):
    """A single statistic with value, label, and optional prefix/suffix."""

    value = blocks.CharBlock(
        required=True,
        max_length=50,
        help_text="The numeric value, e.g. '500+', '15', '98%'.",
    )
    label = blocks.CharBlock(
        required=True,
        max_length=100,
        help_text="Short description, e.g. 'Projects Completed', 'Years Experience'.",
    )
    prefix = blocks.CharBlock(
        required=False,
        max_length=10,
        help_text="Optional prefix before value, e.g. '>' or '£'.",
    )
    suffix = blocks.CharBlock(
        required=False,
        max_length=10,
        help_text="Optional suffix after value, e.g. '+', 'yrs', '%'.",
    )

    class Meta:
        icon = "pick"
        label = "Stat"


class StatsBlock(blocks.StructBlock):
    """
    Block for displaying 2-4 key statistics.

    Used to showcase important numbers like projects completed,
    years of experience, customer satisfaction rates, etc.
    """

    eyebrow = blocks.CharBlock(
        required=False,
        max_length=100,
        help_text="Small text above stats, e.g. 'By the Numbers'.",
    )
    intro = blocks.TextBlock(
        required=False, help_text="Optional introductory text below the eyebrow."
    )
    items = blocks.ListBlock(
        StatItemBlock(), min_num=2, max_num=4, help_text="2-4 statistics to display."
    )

    class Meta:
        template = "sum_core/blocks/stats.html"
        icon = "snippet"
        label = "Stats"
