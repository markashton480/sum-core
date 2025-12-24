"""
Name: Correlation ID Middleware
Path: core/sum_core/ops/middleware.py
Purpose: Add request correlation IDs for distributed tracing and log correlation.
Family: Ops/Observability (Milestone 4)
Dependencies: Django, uuid
"""

from __future__ import annotations

import contextvars
import uuid
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

# Context variable to store request_id for the current request context
# This allows logging filters and other code to access the request_id
# without needing access to the request object.
_request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)

REQUEST_ID_HEADER = "X-Request-ID"


def get_request_id() -> str | None:
    """
    Get the current request ID from context.

    Returns:
        The request ID string if in a request context, None otherwise.
    """
    return _request_id_var.get()


class CorrelationIdMiddleware:
    """
    Middleware that manages request correlation IDs.

    - Reads incoming X-Request-ID header if present, else generates a UUID
    - Stores the ID on request.request_id
    - Makes ID available via context variable for logging
    - Sets X-Request-ID response header
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Get or generate request ID
        request_id = request.headers.get(REQUEST_ID_HEADER)
        if not request_id:
            request_id = str(uuid.uuid4())

        # Store on request object for direct access
        request.request_id = request_id

        # Store in context variable for logging filter access
        token = _request_id_var.set(request_id)

        try:
            response = self.get_response(request)

            # Set response header
            response[REQUEST_ID_HEADER] = request_id

            return response
        finally:
            # Reset context variable after request completes
            _request_id_var.reset(token)
