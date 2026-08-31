from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management import call_command

from apps.documents.models import Document


@pytest.mark.django_db
def test_reconcile_orphan_uploads_deletes_old_unreferenced_file(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    settings.INGESTION_ORPHAN_UPLOAD_GRACE_SECONDS = 0
    orphan = tmp_path / "documents" / "orphan.txt"
    orphan.parent.mkdir(parents=True)
    orphan.write_text("old", encoding="utf-8")

    call_command("reconcile_orphan_uploads")

    assert not orphan.exists()


@pytest.mark.django_db
def test_reconcile_orphan_uploads_preserves_referenced_file(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    settings.INGESTION_ORPHAN_UPLOAD_GRACE_SECONDS = 0
    user = get_user_model().objects.create_user(username="owner")
    document = Document.objects.create(
        owner=user,
        original_filename="notes.txt",
        file=ContentFile(b"hello", name="notes.txt"),
        content_type="text/plain",
        size_bytes=5,
    )
    path = Path(settings.MEDIA_ROOT) / document.file.name

    call_command("reconcile_orphan_uploads")

    assert path.exists()
