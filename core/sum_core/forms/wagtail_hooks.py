"""
Name: Forms Wagtail hooks
Path: core/sum_core/forms/wagtail_hooks.py
Purpose: Add custom admin actions for FormDefinition snippets.
Family: Forms, Admin UX.
Dependencies: Wagtail hooks, snippet action menu.
"""

from __future__ import annotations

from django.contrib.admin.utils import quote
from django.urls import reverse
from sum_core.forms.models import FormDefinition
from wagtail import hooks
from wagtail.snippets.action_menu import ActionMenuItem
from wagtail.snippets.permissions import get_permission_name


class CloneFormDefinitionMenuItem(ActionMenuItem):
    label = "Clone"
    name = "action-clone"
    icon_name = "copy"
    order = 70
    template_name = "sum_core/forms/action_menu/clone.html"

    def is_shown(self, context):
        if context.get("view") != "edit":
            return False

        if context.get("model") is not FormDefinition:
            return False

        request = context.get("request")
        if not request:
            return False

        add_perm = get_permission_name("add", FormDefinition)
        change_perm = get_permission_name("change", FormDefinition)
        return request.user.has_perm(add_perm) and request.user.has_perm(change_perm)

    def get_url(self, parent_context):
        instance = parent_context.get("instance")
        if not instance:
            return None

        namespace = (
            f"wagtailsnippets_{instance._meta.app_label}_{instance._meta.model_name}"
        )
        return reverse(f"{namespace}:clone", args=[quote(instance.pk)])


class PreviewFormDefinitionMenuItem(ActionMenuItem):
    label = "Preview"
    name = "action-preview"
    icon_name = "view"
    order = 60

    def is_shown(self, context):
        if context.get("view") != "edit":
            return False

        if context.get("model") is not FormDefinition:
            return False

        request = context.get("request")
        if not request:
            return False

        change_perm = get_permission_name("change", FormDefinition)
        return request.user.has_perm(change_perm)

    def get_url(self, parent_context):
        instance = parent_context.get("instance")
        if not instance:
            return None

        namespace = (
            f"wagtailsnippets_{instance._meta.app_label}_{instance._meta.model_name}"
        )
        return reverse(f"{namespace}:preview", args=[quote(instance.pk)])


class UsageFormDefinitionMenuItem(ActionMenuItem):
    label = "Usage"
    name = "action-usage"
    icon_name = "list-ul"
    order = 65

    def is_shown(self, context):
        if context.get("view") != "edit":
            return False

        if context.get("model") is not FormDefinition:
            return False

        request = context.get("request")
        if not request:
            return False

        change_perm = get_permission_name("change", FormDefinition)
        return request.user.has_perm(change_perm)

    def get_url(self, parent_context):
        instance = parent_context.get("instance")
        if not instance:
            return None

        namespace = (
            f"wagtailsnippets_{instance._meta.app_label}_{instance._meta.model_name}"
        )
        return reverse(f"{namespace}:usage_report", args=[quote(instance.pk)])


@hooks.register("register_snippet_action_menu_item")
def register_form_definition_clone_menu_item(model):
    if model is FormDefinition:
        return CloneFormDefinitionMenuItem()
    return None


@hooks.register("register_snippet_action_menu_item")
def register_form_definition_preview_menu_item(model):
    if model is FormDefinition:
        return PreviewFormDefinitionMenuItem()
    return None


@hooks.register("register_snippet_action_menu_item")
def register_form_definition_usage_menu_item(model):
    if model is FormDefinition:
        return UsageFormDefinitionMenuItem()
    return None
