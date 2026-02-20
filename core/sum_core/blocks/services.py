"""
Name: Service Blocks
Path: core/sum_core/blocks/services.py
Purpose: StreamField blocks for service sections (cards + detail layouts)
Family: Used by PageStreamBlock and core page models (HomePage, ServicePage, etc.)
Dependencies: Wagtail blocks, wagtailimages, sum_core.blocks.base, design system CSS
"""

from xml.etree import ElementTree

from django.core.exceptions import ValidationError
from sum_core.blocks.forms import LeadMagnetBlock
from sum_core.blocks.links import CtaLinkBlock, UniversalLinkBlock
from sum_core.blocks.process_faq import ProcessStepBlock
from sum_core.blocks.trust import TrustStripItemBlock
from wagtail import blocks
from wagtail.blocks import StructBlockValidationError
from wagtail.images.blocks import ImageChooserBlock


def _raise_icon_svg_error(message: str) -> None:
    raise blocks.StructBlockValidationError({"icon_svg": ValidationError(message)})


def _validate_inline_svg(svg: str) -> None:
    if not isinstance(svg, str) or not svg.strip():
        _raise_icon_svg_error("Provide inline SVG markup.")

    try:
        root = ElementTree.fromstring(svg)
    except ElementTree.ParseError as exc:
        raise blocks.StructBlockValidationError(
            {"icon_svg": ValidationError("Invalid SVG markup.")}
        ) from exc

    def _tag_name(tag: str) -> str:
        return tag.split("}", 1)[-1].lower()

    root_tag = _tag_name(root.tag)
    if root_tag != "svg":
        _raise_icon_svg_error("Root element must be <svg>.")

    disallowed_tags = {
        "script",
        "foreignobject",
        "iframe",
        "object",
        "embed",
        "audio",
        "video",
        "canvas",
    }
    disallowed_attrs = {"style"}

    for elem in root.iter():
        tag = _tag_name(elem.tag)
        if tag in disallowed_tags:
            _raise_icon_svg_error(f"SVG contains disallowed element: <{tag}>")

        for attr_name in elem.attrib:
            clean_name = _tag_name(attr_name)
            if clean_name.startswith("on"):
                _raise_icon_svg_error(
                    f"SVG event handler attribute '{attr_name}' is not allowed on <{tag}>"
                )
            if clean_name == "href":
                _raise_icon_svg_error(f"SVG href attribute is not allowed on <{tag}>")
            if clean_name in disallowed_attrs:
                _raise_icon_svg_error(
                    f"SVG attribute '{clean_name}' is not allowed on <{tag}>"
                )


class ServiceCardItemBlock(blocks.StructBlock):
    """
    A single service card within the ServiceCardsBlock grid.
    """

    icon = blocks.CharBlock(
        required=False, max_length=4, help_text="Emoji or short icon text (optional)"
    )
    image = ImageChooserBlock(
        required=False,
        help_text="Allows proper image/icon; render as the primary visual if present.",
    )
    kicker = blocks.CharBlock(
        required=False,
        max_length=100,
        help_text='Optional label, e.g. "Featured Service" or "02".',
    )
    title = blocks.CharBlock(required=True, max_length=120)
    description = blocks.RichTextBlock(
        required=False,
        features=["bold", "italic", "link", "ul", "ol", "document-link"],
        help_text="Limited to paragraphs + basic inline formatting.",
    )
    price_range = blocks.CharBlock(
        required=False,
        max_length=120,
        help_text='Optional price range text, e.g. "Typically GBP 35k - GBP 80k".',
    )
    link_url = UniversalLinkBlock(
        required=False,
        help_text="Optional link for the service card.",
    )
    link_label = blocks.CharBlock(
        required=False,
        max_length=50,
        help_text="Defaults to “Learn more” if left blank.",
    )
    is_featured = blocks.BooleanBlock(
        required=False,
        default=False,
        help_text="Toggle to mark this card as the featured layout.",
    )

    class Meta:
        icon = "doc-full"
        label = "Service Card"


