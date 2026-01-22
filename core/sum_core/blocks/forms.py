"""
Name: Form Blocks
Path: core/sum_core/blocks/forms.py
Purpose: StreamField blocks for contact and quote request forms
Family: SUM Platform – StreamField Blocks
Dependencies: Wagtail core blocks, PageStreamBlock, templates in sum_core/blocks
"""

from sum_core.blocks.links import UniversalLinkBlock
from wagtail.blocks import (
    BooleanBlock,
    CharBlock,
    ChoiceBlock,
    RichTextBlock,
    StructBlock,
    TextBlock,
    URLBlock,
)
from wagtail.snippets.blocks import SnippetChooserBlock


class ContactFormBlock(StructBlock):
    eyebrow = CharBlock(
        required=False, help_text="Small label above heading (e.g. 'Enquiries')"
    )
    heading = RichTextBlock(required=True, help_text="Section heading")
    intro = RichTextBlock(required=False, help_text="Optional introductory copy")
    phone_label = CharBlock(
        required=False,
        max_length=100,
        help_text="Optional phone CTA label (e.g. 'Prefer to call?').",
    )
    phone_link = UniversalLinkBlock(
        required=False,
        help_text="Optional phone link (use link type 'phone').",
    )
    form_definition = SnippetChooserBlock(
        "sum_core_forms.FormDefinition",
        required=False,
        help_text="Optional dynamic form definition to render.",
    )
    success_message = TextBlock(
        required=False, default="Thanks, we'll be in touch shortly."
    )
    submit_label = CharBlock(required=False, default="Send enquiry")

    class Meta:
        icon = "mail"
        template = "sum_core/blocks/contact_form.html"
        label = "Contact form"
        form_type = "contact"  # metadata for leads system


class QuoteRequestFormBlock(StructBlock):
    eyebrow = CharBlock(
        required=False,
        help_text="Small label above heading (e.g. 'Project Application')",
    )
    heading = RichTextBlock(required=True)
    intro = RichTextBlock(required=False)
    success_message = TextBlock(
        required=False, default="Thanks, we'll prepare your quote."
    )
    submit_label = CharBlock(required=False, default="Request a quote")
    show_compact_meta = BooleanBlock(
        required=False, help_text="Compact layout for sidebars/short sections."
    )

    class Meta:
        icon = "form"
        template = "sum_core/blocks/quote_request_form.html"
        label = "Quote request form"
        form_type = "quote"


class DynamicFormBlock(StructBlock):
    form_definition = SnippetChooserBlock(
        "sum_core_forms.FormDefinition",
        required=True,
        help_text="Select the form to display",
    )
    presentation_style = ChoiceBlock(
        choices=[
            ("inline", "Inline (renders in page flow)"),
            ("modal", "Modal (button opens overlay)"),
            ("sidebar", "Sidebar (fixed slide-in)"),
        ],
        default="inline",
        help_text="How the form should be presented",
    )
    cta_button_text = CharBlock(
        required=False,
        max_length=100,
        help_text="Override default CTA button text (for modal/sidebar styles)",
    )
    success_redirect_url = URLBlock(
        required=False,
        help_text="Optional redirect after submission (defaults to same page with message)",
    )

    def get_context(self, value, parent_context=None):
        context = super().get_context(value, parent_context=parent_context)
        form_definition = value.get("form_definition")
        if form_definition and not form_definition.is_active:
            context["form_inactive_warning"] = True
        return context

    class Meta:
        icon = "form"
        template = "sum_core/blocks/dynamic_form_block.html"
        label = "Dynamic Form"


class LeadMagnetBlock(StructBlock):
    eyebrow = CharBlock(
        required=False,
        max_length=100,
        help_text="Small label above the heading (e.g. 'Free Resource').",
    )
    heading = RichTextBlock(
        required=True,
        features=["bold", "italic"],
        help_text="Lead magnet heading.",
    )
    description = RichTextBlock(
        required=False,
        features=["bold", "italic", "link"],
        help_text="Optional supporting copy.",
    )
    form_definition = SnippetChooserBlock(
        "sum_core_forms.FormDefinition",
        required=False,
        help_text="Optional dynamic form definition. If empty, render email-only.",
    )
    email_label = CharBlock(
        required=False,
        max_length=100,
        help_text="Optional email field label or placeholder.",
    )
    submit_label = CharBlock(
        required=False,
        max_length=80,
        help_text="Optional submit button label.",
    )
    success_message = TextBlock(
        required=False,
        help_text="Optional success message after submission.",
    )
    variant = ChoiceBlock(
        choices=[("inline", "Inline"), ("sidebar", "Sidebar")],
        default="inline",
        required=False,
        help_text="Layout variant for the lead magnet.",
    )

    class Meta:
        icon = "form"
        template = "sum_core/blocks/lead_magnet.html"
        label = "Lead Magnet"
