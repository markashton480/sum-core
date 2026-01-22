"""
Name: Gallery Blocks
Path: core/sum_core/blocks/gallery.py
Purpose: StreamField blocks for gallery/image grid sections.
Family: Used via PageStreamBlock on core pages (e.g., HomePage) and other templates.
Dependencies: Wagtail blocks, wagtail.images ImageChooserBlock, sum_core design tokens.
"""

from sum_core.blocks.links import CtaLinkBlock
from sum_core.utils.links import validate_safe_link
from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock


class GalleryImageBlock(blocks.StructBlock):
    """Individual gallery item with image, alt text, and caption."""

    image = ImageChooserBlock(required=True, help_text="Project photo.")
    alt_text = blocks.CharBlock(
        required=True,
        max_length=255,
        help_text="Alt text for accessibility (required for screen readers).",
    )
    caption = blocks.CharBlock(
        required=False,
        max_length=255,
        help_text="Short caption, e.g. location or project type.",
    )

    class Meta:
        icon = "image"
        label = "Gallery Image"


class GalleryBlock(blocks.StructBlock):
    """
    Gallery section block with heading, intro text, and a grid of images.

    Provides a flexible image gallery for showcasing project photos,
    portfolio pieces, or any visual content in a responsive grid layout.
    """

    eyebrow = blocks.CharBlock(
        required=False,
        max_length=80,
        help_text="Small text above heading, e.g. 'Selected Works'.",
    )
    heading = blocks.RichTextBlock(
        required=False,
        features=["bold", "italic"],
        help_text="Main section heading. Use italics for accent styling.",
    )
    intro = blocks.TextBlock(required=False, help_text="Optional supporting text.")
    images = blocks.ListBlock(
        GalleryImageBlock(),
        min_num=1,
        max_num=24,
        help_text="Add 1–24 images to the gallery.",
    )

    class Meta:
        icon = "image"
        label = "Gallery"
        help_text = "Grid of project images with optional captions."
        template = "sum_core/blocks/gallery.html"


class ProvenancePlateDetailBlock(blocks.StructBlock):
    maker_label = blocks.CharBlock(
        required=False,
        max_length=50,
        default="Maker",
        help_text="Optional label for maker metadata.",
    )
    maker_name = blocks.CharBlock(
        required=True,
        max_length=100,
        help_text="Required maker name.",
    )
    source_label = blocks.CharBlock(
        required=False,
        max_length=50,
        default="Source",
        help_text="Optional label for source metadata.",
    )
    source_coordinates = blocks.CharBlock(
        required=True,
        max_length=100,
        help_text="Coordinates or source reference.",
    )
    source_location = blocks.CharBlock(
        required=False,
        max_length=100,
        help_text="Optional source location.",
    )
    completion_label = blocks.CharBlock(
        required=False,
        max_length=50,
        default="Completion",
        help_text="Optional label for completion date.",
    )
    completion_date = blocks.CharBlock(
        required=False,
        max_length=50,
        help_text="Optional completion date.",
    )

    class Meta:
        icon = "clipboard-list"
        label = "Provenance Plate Details"


class ProvenanceModalMakerBlock(blocks.StructBlock):
    label = blocks.CharBlock(
        required=False,
        max_length=80,
        default="Maker Profile",
        help_text="Optional label for the maker section.",
    )
    name = blocks.CharBlock(
        required=False,
        max_length=100,
        help_text="Maker name.",
    )
    role = blocks.CharBlock(
        required=False,
        max_length=100,
        help_text="Maker role or title.",
    )

    class Meta:
        icon = "user"
        label = "Provenance Maker"


class ProvenanceModalSourceBlock(blocks.StructBlock):
    label = blocks.CharBlock(
        required=False,
        max_length=80,
        default="Material Source",
        help_text="Optional label for the source section.",
    )
    name = blocks.CharBlock(
        required=False,
        max_length=100,
        help_text="Source name or identifier.",
    )
    detail = blocks.CharBlock(
        required=False,
        max_length=120,
        help_text="Additional source detail or context.",
    )

    class Meta:
        icon = "site"
        label = "Provenance Source"