class ServiceCardsBlock(blocks.StructBlock):
    """
    A section containing a grid of ServiceCardItemBlocks.
    """

    eyebrow = blocks.CharBlock(
        required=False,
        max_length=120,
        help_text="Short label above the heading (optional).",
    )
    heading = blocks.RichTextBlock(
        required=True,
        features=["italic", "bold"],
        help_text="Section heading. Use Italic for accent color.",
    )
    intro = blocks.TextBlock(required=False, help_text="Short supporting paragraph.")
    tone = blocks.ChoiceBlock(
        choices=[
            ("light", "Light"),
            ("dark", "Dark"),
            ("muted", "Muted"),
        ],
        default="muted",
        required=False,
        help_text="Visual tone for section background and heading treatment.",
    )
    density = blocks.ChoiceBlock(
        choices=[
            ("compact", "Compact"),
            ("regular", "Regular"),
            ("spacious", "Spacious"),
        ],
        default="regular",
        required=False,
        help_text="Vertical spacing density for the section.",
    )
    variant = blocks.ChoiceBlock(
        choices=[
            ("featured_grid", "Featured grid"),
            ("proof_grid", "Proof grid"),
            ("default", "Standard grid"),
        ],
        default="featured_grid",
        required=False,
        help_text="Select the service cards layout variant.",
    )
    supporting_image = ImageChooserBlock(
        required=False,
        help_text="Optional supporting image tile within the grid layout.",
    )
    alt_text = blocks.CharBlock(
        required=False,
        max_length=255,
        help_text="Alt text for the supporting image (required if image is set).",
    )
    view_all_link = UniversalLinkBlock(required=False, label="View All Link")
    view_all_label = blocks.CharBlock(
        required=False, max_length=50, label="View All Label"
    )
    cards = blocks.ListBlock(ServiceCardItemBlock(), min_num=1, max_num=12)
    layout_style = blocks.ChoiceBlock(
        choices=[("default", "Default"), ("tight", "Tight spacing")],
        default="default",
        required=False,
    )

    class Meta:
        template = "sum_core/blocks/service_cards.html"
        icon = "list-ul"
        label = "Service cards"
        help_text = "Showcase services in a responsive card grid (1–12 cards)."

    def clean(self, value):
        cleaned = super().clean(value)
        cards = cleaned.get("cards") or []
        featured_count = sum(1 for card in cards if card.get("is_featured"))
        if featured_count > 1:
            raise StructBlockValidationError(
                block_errors={
                    "cards": ValidationError(
                        "Only one featured service card is allowed."
                    )
                }
            )
        supporting_image = cleaned.get("supporting_image")
        alt_text = (cleaned.get("alt_text") or "").strip()
        if supporting_image and not alt_text:
            raise StructBlockValidationError(
                block_errors={
                    "alt_text": ValidationError("Alt text is required with an image.")
                }
            )
        if not supporting_image:
            cleaned["alt_text"] = ""
        return cleaned


class ServiceDetailBlock(blocks.StructBlock):
    """
    A two-column service detail block with optional highlights and image.
    """

    eyebrow = blocks.CharBlock(
        required=False,
        max_length=120,
        help_text="Short label displayed above the heading (optional).",
    )
    heading = blocks.RichTextBlock(
        required=True,
        features=["italic", "bold"],
        help_text="Service section heading. Use italics for accent styling.",
    )
    body = blocks.RichTextBlock(
        required=True,
        features=["bold", "italic", "link", "ol", "ul"],
        help_text="Core service description with limited formatting.",
    )
    highlights = blocks.ListBlock(
        blocks.CharBlock(max_length=200),
        required=False,
        help_text="Optional short highlights or bullets.",
    )
    image = ImageChooserBlock(
        required=False,
        help_text="Optional supporting image. Leave blank for text-only layout.",
    )
    alt_text = blocks.CharBlock(
        required=False,
        max_length=255,
        help_text="Alt text for the image (required if image is set).",
    )
    layout = blocks.ChoiceBlock(
        choices=(
            ("image_left", "Image left"),
            ("image_right", "Image right"),
            ("no_image", "No image"),
        ),
        default="image_left",
        required=False,
        help_text="Choose how the section aligns media vs. content.",
    )
    cta_text = blocks.CharBlock(
        required=False,
        max_length=80,
        help_text="Optional call-to-action label (shown when URL provided).",
    )
    cta_url = UniversalLinkBlock(
        required=False,
        help_text="Optional call-to-action link (shown when label provided).",
    )

    class Meta:
        template = "sum_core/blocks/service_detail.html"
        icon = "placeholder"
        label = "Service detail"
        help_text = "Highlight a single service with image, copy, and bullets."

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


