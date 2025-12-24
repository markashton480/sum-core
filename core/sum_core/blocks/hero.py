"""
Name: Hero Blocks
Path: core/sum_core/blocks/hero.py
Purpose: StreamField hero blocks (image/gradient) for page headers
Family: Used by PageStreamBlock and page models (HomePage, future core pages)
Dependencies: Wagtail blocks, sum_core.blocks.base, CSS design system
"""

from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock


class HeroCTABlock(blocks.StructBlock):
    label = blocks.CharBlock(required=True, max_length=100)
    url = blocks.URLBlock(required=True)
    style = blocks.ChoiceBlock(
        choices=[
            ("primary", "Primary"),
            ("secondary", "Secondary"),
            ("outline", "Outline"),
        ],
        default="primary",
    )
    open_in_new_tab = blocks.BooleanBlock(required=False, default=False)

    class Meta:
        icon = "link"
        label = "CTA Button"


class BaseHeroBlock(blocks.StructBlock):
    headline = blocks.RichTextBlock(
        required=True,
        features=["italic"],
        help_text="Main heading. Highlight text and use 'Italic' to apply the accent styling.",
    )
    subheadline = blocks.TextBlock(required=False)
    ctas = blocks.ListBlock(
        HeroCTABlock(),
        min_num=0,
        max_num=2,
        required=False,
        label="CTA Buttons",
    )
    # Optional: small "eyebrow/status" text field
    status = blocks.CharBlock(required=False, max_length=120, label="Status / Eyebrow")


class HeroImageBlock(BaseHeroBlock):
    image = ImageChooserBlock(required=True)
    image_alt = blocks.CharBlock(
        required=True, max_length=150, help_text="Alt text for accessibility"
    )
    overlay_opacity = blocks.ChoiceBlock(
        choices=[
            ("none", "No overlay"),
            ("light", "Light"),
            ("medium", "Medium"),
            ("strong", "Strong"),
        ],
        default="medium",
        help_text="Dark overlay opacity for text contrast",
    )
    layout = blocks.ChoiceBlock(
        choices=[
            ("split", "Split (Image Right)"),
            ("full", "Full (Background Image)"),
        ],
        default="split",
        help_text="Choose the hero layout style.",
    )

    # Floating Card Fields
    floating_card_label = blocks.CharBlock(
        required=False,
        max_length=50,
        label="Floating Card Label",
        help_text="e.g. 'Est. Annual Savings'",
    )
    floating_card_value = blocks.CharBlock(
        required=False,
        max_length=50,
        label="Floating Card Value",
        help_text="e.g. '£2,450'",
    )

    class Meta:
        template = "sum_core/blocks/hero_image.html"
        icon = "image"
        label = "Hero (Image)"
        help_text = "Full-width image hero with overlay and CTA buttons."


class HeroGradientBlock(BaseHeroBlock):
    gradient_style = blocks.ChoiceBlock(
        choices=[
            ("primary", "Primary gradient"),
            ("secondary", "Secondary gradient"),
            ("accent", "Accent gradient"),
        ],
        default="primary",
    )

    class Meta:
        template = "sum_core/blocks/hero_gradient.html"
        icon = "placeholder"
        label = "Hero (Gradient)"
        help_text = "Hero with gradient background using brand colours."
