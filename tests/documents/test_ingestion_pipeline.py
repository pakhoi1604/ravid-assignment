import pytest
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile

from apps.documents.exceptions import IngestionError
from apps.documents.ingestion import run_ingestion_pipeline
from apps.documents.models import Document, IngestionJob


@pytest.fixture
def job(db, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    user = get_user_model().objects.create_user(username="owner", password="password")
    document = Document.objects.create(
        owner=user,
        original_filename="notes.txt",
        file=ContentFile(b"hello world", name="notes.txt"),
        content_type="text/plain",
        size_bytes=11,
    )
    return IngestionJob.objects.create(document=document)


def test_run_ingestion_pipeline_replaces_document_chunks(job, monkeypatch):
    captured = []

    class Store:
        def replace_document_chunks(self, *, user_id, document_id, chunks):
            captured.append((user_id, document_id, chunks))

    monkeypatch.setattr("apps.documents.extraction.extract_text", lambda *_args: "alpha beta")
    monkeypatch.setattr(
        "apps.documents.chunking.split_text", lambda *_args, **_kwargs: ["alpha", "beta"]
    )
    monkeypatch.setattr("apps.documents.vector_store.get_vector_store", lambda: Store())

    count = run_ingestion_pipeline(job)

    assert count == 2
    user_id, document_id, chunks = captured[0]
    assert user_id == job.document.owner_id
    assert document_id == str(job.document.public_id)
    assert [chunk.text for chunk in chunks] == ["alpha", "beta"]
    assert chunks[0].metadata["user_id"] == job.document.owner_id
    assert chunks[0].metadata["document_id"] == str(job.document.public_id)
    assert chunks[0].metadata["ingestion_job_id"] == job.pk
    assert chunks[0].metadata["task_id"] == str(job.task_id)
    assert chunks[0].metadata["chunk_index"] == 0
    assert chunks[0].metadata["source_filename"] == "notes.txt"
    assert chunks[0].id == f"document-{job.document.public_id}-chunk-0"
    assert chunks[1].metadata["chunk_index"] == 1
    assert chunks[1].id == f"document-{job.document.public_id}-chunk-1"


def test_run_ingestion_pipeline_fails_on_empty_text(job, monkeypatch):
    monkeypatch.setattr("apps.documents.extraction.extract_text", lambda *_args: "   ")

    with pytest.raises(IngestionError):
        run_ingestion_pipeline(job)
