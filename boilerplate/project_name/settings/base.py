"""
Base Django/Wagtail settings shared across all environments.

This file contains settings common to both local development and production.
Environment-specific settings should be placed in local.py or production.py.

Replace 'project_name' with your actual project name after copying.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

# =============================================================================
# Core Django Settings
# =============================================================================

BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent

# =============================================================================
# Theme Configuration
# =============================================================================
#
# Per THEME-ARCHITECTURE-SPECv1, themes are copied into the client project
# at init-time. Runtime template/static resolution uses theme/active/, NOT
# sum_core. The .sum/theme.json file is for provenance tracking only.
#


def _get_canonical_theme_root() -> Path | None:
    """
    Optional dev override to load templates/static directly from canonical theme.

    Controlled via SUM_CANONICAL_THEME_ROOT. If set, we validate the path and
    prefer canonical assets ahead of theme/active.
    """

    canonical_root_env = os.getenv("SUM_CANONICAL_THEME_ROOT")
    if not canonical_root_env:
        return None

    canonical_root = Path(canonical_root_env)
    templates_dir = canonical_root / "templates"

    if not canonical_root.exists():
        raise ImproperlyConfigured(
            f"SUM_CANONICAL_THEME_ROOT='{canonical_root_env}' does not exist. "
            "Expected <root>/templates and optional <root>/static. "
            "Unset SUM_CANONICAL_THEME_ROOT to disable."
        )

    if not templates_dir.exists():
        raise ImproperlyConfigured(
            f"SUM_CANONICAL_THEME_ROOT='{canonical_root_env}' is missing required "
            "<root>/templates. Expected layout: <root>/templates and optional "
            "<root>/static. Unset SUM_CANONICAL_THEME_ROOT to disable."
        )

    return canonical_root


def _get_project_theme_slug() -> str | None:
    """
    Read the selected theme slug from .sum/theme.json for logging/debugging.

    This is provenance only - not used for runtime loading.

    Returns:
        Theme slug if configured, None otherwise
    """
    theme_file = BASE_DIR / ".sum" / "theme.json"
    if not theme_file.exists():
        return None

    try:
        with theme_file.open("r", encoding="utf-8") as f:
            config = json.load(f)
        theme_value = config.get("theme")
        return theme_value if isinstance(theme_value, str) else None
    except (json.JSONDecodeError, OSError):
        return None


def _get_theme_template_dirs() -> list[Path]:
    """
    Get template directories for the active theme.

    Per THEME-ARCHITECTURE-SPECv1, templates are resolved from:
    0. SUM_CANONICAL_THEME_ROOT/templates (optional dev override, highest priority)
    1. theme/active/templates/ (client-owned theme)
    2. templates/overrides/ (client-specific overrides)
    3. APP_DIRS (sum_core fallback)

    Returns:
        List of theme template directory paths (empty if no theme installed)
    """
    canonical_theme_root = _get_canonical_theme_root()

    theme_template_dirs: list[Path] = []
    if canonical_theme_root:
        theme_template_dirs.append(canonical_theme_root / "templates")

    theme_templates_dir = BASE_DIR / "theme" / "active" / "templates"
    if theme_templates_dir.exists():
        theme_template_dirs.append(theme_templates_dir)

    return theme_template_dirs


# Theme slug from provenance (for logging/debugging only)
THEME_SLUG = _get_project_theme_slug()

# SECURITY WARNING: keep the secret key used in production secret!
# Override this via environment variable in production
SECRET_KEY: str = os.getenv(
    "DJANGO_SECRET_KEY", "insecure-dev-only-change-in-production"
)

# =============================================================================
# Application Definition
# =============================================================================

INSTALLED_APPS: list[str] = [
    # Django core
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Wagtail core
    "wagtail",
    "wagtail.admin",
    "wagtail.users",
    "wagtail.images",
    "wagtail.documents",
    "wagtail.snippets",
    "wagtail.sites",
    "wagtail.search",
    "wagtail.contrib.forms",
    "wagtail.contrib.settings",
    "wagtail.contrib.redirects",
    # Wagtail dependencies
    "modelcluster",
    "taggit",
    # SUM Core apps (the reusable platform package)
    "sum_core",
    "sum_core.pages",
    "sum_core.navigation",
    "sum_core.leads",
    "sum_core.forms",
    "sum_core.analytics",
    "sum_core.seo",
    # Client home app (update after renaming project_name)
    "project_name.home",
]

MIDDLEWARE: list[str] = [
    "sum_core.ops.middleware.CorrelationIdMiddleware",  # Request correlation
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "wagtail.contrib.redirects.middleware.RedirectMiddleware",
]

ROOT_URLCONF: str = "project_name.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            # Per THEME-ARCHITECTURE-SPECv1, resolution order:
            # 0. SUM_CANONICAL_THEME_ROOT/templates (optional dev override)
            # 1. theme/active/templates/ (client-owned theme)
            # 2. templates/overrides/ (client-specific overrides)
            # 3. APP_DIRS (sum_core fallback)
            *_get_theme_template_dirs(),
            BASE_DIR / "templates" / "overrides",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION: str = "project_name.wsgi.application"

# =============================================================================
# Password Validation
# =============================================================================

AUTH_PASSWORD_VALIDATORS: list[dict[str, str]] = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# =============================================================================
# Internationalization
# =============================================================================

LANGUAGE_CODE: str = "en-gb"
TIME_ZONE: str = "Europe/London"
USE_I18N: bool = True
USE_TZ: bool = True

# =============================================================================
# Static & Media Files
# =============================================================================


def _get_theme_static_dirs() -> list[Path]:
    """
    Get static directories for the active theme.

    Per THEME-ARCHITECTURE-SPECv1, static files are resolved from:
    0. SUM_CANONICAL_THEME_ROOT/static/ (optional dev override, highest priority)
    1. theme/active/static/ (client-owned theme, highest priority)
    2. static/ (client-specific statics)
    3. APP_DIRS (sum_core fallback)

    Returns:
        List of theme static directory paths (empty if no theme installed)
    """
    canonical_theme_root = _get_canonical_theme_root()

    static_dirs: list[Path] = []
    if canonical_theme_root:
        canonical_static_dir = canonical_theme_root / "static"
        if canonical_static_dir.exists():
            static_dirs.append(canonical_static_dir)

    theme_static_dir = BASE_DIR / "theme" / "active" / "static"
    if theme_static_dir.exists():
        static_dirs.append(theme_static_dir)

    return static_dirs


STATIC_URL: str = "/static/"
STATICFILES_DIRS: list[Path] = [
    # Per THEME-ARCHITECTURE-SPECv1, resolution order:
    # 0. SUM_CANONICAL_THEME_ROOT/static/ (optional dev override)
    # 1. theme/active/static/ (client-owned theme, highest priority)
    # 2. static/ (client-specific statics)
    *_get_theme_static_dirs(),
    BASE_DIR / "static",
]
STATIC_ROOT: Path = Path(os.getenv("DJANGO_STATIC_ROOT", str(BASE_DIR / "staticfiles")))

MEDIA_URL: str = "/media/"
MEDIA_ROOT: Path = Path(os.getenv("DJANGO_MEDIA_ROOT", str(BASE_DIR / "media")))

DEFAULT_AUTO_FIELD: str = "django.db.models.BigAutoField"

# =============================================================================
# Wagtail Settings
# =============================================================================

# TODO: Update this to your site name
WAGTAIL_SITE_NAME: str = "My Site"
WAGTAILADMIN_BASE_URL: str = os.getenv("WAGTAILADMIN_BASE_URL", "http://localhost:8001")

# =============================================================================
# Celery Configuration (defaults for development)
# =============================================================================

CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "memory://")
CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "cache+memory://")

# =============================================================================
# Email Configuration (defaults for development)
# =============================================================================

EMAIL_BACKEND: str = os.getenv(
    "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST: str = os.getenv("EMAIL_HOST", "localhost")
EMAIL_PORT: int = int(os.getenv("EMAIL_PORT", "25"))
EMAIL_HOST_USER: str = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD: str = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS: bool = os.getenv("EMAIL_USE_TLS", "False").lower() == "true"
EMAIL_USE_SSL: bool = os.getenv("EMAIL_USE_SSL", "False").lower() == "true"
DEFAULT_FROM_EMAIL: str = os.getenv("DEFAULT_FROM_EMAIL", "noreply@example.com")

# =============================================================================
# Lead Notification Settings
# =============================================================================

LEAD_NOTIFICATION_EMAIL: str = os.getenv("LEAD_NOTIFICATION_EMAIL", "")

# =============================================================================
# Webhook Configuration
# =============================================================================

ZAPIER_WEBHOOK_URL: str = os.getenv("ZAPIER_WEBHOOK_URL", "")
