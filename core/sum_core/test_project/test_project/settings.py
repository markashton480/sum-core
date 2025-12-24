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
from pathlib import Path

from sum_core.ops.logging import get_logging_config
from sum_core.ops.sentry import init_sentry

# Wagtail Settings
WAGTAIL_SITE_NAME: str = "SUM Test Project"
WAGTAIL_ENABLE_UPDATE_CHECK = "lts"
WAGTAILADMIN_BASE_URL: str = "http://localhost:8000"

BASE_DIR: Path = Path(__file__).resolve().parent.parent

# Detect test runs early so we can keep template resolution deterministic.
# During pytest runs we ALWAYS resolve theme templates from theme/active/templates
# (and let tests explicitly install Theme A there), rather than auto-pointing at
# any repo-local Theme A directories.
RUNNING_TESTS = any("pytest" in arg for arg in sys.argv)

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
    "sum_core.navigation",
    "sum_core.leads",
    "sum_core.forms",
    "sum_core.analytics",
    "sum_core.seo",
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

ROOT_URLCONF: str = "test_project.urls"

REPO_ROOT: Path = BASE_DIR.parent.parent.parent
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
    REPO_ROOT / "themes" / "theme_a" / "templates",
    BASE_DIR.parent / "themes" / "theme_a" / "templates",
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
    supplied_any = any([DB_NAME, DB_USER, DB_PASSWORD, DB_HOST])
    required_present = DB_NAME and DB_HOST
    if supplied_any and not required_present:
        missing = []
        if not DB_NAME:
            missing.append("DJANGO_DB_NAME")
        if not DB_HOST:
            missing.append("DJANGO_DB_HOST")
        raise ValueError(
            "Partial Postgres configuration supplied. Missing required env vars: "
            + ", ".join(missing)
        )


USE_POSTGRES_FOR_TESTS = os.getenv("SUM_TEST_DB", "sqlite").lower() == "postgres"

if not RUNNING_TESTS:
    _validate_db_env()

if (DB_HOST and DB_NAME) and (not RUNNING_TESTS or USE_POSTGRES_FOR_TESTS):
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
else:
    SQLITE_DB_NAME: str = ":memory:" if RUNNING_TESTS else str(BASE_DIR / "db.sqlite3")
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": SQLITE_DB_NAME,
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
    REPO_ROOT / "themes" / "theme_a" / "static",
    BASE_DIR.parent / "themes" / "theme_a" / "static",
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
