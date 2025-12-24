"""
Name: Process & FAQ Blocks
Path: core/sum_core/blocks/process_faq.py
Purpose: StreamField blocks for Process Steps and FAQ accordions.
Family: SUM core StreamField blocks (Process & FAQ).
Dependencies: Wagtail blocks, Django utilities, json.
"""

import json

from django.utils.html import strip_tags
from wagtail import blocks


class ProcessStepBlock(blocks.StructBlock):
    """
    A single step within the ProcessStepsBlock.
    """

    number = blocks.IntegerBlock(
        required=False,
        min_value=1,
        max_value=20,
        help_text="Optional. If omitted, steps are auto-numbered.",
    )
    title = blocks.CharBlock(required=True)
    description = blocks.RichTextBlock(
        required=False,
        features=["bold", "italic", "link", "ul", "ol", "document-link"],
        help_text="Description of the step.",
    )

    class Meta:
        icon = "list-ol"
        label = "Process Step"


class ProcessStepsBlock(blocks.StructBlock):
    """
    Timeline/steps layout block.
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
    steps = blocks.ListBlock(ProcessStepBlock(), min_num=3, max_num=8)

    class Meta:
        icon = "list-ol"
        label = "Process Steps"
        template = "sum_core/blocks/process_steps.html"
        group = "Sections"


class FAQItemBlock(blocks.StructBlock):
    """
    A single FAQ question and answer.
    """

    question = blocks.CharBlock(required=True)
    answer = blocks.RichTextBlock(
        required=True,
        features=["h3", "h4", "bold", "italic", "link", "ul", "ol", "document-link"],
    )

    class Meta:
        icon = "help"
        label = "FAQ Item"


class FAQBlock(blocks.StructBlock):
    """
    Accordion-style FAQ block with valid JSON-LD schema.
    """

    eyebrow = blocks.CharBlock(required=False)
    heading = blocks.RichTextBlock(required=True, features=["italic", "bold"])
    intro = blocks.RichTextBlock(required=False, features=["bold", "italic", "link"])
    items = blocks.ListBlock(FAQItemBlock(), min_num=1, max_num=20)
    allow_multiple_open = blocks.BooleanBlock(
        required=False,
        default=True,
        help_text="If unchecked, opening one item closes others.",
    )

    def get_context(self, value, parent_context=None):
        context = super().get_context(value, parent_context=parent_context)

        # Build JSON-LD schema
        main_entity = []
        for item in value.get("items", []):
            question = item.get("question", "")
            # Handle RichText or str for answer
            raw_answer = item.get("answer", "")
            if hasattr(raw_answer, "source"):
                answer_text = strip_tags(raw_answer.source)
            else:
                answer_text = strip_tags(str(raw_answer))

            main_entity.append(
                {
                    "@type": "Question",
                    "name": question,
                    "acceptedAnswer": {"@type": "Answer", "text": answer_text},
                }
            )

        schema_data = {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": main_entity,
        }

        context["faq_schema_json"] = json.dumps(schema_data)
        return context

    class Meta:
        icon = "help"
        label = "FAQ"
        template = "sum_core/blocks/faq.html"
        group = "Sections"
