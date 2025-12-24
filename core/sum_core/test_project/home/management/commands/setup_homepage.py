"""
Management command to set up a test HomePage for the SUM test project.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand
from home.models import HomePage
from wagtail.models import Page, Site


class Command(BaseCommand):
    help = "Set up a test HomePage for the SUM test project"

    def handle(self, *args, **options) -> None:
        # Get or create the homepage
        root = Page.get_first_root_node()

        # Check if homepage already exists
        try:
            homepage = HomePage.objects.get(slug="sum-home")
            self.stdout.write("HomePage already exists")
        except HomePage.DoesNotExist:
            homepage = HomePage(
                title="Welcome to SUM",
                slug="sum-home",
                intro="<p>This is a test homepage using the SUM core base layout and branding system.</p>",
            )
            root.add_child(instance=homepage)
            self.stdout.write("Created HomePage")

        # Set as site root
        site = Site.objects.get(is_default_site=True)
        site.root_page = homepage
        site.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"HomePage set as root page for site '{site.site_name}'. "
                f"Visit http://127.0.0.1:8000/ to see the result."
            )
        )
