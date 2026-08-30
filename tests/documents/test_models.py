import uuid

import pytest
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile

from apps.documents.models import Document, IngestionJob


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
    assert job.status == IngestionJob.Status.PENDING
    assert job.error == ""


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
