"""Initial migration — creates ImportBatch and MailingRecord tables."""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies: list = []

    operations = [
        migrations.CreateModel(
            name="ImportBatch",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("file_path", models.CharField(max_length=1024)),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("total", models.PositiveIntegerField(default=0)),
                ("created", models.PositiveIntegerField(default=0)),
                ("skipped", models.PositiveIntegerField(default=0)),
                ("failed", models.PositiveIntegerField(default=0)),
            ],
            options={
                "verbose_name": "Import Batch",
                "verbose_name_plural": "Import Batches",
            },
        ),
        migrations.CreateModel(
            name="MailingRecord",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "external_id",
                    models.CharField(db_index=True, max_length=255, unique=True),
                ),
                ("user_id", models.PositiveIntegerField()),
                ("email", models.EmailField(max_length=254)),
                ("subject", models.CharField(max_length=998)),
                ("message", models.TextField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("sent", "Sent"),
                            ("failed", "Failed"),
                        ],
                        default="pending",
                        max_length=10,
                    ),
                ),
                ("error", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "batch",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="records",
                        to="mailings.importbatch",
                    ),
                ),
            ],
            options={
                "verbose_name": "Mailing Record",
                "verbose_name_plural": "Mailing Records",
            },
        ),
    ]
