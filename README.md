# SUM Platform

A Django/Wagtail CMS platform for service businesses, with CLI-driven
deployment, multi-theme support, and built-in lead management.

## Components

| Component | Version | Description |
|-----------|---------|-------------|
| [sum_core](core/) | 0.7.7 | Core Django/Wagtail package — page types, blocks, lead system |
| [CLI](cli/) | 3.3.2 | Operator tool — init, update, backup, restore, destroy, themes |
| [Theme A](themes/theme_a/) | 1.0.7 | Default theme — Tailwind-based, responsive, accessible |
| [Boilerplate](boilerplate/) | — | Project template used by CLI during `init` |

## Features

- **Content Management** — Page types, StreamField blocks, and Wagtail CMS authoring
- **Lead Capture** — Contact and quote forms with spam protection and attribution tracking
- **Branding** — Colors, fonts, logos, and business info configurable through admin
- **Navigation** — Header menus (3 levels), footer sections, mobile sticky CTA
- **Technical SEO** — Sitemaps, robots.txt, meta tags, Open Graph, JSON-LD
- **Analytics** — GA4/GTM integration with lead tracking dashboard
- **Email & Webhooks** — Lead notifications via SMTP and Zapier integration
- **Observability** — Health checks, Sentry integration, structured logging

## For Operators

Install the CLI and create your first site:

    pip install sum-cli
    sum-platform init mysite --theme theme_a

> Full operator guide: [cli/README.md](cli/README.md)

## For Developers

    make install-dev    # Editable install + dev tooling
    make db-up          # Start Postgres (Docker)
    make dev-reset      # Migrate + seed
    make run            # Start dev server

Requires Python 3.12+ and Docker (for Postgres).

> Developer guide: [docs/dev/DEV-README.md](docs/dev/DEV-README.md)
>
> Documentation index: [docs/ROUTER.md](docs/ROUTER.md)

## Repository Structure

```
core/sum_core/       Core platform package (the product)
cli/                 CLI tool (sum-platform)
themes/theme_a/      Default Tailwind theme
boilerplate/         Project template for CLI init
docs/                Documentation
tests/               Test suites
```

## License

TBD
