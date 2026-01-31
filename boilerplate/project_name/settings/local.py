"""
Local development settings.

This file contains settings for local development only.
Uses SQLite and in-memory services for simplicity.
"""

from __future__ import annotations

import os

from sum_core.ops.logging import get_logging_config
from sum_core.ops.sentry import init_sentry

from .base import *  # noqa: F401, F403

# =============================================================================
# Debug Settings
# =============================================================================

DEBUG: bool = True
ALLOWED_HOSTS: list[str] = ["localhost", "127.0.0.1", "[::1]", "testserver"]

# Support additional hosts via environment variable (e.g., for ngrok, custom domains)
_allowed_hosts_extra = os.getenv("ALLOWED_HOSTS_EXTRA", "")
if _allowed_hosts_extra:
    ALLOWED_HOSTS.extend(
        host.strip() for host in _allowed_hosts_extra.split(",") if host.strip()
    )

# CSRF trusted origins for local dev with tunnels/custom domains
CSRF_TRUSTED_ORIGINS: list[str] = [
    origin.strip()
    for origin in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]

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
