"""
Name: Testimonials Blocks
Path: core/sum_core/blocks/testimonials.py
Purpose: StreamField blocks for testimonial/social proof sections.
Family: Used by HomePage and other page StreamFields accepting social proof blocks.
Dependencies: Wagtail core blocks, base block mixins (from sum_core.blocks.base or similar), design system templates/CSS.
"""

from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock


class TestimonialBlock(blocks.StructBlock):
    quote = blocks.TextBlock(required=True, help_text="Customer quote or review text.")
    author_name = blocks.CharBlock(required=True, help_text="Name of the customer.")
    company = blocks.CharBlock(
        required=False, help_text="Company or context (optional)."
    )
    photo = ImageChooserBlock(required=False, help_text="Optional headshot or avatar.")
    rating = blocks.IntegerBlock(
        required=False,
        min_value=1,
        max_value=5,
        help_text="Optional rating from 1 to 5 stars.",
    )

    class Meta:
        icon = "user"
        label = "Testimonial"


class TestimonialsBlock(blocks.StructBlock):
    eyebrow = blocks.CharBlock(
        required=False, help_text="Small text above heading, e.g. 'Client Stories'."
    )
    heading = blocks.RichTextBlock(
        required=False,
        features=["bold", "italic"],
        help_text="Main section heading. Use italics for accent styling.",
    )
    testimonials = blocks.ListBlock(
        TestimonialBlock(),
        min_num=1,
        max_num=12,
        help_text="One or more testimonial cards.",
    )

    class Meta:
        template = "sum_core/blocks/testimonials.html"
        icon = "group"
        label = "Testimonials"
