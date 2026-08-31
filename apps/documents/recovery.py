import uuid
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.documents.dispatch import create_ingestion_dispatch
from apps.documents.exceptions import IngestionError
from apps.documents.models import IngestionGeneration, IngestionJob
from apps.documents.vector_store import get_vector_store


def recover_stale_ingestion_jobs(*, limit: int = 100, dry_run: bool = False) -> int:
    now = timezone.now()
    stale_pending_before = now - timedelta(seconds=settings.INGESTION_STALE_PENDING_SECONDS)
    recovered = 0
    with transaction.atomic():
        jobs = (
            IngestionJob.objects.select_for_update(skip_locked=True)
            .select_related("document")
            .filter(
                Q(status=IngestionJob.Status.PENDING, created_at__lte=stale_pending_before)
                | Q(status=IngestionJob.Status.PROCESSING, lease_expires_at__lte=now)
            )
            .order_by("created_at")[:limit]
        )
        for job in jobs:
            if job.attempt_count >= settings.INGESTION_MAX_RECOVERY_ATTEMPTS:
                if not dry_run:
                    job.status = IngestionJob.Status.FAILURE
                    job.failure_code = "manual_intervention_required"
                    job.completed_at = now
                    job.save(update_fields=["status", "failure_code", "completed_at", "updated_at"])
                continue
            recovered += 1
            if dry_run:
                continue
            job.generation = uuid.uuid4()
            job.status = IngestionJob.Status.PENDING
            job.error = ""
            job.failure_code = ""
            job.started_at = None
            job.completed_at = None
            job.lease_expires_at = None
            job.save(
                update_fields=[
                    "generation",
                    "status",
                    "error",
                    "failure_code",
                    "started_at",
                    "completed_at",
                    "lease_expires_at",
                    "updated_at",
                ]
            )
            create_ingestion_dispatch(job)
    return recovered


def reindex_legacy_documents(*, limit: int = 100, dry_run: bool = False) -> int:
    queryset = (
        IngestionJob.objects.select_related("document")
        .filter(status=IngestionJob.Status.SUCCESS, document__active_generation__isnull=True)
        .order_by("created_at")[:limit]
    )
    count = 0
    with transaction.atomic():
        for job in queryset.select_for_update(skip_locked=True):
            count += 1
            if dry_run:
                continue
            job.generation = uuid.uuid4()
            job.status = IngestionJob.Status.PENDING
            job.error = ""
            job.failure_code = ""
            job.started_at = None
            job.completed_at = None
            job.lease_expires_at = None
            job.save(
                update_fields=[
                    "generation",
                    "status",
                    "error",
                    "failure_code",
                    "started_at",
                    "completed_at",
                    "lease_expires_at",
                    "updated_at",
                ]
            )
            create_ingestion_dispatch(job)
    return count


def cleanup_due_generations(*, limit: int = 100) -> int:
    now = timezone.now()
    cleaned = 0
    live_generations = set(
        IngestionJob.objects.filter(
            status__in=[IngestionJob.Status.PENDING, IngestionJob.Status.PROCESSING]
        ).values_list("generation", flat=True)
    )
    manifests = (
        IngestionGeneration.objects.select_related("document", "document__owner")
        .filter(
            status=IngestionGeneration.Status.STALE,
            cleanup_after__lte=now,
            cleanup_attempts__lt=settings.INGESTION_CLEANUP_MAX_ATTEMPTS,
        )
        .order_by("cleanup_after", "created_at")[:limit]
    )
    for manifest in manifests:
        if (
            manifest.document.active_generation == manifest.generation
            or manifest.generation in live_generations
        ):
            continue
        try:
            get_vector_store().delete_document_generation(
                user_id=manifest.document.owner_id,
                document_id=str(manifest.document.public_id),
                generation=str(manifest.generation),
            )
        except IngestionError:
            manifest.cleanup_attempts += 1
            if manifest.cleanup_attempts >= settings.INGESTION_CLEANUP_MAX_ATTEMPTS:
                manifest.failure_code = "cleanup_exhausted"
                manifest.cleanup_after = None
            else:
                manifest.failure_code = "cleanup_failed"
                manifest.cleanup_after = now + timedelta(
                    seconds=settings.INGESTION_CLEANUP_BACKOFF_SECONDS
                )
            manifest.save(
                update_fields=[
                    "cleanup_attempts",
                    "failure_code",
                    "cleanup_after",
                    "updated_at",
                ]
            )
            continue
        manifest.status = IngestionGeneration.Status.CLEANED
        manifest.failure_code = ""
        manifest.cleanup_attempts += 1
        manifest.save(update_fields=["status", "failure_code", "cleanup_attempts", "updated_at"])
        cleaned += 1
    return cleaned
