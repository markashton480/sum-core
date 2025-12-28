# SUM Core

A Django/Wagtail foundation for launching lead-focused websites for home improvement trades. SUM Core provides a complete content management system with built-in forms, lead capture, analytics, and technical SEO—ready to theme and deploy.

## Features

- **Content Management**: Page types (Home, Services, Standard pages) built on Wagtail CMS with StreamField blocks for flexible content authoring
- **Lead Capture**: Contact and quote request forms with spam protection, attribution tracking, and email/webhook notifications
- **Branding System**: Configurable colors, fonts, logos, and business info through the admin interface
- **Navigation**: Header menus (3 levels), footer sections, and mobile sticky CTA—all managed through Wagtail settings
- **Technical SEO**: Automatic sitemaps, robots.txt, meta tags, Open Graph, and JSON-LD structured data
- **Analytics**: GA4/GTM integration with lead tracking dashboard
- **Email & Webhooks**: Lead notifications via SMTP and Zapier integration
- **Observability**: Health checks, Sentry integration, and structured logging

## Installation

### Requirements

- Python 3.12+
- PostgreSQL (recommended for production)
- libmagic (for file type validation)
  - **Ubuntu/Debian**: `sudo apt-get install libmagic1`
  - **macOS**: `brew install libmagic`
  - **Windows**: Install python-magic-bin: `pip install python-magic-bin`

### Install SUM Core

Install from the public repository:

```bash
pip install "sum_core @ git+https://github.com/markashton480/sum-core.git@v0.6.0"
```

For the latest development version:

```bash
pip install "sum_core @ git+https://github.com/markashton480/sum-core.git@main"
```

### Configure Your Django Project

Add SUM Core apps to your `INSTALLED_APPS` in `settings.py`:

```python
INSTALLED_APPS = [
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
    # SUM Core apps
    "sum_core",
    "sum_core.pages",
    "sum_core.navigation",
    "sum_core.leads",
    "sum_core.forms",
    "sum_core.analytics",
    "sum_core.seo",
    # Your client-specific apps
    "home",  # Create your HomePage model here
]
```

Wire up URLs in `urls.py`:

```python
from django.urls import path, include
from wagtail import urls as wagtail_urls
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.documents import urls as wagtaildocs_urls

urlpatterns = [
    path("admin/", include(wagtailadmin_urls)),
    path("documents/", include(wagtaildocs_urls)),
    path("forms/", include("sum_core.forms.urls")),
    path("", include("sum_core.ops.urls")),      # /health/
    path("", include("sum_core.seo.urls")),      # sitemap.xml, robots.txt
    path("", include(wagtail_urls)),             # Must be last
]
```

Run migrations and create a superuser:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Quick Start

1. **Access the admin**: Visit `http://localhost:8000/admin/`
2. **Configure your site**: Go to Settings → Site settings to set your branding, colors, fonts, and business info
3. **Set up navigation**: Configure your header and footer menus in Settings → Header/Footer Navigation
4. **Create content**: Add pages using the Wagtail page tree
5. **Configure forms**: Set lead notification emails and rate limits in Django admin

## Documentation

- **[Platform Handbook](docs/HANDBOOK.md)**: Complete guide to the platform
- **[Wiring Guide](docs/dev/WIRING-INVENTORY.md)**: How to integrate SUM Core into your project
- **[Block Reference](docs/dev/blocks-reference.md)**: Available StreamField blocks
- **Design assets**: `docs/dev/design/` (HTML mockups and references)

## Environment Configuration

Key environment variables (see [`.env.example`](.env.example) for complete list):

```bash
# Database
DJANGO_DB_NAME=your_db
DJANGO_DB_USER=your_user
DJANGO_DB_PASSWORD=your_password
DJANGO_DB_HOST=localhost
DJANGO_DB_PORT=5432

# Email notifications
DEFAULT_FROM_EMAIL=noreply@yoursite.com
LEAD_NOTIFICATION_EMAIL=leads@yoursite.com

# Optional integrations
ZAPIER_WEBHOOK_URL=https://hooks.zapier.com/...
SENTRY_DSN=https://...
```

## Example Projects

- **[sum_client](clients/sum_client/)**: Reference implementation showing recommended project structure
- **[showroom](clients/showroom/)**: Demonstration site with sample content


## License

TBD
