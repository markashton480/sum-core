from django.db import migrations
from wagtail.fields import RichTextField


class Migration(migrations.Migration):
    dependencies = [
        ("sum_core_pages", "0034_portfolio_hero_heading_fields"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="portfolioindexpage",
            name="hero_heading_emphasis",
        ),
        migrations.RemoveField(
            model_name="portfolioindexpage",
            name="hero_heading_line_1",
        ),
        migrations.RemoveField(
            model_name="portfolioindexpage",
            name="hero_heading_line_2",
        ),
        migrations.AddField(
            model_name="portfolioindexpage",
            name="hero_heading",
            field=RichTextField(
                blank=True,
                features=["italic", "bold"],
                help_text="Hero heading copy; supports italic/bold for emphasis.",
            ),
        ),
    ]
