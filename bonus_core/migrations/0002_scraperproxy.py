# Generated for scraper proxy configuration.
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("bonus_core", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ScraperProxy",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(blank=True, default="", max_length=120)),
                ("server", models.CharField(max_length=500)),
                ("username", models.CharField(blank=True, default="", max_length=255)),
                ("password", models.CharField(blank=True, default="", max_length=255)),
                ("is_active", models.BooleanField(default=True)),
                ("priority", models.IntegerField(default=0)),
                ("notes", models.TextField(blank=True, default="")),
                (
                    "geo",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="scraper_proxies",
                        to="bonus_core.geo",
                    ),
                ),
            ],
            options={
                "ordering": ["-priority", "id"],
                "indexes": [
                    models.Index(fields=["geo", "is_active"], name="bc_sproxy_geo_active_idx"),
                    models.Index(fields=["is_active", "priority"], name="bc_sproxy_active_prio_idx"),
                ],
            },
        ),
    ]
