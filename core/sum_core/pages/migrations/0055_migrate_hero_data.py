"""
Data migration: No-op migration placeholder.

HomePage was created fresh in sum_core via migration 0053_homepage.py.
There are no existing HomePage instances to migrate data from, so this is a no-op.

StandardPage already has hero_intro field from prior migrations, so this is also a no-op.
"""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("sum_core_pages", "0054_homepage_body_field_fix"),
    ]

    operations = [
        # This is a no-op migration. HomePage/StandardPage hero fields don't need
        # data migration since HomePage was just created and StandardPage already
        # has the hero_intro field from prior work.
    ]
