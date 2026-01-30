"""
Name: Shared form view utilities
Path: core/sum_core/forms/views/base.py
Purpose: Common validation, parsing, site handling, and spam checks for form submissions.
Family: Forms, Leads, Attribution.
Dependencies: FormConfiguration, Django cache, Wagtail Site.
"""

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING, Any, cast

from django.http import HttpRequest, JsonResponse
from sum_core.forms.models import FormConfiguration
from sum_core.forms.services import SpamCheckResult
from sum_core.leads.services import AttributionData
from wagtail.models import Site

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# UK phone validation regex - accepts common UK formats
# Matches: 07xxx, +447xxx, 0044 7xxx, 01xxx, 02xxx, 03xxx, etc.
UK_PHONE_REGEX = re.compile(
    r"^(?:"
    r"(?:\+44|0044)[\s\-]?7\d{3}[\s\-]?\d{6}"  # UK mobile with country code
    r"|07\d{3}[\s\-]?\d{6}"  # UK mobile without country code
    r"|(?:\+44|0044)[\s\-]?[123]\d{2,3}[\s\-]?\d{6,7}"  # UK landline with country code
    r"|0[123]\d{2,3}[\s\-]?\d{6,7}"  # UK landline without country code
    r")$"
)


def parse_request_data(request: HttpRequest) -> dict[str, Any] | None:
    """Parse request body as JSON or form data."""
    content_type = request.content_type or ""

    if "application/json" in content_type:
        try:
            return cast(dict[str, Any], json.loads(request.body))
        except (json.JSONDecodeError, ValueError):
            return None

    # Fall back to form-encoded data
    return cast(dict[str, Any], request.POST.dict())


def get_site(request: HttpRequest) -> Site | None:
    """Get the Wagtail Site for this request."""
    site = Site.find_for_request(request)
    if site is not None:
        return site

    return Site.objects.filter(is_default_site=True).first() or Site.objects.first()


def get_config(site: Site) -> FormConfiguration:
    """Get or create FormConfiguration for site."""
    return FormConfiguration.get_for_site(site)


def format_form_errors(form) -> dict[str, list[str]]:
    """Convert Django form errors to JSON-serializable dict."""
    errors: dict[str, list[str]] = {}
    for field, messages in form.errors.get_json_data().items():
        errors[field] = [entry.get("message", "") for entry in messages]
    return errors


def build_attribution_data(
    data: dict[str, Any], request: HttpRequest
) -> AttributionData:
    """Build AttributionData for form submissions."""

    def pick(*values: str | None) -> str:
        for value in values:
            if isinstance(value, str) and value:
                return value
        return ""

    referrer = request.META.get("HTTP_REFERER", "")
    return AttributionData(
        utm_source=pick(data.get("utm_source", ""), request.GET.get("utm_source", "")),
        utm_medium=pick(data.get("utm_medium", ""), request.GET.get("utm_medium", "")),
        utm_campaign=pick(
            data.get("utm_campaign", ""), request.GET.get("utm_campaign", "")
        ),
        utm_term=pick(data.get("utm_term", ""), request.GET.get("utm_term", "")),
        utm_content=pick(
            data.get("utm_content", ""), request.GET.get("utm_content", "")
        ),
        landing_page_url=pick(data.get("landing_page_url", ""), referrer, request.path),
        page_url=pick(data.get("page_url", ""), referrer),
        referrer_url=pick(data.get("referrer_url", ""), referrer),
    )


def spam_response(
    spam_result: SpamCheckResult, request: HttpRequest
) -> JsonResponse | None:
    """Return a JsonResponse for spam/rate-limit results."""
    if spam_result.should_rate_limit:
        return JsonResponse(
            {"success": False, "errors": {"__all__": ["Too many requests"]}},
            status=429,
        )

    if spam_result.is_spam:
        # Return 400 for spam (indistinguishable from validation error to bots)
        is_xhr = request.headers.get("X-Requested-With") == "XMLHttpRequest"
        if is_xhr and spam_result.reason.startswith("Submitted too quickly"):
            message = "Please wait a moment and try again."
        elif is_xhr and spam_result.reason == "Time token expired":
            message = "Please refresh the page and try again."
        else:
            message = "Invalid submission"

        return JsonResponse(
            {"success": False, "errors": {"__all__": [message]}},
            status=400,
        )

    return None
