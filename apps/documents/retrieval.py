from collections.abc import Callable, Sequence
from typing import Protocol

from langchain_core.documents import Document as RetrievedDocument

from apps.documents.exceptions import VectorRetrievalError
from apps.documents.models import Document
from apps.documents.vector_store import get_vector_store


class ActiveDocumentRetriever(Protocol):
    def retrieve_for_user(
        self,
        *,
        user_id: int,
        query: str,
        active_generations: Sequence[str] | None,
        k: int,
        search_type: str,
        score_threshold: float | None = None,
        fetch_k: int | None = None,
    ) -> list[RetrievedDocument]: ...


def retrieve_active_documents_for_user(
    *,
    user_id: int,
    query: str,
    k: int,
    search_type: str,
    score_threshold: float | None = None,
    fetch_k: int | None = None,
    vector_store_factory: Callable[[], ActiveDocumentRetriever] = get_vector_store,
) -> list[RetrievedDocument]:
    active = {
        str(public_id): str(generation)
        for public_id, generation in Document.objects.filter(
            owner_id=user_id,
            active_generation__isnull=False,
        ).values_list("public_id", "active_generation")
    }
    if not active:
        return []

    documents = vector_store_factory().retrieve_for_user(
        user_id=user_id,
        query=query,
        active_generations=tuple(sorted(set(active.values()))),
        k=k,
        search_type=search_type,
        score_threshold=score_threshold,
        fetch_k=fetch_k,
    )
    for document in documents:
        metadata = document.metadata
        document_id = metadata.get("document_id")
        generation = metadata.get("generation")
        if not isinstance(document_id, str) or active.get(document_id) != generation:
            raise VectorRetrievalError("Vector retrieval is unavailable.")
    return documents