class ServiceIconGridItemBlock(blocks.StructBlock):
    icon_svg = blocks.TextBlock(
        required=True,
        help_text="Inline SVG markup for the service icon.",
    )
    title = blocks.CharBlock(required=True, max_length=120)
    description = blocks.RichTextBlock(
        required=True,
        features=["bold", "italic", "link"],
        help_text="Short service description.",
    )

    class Meta:
        icon = "placeholder"
        label = "Service icon item"

    def clean(self, value):
        cleaned = super().clean(value)
        _validate_inline_svg(cleaned.get("icon_svg", ""))
        return cleaned


class ServiceIconGridBlock(blocks.StructBlock):
    items = blocks.ListBlock(
        ServiceIconGridItemBlock(),
        min_num=2,
        max_num=6,
        help_text="Two to six icon cards.",
    )

    class Meta:
        template = "sum_core/blocks/service_icon_grid.html"
        icon = "list-ul"
        label = "Service icon grid"
        help_text = "Icon-first 4-up service grid (services-06)."


class AccreditationPolicyCardBlock(blocks.StructBlock):
    heading = blocks.CharBlock(required=True, max_length=80)
    description = blocks.RichTextBlock(
        required=True,
        features=["bold", "italic", "link"],
        help_text="Short policy description.",
    )

    class Meta:
        icon = "doc-full"
        label = "Accreditation policy card"


class AccreditationsAndWarrantyBlock(blocks.StructBlock):
    eyebrow = blocks.CharBlock(
        required=False,
        max_length=120,
        help_text="Short label above the accreditations strip (optional).",
    )
    logos = blocks.ListBlock(
        TrustStripItemBlock(),
        min_num=2,
        max_num=8,
        help_text="2-8 accreditation logos.",
    )
    policies = blocks.ListBlock(
        AccreditationPolicyCardBlock(),
        min_num=2,
        max_num=2,
        help_text="Exactly two policy cards.",
    )

    class Meta:
        template = "sum_core/blocks/accreditations_and_warranty.html"
        icon = "group"
        label = "Accreditations + warranty"
        help_text = "Logo strip with warranty and liability policy cards."


class ValuePropositionStatBlock(blocks.StructBlock):
    value = blocks.CharBlock(required=True, max_length=20)
    label = blocks.CharBlock(required=True, max_length=80)

    class Meta:
        icon = "placeholder"
        label = "Value proposition stat"


class ValuePropositionBlock(blocks.StructBlock):
    heading = blocks.RichTextBlock(
        required=True,
        features=["italic", "bold"],
        help_text="Main heading.",
    )
    body = blocks.RichTextBlock(
        required=True,
        features=["bold", "italic", "link", "ul", "ol"],
        help_text="Multi-paragraph value proposition copy.",
    )
    primary_cta = CtaLinkBlock(required=False)
    secondary_cta = CtaLinkBlock(required=False)
    phone_label = blocks.CharBlock(required=False, max_length=100)
    phone_link = UniversalLinkBlock(required=False)
    stats = blocks.ListBlock(
        ValuePropositionStatBlock(),
        min_num=2,
        max_num=2,
        required=True,
        help_text="Exactly two stat tiles required for the layout.",
    )
    image = ImageChooserBlock(required=False)
    alt_text = blocks.CharBlock(
        required=False,
        max_length=255,
        help_text="Alt text for the image (required if image is set).",
    )
    image_quote = blocks.CharBlock(required=False, max_length=200)

    class Meta:
        template = "sum_core/blocks/value_proposition.html"
        icon = "placeholder"
        label = "Value proposition"
        help_text = "Value proposition section with CTA cluster and stats."

    def clean(self, value):
        cleaned = super().clean(value)
        image = cleaned.get("image")
        alt_text = (cleaned.get("alt_text") or "").strip()
        if image and not alt_text:
            raise blocks.StructBlockValidationError(
                block_errors={
                    "alt_text": ValidationError("Alt text is required with an image.")
                },
            )
        if not image:
            cleaned["alt_text"] = ""
        return cleaned


