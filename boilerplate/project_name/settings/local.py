"""
Local development settings.

This file contains settings for local development only.
Uses SQLite and in-memory services for simplicity.
"""
from __future__ import annotations

from sum_core.ops.logging import get_logging_config
from sum_core.ops.sentry import init_sentry

from .base import *  # noqa: F401, F403

# =============================================================================
# Debug Settings
# =============================================================================

DEBUG: bool = True
ALLOWED_HOSTS: list[str] = ["localhost", "127.0.0.1", "[::1]", "testserver"]

# =============================================================================
# Database - SQLite for local development
# =============================================================================

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",  # noqa: F405
    }
}

# =============================================================================
# Cache - Local memory cache for development
# =============================================================================

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "client-cache",
    }
}

# =============================================================================
# Celery - Run tasks synchronously for local development
# =============================================================================

CELERY_TASK_ALWAYS_EAGER: bool = True
CELERY_TASK_EAGER_PROPAGATES: bool = True

# =============================================================================
# Observability (sum_core.ops)
# =============================================================================

LOGGING = get_logging_config(debug=DEBUG)

# Initialize Sentry if SENTRY_DSN is set (no-ops otherwise)
init_sentry()