class ProvenanceModalGuaranteeBlock(blocks.StructBlock):
    label = blocks.CharBlock(
        required=False,
        max_length=80,
        default="Guarantee ID",
        help_text="Optional label for guarantee metadata.",
    )
    value = blocks.CharBlock(
        required=False,
        max_length=80,
        help_text="Guarantee identifier or value.",
    )

    class Meta:
        icon = "tick"
        label = "Provenance Guarantee"


class ProvenanceModalBlock(blocks.StructBlock):
    title = blocks.CharBlock(
        required=False,
        max_length=100,
        default="Artifact Dossier",
        help_text="Optional modal title.",
    )
    maker = ProvenanceModalMakerBlock(required=True)
    source = ProvenanceModalSourceBlock(required=True)
    guarantee = ProvenanceModalGuaranteeBlock(required=True)
    cta = CtaLinkBlock(required=False)

    class Meta:
        icon = "form"
        label = "Provenance Modal"


class ProvenancePlateBlock(blocks.StructBlock):
    """
    Signature provenance plate section with optional modal details.
    """

    eyebrow = blocks.CharBlock(
        required=False,
        max_length=100,
        help_text="Optional label above the heading.",
    )
    heading = blocks.RichTextBlock(
        required=True,
        features=["bold", "italic"],
        help_text="Main section heading.",
    )
    body = blocks.RichTextBlock(
        required=True,
        features=["bold", "italic", "link", "ol", "ul"],
        help_text="Primary descriptive copy.",
    )
    points = blocks.ListBlock(
        blocks.CharBlock(max_length=200),
        required=False,
        help_text="Optional bullet points.",
    )
    cta = CtaLinkBlock(required=False)
    cta_action = blocks.ChoiceBlock(
        choices=[("modal", "Modal"), ("link", "Link")],
        default="modal",
        required=False,
        help_text="Choose modal or link CTA behavior.",
    )
    plate = ProvenancePlateDetailBlock(required=True)
    modal = ProvenanceModalBlock(required=False)
    modal_id = blocks.CharBlock(
        required=False,
        max_length=100,
        default="provenance-modal",
        help_text="Optional modal DOM id.",
    )

    class Meta:
        icon = "doc-full"
        template = "sum_core/blocks/provenance_plate.html"
        label = "Provenance Plate"


class FeaturedCaseStudyBlock(blocks.StructBlock):
    eyebrow = blocks.CharBlock(max_length=100, required=False)
    heading = blocks.RichTextBlock(required=True)
    intro = blocks.RichTextBlock(required=False)
    points = blocks.ListBlock(blocks.TextBlock(max_length=500), required=False)
    cta_text = blocks.CharBlock(max_length=50, required=False)
    cta_url = blocks.CharBlock(
        required=False, max_length=255, validators=[validate_safe_link]
    )
    image = ImageChooserBlock(required=True)
    alt_text = blocks.CharBlock(
        required=True, max_length=255, help_text="Alt text for accessibility."
    )
    stats_label = blocks.CharBlock(max_length=50, required=False)
    stats_value = blocks.CharBlock(max_length=100, required=False)
    project_label = blocks.CharBlock(
        required=False,
        max_length=100,
        help_text="Optional project label.",
    )
    project_title = blocks.CharBlock(
        required=False,
        max_length=200,
        help_text="Optional project title.",
    )
    quote = blocks.TextBlock(
        required=False,
        help_text="Optional pull quote.",
    )
    challenge_body = blocks.RichTextBlock(
        required=False,
        features=["bold", "italic", "link", "ol", "ul"],
        help_text="Optional challenge narrative.",
    )
    outcome_body = blocks.RichTextBlock(
        required=False,
        features=["bold", "italic", "link", "ol", "ul"],
        help_text="Optional outcome narrative.",
    )
    citation_name = blocks.CharBlock(
        required=False,
        max_length=100,
        help_text="Optional quote attribution name.",
    )
    citation_location = blocks.CharBlock(
        required=False,
        max_length=100,
        help_text="Optional quote attribution location.",
    )

    class Meta:
        icon = "doc-full"
        label = "Featured Case Study"
        template = "sum_core/blocks/featured_case_study.html"
