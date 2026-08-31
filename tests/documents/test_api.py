import uuid

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse

from apps.documents.models import Document, IngestionDispatch, IngestionJob


@pytest.fixture
def user(db):
    return get_user_model().objects.create_user(username="owner", password="password")


@pytest.fixture
def other_user(db):
    return get_user_model().objects.create_user(username="other", password="password")


def auth_headers_for(client, user):
    response = client.post(
        reverse("token_obtain_pair"),
        {"username": user.username, "password": "password"},
        content_type="application/json",
    )
    return {"HTTP_AUTHORIZATION": f"Bearer {response.json()['access']}"}


def upload_file(name="notes.txt", content=b"hello"):
    return SimpleUploadedFile(name, content, content_type="text/plain")


@pytest.mark.django_db
@override_settings(MEDIA_ROOT="/tmp/ravid-test-media")
def test_upload_creates_document_and_job(client, user, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        response = client.post(
            reverse("document-upload"),
            {"file": upload_file()},
            **auth_headers_for(client, user),
        )

    assert response.status_code == 202
    payload = response.json()
    assert payload["message"] == "Document uploaded and ingestion started"
    assert uuid.UUID(payload["document_id"])
    assert uuid.UUID(payload["task_id"])

    document = Document.objects.get()
    job = IngestionJob.objects.get()
    dispatch = IngestionDispatch.objects.get()
    assert document.owner == user
    assert document.original_filename == "notes.txt"
    assert document.size_bytes == 5
    assert dispatch.job == job
    assert dispatch.generation == job.generation


@pytest.mark.django_db
def test_upload_rejects_invalid_extension(client, user):
    response = client.post(
        reverse("document-upload"),
        {"file": upload_file("image.png")},
        **auth_headers_for(client, user),
    )

    assert response.status_code == 400
    assert response.json() == {
        "error": "Invalid file format. Only PDF, TXT, and Markdown files are allowed."
    }


@pytest.mark.django_db
def test_upload_rejects_missing_file(client, user):
    response = client.post(reverse("document-upload"), {}, **auth_headers_for(client, user))

    assert response.status_code == 400
    assert response.json()["error"]


@pytest.mark.django_db
@override_settings(MAX_UPLOAD_SIZE_MB=0)
def test_upload_rejects_oversized_file(client, user):
    response = client.post(
        reverse("document-upload"),
        {"file": upload_file(content=b"x")},
        **auth_headers_for(client, user),
    )

    assert response.status_code == 400
    assert response.json()["error"] == "File exceeds maximum size of 0 MB."


@pytest.mark.django_db
def test_status_serializes_pending_truthfully(client, user):
    document = Document.objects.create(
        owner=user,
        original_filename="notes.txt",
        file="documents/notes.txt",
        content_type="text/plain",
        size_bytes=5,
    )
    job = IngestionJob.objects.create(document=document)

    response = client.get(
        reverse("document-status"),
        {"task_id": str(job.task_id)},
        **auth_headers_for(client, user),
    )

    assert response.status_code == 200
    assert response.json() == {"task_id": str(job.task_id), "status": "PENDING"}


@pytest.mark.django_db
def test_status_success_and_failure_shapes(client, user):
    success_document = Document.objects.create(
        owner=user,
        original_filename="ok.txt",
        file="documents/ok.txt",
        content_type="text/plain",
        size_bytes=2,
    )
    success_job = IngestionJob.objects.create(
        document=success_document,
        status=IngestionJob.Status.SUCCESS,
    )
    failure_document = Document.objects.create(
        owner=user,
        original_filename="bad.txt",
        file="documents/bad.txt",
        content_type="text/plain",
        size_bytes=3,
    )
    failure_job = IngestionJob.objects.create(
        document=failure_document,
        status=IngestionJob.Status.FAILURE,
        error="Failed to parse document content.",
    )

    success_response = client.get(
        reverse("document-status"),
        {"task_id": str(success_job.task_id)},
        **auth_headers_for(client, user),
    )
    failure_response = client.get(
        reverse("document-status"),
        {"task_id": str(failure_job.task_id)},
        **auth_headers_for(client, user),
    )

    assert success_response.status_code == 200
    assert success_response.json()["message"] == (
        "Document successfully parsed, embedded, and indexed in vector storage."
    )
    assert failure_response.status_code == 200
    assert failure_response.json()["error"] == "Failed to parse document content."


@pytest.mark.django_db
def test_status_is_owner_scoped(client, user, other_user):
    document = Document.objects.create(
        owner=other_user,
        original_filename="private.txt",
        file="documents/private.txt",
        content_type="text/plain",
        size_bytes=7,
    )
    job = IngestionJob.objects.create(document=document)

    response = client.get(
        reverse("document-status"),
        {"task_id": str(job.task_id)},
        **auth_headers_for(client, user),
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_status_requires_task_id(client, user):
    response = client.get(reverse("document-status"), **auth_headers_for(client, user))

    assert response.status_code == 400
    assert response.json() == {"error": "task_id is required."}


@pytest.mark.django_db
def test_status_treats_malformed_task_id_as_not_found(client, user):
    response = client.get(
        reverse("document-status"),
        {"task_id": "not-a-uuid"},
        **auth_headers_for(client, user),
    )

    assert response.status_code == 404
    assert response.json() == {"error": "Ingestion task not found."}
