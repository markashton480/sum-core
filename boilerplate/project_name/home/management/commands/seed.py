"""
Seed the test project using YAML content profiles.

Usage:
    python manage.py seed starter          # Clean production-ready content
    python manage.py seed starter --clear  # Clear existing content first
    python manage.py seed starter --dry-run

The content directory is auto-detected by walking up the directory tree,
so the command works from subdirectories. The command also attempts to add
the repository root to ``sys.path`` so the ``seeders`` package is importable.
"""

from __future__ import annotations

import sys
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError, CommandParser


def _ensure_repo_root_on_path() -> None:
    """Add the repo root (containing seeders/content) to sys.path if needed."""
    for parent in Path(__file__).resolve().parents:
        if (parent / "seeders").is_dir() and (parent / "content").is_dir():
            sys.path.insert(0, str(parent))
            return


_ensure_repo_root_on_path()


try:
    from seeders import SeedOrchestrator, SeedPlan
    from seeders.exceptions import SeederError
except ImportError as _import_err:
    # Provide a helpful error message when seeders cannot be imported
    _IMPORT_ERROR_MSG = (
        "Cannot import 'seeders' package. This typically happens when running "
        "the seed command from a subdirectory.\n\n"
        "Solutions:\n"
        "  1. Run from the repository root:\n"
        "     python core/sum_core/test_project/manage.py seed <profile>\n\n"
        "  2. Use the Makefile target:\n"
        "     make seed\n\n"
        "  3. Set PYTHONPATH to include the repo root:\n"
        "     PYTHONPATH=. python manage.py seed <profile>\n"
    )
    raise ImportError(_IMPORT_ERROR_MSG) from _import_err


class Command(BaseCommand):
    help = "Seed the test project from YAML content profiles."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "profile",
            nargs="?",
            help="Content profile to seed (e.g., starter).",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing seeded content before re-seeding.",
        )
        parser.add_argument(
            "--content-path",
            default=None,
            help="Override the content directory (defaults to ./content).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate content and print the plan without writing.",
        )

    def handle(self, *args, **options) -> None:
        content_path = options.get("content_path")
        content_dir = Path(content_path).expanduser() if content_path else None
        orchestrator = SeedOrchestrator(content_dir=content_dir)

        profile = options.get("profile") or self._default_profile(orchestrator)
        if not profile:
            profiles = orchestrator.list_profiles()
            if profiles:
                raise CommandError(
                    "Missing profile. Available profiles: " + ", ".join(profiles)
                )
            raise CommandError("Missing profile and no content profiles were found.")

        try:
            if options.get("dry_run"):
                plan = orchestrator.plan(profile)
                self._print_plan(plan)
                return
            orchestrator.seed(profile, clear=options.get("clear", False))
        except SeederError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(self.style.SUCCESS(f"Seeded profile '{profile}'."))

    def _default_profile(self, orchestrator: SeedOrchestrator) -> str | None:
        """Return a sensible default profile, if one can be inferred.

        ``starter`` is the clean production-ready default.
        """
        profiles = orchestrator.list_profiles()
        if "starter" in profiles:
            return "starter"
        if len(profiles) == 1:
            return profiles[0]
        return None

    def _print_plan(self, plan: SeedPlan) -> None:
        self.stdout.write(self.style.MIGRATE_HEADING("Seed plan"))
        self.stdout.write(self.style.NOTICE(f"  Profile: {plan.profile}"))
        self.stdout.write(self.style.NOTICE(f"  Content dir: {plan.content_dir}"))
        if plan.pages:
            self.stdout.write(self.style.SUCCESS("  Pages:"))
            for page in plan.pages:
                self.stdout.write(f"    - {page}")
        if plan.seeders:
            self.stdout.write(self.style.SUCCESS("  Seeders:"))
            for seeder in plan.seeders:
                self.stdout.write(f"    - {seeder}")
