import uuid
from types import SimpleNamespace

import pytest
from django.contrib.auth import get_user_model
from langchain_core.documents import Document as RetrievedDocument

from apps.documents.exceptions import VectorRetrievalError
from apps.documents.models import Document
from apps.documents.retrieval import retrieve_active_documents_for_user


@pytest.mark.django_db
def test_active_retrieval_filters_to_current_generations(settings):
    settings.MEDIA_ROOT = settings.BASE_DIR / "tmp-test-media"
    user = get_user_model().objects.create_user(username="owner")
    generation = uuid.uuid4()
    document = Document.objects.create(
        owner=user,
        original_filename="notes.txt",
        file="documents/notes.txt",
        content_type="text/plain",
        size_bytes=5,
        active_generation=generation,
    )
    calls = []
    result_document = RetrievedDocument(
        page_content="safe",
        metadata={
            "user_id": user.id,
            "document_id": str(document.public_id),
            "generation": str(generation),
        },
    )
    store = SimpleNamespace(
        retrieve_for_user=lambda **kwargs: calls.append(kwargs) or [result_document]
    )

    result = retrieve_active_documents_for_user(
        user_id=user.id,
        query="query",
        k=4,
        search_type="similarity",
        vector_store_factory=lambda: store,
    )

    assert result == [result_document]
    assert calls[0]["active_generations"] == (str(generation),)


@pytest.mark.django_db
def test_active_retrieval_returns_empty_without_active_documents():
    user = get_user_model().objects.create_user(username="owner")

    assert (
        retrieve_active_documents_for_user(
            user_id=user.id,
            query="query",
            k=4,
            search_type="similarity",
            vector_store_factory=lambda: pytest.fail("must not query Chroma"),
        )
        == []
    )


@pytest.mark.django_db
def test_active_retrieval_rejects_wrong_document_generation_pair():
    user = get_user_model().objects.create_user(username="owner")
    document = Document.objects.create(
        owner=user,
        original_filename="notes.txt",
        file="documents/notes.txt",
        content_type="text/plain",
        size_bytes=5,
        active_generation=uuid.uuid4(),
    )
    store = SimpleNamespace(
        retrieve_for_user=lambda **kwargs: [
            RetrievedDocument(
                page_content="stale",
                metadata={
                    "user_id": user.id,
                    "document_id": str(document.public_id),
                    "generation": str(uuid.uuid4()),
                },
            )
        ]
    )

    with pytest.raises(VectorRetrievalError):
        retrieve_active_documents_for_user(
            user_id=user.id,
            query="query",
            k=4,
            search_type="similarity",
            vector_store_factory=lambda: store,
        )
