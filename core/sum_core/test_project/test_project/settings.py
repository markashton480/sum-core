"""
Name: Test Project Settings
Path: core/sum_core/test_project/test_project/settings.py
Purpose: Minimal Django/Wagtail settings for validating the sum_core package.
Family: Used exclusively by the sum_core.test_project for local and CI validation.
Dependencies: Django, Wagtail, sum_core
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

from sum_core.ops.logging import get_logging_config
from sum_core.ops.sentry import init_sentry

# Wagtail Settings
WAGTAIL_SITE_NAME: str = "SUM Test Project"
WAGTAIL_ENABLE_UPDATE_CHECK = "lts"
WAGTAILADMIN_BASE_URL: str = "http://localhost:8000"

# Wagtail file upload limits (default is 10MB, increased to 50MB to match Django limits)
WAGTAILIMAGES_MAX_UPLOAD_SIZE: int = 52_428_800  # 50MB
WAGTAILDOCS_MAX_UPLOAD_SIZE: int = 52_428_800  # 50MB

BASE_DIR: Path = Path(__file__).resolve().parent.parent

# Detect test runs early so we can keep template resolution deterministic.
# During pytest runs we ALWAYS resolve theme templates from theme/active/templates
# (and let tests explicitly install Theme A there), rather than auto-pointing at
# any repo-local Theme A directories.
RUNNING_TESTS = any("pytest" in arg for arg in sys.argv)

# CI environment detection - GitHub Actions sets CI=true
# Used to skip database validation for commands like makemigrations that don't need a real DB
RUNNING_IN_CI = os.getenv("CI", "").lower() == "true"

# Commands that don't require database connection (schema inspection only)
_DB_OPTIONAL_COMMANDS = {"makemigrations", "showmigrations", "check", "diffsettings"}
_SKIP_DB_VALIDATION = any(cmd in sys.argv for cmd in _DB_OPTIONAL_COMMANDS)

ENV_FILE_PATH: Path | None = None


def _load_env_file() -> Path | None:
    """
    Lightweight .env loader so the test project picks up DB settings without
    requiring python-dotenv. Walks up the tree to find the first .env file.
    """
    for directory in [
        Path(__file__).resolve().parent,
        *Path(__file__).resolve().parents,
    ]:
        candidate = directory / ".env"
        if not candidate.exists():
            continue
        for raw_line in candidate.read_text().splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)
        return candidate
    return None


ENV_FILE_PATH = _load_env_file()

SECRET_KEY: str = "dev-only-not-for-production"
DEBUG: bool = True
ALLOWED_HOSTS: list[str] = ["localhost", "testserver", "127.0.0.1", "[::1]"]
if os.getenv("ALLOWED_HOSTS_EXTRA"):
    ALLOWED_HOSTS.extend(os.getenv("ALLOWED_HOSTS_EXTRA", "").split(","))

CSRF_TRUSTED_ORIGINS: list[str] = [
    origin.strip()
    for origin in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]

VISUAL_TEST: bool = os.getenv("VISUAL_TEST") == "1"
VISUAL_TEST_FROZEN_ISO: str = os.getenv(
    "VISUAL_TEST_FROZEN_ISO", "2025-10-14T00:00:00Z"
)
try:
    _frozen_iso = VISUAL_TEST_FROZEN_ISO.replace("Z", "+00:00")
    VISUAL_TEST_FROZEN_YEAR: int = datetime.fromisoformat(_frozen_iso).year
except ValueError:
    VISUAL_TEST_FROZEN_YEAR = 2025

INSTALLED_APPS: list[str] = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Wagtail core and contrib apps
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
    # Project apps
    "sum_core",
    "sum_core.pages",
    "sum_core.banners",
    "sum_core.navigation",
    "sum_core.leads",
    "sum_core.forms",
    "sum_core.analytics",
    "sum_core.seo",
    "sum_core.seo_engine",
    "sum_core.wagtail_trash",
    "home",
]

# Cache configuration (used for rate limiting)
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "sum-core-cache",
    }
}

MIDDLEWARE: list[str] = [
    "sum_core.ops.middleware.CorrelationIdMiddleware",  # Must be early for request_id
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "wagtail.contrib.redirects.middleware.RedirectMiddleware",
]

# Allow Wagtail admin preview iframe to load pages from the same origin
X_FRAME_OPTIONS: str = "SAMEORIGIN"

ROOT_URLCONF: str = "test_project.urls"

REPO_ROOT: Path = BASE_DIR.parent.parent.parent
ACTIVE_THEME_SLUG: str = os.getenv("ACTIVE_THEME_SLUG", "theme_a")
THEME_ACTIVE_TEMPLATES_DIR: Path = BASE_DIR / "theme" / "active" / "templates"

# -----------------------------------------------------------------------------
# Template Resolution Order (deterministic, first-existing wins)
# -----------------------------------------------------------------------------
# 1. Client-owned theme: theme/active/templates (installed by `sum init`)
# 2. Repo-root theme: themes/theme_a/templates (local dev convenience)
# 3. Legacy fallback: core-relative path (deprecated, kept for backwards compat)
# 4. Client overrides: templates/overrides
# 5. Core package APP_DIRS fallback: sum_core/templates (always available)
#
# This order is IDENTICAL in test and production. Do NOT add RUNNING_TESTS
# conditionals here — template resolution must be deterministic.
# -----------------------------------------------------------------------------
THEME_TEMPLATES_CANDIDATES: list[Path] = [
    THEME_ACTIVE_TEMPLATES_DIR,
    REPO_ROOT / "themes" / ACTIVE_THEME_SLUG / "templates",
    BASE_DIR.parent / "themes" / ACTIVE_THEME_SLUG / "templates",
]
THEME_TEMPLATE_DIRS: list[Path] = [
    candidate for candidate in THEME_TEMPLATES_CANDIDATES if candidate.exists()
]
if not THEME_TEMPLATE_DIRS:
    THEME_TEMPLATE_DIRS = [THEME_ACTIVE_TEMPLATES_DIR]

THEME_TEMPLATES_DIR: Path = THEME_TEMPLATE_DIRS[0]
CLIENT_OVERRIDES_DIR: Path = BASE_DIR / "templates" / "overrides"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # Per v0.6 theme-owned rendering contract:
        # 1. theme/active/templates (client-owned theme)
        # 2. repo-root theme fallback (local dev convenience)
        # 3. templates/overrides (client overrides)
        # 4. APP_DIRS fallback (sum_core/templates)
        "DIRS": [*THEME_TEMPLATE_DIRS, CLIENT_OVERRIDES_DIR],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "sum_core.context_processors.visual_test",
            ],
        },
    },
]

WSGI_APPLICATION: str = "test_project.wsgi.application"

DB_NAME = os.getenv("DJANGO_DB_NAME")
DB_USER = os.getenv("DJANGO_DB_USER")
DB_PASSWORD = os.getenv("DJANGO_DB_PASSWORD")
DB_HOST = os.getenv("DJANGO_DB_HOST")
DB_PORT = os.getenv("DJANGO_DB_PORT", "5432")


def _validate_db_env() -> None:
    """Validate database environment configuration.

    For development (non-test) runs, Postgres is REQUIRED. This ensures all agents
    share the same database state and prevents silent SQLite fallback issues.

    For tests, SQLite in-memory is used by default for speed, unless SUM_TEST_DB=postgres.
    """
    required_present = DB_NAME and DB_HOST
    supplied_any = any([DB_NAME, DB_USER, DB_PASSWORD, DB_HOST])

    if not required_present:
        if supplied_any:
            # Partial config - tell them what's missing
            missing = []
            if not DB_NAME:
                missing.append("DJANGO_DB_NAME")
            if not DB_HOST:
                missing.append("DJANGO_DB_HOST")
            raise ValueError(
                "Partial Postgres configuration supplied. Missing required env vars: "
                + ", ".join(missing)
            )
        else:
            # No config at all - explain the setup
            raise ValueError(
                "Database configuration required.\n\n"
                "The test project requires Postgres for development. SQLite is only "
                "used during pytest runs.\n\n"
                "To set up:\n"
                "  1. cp .env.example .env\n"
                "  2. make db-up\n"
                "  3. make dev-reset  # migrate + seed\n\n"
                "See AGENTS.md for full setup instructions."
            )


USE_POSTGRES_FOR_TESTS = os.getenv("SUM_TEST_DB", "sqlite").lower() == "postgres"

# Development runs require Postgres - fail fast if not configured
# Skip validation for: tests, CI makemigrations, and other DB-optional commands
if not RUNNING_TESTS and not _SKIP_DB_VALIDATION:
    _validate_db_env()

# Database configuration: Postgres for dev, SQLite for tests (unless overridden)
if (RUNNING_TESTS and not USE_POSTGRES_FOR_TESTS) or _SKIP_DB_VALIDATION:
    # Tests and DB-optional commands use in-memory SQLite for speed
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }
else:
    # Development and Postgres-backed tests use Postgres
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": DB_NAME,
            "USER": DB_USER,
            "PASSWORD": DB_PASSWORD,
            "HOST": DB_HOST,
            "PORT": DB_PORT,
        }
    }

AUTH_PASSWORD_VALIDATORS: list[dict[str, str]] = []

LANGUAGE_CODE: str = "en-gb"
TIME_ZONE: str = "Europe/London"
USE_I18N: bool = True
USE_TZ: bool = True


# Media

FILE_UPLOAD_MAX_MEMORY_SIZE = 52_428_800  # 50MB

DATA_UPLOAD_MAX_MEMORY_SIZE = 52_428_800  # 50MB

MEDIA_URL: str = "/images/"
_REPO_ROOT: Path | None = None
for directory in [BASE_DIR, *BASE_DIR.parents]:
    if (directory / ".git").exists():
        _REPO_ROOT = directory
        break

MEDIA_ROOT: Path = Path(
    os.getenv("SUM_MEDIA_ROOT", str((_REPO_ROOT or Path.cwd()) / "media"))
)

STATIC_URL: str = "/static/"

THEME_ACTIVE_STATIC_DIR: Path = BASE_DIR / "theme" / "active" / "static"
THEME_STATIC_CANDIDATES: list[Path] = [
    THEME_ACTIVE_STATIC_DIR,
    REPO_ROOT / "themes" / ACTIVE_THEME_SLUG / "static",
    BASE_DIR.parent / "themes" / ACTIVE_THEME_SLUG / "static",
]
THEME_STATIC_DIRS: list[Path] = [
    candidate for candidate in THEME_STATIC_CANDIDATES if candidate.exists()
]
if not THEME_STATIC_DIRS:
    THEME_STATIC_DIRS = [THEME_ACTIVE_STATIC_DIR]

THEME_STATIC_DIR: Path = THEME_STATIC_DIRS[0]
STATICFILES_DIRS: list[Path] = [
    # Per v0.6 theme-owned rendering contract: client-owned theme statics first.
    *THEME_STATIC_DIRS,
]

DEFAULT_AUTO_FIELD: str = "django.db.models.BigAutoField"

# Celery Configuration
# In test project, tasks run synchronously for predictable testing
CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "memory://")
CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "cache+memory://")
CELERY_TASK_ALWAYS_EAGER: bool = True  # Run tasks synchronously
CELERY_TASK_EAGER_PROPAGATES: bool = True  # Propagate exceptions in eager mode

# Image optimization defaults
SUM_CORE_IMAGE_OPTIMIZATION_ENABLED: bool = True
SUM_CORE_IMAGE_PROFILE_OVERRIDES: dict[str, dict[str, object]] = {}
SUM_CORE_IMAGE_PREGENERATE_ON_UPLOAD: bool = True
SUM_CORE_IMAGE_PREGENERATE_ON_ATTACH: bool = True
SUM_CORE_IMAGE_PREGENERATE_ON_PUBLISH: bool = True
SUM_CORE_IMAGE_PREGENERATE_UPLOAD_PROFILES: list[str] = [
    "hero_full",
    "card_landscape",
    "content_inline",
    "logo",
    "og_social",
]
SUM_CORE_IMAGE_PREGENERATE_ATTACH_PROFILES: list[str] = [
    "hero_full",
    "hero_block",
    "card_landscape",
    "content_inline",
    "og_social",
]
SUM_CORE_IMAGE_PREGENERATE_SYNC_IN_TESTS: bool = True
SUM_CORE_IMAGE_PREGENERATE_LOCK_SECONDS: int = 180

# Forms Configuration
# Silence Django 6.0 deprecation warning about URL scheme
# Default scheme will change from 'http' to 'https' in Django 6.0
FORMS_URLFIELD_ASSUME_HTTPS: bool = True

# Email Configuration
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

# Lead Notification Settings
LEAD_NOTIFICATION_EMAIL: str = os.getenv("LEAD_NOTIFICATION_EMAIL", "")

# Webhook Configuration
ZAPIER_WEBHOOK_URL: str = os.getenv("ZAPIER_WEBHOOK_URL", "")

# =============================================================================
# Logging Configuration
# =============================================================================


LOGGING = get_logging_config(debug=DEBUG)

# =============================================================================
# Sentry Integration (optional - only if SENTRY_DSN is set)
# =============================================================================


init_sentry()
