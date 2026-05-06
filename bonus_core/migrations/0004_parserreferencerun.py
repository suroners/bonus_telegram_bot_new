# Generated for parser reference dataset persistence.
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("bonus_core", "0003_aiproviderconfig_script"),
    ]

    operations = [
        migrations.CreateModel(
            name="ParserReferenceRun",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "provider",
                    models.CharField(
                        choices=[
                            ("openai", "OpenAI"),
                            ("google", "Google Gemini"),
                            ("anthropic", "Anthropic"),
                            ("script", "Script Parser"),
                        ],
                        max_length=30,
                    ),
                ),
                ("model", models.CharField(blank=True, default="", max_length=120)),
                ("label", models.CharField(blank=True, default="baseline", max_length=120)),
                (
                    "status",
                    models.CharField(
                        choices=[("RUNNING", "Running"), ("SUCCESS", "Success"), ("FAILED", "Failed")],
                        default="RUNNING",
                        max_length=20,
                    ),
                ),
                ("bonus_count", models.IntegerField(default=0)),
                ("error_message", models.TextField(blank=True, default="")),
                (
                    "source_scraped_history",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="parser_reference_runs",
                        to="bonus_core.scrapedhistory",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["provider", "label", "status"], name="bc_pref_run_state_idx"),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("source_scraped_history", "provider", "label"),
                        name="bonus_core_pref_run_unique_idx",
                    )
                ],
            },
        ),
    ]
