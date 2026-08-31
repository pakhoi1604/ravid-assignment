import uuid
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.documents.models import IngestionDispatch, IngestionJob


def create_ingestion_dispatch(job: IngestionJob) -> IngestionDispatch:
    return IngestionDispatch.objects.create(
        job=job,
        generation=job.generation,
        available_at=timezone.now(),
    )


def retry_dispatch(dispatch: IngestionDispatch) -> IngestionDispatch:
    dispatch.status = IngestionDispatch.Status.PENDING
    dispatch.failure_code = ""
    dispatch.claim_token = None
    dispatch.claim_expires_at = None
    dispatch.available_at = timezone.now()
    dispatch.save(
        update_fields=[
            "status",
            "failure_code",
            "claim_token",
            "claim_expires_at",
            "available_at",
            "updated_at",
        ]
    )
    return dispatch


def claim_due_dispatches(*, limit: int) -> list[IngestionDispatch]:
    now = timezone.now()
    claim_expires_at = now + timedelta(seconds=settings.INGESTION_OUTBOX_CLAIM_SECONDS)
    claimed = []
    with transaction.atomic():
        due = (
            IngestionDispatch.objects.select_for_update(skip_locked=True)
            .select_related("job")
            .filter(status=IngestionDispatch.Status.PENDING, available_at__lte=now)
            .order_by("available_at", "created_at")[:limit]
        )
        for dispatch in due:
            dispatch.status = IngestionDispatch.Status.PUBLISHING
            dispatch.claim_token = uuid.uuid4()
            dispatch.claim_expires_at = claim_expires_at
            dispatch.attempts += 1
            dispatch.save(
                update_fields=[
                    "status",
                    "claim_token",
                    "claim_expires_at",
                    "attempts",
                    "updated_at",
                ]
            )
            claimed.append(dispatch)
    return claimed


def publish_due_dispatches(*, limit: int = 100) -> int:
    from apps.documents.tasks import enqueue_ingestion

    published = 0
    for dispatch in claim_due_dispatches(limit=limit):
        token = dispatch.claim_token
        try:
            enqueue_ingestion(dispatch.job, generation=dispatch.generation)
        except Exception:
            next_status = IngestionDispatch.Status.PENDING
            if dispatch.attempts >= settings.INGESTION_OUTBOX_MAX_ATTEMPTS:
                next_status = IngestionDispatch.Status.DEAD
            IngestionDispatch.objects.filter(
                pk=dispatch.pk,
                status=IngestionDispatch.Status.PUBLISHING,
                claim_token=token,
            ).update(
                status=next_status,
                failure_code="broker_publish_failed",
                claim_token=None,
                claim_expires_at=None,
                available_at=timezone.now()
                + timedelta(seconds=settings.INGESTION_OUTBOX_BACKOFF_SECONDS),
                updated_at=timezone.now(),
            )
            continue

        updated = IngestionDispatch.objects.filter(
            pk=dispatch.pk,
            status=IngestionDispatch.Status.PUBLISHING,
            claim_token=token,
        ).update(
            status=IngestionDispatch.Status.PUBLISHED,
            failure_code="",
            claim_token=None,
            claim_expires_at=None,
            published_at=timezone.now(),
            updated_at=timezone.now(),
        )
        published += updated
    return published


def reset_expired_dispatch_claims() -> int:
    now = timezone.now()
    expired = IngestionDispatch.objects.filter(
        status=IngestionDispatch.Status.PUBLISHING,
        claim_expires_at__lte=now,
    )
    dead_count = expired.filter(attempts__gte=settings.INGESTION_OUTBOX_MAX_ATTEMPTS).update(
        status=IngestionDispatch.Status.DEAD,
        claim_token=None,
        claim_expires_at=None,
        failure_code="publish_claim_expired",
        updated_at=now,
    )
    pending_count = expired.filter(attempts__lt=settings.INGESTION_OUTBOX_MAX_ATTEMPTS).update(
        status=IngestionDispatch.Status.PENDING,
        claim_token=None,
        claim_expires_at=None,
        failure_code="publish_claim_expired",
        available_at=now,
        updated_at=now,
    )
    return dead_count + pending_count
