import logging
import uuid
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.documents.exceptions import IngestionError
from apps.documents.ingestion import run_ingestion_pipeline
from apps.documents.models import Document, IngestionGeneration, IngestionJob

logger = logging.getLogger(__name__)


def sanitize_error(exc: Exception) -> str:
    if isinstance(exc, IngestionError):
        return str(exc) or "Failed to parse document content."
    return "Failed to parse document content."


def enqueue_ingestion(job: IngestionJob, *, generation=None):
    generation = generation or job.generation
    delivery_id = uuid.uuid4()
    return ingest_document.apply_async(
        args=[str(job.task_id), str(generation)],
        task_id=str(delivery_id),
    )


def _claim_pending_job(task_uuid: uuid.UUID, generation: uuid.UUID) -> IngestionJob | None:
    lease_expires_at = timezone.now() + timedelta(
        seconds=settings.INGESTION_STALE_PROCESSING_SECONDS
    )
    with transaction.atomic():
        try:
            job = (
                IngestionJob.objects.select_for_update()
                .select_related("document")
                .get(task_id=task_uuid)
            )
        except IngestionJob.DoesNotExist:
            logger.warning(
                "Ignoring ingestion task with unknown task_id", extra={"task_id": str(task_uuid)}
            )
            return None
        if job.status != IngestionJob.Status.PENDING or job.generation != generation:
            return None
        job.status = IngestionJob.Status.PROCESSING
        job.error = ""
        job.failure_code = ""
        job.started_at = timezone.now()
        job.completed_at = None
        job.lease_expires_at = lease_expires_at
        job.attempt_count += 1
        job.save(
            update_fields=[
                "status",
                "error",
                "failure_code",
                "started_at",
                "completed_at",
                "lease_expires_at",
                "attempt_count",
                "updated_at",
            ]
        )
        return job


def _finalize_success(task_uuid: uuid.UUID, generation: uuid.UUID, chunk_count: int) -> bool:
    cleanup_after = timezone.now() + timedelta(seconds=settings.INGESTION_CLEANUP_GRACE_SECONDS)
    with transaction.atomic():
        try:
            job = (
                IngestionJob.objects.select_for_update()
                .select_related("document")
                .get(task_id=task_uuid)
            )
        except IngestionJob.DoesNotExist:
            return False
        if job.status != IngestionJob.Status.PROCESSING or job.generation != generation:
            _mark_stale_generation(job.document, generation)
            return False

        document = Document.objects.select_for_update().get(pk=job.document_id)
        previous_generation = document.active_generation
        document.active_generation = generation
        document.save(update_fields=["active_generation", "updated_at"])

        job.status = IngestionJob.Status.SUCCESS
        job.error = ""
        job.failure_code = ""
        job.completed_at = timezone.now()
        job.lease_expires_at = None
        job.save(
            update_fields=[
                "status",
                "error",
                "failure_code",
                "completed_at",
                "lease_expires_at",
                "updated_at",
            ]
        )
        IngestionGeneration.objects.update_or_create(
            document=document,
            generation=generation,
            defaults={
                "status": IngestionGeneration.Status.ACTIVE,
                "observed_chunk_count": chunk_count,
                "failure_code": "",
                "cleanup_after": None,
            },
        )
        if previous_generation and previous_generation != generation:
            IngestionGeneration.objects.update_or_create(
                document=document,
                generation=previous_generation,
                defaults={
                    "status": IngestionGeneration.Status.STALE,
                    "cleanup_after": cleanup_after,
                    "failure_code": "",
                },
            )
        return True


def _finalize_failure(task_uuid: uuid.UUID, generation: uuid.UUID, error: str) -> bool:
    with transaction.atomic():
        try:
            job = (
                IngestionJob.objects.select_for_update()
                .select_related("document")
                .get(task_id=task_uuid)
            )
        except IngestionJob.DoesNotExist:
            return False
        if job.status != IngestionJob.Status.PROCESSING or job.generation != generation:
            _mark_stale_generation(job.document, generation)
            return False
        job.status = IngestionJob.Status.FAILURE
        job.error = error
        job.failure_code = "ingestion_failed"
        job.completed_at = timezone.now()
        job.lease_expires_at = None
        job.save(
            update_fields=[
                "status",
                "error",
                "failure_code",
                "completed_at",
                "lease_expires_at",
                "updated_at",
            ]
        )
        IngestionGeneration.objects.update_or_create(
            document=job.document,
            generation=generation,
            defaults={
                "status": IngestionGeneration.Status.STALE,
                "failure_code": "ingestion_failed",
                "cleanup_after": timezone.now()
                + timedelta(seconds=settings.INGESTION_CLEANUP_GRACE_SECONDS),
            },
        )
        return True


def _mark_stale_generation(document, generation: uuid.UUID) -> None:
    IngestionGeneration.objects.update_or_create(
        document=document,
        generation=generation,
        defaults={
            "status": IngestionGeneration.Status.STALE,
            "cleanup_after": timezone.now()
            + timedelta(seconds=settings.INGESTION_CLEANUP_GRACE_SECONDS),
        },
    )


@shared_task(
    bind=True,
    autoretry_for=(),
    ignore_result=True,
    name="apps.documents.tasks.ingest_document",
)
def ingest_document(self, task_id: str, generation: str | None = None) -> int:
    try:
        task_uuid = uuid.UUID(str(task_id))
        generation_uuid = uuid.UUID(str(generation)) if generation is not None else None
    except (TypeError, ValueError):
        logger.warning("Ignoring ingestion task with invalid task_id", extra={"task_id": task_id})
        return 0
    if generation_uuid is None:
        logger.warning(
            "Ignoring ingestion task without generation", extra={"task_id": str(task_uuid)}
        )
        return 0

    job = _claim_pending_job(task_uuid, generation_uuid)
    if job is None:
        return 0

    try:
        chunk_count = run_ingestion_pipeline(job, generation_uuid)
    except Exception as exc:
        _finalize_failure(task_uuid, generation_uuid, sanitize_error(exc))
        if not isinstance(exc, IngestionError):
            logger.exception(
                "Unexpected document ingestion failure", extra={"task_id": str(task_uuid)}
            )
        return 0

    _finalize_success(task_uuid, generation_uuid, chunk_count)
    return chunk_count


@shared_task(
    bind=True,
    autoretry_for=(),
    ignore_result=True,
    name="apps.documents.tasks.publish_ingestion_dispatches",
)
def publish_ingestion_dispatches(self, limit: int = 100) -> int:
    from apps.documents.dispatch import publish_due_dispatches, reset_expired_dispatch_claims

    reset_expired_dispatch_claims()
    return publish_due_dispatches(limit=limit)


@shared_task(
    bind=True,
    autoretry_for=(),
    ignore_result=True,
    name="apps.documents.tasks.recover_ingestion_work",
)
def recover_ingestion_work(self, limit: int = 100) -> int:
    from apps.documents.recovery import cleanup_due_generations, recover_stale_ingestion_jobs

    recovered = recover_stale_ingestion_jobs(limit=limit)
    cleaned = cleanup_due_generations(limit=limit)
    return recovered + cleaned
