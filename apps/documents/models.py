import uuid
from pathlib import Path

from django.conf import settings
from django.db import models
from django.utils.text import get_valid_filename


def document_upload_path(instance: "Document", filename: str) -> str:
    safe_name = get_valid_filename(Path(filename).name) or "upload"
    return f"documents/user-{instance.owner_id}/{instance.public_id}/{safe_name}"


class Document(models.Model):
    public_id = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    original_filename = models.CharField(max_length=255)
    file = models.FileField(upload_to=document_upload_path)
    content_type = models.CharField(max_length=120, blank=True)
    size_bytes = models.PositiveBigIntegerField()
    active_generation = models.UUIDField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["owner", "-created_at"]),
            models.Index(fields=["public_id"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.original_filename} ({self.public_id})"


class IngestionJob(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        SUCCESS = "SUCCESS", "Success"
        FAILURE = "FAILURE", "Failure"

    document = models.OneToOneField(
        Document,
        on_delete=models.CASCADE,
        related_name="ingestion_job",
    )
    task_id = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    generation = models.UUIDField(default=uuid.uuid4, editable=False)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    error = models.TextField(blank=True)
    failure_code = models.CharField(max_length=80, blank=True)
    attempt_count = models.PositiveIntegerField(default=0)
    lease_expires_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["task_id"]),
            models.Index(fields=["status", "generation"]),
            models.Index(fields=["status", "lease_expires_at"]),
            models.Index(fields=["status", "-created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.task_id} {self.status}"


class IngestionGeneration(models.Model):
    class Status(models.TextChoices):
        WRITING = "WRITING", "Writing"
        ACTIVE = "ACTIVE", "Active"
        STALE = "STALE", "Stale"
        CLEANED = "CLEANED", "Cleaned"

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="ingestion_generations",
    )
    generation = models.UUIDField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.WRITING)
    expected_chunk_count = models.PositiveIntegerField(default=0)
    observed_chunk_count = models.PositiveIntegerField(default=0)
    cleanup_after = models.DateTimeField(null=True, blank=True)
    cleanup_attempts = models.PositiveIntegerField(default=0)
    failure_code = models.CharField(max_length=80, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["document", "generation"],
                name="unique_ingestion_generation_per_document",
            )
        ]
        indexes = [
            models.Index(fields=["status", "cleanup_after"]),
            models.Index(fields=["generation"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.document_id} {self.generation} {self.status}"


class IngestionDispatch(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PUBLISHING = "PUBLISHING", "Publishing"
        PUBLISHED = "PUBLISHED", "Published"
        DEAD = "DEAD", "Dead"

    job = models.ForeignKey(
        IngestionJob,
        on_delete=models.CASCADE,
        related_name="dispatches",
    )
    generation = models.UUIDField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    attempts = models.PositiveIntegerField(default=0)
    available_at = models.DateTimeField(null=True, blank=True)
    claim_token = models.UUIDField(null=True, blank=True)
    claim_expires_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    failure_code = models.CharField(max_length=80, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["job", "generation"],
                name="unique_ingestion_dispatch_per_generation",
            )
        ]
        indexes = [
            models.Index(fields=["status", "available_at"]),
            models.Index(fields=["status", "claim_expires_at"]),
        ]
        ordering = ["available_at", "created_at"]

    def __str__(self) -> str:
        return f"{self.job_id} {self.generation} {self.status}"
