# SUM Platform — Project Boilerplate

This directory is the **project template** used by `sum-platform init`.
You do not interact with it directly.

## For Operators

To create a new site:

```bash
pip install sum-cli
sudo sum-platform init mysite --git-provider github --git-org my-org
```

See the [CLI documentation](../cli/README.md) for the full command reference.

## For CLI Developers

### What happens during `init`

When an operator runs `sum-platform init <name>`, the CLI:

1. Copies this boilerplate into `/srv/sum/<name>/app/`.
2. Renames the `project_name/` package to the site slug and replaces
   all `project_name` references in every file.
3. Rewrites `requirements.txt` to pin `sum-core` (or editable install
   with `--dev`).
4. Generates `.env` from `.env.example` with production credentials.
5. Selects CI workflows (`.github/` or `.gitea/`) per `--git-provider`.
6. Copies the chosen theme into `theme/active/` with a lockfile at
   `.sum/theme.json`.
7. Copies seeders and the content profile for the `seed` command.
8. Creates a virtualenv, installs deps, migrates, seeds, creates a
   superuser, collects static files, and configures systemd + Caddy.

Entry points: `cli/sum/commands/init.py` and `cli/sum/setup/scaffold.py`.

### Template files

```
boilerplate/
├── manage.py                 # Django management entry point
├── pytest.ini                # Test runner configuration
├── requirements.txt          # Dependencies (sum-core pinned by version)
├── .env.example              # Environment variable template
├── .gitignore
├── project_name/             # Django project package (renamed during init)
│   ├── settings/             # base / local / production settings
│   ├── home/                 # Home app with models, migrations, seed commands
│   ├── urls.py
│   └── wsgi.py
├── templates/overrides/      # Client template overrides
├── static/client/            # Client static assets
├── tests/                    # Integration tests
└── .github/workflows/        # CI and deploy workflows
```

### Placeholders

| Token | Replaced with |
|-------|---------------|
| `project_name` | Site slug as a valid Python package name (e.g. `acme`) |
