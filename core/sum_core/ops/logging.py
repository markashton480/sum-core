"""
Name: Structured Logging Configuration
Path: core/sum_core/ops/logging.py
Purpose: JSON structured logging for production with request_id correlation.
Family: Ops/Observability (Milestone 4)
Dependencies: Python logging, json
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any


class RequestIdFilter(logging.Filter):
    """
    Logging filter that adds request_id to log records.

    Retrieves the request_id from the context variable set by
    CorrelationIdMiddleware.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        from sum_core.ops.middleware import get_request_id

        if not hasattr(record, "request_id"):
            record.request_id = get_request_id() or "-"
        return True


class JsonFormatter(logging.Formatter):
    """
    Formatter that outputs JSON strings.

    Fields included:
    - timestamp (ISO 8601)
    - level
    - logger
    - message
    - request_id (if present)
    - extra fields (key/value pairs)
    - exception info (if present)
    """

    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),  # noqa: UP017
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }

        # Add extra fields if present (from logger.info("msg", extra={...}))
        if hasattr(record, "__dict__"):
            # Standard log record attributes to exclude
            exclude_attrs = {
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "exc_info",
                "exc_text",
                "thread",
                "threadName",
                "message",
                "request_id",
                "taskName",
            }
            for key, value in record.__dict__.items():
                if key not in exclude_attrs and not key.startswith("_"):
                    log_data[key] = value

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, default=str)


def get_logging_config(
    debug: bool = False,
    log_level: str = "INFO",
) -> dict[str, Any]:
    """
    Get Django LOGGING configuration dict.

    Args:
        debug: If True, use readable console format. If False, use JSON.
        log_level: Default log level (default: INFO).

    Returns:
        LOGGING configuration dict for Django settings.
    """
    # Allow override from environment
    log_level = os.environ.get("LOG_LEVEL", log_level).upper()
    # use_json logic embodied in condition below

    if debug and os.environ.get("LOG_FORMAT", "auto").lower() != "json":
        # Development: readable console output
        formatter = "verbose"
    else:
        # Production: JSON structured logging
        formatter = "json"

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "request_id": {
                "()": "sum_core.ops.logging.RequestIdFilter",
            },
        },
        "formatters": {
            "verbose": {
                "format": "[{asctime}] [{levelname}] [{name}] [{request_id}] {message}",
                "style": "{",
            },
            "json": {
                "()": "sum_core.ops.logging.JsonFormatter",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": formatter,
                "filters": ["request_id"],
            },
        },
        "root": {
            "handlers": ["console"],
            "level": log_level,
        },
        "loggers": {
            "django": {
                "handlers": ["console"],
                "level": log_level,
                "propagate": False,
            },
            "django.request": {
                "handlers": ["console"],
                "level": log_level,
                "propagate": False,
            },
            "sum_core": {
                "handlers": ["console"],
                "level": log_level,
                "propagate": False,
            },
            "celery": {
                "handlers": ["console"],
                "level": log_level,
                "propagate": False,
            },
        },
    }
