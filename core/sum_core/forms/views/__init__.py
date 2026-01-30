"""
Form views package - re-exports for backwards compatibility.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.http import HttpRequest, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_protect

from .base import (
    UK_PHONE_REGEX,
    build_attribution_data,
    format_form_errors,
    get_config,
    get_site,
    parse_request_data,
    spam_response,
)
from .dynamic import (
    build_dynamic_form_data,
    cleanup_uploaded_files,
    get_form_definition,
    handle_dynamic_form_submission,
    queue_dynamic_form_tasks,
    store_uploaded_file,
    validate_dynamic_lead_fields,
)
from .static import (
    create_static_lead,
    handle_static_form_submission,
    queue_static_notification_tasks,
    validate_static_submission,
)

if TYPE_CHECKING:
    from wagtail.models import Site


@method_decorator(csrf_protect, name="dispatch")
class FormSubmissionView(View):
    """
    Handle form submissions from Contact and Quote forms.

    Accepts POST with JSON or form-encoded data.
    Performs spam checks, validates input, and creates Lead records.

    Response codes:
    - 200: Success, Lead created
    - 400: Validation error (missing fields, spam detected)
    - 429: Rate limit exceeded
    - 405: Method not allowed (not POST)
    """

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        data = parse_request_data(request)
        if data is None:
            return JsonResponse(
                {"success": False, "errors": {"__all__": ["Invalid request data"]}},
                status=400,
            )

        site = get_site(request)
        if site is None:
            return JsonResponse(
                {"success": False, "errors": {"__all__": ["Site not found"]}},
                status=400,
            )

        if data.get("form_definition_id"):
            return handle_dynamic_form_submission(request, data, site)

        return handle_static_form_submission(request, data, site)

    # Backwards compatibility: expose methods that match original class interface
    def _parse_request_data(self, request: HttpRequest) -> dict[str, Any] | None:
        return parse_request_data(request)

    def _get_site(self, request: HttpRequest) -> Site | None:
        return get_site(request)

    def _get_config(self, site: Site):
        return get_config(site)

    def _validate_submission(self, data: dict, config) -> dict:
        return validate_static_submission(data, config)

    def _validate_dynamic_lead_fields(self, cleaned_data: dict[str, Any]) -> dict:
        return validate_dynamic_lead_fields(cleaned_data)

    def _build_dynamic_form_data(self, form, form_definition, request: HttpRequest):
        return build_dynamic_form_data(form, form_definition, request)

    def _store_uploaded_file(self, uploaded_file, form_definition, field_name: str):
        return store_uploaded_file(uploaded_file, form_definition, field_name)

    def _cleanup_uploaded_files(self, form_data: dict[str, Any]) -> None:
        return cleanup_uploaded_files(form_data)

    def _build_attribution_data(self, data: dict[str, Any], request: HttpRequest):
        return build_attribution_data(data, request)

    def _format_form_errors(self, form) -> dict[str, list[str]]:
        return format_form_errors(form)

    def _get_form_definition(self, form_definition_id, site):
        return get_form_definition(form_definition_id, site)

    def _spam_response(self, spam_result, request: HttpRequest):
        return spam_response(spam_result, request)

    def _create_lead(self, data: dict, site):
        return create_static_lead(data, site)

    def _queue_notification_tasks(self, lead, site_id: int, request) -> None:
        return queue_static_notification_tasks(lead, site_id, request)

    def _queue_dynamic_form_tasks(self, lead, form_definition, request) -> None:
        return queue_dynamic_form_tasks(lead, form_definition, request)

    def _handle_static_form_submission(
        self, request: HttpRequest, data: dict[str, Any], site
    ) -> JsonResponse:
        return handle_static_form_submission(request, data, site)

    def _handle_dynamic_form_submission(
        self, request: HttpRequest, data: dict[str, Any], site
    ) -> JsonResponse:
        return handle_dynamic_form_submission(request, data, site)


form_submission_view = FormSubmissionView.as_view()

__all__ = [
    "UK_PHONE_REGEX",
    "FormSubmissionView",
    "build_attribution_data",
    "build_dynamic_form_data",
    "cleanup_uploaded_files",
    "create_static_lead",
    "form_submission_view",
    "format_form_errors",
    "get_config",
    "get_form_definition",
    "get_site",
    "handle_dynamic_form_submission",
    "handle_static_form_submission",
    "parse_request_data",
    "queue_dynamic_form_tasks",
    "queue_static_notification_tasks",
    "spam_response",
    "store_uploaded_file",
    "validate_dynamic_lead_fields",
    "validate_static_submission",
]
