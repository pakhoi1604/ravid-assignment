import pytest
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile

from apps.documents.exceptions import IngestionError
from apps.documents.models import Document, IngestionJob
from apps.documents.tasks import enqueue_ingestion, ingest_document


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
def test_ingest_document_marks_success(job, monkeypatch):
    monkeypatch.setattr("apps.documents.tasks.run_ingestion_pipeline", lambda current_job: 3)

    result = ingest_document(str(job.task_id))

    job.refresh_from_db()
    assert result == 3
    assert job.status == IngestionJob.Status.SUCCESS
    assert job.error == ""
    assert job.started_at is not None
    assert job.completed_at is not None


@pytest.mark.django_db
def test_ingest_document_marks_expected_failure(job, monkeypatch):
    def fail(_job):
        raise IngestionError("Failed to parse document content.")

    monkeypatch.setattr("apps.documents.tasks.run_ingestion_pipeline", fail)

    result = ingest_document(str(job.task_id))

    job.refresh_from_db()
    assert result == 0
    assert job.status == IngestionJob.Status.FAILURE
    assert job.error == "Failed to parse document content."
    assert job.completed_at is not None


@pytest.mark.django_db
def test_ingest_document_ignores_unknown_task_id():
    assert ingest_document("00000000-0000-0000-0000-000000000000") == 0
    assert ingest_document("not-a-uuid") == 0


@pytest.mark.django_db
def test_enqueue_uses_job_task_id(job, monkeypatch):
    calls = []

    class StubTask:
        def apply_async(self, *, args, task_id):
            calls.append((args, task_id))
            return object()

    monkeypatch.setattr("apps.documents.tasks.ingest_document", StubTask())

    enqueue_ingestion(job)

    assert calls == [([str(job.task_id)], str(job.task_id))]
