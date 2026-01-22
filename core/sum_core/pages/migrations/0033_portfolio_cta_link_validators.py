from django.db import migrations, models

from sum_core.pages.portfolio import validate_safe_link


class Migration(migrations.Migration):
    dependencies = [
        ("sum_core_pages", "0032_portfolio_index_content_fields"),
    ]

    operations = [
        migrations.AlterField(
            model_name="portfolioindexpage",
            name="cta_primary_link",
            field=models.CharField(
                blank=True,
                help_text="URL or anchor for the primary CTA button.",
                max_length=255,
                validators=[validate_safe_link],
            ),
        ),
        migrations.AlterField(
            model_name="portfolioindexpage",
            name="cta_secondary_link",
            field=models.CharField(
                blank=True,
                help_text="URL or anchor for the secondary CTA button.",
                max_length=255,
                validators=[validate_safe_link],
            ),
        ),
    ]
