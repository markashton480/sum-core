"""
Name: Sum Core Wagtail hooks
Path: core/sum_core/wagtail_hooks.py
Purpose: Register shared Wagtail admin hooks for sum_core.
"""

from django.templatetags.static import static
from django.utils.html import format_html
from wagtail import hooks


@hooks.register("insert_global_admin_js")
def insert_universal_link_admin_js() -> str:
    """Inject UniversalLinkBlock admin UX behavior into the Wagtail editor."""
    return format_html(
        '<script src="{}"></script>',
        static("sum_core/js/universal_link_admin.js"),
    )
