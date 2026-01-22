from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("sum_core_pages", "0033_portfolio_cta_link_validators"),
    ]

    operations = [
        migrations.AddField(
            model_name="portfolioindexpage",
            name="hero_heading_line_1",
            field=models.CharField(
                blank=True,
                help_text="First line of the portfolio hero heading.",
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name="portfolioindexpage",
            name="hero_heading_emphasis",
            field=models.CharField(
                blank=True,
                help_text="Emphasized word in the portfolio hero heading.",
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name="portfolioindexpage",
            name="hero_heading_line_2",
            field=models.CharField(
                blank=True,
                help_text="Second line of the portfolio hero heading.",
                max_length=255,
            ),
        ),
    ]
