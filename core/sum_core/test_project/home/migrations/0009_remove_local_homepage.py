# Transition migration: HomePage has moved to sum_core.pages
# This migration removes the local model definition so Django's model registry
# points to sum_core_pages.HomePage instead of home.HomePage.
#
# Note: The old home_homepage table will be DROPPED by DeleteModel. This is
# acceptable because:
# 1. test_project is a test harness with ephemeral databases
# 2. sum_core_pages.HomePage creates its own table (sum_core_pages_homepage)
# 3. Client projects will never have had home_homepage tables

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("home", "0008_homepage_desktop_sticky_cta_snippet"),
        ("sum_core_pages", "0053_homepage"),
    ]

    operations = [
        # Delete the local HomePage model - it now lives in sum_core.pages.home
        # This makes Django's model registry use sum_core_pages.HomePage
        migrations.DeleteModel(
            name="HomePage",
        ),
    ]
