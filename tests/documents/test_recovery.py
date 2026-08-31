from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.utils import timezone

from apps.documents.models import Document, IngestionDispatch, IngestionGeneration, IngestionJob
from apps.documents.recovery import (
    cleanup_due_generations,
    recover_stale_ingestion_jobs,
    reindex_legacy_documents,
)


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
def test_recover_stale_processing_rotates_generation(job):
    old_generation = job.generation
    job.status = IngestionJob.Status.PROCESSING
    job.lease_expires_at = timezone.now() - timedelta(seconds=1)
    job.save(update_fields=["status", "lease_expires_at"])

    assert recover_stale_ingestion_jobs(limit=10) == 1

    job.refresh_from_db()
    assert job.status == IngestionJob.Status.PENDING
    assert job.generation != old_generation
    assert IngestionDispatch.objects.get().generation == job.generation


@pytest.mark.django_db
def test_recover_stale_jobs_honors_dry_run(job):
    job.status = IngestionJob.Status.PROCESSING
    job.lease_expires_at = timezone.now() - timedelta(seconds=1)
    job.save(update_fields=["status", "lease_expires_at"])
    generation = job.generation

    assert recover_stale_ingestion_jobs(limit=10, dry_run=True) == 1

    job.refresh_from_db()
    assert job.status == IngestionJob.Status.PROCESSING
    assert job.generation == generation
    assert IngestionDispatch.objects.count() == 0


@pytest.mark.django_db
def test_recover_stale_jobs_does_not_starve_stale_rows_behind_fresh_rows(job):
    user = job.document.owner
    fresh_document = Document.objects.create(
        owner=user,
        original_filename="fresh.txt",
        file=ContentFile(b"fresh", name="fresh.txt"),
        content_type="text/plain",
        size_bytes=5,
    )
    fresh_job = IngestionJob.objects.create(document=fresh_document)
    fresh_job.created_at = timezone.now()
    fresh_job.save(update_fields=["created_at"])
    job.status = IngestionJob.Status.PROCESSING
    job.lease_expires_at = timezone.now() - timedelta(seconds=1)
    job.save(update_fields=["status", "lease_expires_at"])

    assert recover_stale_ingestion_jobs(limit=1) == 1

    job.refresh_from_db()
    fresh_job.refresh_from_db()
    assert job.status == IngestionJob.Status.PENDING
    assert fresh_job.status == IngestionJob.Status.PENDING


@pytest.mark.django_db
def test_reindex_legacy_documents_resets_success_job(job):
    job.status = IngestionJob.Status.SUCCESS
    job.save(update_fields=["status"])
    old_generation = job.generation

    assert reindex_legacy_documents(limit=10) == 1

    job.refresh_from_db()
    assert job.status == IngestionJob.Status.PENDING
    assert job.generation != old_generation
    assert IngestionDispatch.objects.get().generation == job.generation


@pytest.mark.django_db
def test_cleanup_due_generations_exhausts_after_bounded_failures(job, monkeypatch, settings):
    settings.INGESTION_CLEANUP_MAX_ATTEMPTS = 1
    job.status = IngestionJob.Status.SUCCESS
    job.save(update_fields=["status"])
    manifest = IngestionGeneration.objects.create(
        document=job.document,
        generation=job.generation,
        status=IngestionGeneration.Status.STALE,
        cleanup_after=timezone.now() - timedelta(seconds=1),
    )

    class Store:
        def delete_document_generation(self, **kwargs):
            from apps.documents.exceptions import IngestionError

            raise IngestionError("Failed to parse document content.")

    monkeypatch.setattr("apps.documents.recovery.get_vector_store", lambda: Store())

    assert cleanup_due_generations(limit=10) == 0
    manifest.refresh_from_db()
    assert manifest.failure_code == "cleanup_exhausted"
    assert manifest.cleanup_after is None
