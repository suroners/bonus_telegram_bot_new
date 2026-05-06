# Generated for local Script Parser provider support.
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("bonus_core", "0002_scraperproxy"),
    ]

    operations = [
        migrations.AlterField(
            model_name="aiproviderconfig",
            name="provider",
            field=models.CharField(
                choices=[
                    ("openai", "OpenAI"),
                    ("google", "Google Gemini"),
                    ("anthropic", "Anthropic"),
                    ("script", "Script Parser"),
                ],
                max_length=30,
            ),
        ),
    ]