class ProcessTimelineBlock(blocks.StructBlock):
    """
    Timeline section for services-05.
    """

    eyebrow = blocks.CharBlock(
        required=False, help_text="Optional short label / kicker."
    )
    heading = blocks.RichTextBlock(
        required=True, features=["italic", "bold"], help_text="Section heading."
    )
    intro = blocks.RichTextBlock(
        required=False,
        features=["bold", "italic", "link"],
        help_text="Optional short supporting text.",
    )
    tone = blocks.ChoiceBlock(
        choices=[
            ("light", "Light"),
            ("dark", "Dark"),
            ("muted", "Muted"),
        ],
        default="light",
        required=False,
        help_text="Visual tone for section background and contrast.",
    )
    density = blocks.ChoiceBlock(
        choices=[
            ("compact", "Compact"),
            ("regular", "Regular"),
            ("spacious", "Spacious"),
        ],
        default="regular",
        required=False,
        help_text="Vertical spacing density for the section.",
    )
    steps = blocks.ListBlock(
        ProcessStepBlock(),
        min_num=2,
        max_num=5,
        help_text="Timeline steps for the process section (2–5).",
    )
    cta_label = blocks.CharBlock(
        required=False,
        max_length=80,
        help_text="Optional call-to-action label shown below the timeline.",
    )
    cta_link = UniversalLinkBlock(
        required=False,
        help_text="Optional call-to-action link.",
    )

    def get_context(self, value, parent_context=None):
        """
        Compute timeline context including highlight_index for visual emphasis.

        Highlight algorithm: for <=2 steps, highlight the first (1-based index).
        For 3+ steps, highlight the middle step rounded up (1-based index).
        """
        context = super().get_context(value, parent_context=parent_context)
        steps = value.get("steps") or []
        steps_count = len(steps)
        context["steps_count"] = steps_count
        if steps_count <= 2:
            context["highlight_index"] = 1
        else:
            context["highlight_index"] = (steps_count // 2) + 1
        return context

    class Meta:
        icon = "list-ol"
        label = "Process timeline"
        template = "sum_core/blocks/process_timeline.html"
        group = "Sections"
        help_text = "Services timeline section (services-05)."


class ProcessTimelineLeadMagnetBlock(ProcessTimelineBlock):
    """
    Legacy combined timeline + lead magnet section for services-05.
    """

    lead_magnet = LeadMagnetBlock(
        required=False,
        help_text="Embedded lead magnet rendered within the same section.",
    )

    class Meta:
        icon = "list-ol"
        label = "Process timeline + lead magnet (legacy)"
        template = "sum_core/blocks/process_timeline_lead_magnet.html"
        group = "Legacy Sections"
        help_text = "Legacy block. Use Process timeline + Lead magnet blocks instead."


class CenteredCTASectionBlock(blocks.StructBlock):
    """
    Centered CTA section with heading and single CTA button (services-11).
    """

    eyebrow = blocks.CharBlock(
        required=False,
        max_length=80,
        help_text="Optional short label above the heading.",
    )
    heading = blocks.RichTextBlock(
        required=True,
        features=["italic", "bold"],
        help_text="Section heading.",
    )
    cta_label = blocks.CharBlock(
        required=False,
        max_length=80,
        help_text="Optional call-to-action label shown below the heading.",
    )
    cta_link = UniversalLinkBlock(
        required=False,
        help_text="Optional call-to-action link.",
    )

    class Meta:
        icon = "placeholder"
        label = "Centered CTA section"
        template = "sum_core/blocks/centered_cta_section.html"
        group = "Sections"
        help_text = "Centered CTA section with a single button (services-11)."
