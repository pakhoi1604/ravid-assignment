import uuid

import pytest
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db import IntegrityError

from apps.documents.models import Document, IngestionDispatch, IngestionGeneration, IngestionJob


@pytest.fixture
def user(db, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    return get_user_model().objects.create_user(username="owner", password="password")


@pytest.mark.django_db
def test_document_has_public_id_and_safe_upload_path(user):
    document = Document.objects.create(
        owner=user,
        original_filename="../unsafe name.txt",
        file=ContentFile(b"hello", name="../unsafe name.txt"),
        content_type="text/plain",
        size_bytes=5,
    )

    assert isinstance(document.public_id, uuid.UUID)
    assert f"user-{user.pk}" in document.file.name
    assert str(document.public_id) in document.file.name
    assert ".." not in document.file.name


@pytest.mark.django_db
def test_ingestion_job_defaults_to_pending(user):
    document = Document.objects.create(
        owner=user,
        original_filename="notes.txt",
        file=ContentFile(b"hello", name="notes.txt"),
        content_type="text/plain",
        size_bytes=5,
    )

    job = IngestionJob.objects.create(document=document)

    assert isinstance(job.task_id, uuid.UUID)
    assert isinstance(job.generation, uuid.UUID)
    assert job.status == IngestionJob.Status.PENDING
    assert job.error == ""
    assert job.failure_code == ""
    assert job.attempt_count == 0
    assert job.lease_expires_at is None


@pytest.mark.django_db
def test_user_delete_cascades_document_and_job(user):
    document = Document.objects.create(
        owner=user,
        original_filename="notes.txt",
        file=ContentFile(b"hello", name="notes.txt"),
        content_type="text/plain",
        size_bytes=5,
    )
    IngestionJob.objects.create(document=document)

    user.delete()

    assert Document.objects.count() == 0
    assert IngestionJob.objects.count() == 0


@pytest.mark.django_db
def test_ingestion_generation_is_unique_per_document_generation(user):
    document = Document.objects.create(
        owner=user,
        original_filename="notes.txt",
        file=ContentFile(b"hello", name="notes.txt"),
        content_type="text/plain",
        size_bytes=5,
    )
    generation = uuid.uuid4()
    IngestionGeneration.objects.create(document=document, generation=generation)

    with pytest.raises(IntegrityError):
        IngestionGeneration.objects.create(document=document, generation=generation)


@pytest.mark.django_db
def test_ingestion_dispatch_is_unique_per_job_generation(user):
    document = Document.objects.create(
        owner=user,
        original_filename="notes.txt",
        file=ContentFile(b"hello", name="notes.txt"),
        content_type="text/plain",
        size_bytes=5,
    )
    job = IngestionJob.objects.create(document=document)
    IngestionDispatch.objects.create(job=job, generation=job.generation)

    with pytest.raises(IntegrityError):
        IngestionDispatch.objects.create(job=job, generation=job.generation)
