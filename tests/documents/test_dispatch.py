import pytest
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.utils import timezone

from apps.documents.dispatch import (
    claim_due_dispatches,
    create_ingestion_dispatch,
    publish_due_dispatches,
    reset_expired_dispatch_claims,
)
from apps.documents.models import Document, IngestionDispatch, IngestionJob


@pytest.fixture
def job(db, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    user = get_user_model().objects.create_user(username="owner", password="password")
    document = Document.objects.create(
        owner=user,
        original_filename="notes.txt",
        file=ContentFile(b"hello", name="notes.txt"),
        content_type="text/plain",
        size_bytes=5,
    )
    return IngestionJob.objects.create(document=document)


@pytest.mark.django_db
def test_create_ingestion_dispatch_uses_current_generation(job):
    dispatch = create_ingestion_dispatch(job)

    assert dispatch.job == job
    assert dispatch.generation == job.generation
    assert dispatch.status == IngestionDispatch.Status.PENDING


@pytest.mark.django_db
def test_claim_due_dispatches_sets_lease(job):
    dispatch = create_ingestion_dispatch(job)

    claimed = claim_due_dispatches(limit=1)
    dispatch.refresh_from_db()

    assert claimed == [dispatch]
    assert dispatch.status == IngestionDispatch.Status.PUBLISHING
    assert dispatch.claim_token is not None
    assert dispatch.claim_expires_at is not None
    assert dispatch.attempts == 1


@pytest.mark.django_db
def test_publish_due_dispatches_marks_published(job, monkeypatch):
    create_ingestion_dispatch(job)
    calls = []
    monkeypatch.setattr(
        "apps.documents.tasks.enqueue_ingestion",
        lambda current_job, generation: calls.append((current_job.pk, generation)),
    )

    assert publish_due_dispatches(limit=1) == 1

    dispatch = IngestionDispatch.objects.get()
    assert dispatch.status == IngestionDispatch.Status.PUBLISHED
    assert calls == [(job.pk, job.generation)]


@pytest.mark.django_db
def test_reset_expired_dispatch_claims(job):
    dispatch = create_ingestion_dispatch(job)
    dispatch.status = IngestionDispatch.Status.PUBLISHING
    dispatch.claim_token = "00000000-0000-0000-0000-000000000000"
    dispatch.claim_expires_at = timezone.now()
    dispatch.save()

    assert reset_expired_dispatch_claims() == 1
    dispatch.refresh_from_db()
    assert dispatch.status == IngestionDispatch.Status.PENDING
    assert dispatch.failure_code == "publish_claim_expired"


@pytest.mark.django_db
def test_reset_expired_dispatch_claims_marks_exhausted_dead(job, settings):
    settings.INGESTION_OUTBOX_MAX_ATTEMPTS = 2
    dispatch = create_ingestion_dispatch(job)
    dispatch.status = IngestionDispatch.Status.PUBLISHING
    dispatch.attempts = 2
    dispatch.claim_token = "00000000-0000-0000-0000-000000000000"
    dispatch.claim_expires_at = timezone.now()
    dispatch.save()

    assert reset_expired_dispatch_claims() == 1
    dispatch.refresh_from_db()
    assert dispatch.status == IngestionDispatch.Status.DEAD
