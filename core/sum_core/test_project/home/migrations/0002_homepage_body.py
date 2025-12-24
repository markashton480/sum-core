# Generated manually for M2-001 task - adding body StreamField to HomePage

import wagtail.fields
from django.db import migrations

from sum_core.blocks.base import PageStreamBlock


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="homepage",
            name="body",
            field=wagtail.fields.StreamField(
                PageStreamBlock(),
                blank=True,
                null=True,
                use_json_field=True,
                help_text="Add content blocks to build your homepage layout.",
            ),
        ),
    ]
