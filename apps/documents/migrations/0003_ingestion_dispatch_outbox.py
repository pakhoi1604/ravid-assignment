import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("documents", "0002_ingestion_generations"),
    ]

    operations = [
        migrations.CreateModel(
            name="IngestionDispatch",
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
                ("generation", models.UUIDField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "Pending"),
                            ("PUBLISHING", "Publishing"),
                            ("PUBLISHED", "Published"),
                            ("DEAD", "Dead"),
                        ],
                        default="PENDING",
                        max_length=20,
                    ),
                ),
                ("attempts", models.PositiveIntegerField(default=0)),
                ("available_at", models.DateTimeField(blank=True, null=True)),
                ("claim_token", models.UUIDField(blank=True, null=True)),
                ("claim_expires_at", models.DateTimeField(blank=True, null=True)),
                ("published_at", models.DateTimeField(blank=True, null=True)),
                ("failure_code", models.CharField(blank=True, max_length=80)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "job",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="dispatches",
                        to="documents.ingestionjob",
                    ),
                ),
            ],
            options={
                "ordering": ["available_at", "created_at"],
                "indexes": [
                    models.Index(
                        fields=["status", "available_at"],
                        name="documents_i_status_3521e2_idx",
                    ),
                    models.Index(
                        fields=["status", "claim_expires_at"],
                        name="documents_i_status_234d9b_idx",
                    ),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("job", "generation"),
                        name="unique_ingestion_dispatch_per_generation",
                    )
                ],
            },
        ),
    ]
