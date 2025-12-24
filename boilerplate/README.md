# SUM Client Boilerplate

This directory is the **copy-ready template** for new SUM Platform client projects.

## What This Is

A minimal, runnable Django/Wagtail project that consumes `sum_core` as its foundation. When you create a new client site, you copy this boilerplate to `/clients/<your-project-name>/` and customize it.

## Quick Start

### 1. Copy the Boilerplate

```bash
# From the repo root:
cp -r boilerplate clients/my_client
cd clients/my_client
```

### 2. Rename the Project Module

Replace `project_name` with your actual project name throughout:

```bash
# Rename the directory
mv project_name my_client

# Update all references (Linux/macOS):
find . -type f \( -name "*.py" -o -name "*.txt" -o -name "pytest.ini" \) \
  -exec sed -i 's/project_name/my_client/g' {} +

# Verify no stale references remain:
grep -r "project_name" .
```

### 3. Set Up Your Environment

```bash
# From the client project directory:
cp .env.example .env
# Edit .env with your local/production values

# Create virtual environment (or use the repo-level one):
python -m venv .venv
source .venv/bin/activate

# Install dependencies:
pip install -r requirements.txt
```

### 4. Run Migrations & Start

```bash
# Run migrations:
python manage.py migrate

# Create a superuser:
python manage.py createsuperuser

# Start the development server:
python manage.py runserver 8001
```

Visit:

- **Site**: http://localhost:8001/
- **Admin**: http://localhost:8001/admin/

## What Must Be Changed Per Client

| File / Location                 | What to Change                                  |
| ------------------------------- | ----------------------------------------------- |
| `project_name/` directory       | Rename to your project name                     |
| `project_name/settings/base.py` | Update `WAGTAIL_SITE_NAME`                      |
| `project_name/home/apps.py`     | Update `name` and `label` to match              |
| `manage.py`                     | Already uses `DJANGO_SETTINGS_MODULE` correctly |
| `.env`                          | Configure for your environment                  |

### Environment Variables

See `.env.example` for all configurable values. Critical production requirements:

- `DJANGO_SECRET_KEY` - **Required**: Generate a unique secret key
- `ALLOWED_HOSTS` - **Required**: Comma-separated list of domains
- `DJANGO_DB_*` - **Required**: PostgreSQL connection details
- `REDIS_URL` - Recommended: For cache and Celery

## Project Structure

```
my_client/
├── manage.py               # Django management command
├── pytest.ini              # Test configuration
├── requirements.txt        # Dependencies (includes sum_core)
├── .env.example            # Environment variable template
│
├── project_name/           # Your Django project package
│   ├── __init__.py
│   ├── urls.py             # URL configuration (includes sum_core routes)
│   ├── wsgi.py             # WSGI entry point
│   │
│   ├── settings/           # Environment-split settings
│   │   ├── __init__.py
│   │   ├── base.py         # Shared settings
│   │   ├── local.py        # Local development
│   │   └── production.py   # Production deployment
│   │
│   └── home/               # Client-specific home app
│       ├── __init__.py
│       ├── apps.py
│       ├── models.py       # HomePage model using sum_core features
│       └── migrations/
│
├── templates/
│   └── overrides/          # Override sum_core templates here
│       └── .gitkeep
│
├── static/
│   └── client/             # Client-specific static files
│       └── .gitkeep
│
└── tests/
    ├── __init__.py
    └── test_health.py      # Integration test for sum_core wiring
```

## Template & Static Overrides

### Templates

Place template overrides in `templates/overrides/`. To override a sum_core template:

```
templates/overrides/sum_core/home_page.html
```

The override path mirrors sum_core's template path.

### Static Files

Place client-specific assets in `static/client/`:

```
static/client/css/custom.css
static/client/images/logo.png
```

## Testing

```bash
# Run tests:
pytest

# With coverage:
pytest --cov=.
```

The boilerplate includes a minimal integration test (`test_health.py`) that verifies sum_core wiring. This test should continue to pass after copying and renaming.

## Production Deployment

1. Set `DJANGO_SETTINGS_MODULE=project_name.settings.production`
2. Ensure all required environment variables are set (see `.env.example`)
3. Run `python manage.py collectstatic`
4. Deploy with gunicorn: `gunicorn project_name.wsgi:application`

## Dependencies

This project depends on `sum_core` from the SUM Platform monorepo.

### Default Mode: Git Tag Pinning

By default, `requirements.txt` references a specific git tag of `sum_core`:

```
sum-core @ git+https://github.com/markashton480/sum-core.git@SUM_CORE_GIT_REF#subdirectory=core
```

**Before deploying**, replace `SUM_CORE_GIT_REF` with the actual version tag (e.g., `v0.1.0`).

### Monorepo Development Mode

If you're developing within the SUM Platform monorepo and want to make changes to `sum_core` alongside your client project:

1. Edit `requirements.txt`:

   ```bash
   # Comment out the git install line
   # sum-core @ git+https://...

   # Uncomment the editable install
   -e ../../core
   ```

2. Reinstall dependencies:
   ```bash
   pip install -r requirements.txt
   ```

Now changes to `/core/sum_core/` will be immediately reflected in your client project.

**Important**: Do not commit the editable install to your client project repository. It's for local development only.
