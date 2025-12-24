# Generated manually for M3-002 task - adding SEO and Open Graph fields to HomePage

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("home", "0002_homepage_body"),
        ("wagtailimages", "0027_image_description"),
    ]

    operations = [
        migrations.AddField(
            model_name="homepage",
            name="meta_title",
            field=models.CharField(
                blank=True,
                help_text='Optional. If blank, defaults to "{page title} | {site name}".',
                max_length=60,
            ),
        ),
        migrations.AddField(
            model_name="homepage",
            name="meta_description",
            field=models.TextField(
                blank=True,
                help_text="Optional. Brief summary for search engines (recommended max 160 characters).",
                max_length=160,
            ),
        ),
        migrations.AddField(
            model_name="homepage",
            name="og_image",
            field=models.ForeignKey(
                blank=True,
                help_text="Optional. If blank, uses the page featured image (if present), otherwise the site default OG image.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="wagtailimages.image",
            ),
        ),
    ]
