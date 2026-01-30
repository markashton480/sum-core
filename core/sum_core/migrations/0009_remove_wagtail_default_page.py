"""
Remove the default Wagtail welcome page.

Wagtail's 0002_initial_data migration creates a "Welcome to your new Wagtail site!"
page. This migration removes it to provide a clean slate for sum_core installations.

This migration is idempotent: if the welcome page has already been removed or replaced,
it does nothing.
"""

from django.db import migrations


def remove_wagtail_default_page(apps, schema_editor):
    """Remove the default Wagtail welcome page and update the default Site."""
    Page = apps.get_model("wagtailcore", "Page")
    Site = apps.get_model("wagtailcore", "Site")
    ContentType = apps.get_model("contenttypes", "ContentType")

    page_content_type = ContentType.objects.filter(
        app_label="wagtailcore",
        model="page",
    ).first()
    if page_content_type is None:
        return

    welcome_page = Page.objects.filter(
        title="Welcome to your new Wagtail site!",
        slug="home",
        depth=2,
        content_type=page_content_type,
    ).first()

    if welcome_page is None:
        return

    root_page = Page.objects.filter(depth=1).first()
    if root_page is None:
        return

    Site.objects.filter(root_page_id=welcome_page.pk).update(root_page_id=root_page.pk)

    welcome_page.delete()

    actual_children = Page.objects.filter(
        path__startswith=root_page.path,
        depth=root_page.depth + 1,
    ).count()
    if root_page.numchild != actual_children:
        root_page.numchild = actual_children
        root_page.save(update_fields=["numchild"])


def reverse_migration(apps, schema_editor):
    """Reverse migration is a no-op.

    We don't recreate the welcome page because:
    1. The site may already have a proper HomePage
    2. Wagtail's original migration can be re-run if needed
    """
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("sum_core", "0008_sitesettings_cookie_banner_enabled_and_more"),
        ("wagtailcore", "0002_initial_data"),
    ]

    operations = [
        migrations.RunPython(
            remove_wagtail_default_page,
            reverse_migration,
        ),
    ]
