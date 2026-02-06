"""
Name: Cleanup Trash Management Command
Path: core/sum_core/wagtail_trash/management/commands/cleanup_trash.py
Purpose: Permanently delete old items from trash via scheduled cleanup.
Family: SUM Platform Core - Page Management
Dependencies: Django management commands, TrashService

Usage:
    python manage.py cleanup_trash                    # Delete items > 30 days
    python manage.py cleanup_trash --days 7           # Delete items > 7 days
    python manage.py cleanup_trash --days 30 --dry-run  # Preview only

Cron Integration:
    # Weekly cleanup of items older than 30 days (Sundays at 3am)
    0 3 * * 0 /path/to/venv/bin/python /path/to/manage.py cleanup_trash --days 30
"""

from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from sum_core.wagtail_trash.models import TrashedPageInfo
from sum_core.wagtail_trash.services import TrashService


class Command(BaseCommand):
    help = "Permanently delete old items from the Wagtail trash"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=30,
            help="Delete items older than N days (default: 30)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without deleting",
        )

    def handle(self, *args, **options):
        days = options["days"]
        dry_run = options["dry_run"]
        verbosity = options["verbosity"]

        if days <= 0:
            raise CommandError(f"--days must be a positive number, got {days}")

        cutoff = timezone.now() - timedelta(days=days)

        # Find items to delete
        items_to_delete = TrashedPageInfo.objects.filter(trashed_at__lt=cutoff)
        count = items_to_delete.count()

        if count == 0:
            self.stdout.write(
                self.style.SUCCESS(f"No items older than {days} days found in trash.")
            )
            return

        if dry_run:
            self.stdout.write(
                self.style.WARNING(f"DRY RUN: Would delete {count} items:")
            )
            for info in items_to_delete:
                age = (timezone.now() - info.trashed_at).days
                self.stdout.write(f"  - {info.page.title} (trashed {age} days ago)")
            return

        # Perform deletion
        if verbosity > 0:
            self.stdout.write(f"Deleting {count} items older than {days} days...")

        service = TrashService()
        deleted_count = service.empty_trash(older_than_days=days)

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully deleted {deleted_count} items from trash."
            )
        )
