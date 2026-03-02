"""
Name: Image Rendition Backfill Command
Path: core/sum_core/management/commands/sum_core_images_backfill.py
Purpose: Queue/profile-generate optimized renditions for existing image libraries.
Family: sum_core image optimization.
Dependencies: Django management base, Wagtail image model, image dispatch layer.
"""

from __future__ import annotations

from argparse import ArgumentParser
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from sum_core.images.dispatch import dispatch_pregeneration_for_images
from sum_core.images.settings import get_image_optimization_settings
from wagtail.images import get_image_model


class Command(BaseCommand):
    help = "Backfill image optimization renditions for existing media library."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--profiles",
            type=str,
            default="",
            help="Comma-separated profile names to backfill.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Number of images to process per batch.",
        )
        parser.add_argument(
            "--start-id",
            type=int,
            default=1,
            help="Start processing from image ID >= this value.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be queued without dispatching tasks.",
        )
        parser.add_argument(
            "--max-images",
            type=int,
            default=0,
            help="Optional cap on number of images to queue.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        batch_size = int(options["batch_size"])
        start_id = int(options["start_id"])
        dry_run = bool(options["dry_run"])
        max_images = int(options["max_images"])

        if batch_size < 1:
            raise CommandError("--batch-size must be at least 1.")
        if start_id < 1:
            raise CommandError("--start-id must be at least 1.")
        if max_images < 0:
            raise CommandError("--max-images cannot be negative.")

        image_settings = get_image_optimization_settings()
        available_profiles = set(image_settings.profiles)

        raw_profiles = str(options["profiles"] or "").strip()
        if raw_profiles:
            selected_profiles = [
                p.strip() for p in raw_profiles.split(",") if p.strip()
            ]
        else:
            selected_profiles = list(image_settings.pregenerate_upload_profiles)

        unknown = [
            profile
            for profile in selected_profiles
            if profile not in available_profiles
        ]
        if unknown:
            raise CommandError(
                "Unknown profiles: "
                f"{unknown}. Available profiles: {sorted(available_profiles)}"
            )

        image_model = get_image_model()
        queryset = image_model.objects.filter(id__gte=start_id).order_by("id")
        if max_images:
            queryset = queryset[:max_images]

        image_ids = list(queryset.values_list("id", flat=True))
        total = len(image_ids)

        self.stdout.write(
            f"Backfill image count={total} profiles={selected_profiles} start_id={start_id}"
        )

        if dry_run or total == 0:
            self.stdout.write(
                self.style.SUCCESS(
                    "Dry run complete." if dry_run else "Nothing to process."
                )
            )
            return

        queued = 0
        for index in range(0, total, batch_size):
            batch_ids = image_ids[index : index + batch_size]
            dispatch_pregeneration_for_images(
                image_ids=batch_ids,
                profiles=selected_profiles,
                reason="backfill",
            )
            queued += len(batch_ids)
            self.stdout.write(
                f"Queued batch {index // batch_size + 1}: {len(batch_ids)} images (total queued: {queued})"
            )

        self.stdout.write(self.style.SUCCESS(f"Queued {queued} images for backfill."))
