"""
Name: Form template tags
Path: core/sum_core/templatetags/form_tags.py
Purpose: Template tags for form hidden fields, time tokens, and attribution capture.
Family: Forms, Templates.
Dependencies: Django template system, sum_core.forms.services.
"""

from __future__ import annotations

from django import template
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from sum_core.forms.dynamic import DynamicFormGenerator
from sum_core.forms.services import generate_time_token

register = template.Library()


@register.filter(name="generate_dynamic_form")
def generate_dynamic_form(form_definition):
    """
    Return a dynamic form instance from a FormDefinition.

    Usage:
        {% load form_tags %}
        {% with form_class=form_definition|generate_dynamic_form %}
            {% with form=form_class %}
                {{ form }}
            {% endwith %}
        {% endwith %}
    """
    if not form_definition:
        return None

    form_class = DynamicFormGenerator(form_definition).generate_form_class()
    return form_class()


@register.filter(name="form_field")
def form_field(form, field_name):
    """Return a bound form field by name for template lookups."""
    if not form or not field_name:
        return None
    return form[field_name]


@register.simple_tag
def form_time_token() -> str:
    """
    Generate a hidden input field with a signed time token.

    This token is used to verify that a minimum time has passed between
    form render and submission (anti-bot protection).

    Usage:
        {% load form_tags %}
        <form>
            {% form_time_token %}
            ...
        </form>
    """
    token = generate_time_token()
    return str(
        format_html(
            '<input type="hidden" name="_time_token" value="{}">',
            token,
        )
    )


@register.simple_tag(takes_context=True)
def form_hidden_fields(context, form_type: str = "") -> str:
    """
    Generate all required hidden fields for form submission.

    Includes:
    - Time token (anti-bot)
    - Form type
    - Page URL (from context)

    Attribution fields (UTM params, referrer, landing page) are populated
    via JavaScript since they require client-side access.

    Usage:
        {% load form_tags %}
        <form>
            {% form_hidden_fields form_type="contact" %}
            ...
        </form>
    """
    request = context.get("request")
    page_url = ""
    if request:
        page_url = request.build_absolute_uri()

    token = generate_time_token()

    fields = [
        format_html(
            '<input type="hidden" name="_time_token" value="{}">',
            token,
        ),
        format_html(
            '<input type="hidden" name="form_type" value="{}">',
            form_type,
        ),
        format_html(
            '<input type="hidden" name="page_url" value="{}" class="js-page-url">',
            page_url,
        ),
        # These are populated by JavaScript
        '<input type="hidden" name="referrer_url" value="" class="js-referrer-url">',
        '<input type="hidden" name="landing_page_url" value="" class="js-landing-page-url">',
        '<input type="hidden" name="utm_source" value="" class="js-utm-source">',
        '<input type="hidden" name="utm_medium" value="" class="js-utm-medium">',
        '<input type="hidden" name="utm_campaign" value="" class="js-utm-campaign">',
        '<input type="hidden" name="utm_term" value="" class="js-utm-term">',
        '<input type="hidden" name="utm_content" value="" class="js-utm-content">',
    ]

    return str(mark_safe("\n".join(fields)))


@register.inclusion_tag("sum_core/includes/form_attribution_script.html")
def form_attribution_script() -> dict:
    """
    Include JavaScript for populating attribution hidden fields.

    This script captures UTM parameters from the URL and referrer from
    document.referrer, populating the corresponding hidden fields.

    Usage:
        {% load form_tags %}
        {% form_attribution_script %}
    """
    return {}
