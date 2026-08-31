import uuid

import django.db.models.deletion
from django.db import migrations, models


def seed_job_generations(apps, schema_editor):
    IngestionJob = apps.get_model("documents", "IngestionJob")
    for job in IngestionJob.objects.filter(generation__isnull=True).only("pk"):
        job.generation = uuid.uuid4()
        job.save(update_fields=["generation"])


class Migration(migrations.Migration):
    dependencies = [
        ("documents", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="document",
            name="active_generation",
            field=models.UUIDField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="ingestionjob",
            name="attempt_count",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="ingestionjob",
            name="failure_code",
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name="ingestionjob",
            name="generation",
            field=models.UUIDField(default=uuid.uuid4, editable=False),
        ),
        migrations.AddField(
            model_name="ingestionjob",
            name="lease_expires_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name="IngestionGeneration",
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
                            ("WRITING", "Writing"),
                            ("ACTIVE", "Active"),
                            ("STALE", "Stale"),
                            ("CLEANED", "Cleaned"),
                        ],
                        default="WRITING",
                        max_length=20,
                    ),
                ),
                ("expected_chunk_count", models.PositiveIntegerField(default=0)),
                ("observed_chunk_count", models.PositiveIntegerField(default=0)),
                ("cleanup_after", models.DateTimeField(blank=True, null=True)),
                ("cleanup_attempts", models.PositiveIntegerField(default=0)),
                ("failure_code", models.CharField(blank=True, max_length=80)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "document",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ingestion_generations",
                        to="documents.document",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(
                        fields=["status", "cleanup_after"],
                        name="documents_i_status_e58dac_idx",
                    ),
                    models.Index(fields=["generation"], name="documents_i_generat_a3358e_idx"),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("document", "generation"),
                        name="unique_ingestion_generation_per_document",
                    )
                ],
            },
        ),
        migrations.AddIndex(
            model_name="ingestionjob",
            index=models.Index(
                fields=["status", "generation"],
                name="documents_i_status_84d16a_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="ingestionjob",
            index=models.Index(
                fields=["status", "lease_expires_at"],
                name="documents_i_status_9179dc_idx",
            ),
        ),
        migrations.RunPython(seed_job_generations, migrations.RunPython.noop),
    ]
