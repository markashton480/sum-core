"""
Name: Sentry Integration
Path: core/sum_core/ops/sentry.py
Purpose: Conditional Sentry initialization for error tracking.
Family: Ops/Observability (Milestone 4)
Dependencies: sentry-sdk, Django, Celery
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

# List of sensitive field names to scrub from Sentry events
SENSITIVE_FIELDS = frozenset(
    {
        "email",
        "phone",
        "phone_number",
        "message",
        "password",
        "secret",
        "token",
        "api_key",
        "apikey",
        "credit_card",
        "ssn",
    }
)


def _strip_pii(event: dict, hint: dict) -> dict | None:
    """
    Sentry before_send hook to scrub PII from events.

    Removes sensitive data from breadcrumbs and event data to ensure
    we don't accidentally capture email addresses, phone numbers,
    or message content.
    """
    # Scrub sensitive fields from event data
    if "extra" in event:
        for field in SENSITIVE_FIELDS:
            if field in event["extra"]:
                event["extra"][field] = "[Filtered]"

    # Scrub breadcrumbs
    if "breadcrumbs" in event:
        for breadcrumb in event.get("breadcrumbs", {}).get("values", []):
            if "data" in breadcrumb:
                for field in SENSITIVE_FIELDS:
                    if field in breadcrumb["data"]:
                        breadcrumb["data"][field] = "[Filtered]"

    return event


def init_sentry() -> bool:
    """
    Initialize Sentry if SENTRY_DSN environment variable is set.

    Configures:
        - Django integration for request tracking
        - Celery integration for task error tracking
        - Logging integration (but not as breadcrumbs for PII safety)
        - Environment and release tags from env vars

    Returns:
        True if Sentry was initialized, False otherwise.
    """
    dsn = os.environ.get("SENTRY_DSN")

    if not dsn:
        logger.debug("SENTRY_DSN not set, Sentry integration disabled")
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.django import DjangoIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration

        # Configure logging integration - capture errors but not breadcrumbs
        # to avoid capturing PII in log messages
        logging_integration = LoggingIntegration(
            level=logging.INFO,  # Capture info and above as breadcrumbs
            event_level=logging.ERROR,  # Only send errors as events
        )

        sentry_sdk.init(
            dsn=dsn,
            environment=os.environ.get("SENTRY_ENVIRONMENT", "development"),
            release=os.environ.get("GIT_SHA") or os.environ.get("RELEASE"),
            integrations=[
                DjangoIntegration(),
                CeleryIntegration(),
                logging_integration,
            ],
            # Performance monitoring
            traces_sample_rate=float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0")),
            # Don't send PII
            send_default_pii=False,
            # Custom before_send hook for additional scrubbing
            before_send=_strip_pii,  # type: ignore[arg-type]
        )

        logger.info(
            "Sentry initialized",
            extra={
                "environment": os.environ.get("SENTRY_ENVIRONMENT", "development"),
                "release": os.environ.get("GIT_SHA") or os.environ.get("RELEASE"),
            },
        )
        return True

    except ImportError:
        logger.warning("sentry-sdk not installed, Sentry integration disabled")
        return False
    except Exception as e:
        logger.exception(f"Failed to initialize Sentry: {e}")
        return False


def set_sentry_context(request_id: str | None = None, **kwargs) -> None:
    """
    Set Sentry scope context for the current request/task.

    Args:
        request_id: The correlation ID to tag events with.
        **kwargs: Additional context key-value pairs.
    """
    try:
        import sentry_sdk

        with sentry_sdk.configure_scope() as scope:
            if request_id:
                scope.set_tag("request_id", request_id)

            for key, value in kwargs.items():
                if value is not None:
                    scope.set_tag(key, str(value))

    except ImportError:
        pass  # Sentry not installed
    except Exception:
        pass  # Don't break app if Sentry fails
