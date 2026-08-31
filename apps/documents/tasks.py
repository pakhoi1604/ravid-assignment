import logging
import uuid

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from apps.documents.exceptions import IngestionError
from apps.documents.ingestion import run_ingestion_pipeline
from apps.documents.models import IngestionJob

logger = logging.getLogger(__name__)


def sanitize_error(exc: Exception) -> str:
    if isinstance(exc, IngestionError):
        return str(exc) or "Failed to parse document content."
    return "Failed to parse document content."


def enqueue_ingestion(job: IngestionJob):
    return ingest_document.apply_async(args=[str(job.task_id)], task_id=str(job.task_id))


@shared_task(bind=True, autoretry_for=(), name="apps.documents.tasks.ingest_document")
def ingest_document(self, task_id: str) -> int:
    try:
        task_uuid = uuid.UUID(str(task_id))
    except ValueError:
        logger.warning("Ignoring ingestion task with invalid task_id", extra={"task_id": task_id})
        return 0

    try:
        job = IngestionJob.objects.select_related("document").get(task_id=task_uuid)
    except IngestionJob.DoesNotExist:
        logger.warning(
            "Ignoring ingestion task with unknown task_id", extra={"task_id": str(task_uuid)}
        )
        return 0

    with transaction.atomic():
        job.status = IngestionJob.Status.PROCESSING
        job.error = ""
        job.started_at = job.started_at or timezone.now()
        job.completed_at = None
        job.save(update_fields=["status", "error", "started_at", "completed_at", "updated_at"])

    try:
        chunk_count = run_ingestion_pipeline(job)
    except Exception as exc:
        job.status = IngestionJob.Status.FAILURE
        job.error = sanitize_error(exc)
        job.completed_at = timezone.now()
        job.save(update_fields=["status", "error", "completed_at", "updated_at"])
        if not isinstance(exc, IngestionError):
            logger.exception(
                "Unexpected document ingestion failure", extra={"task_id": str(task_uuid)}
            )
        return 0

    job.status = IngestionJob.Status.SUCCESS
    job.error = ""
    job.completed_at = timezone.now()
    job.save(update_fields=["status", "error", "completed_at", "updated_at"])
    return chunk_count
