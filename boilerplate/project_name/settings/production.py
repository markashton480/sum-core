"""
Production settings.

This file contains settings for production deployments.
All sensitive values must be provided via environment variables.
"""
from __future__ import annotations

import os

from sum_core.ops.logging import get_logging_config
from sum_core.ops.sentry import init_sentry

from .base import *  # noqa: F401, F403

# =============================================================================
# Security Settings
# =============================================================================

DEBUG: bool = False

# SECURITY: ALLOWED_HOSTS must be set in production
ALLOWED_HOSTS: list[str] = os.getenv("ALLOWED_HOSTS", "").split(",")

# SECURITY: Enforce HTTPS
SECURE_SSL_REDIRECT: bool = os.getenv("SECURE_SSL_REDIRECT", "True").lower() == "true"
SESSION_COOKIE_SECURE: bool = True
CSRF_COOKIE_SECURE: bool = True
SECURE_BROWSER_XSS_FILTER: bool = True
SECURE_CONTENT_TYPE_NOSNIFF: bool = True
X_FRAME_OPTIONS: str = "DENY"

# HSTS settings
SECURE_HSTS_SECONDS: int = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS: bool = True
SECURE_HSTS_PRELOAD: bool = True

# =============================================================================
# Database - PostgreSQL for production
# =============================================================================

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ["DJANGO_DB_NAME"],
        "USER": os.environ["DJANGO_DB_USER"],
        "PASSWORD": os.environ["DJANGO_DB_PASSWORD"],
        "HOST": os.environ["DJANGO_DB_HOST"],
        "PORT": os.getenv("DJANGO_DB_PORT", "5432"),
        "CONN_MAX_AGE": 60,
        "OPTIONS": {
            "connect_timeout": 10,
        },
    }
}

# =============================================================================
# Cache - Redis for production
# =============================================================================

REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}

# =============================================================================
# Celery - Production broker configuration
# =============================================================================

CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", REDIS_URL)  # noqa: F405
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", REDIS_URL)  # noqa: F405
CELERY_TASK_ALWAYS_EAGER: bool = False
CELERY_TASK_EAGER_PROPAGATES: bool = False

# =============================================================================
# Static Files - Production configuration
# =============================================================================

# In production, static files should be served by a CDN or whitenoise
# This is a basic setup; extend as needed for your infrastructure

# =============================================================================
# Observability (sum_core.ops)
# =============================================================================

LOGGING = get_logging_config(debug=DEBUG)

# Initialize Sentry (required in production if SENTRY_DSN is set)
init_sentry()
