from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("sum_core_pages", "0031_blogindexpage_sidebar_subscribe"),
    ]

    operations = [
        migrations.AddField(
            model_name="portfolioindexpage",
            name="portfolio_quote",
            field=models.TextField(
                blank=True,
                help_text="Optional quote displayed within the portfolio grid.",
            ),
        ),
        migrations.AddField(
            model_name="portfolioindexpage",
            name="cta_eyebrow",
            field=models.CharField(
                blank=True,
                help_text="Optional eyebrow text for the portfolio CTA section.",
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name="portfolioindexpage",
            name="cta_heading",
            field=models.CharField(
                blank=True,
                help_text="Main heading for the portfolio CTA section.",
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name="portfolioindexpage",
            name="cta_primary_label",
            field=models.CharField(
                blank=True,
                help_text="Label for the primary CTA button.",
                max_length=100,
            ),
        ),
        migrations.AddField(
            model_name="portfolioindexpage",
            name="cta_primary_link",
            field=models.CharField(
                blank=True,
                help_text="URL or anchor for the primary CTA button.",
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name="portfolioindexpage",
            name="cta_secondary_label",
            field=models.CharField(
                blank=True,
                help_text="Label for the secondary CTA button.",
                max_length=100,
            ),
        ),
        migrations.AddField(
            model_name="portfolioindexpage",
            name="cta_secondary_link",
            field=models.CharField(
                blank=True,
                help_text="URL or anchor for the secondary CTA button.",
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name="casestudypage",
            name="portfolio_number",
            field=models.CharField(
                blank=True,
                help_text="Optional display number for portfolio highlights.",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="casestudypage",
            name="location",
            field=models.CharField(
                blank=True,
                help_text="Optional location label for portfolio metadata.",
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name="casestudypage",
            name="material",
            field=models.CharField(
                blank=True,
                help_text="Optional material label for portfolio metadata.",
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name="casestudypage",
            name="portfolio_summary",
            field=models.TextField(
                blank=True,
                help_text="Optional summary used in portfolio grid cards.",
            ),
        ),
        migrations.AddField(
            model_name="casestudypage",
            name="portfolio_quote",
            field=models.TextField(
                blank=True,
                help_text="Optional quote used in portfolio metadata highlights.",
            ),
        ),
    ]
