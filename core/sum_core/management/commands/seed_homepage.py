"""
Name: Seed Homepage Management Command
Path: core/sum_core/management/commands/seed_homepage.py
Purpose: Create the initial HomePage for new projects using sum_core.
Family: Django management command.
Dependencies: Django, Wagtail, home.models.HomePage.
"""

from __future__ import annotations

from argparse import ArgumentParser
from typing import Any

from django.core.management.base import BaseCommand
from home.models import HomePage
from wagtail.models import Page, Site


class Command(BaseCommand):
    help = "Seed initial homepage for a new client project"

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--preset",
            type=str,
            help="Theme preset name (future use).",
            required=False,
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Recreate homepage even if it exists.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        preset = options.get("preset")
        force = options.get("force", False)

        root = Page.get_first_root_node()
        site = Site.objects.filter(is_default_site=True).first()
        if site is None:
            self.stderr.write(
                self.style.ERROR(
                    "No default Wagtail Site exists. Create one in the Wagtail admin "
                    "(Settings → Sites) or via fixtures, then rerun this command."
                )
            )
            return
        existing = HomePage.objects.first()

        if existing and not force:
            self.stdout.write(
                self.style.WARNING(
                    f"Homepage already exists (ID: {existing.id}). Use --force to recreate."
                )
            )
            return

        if existing and force:
            self.stdout.write("Removing existing homepage...")
            self._reset_sites_to_root(existing, root)
            existing.delete()
            root = Page.get_first_root_node()

        existing_home_child = root.get_children().filter(slug="home").first()
        if existing_home_child and not isinstance(
            existing_home_child.specific, HomePage
        ):
            self.stdout.write("Removing existing 'home' page to seed HomePage...")
            self._reset_sites_to_root(existing_home_child, root)
            existing_home_child.delete()
            root = Page.get_first_root_node()

        homepage = HomePage(
            title="Welcome",
            slug="home",
            seo_title="Home",
            search_description="Welcome to our website",
            body=self._get_default_content(preset),
        )

        root.add_child(instance=homepage)
        homepage.save_revision().publish()

        site.root_page = homepage
        site.save()
        Site.clear_site_root_paths_cache()

        self.stdout.write(
            self.style.SUCCESS(f"✅ Homepage created successfully (ID: {homepage.id})")
        )
        self.stdout.write("URL: http://127.0.0.1:8000/")

    def _reset_sites_to_root(self, page: Page, root: Page) -> None:
        for site in Site.objects.filter(root_page_id=page.id):
            site.root_page = root
            site.save()
        Site.clear_site_root_paths_cache()

    def _get_default_content(self, preset: str | None) -> list[dict[str, Any]]:
        # Preset support is reserved for a future phase.
        return [
            {
                "type": "hero_gradient",
                "value": {
                    "headline": "<p>Welcome to Your New Site</p>",
                    "subheadline": "Your professional website is ready to customize.",
                    "ctas": [],
                    "gradient_style": "primary",
                },
            },
            {
                "type": "rich_text",
                "value": (
                    "<p>This is your homepage. Edit this content in the Wagtail admin.</p>"
                ),
            },
        ]
