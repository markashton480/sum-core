"""
Name: Form field blocks
Path: core/sum_core/forms/fields.py
Purpose: StreamField blocks for dynamic FormDefinition schemas.
Family: Forms, Dynamic Forms foundation.
Dependencies: Wagtail blocks
"""

from __future__ import annotations

from django.core.validators import validate_slug
from wagtail import blocks
from wagtail.blocks.stream_block import StreamValue


class FormFieldBlock(blocks.StructBlock):
    """Base struct for form field definitions."""

    field_name = blocks.CharBlock(
        required=True,
        validators=[validate_slug],
        help_text="Unique field identifier (e.g., 'email', 'phone').",
    )
    label = blocks.CharBlock(
        required=True,
        help_text="Field label shown to users.",
    )
    help_text = blocks.CharBlock(
        required=False,
        help_text="Optional help text below field.",
    )
    required = blocks.BooleanBlock(
        required=False,
        default=True,
        help_text="Mark field as required.",
    )
    css_class = blocks.CharBlock(
        required=False,
        help_text="Optional CSS classes for styling.",
    )

    class Meta:
        abstract = True
        icon = "form"
        label = "Form field"

    def clean(self, value, **kwargs):
        """Ensure defaults are populated for optional fields."""
        cleaned = super().clean(value, **kwargs)

        for name, block in self.child_blocks.items():
            if name not in cleaned:
                default = block.get_default()
                if default is not None:
                    cleaned[name] = default

        return cleaned


class ChoiceHandlingMixin:
    """Shared handling for converting raw choices into StreamValue."""

    choice_field_name = "choices"
    child_blocks: dict[str, blocks.Block]

    def _coerce_choices(self, value: dict) -> dict:
        choices_value = value.get(self.choice_field_name, [])
        if not isinstance(choices_value, StreamValue):
            choices_value = self.child_blocks[self.choice_field_name].to_python(
                choices_value
            )
            value = {**value, self.choice_field_name: choices_value}

        return value


class ChoiceOptionBlock(blocks.StructBlock):
    """Option for select, checkbox group, and radio button fields."""

    value = blocks.CharBlock(
        required=True,
        help_text="Value submitted when selected.",
    )
    label = blocks.CharBlock(
        required=True,
        help_text="Display label shown to users.",
    )

    class Meta:
        icon = "list-ul"
        label = "Option"


class ChoiceOptionsStreamBlock(blocks.StreamBlock):
    option = ChoiceOptionBlock()

    class Meta:
        min_num = 1
        label = "Options"
        icon = "list-ul"
        help_text = "Add one or more selectable options."


class TextInputBlock(FormFieldBlock):
    max_length = blocks.IntegerBlock(
        required=False,
        default=255,
        min_value=1,
        help_text="Maximum number of characters allowed.",
    )
    placeholder = blocks.CharBlock(
        required=False,
        help_text="Optional placeholder text shown in the field.",
    )

    class Meta:
        icon = "edit"
        label = "Text input"


class EmailInputBlock(TextInputBlock):
    class Meta:
        icon = "mail"
        label = "Email input"
        help_text = "Collects an email address with validation."


class PhoneInputBlock(FormFieldBlock):
    format_mask = blocks.CharBlock(
        required=False,
        help_text='Optional input mask (e.g., "(###) ###-####").',
    )
    placeholder = blocks.CharBlock(
        required=False,
        help_text="Optional placeholder text shown in the field.",
    )

    class Meta:
        icon = "phone"
        label = "Phone input"


class TextareaBlock(FormFieldBlock):
    rows = blocks.IntegerBlock(
        required=False,
        default=4,
        min_value=1,
        help_text="Number of visible text rows.",
    )
    max_length = blocks.IntegerBlock(
        required=False,
        min_value=1,
        help_text="Optional maximum number of characters allowed.",
    )
    placeholder = blocks.CharBlock(
        required=False,
        help_text="Optional placeholder text shown in the field.",
    )

    class Meta:
        icon = "pilcrow"
        label = "Textarea"


class SelectBlock(ChoiceHandlingMixin, FormFieldBlock):
    choices = ChoiceOptionsStreamBlock(required=True)
    allow_multiple = blocks.BooleanBlock(
        required=False,
        default=False,
        help_text="Allow multiple selections.",
    )

    class Meta:
        icon = "list-ul"
        label = "Select"

    def clean(self, value, **kwargs):
        return super().clean(self._coerce_choices(value), **kwargs)


class CheckboxBlock(FormFieldBlock):
    checked_value = blocks.CharBlock(
        required=False,
        default="yes",
        help_text="Value submitted when the checkbox is checked.",
    )

    class Meta:
        icon = "tick"
        label = "Checkbox"


class CheckboxGroupBlock(ChoiceHandlingMixin, FormFieldBlock):
    choices = ChoiceOptionsStreamBlock(required=True)

    class Meta:
        icon = "list-ul"
        label = "Checkbox group"

    def clean(self, value, **kwargs):
        return super().clean(self._coerce_choices(value), **kwargs)


class RadioButtonsBlock(ChoiceHandlingMixin, FormFieldBlock):
    choices = ChoiceOptionsStreamBlock(required=True)

    class Meta:
        icon = "radio-empty"
        label = "Radio buttons"

    def clean(self, value, **kwargs):
        return super().clean(self._coerce_choices(value), **kwargs)


class FileUploadBlock(FormFieldBlock):
    allowed_extensions = blocks.CharBlock(
        required=True,
        help_text="Comma-separated allowed extensions (e.g., '.pdf,.doc,.docx').",
    )
    max_file_size_mb = blocks.IntegerBlock(
        required=False,
        default=10,
        min_value=1,
        help_text="Maximum file size in megabytes.",
    )

    class Meta:
        icon = "doc-full"
        label = "File upload"


class SectionHeadingBlock(blocks.StructBlock):
    heading = blocks.CharBlock(
        required=True,
        help_text="Section heading text.",
    )
    level = blocks.ChoiceBlock(
        choices=[("h2", "H2"), ("h3", "H3"), ("h4", "H4")],
        default="h2",
        help_text="Heading level.",
    )

    class Meta:
        icon = "title"
        label = "Section heading"

    def clean(self, value, **kwargs):
        cleaned = super().clean(value, **kwargs)
        if "level" not in cleaned:
            default = self.child_blocks["level"].get_default()
            if default is not None:
                cleaned["level"] = default

        return cleaned


class HelpTextBlock(blocks.StructBlock):
    text = blocks.RichTextBlock(
        required=True,
        features=["bold", "italic", "ol", "ul", "link"],
        help_text="Helper copy or instructions.",
    )

    class Meta:
        icon = "help"
        label = "Help text"

    def clean(self, value, **kwargs):
        text_value = value.get("text")
        if isinstance(text_value, str):
            value = {**value, "text": self.child_blocks["text"].to_python(text_value)}

        return super().clean(value, **kwargs)


class FormFieldsStreamBlock(blocks.StreamBlock):
    text_input = TextInputBlock()
    email_input = EmailInputBlock()
    phone_input = PhoneInputBlock()
    textarea = TextareaBlock()
    select = SelectBlock()
    checkbox = CheckboxBlock()
    checkbox_group = CheckboxGroupBlock()
    radio_buttons = RadioButtonsBlock()
    file_upload = FileUploadBlock()
    section_heading = SectionHeadingBlock()
    help_text = HelpTextBlock()

    class Meta:
        label = "Form fields"
        icon = "form"
        help_text = "Build forms with text, choice, and layout blocks."


FORM_FIELD_BLOCKS = list(FormFieldsStreamBlock.base_blocks.items())
