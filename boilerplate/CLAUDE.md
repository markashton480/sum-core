# project_name — SUM Platform Client Site

This is a SUM Platform client site built on Django/Wagtail with `sum_core`.

## Quick Command Reference

| Command | Description |
|---------|-------------|
| `python manage.py seed <profile>` | Seed site with content profile |
| `python manage.py seed <profile> --clear` | Clear and re-seed content |
| `sum-platform update project_name` | Pull updates, migrate, restart |
| `sum-platform backup project_name` | Create differential backup |
| `sum-platform backup project_name --type full` | Create full backup |
| `sum-platform restore project_name --latest` | Restore from latest backup |
| `sum-platform check project_name` | Validate project setup |
| `sum-platform theme check` | Check for theme updates |
| `sum-platform theme update` | Update to latest theme version |
| `sum-platform monitor` | Check backup health |

## Directory Structure

```
project_name/          # Django project package
├── settings/          # base / local / production settings
├── home/              # Home app (re-exports sum_core models)
├── urls.py
└── wsgi.py
templates/overrides/   # Client template overrides
static/client/         # Client static assets
theme/active/          # Active theme (managed by CLI)
tests/                 # Integration tests
.env                   # Environment configuration (DO NOT commit)
.sum/
├── config.yml         # Site configuration
└── theme.json         # Theme version lockfile
```

## Configuration Files

| File | Purpose |
|------|---------|
| `.env` | Database credentials, Django settings, email/SMTP config, domain config |
| `.sum/config.yml` | Site metadata (slug, theme, git provider) |
| `.sum/theme.json` | Theme version tracking and lockfile |
| `requirements.txt` | Python dependencies (sum-core pinned) |

## Important Notes

### Architecture

- **All page types and models live in `sum_core`** — this project re-exports them
- The `home/` app imports and re-exports page models from `sum_core.pages`
- Do not create new models here; they belong in the core platform

### Theme Management

- **Do not modify `theme/active/`** — it is managed by the CLI
- Use `templates/overrides/` for template customizations
- Use `static/client/` for custom CSS/JS assets
- Check theme updates with `sum-platform theme check`

### Security

- **Do not commit `.env`** — it contains secrets
- Keep database credentials in `.env` only
- Use environment variables for all sensitive configuration

### Production Operations

Run management commands as the deploy user:

```bash
sudo -u deploy /srv/sum/project_name/venv/bin/python /srv/sum/project_name/app/manage.py <command>
```

Examples:

```bash
# Re-seed with a content profile
sudo -u deploy /srv/sum/project_name/venv/bin/python /srv/sum/project_name/app/manage.py seed my-profile --clear

# Create superuser
sudo -u deploy /srv/sum/project_name/venv/bin/python /srv/sum/project_name/app/manage.py createsuperuser

# Run migrations
sudo -u deploy /srv/sum/project_name/venv/bin/python /srv/sum/project_name/app/manage.py migrate
```

### Backups

- PostgreSQL backups are encrypted (AES-256-CBC) and stored on a remote storage box via pgBackRest
- Local `backups/` directory is used for promote operations (pg_dump files)
- Monitor backup health with `sum-platform monitor`

## Documentation

Full operator documentation: https://github.com/markashton480/sum-platform/wiki

For support, contact your SUM Platform administrator.
