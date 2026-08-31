import math
from collections.abc import Sequence
from functools import lru_cache
from threading import Lock

import httpx
from django.conf import settings
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

from apps.documents.contracts import Chunk
from apps.documents.exceptions import IngestionError, VectorRetrievalError

ALLOWED_RETRIEVAL_SEARCH_TYPES = {"similarity", "similarity_score_threshold", "mmr"}
_STORE_BUILD_LOCK = Lock()


def validate_retrieval_settings(
    *,
    k: int,
    search_type: str,
    score_threshold: float | None = None,
    fetch_k: int | None = None,
) -> None:
    if isinstance(k, bool) or not isinstance(k, int) or k <= 0:
        raise ValueError("k must be a positive integer.")
    if search_type not in ALLOWED_RETRIEVAL_SEARCH_TYPES:
        raise ValueError("search_type is not supported.")

    if search_type == "similarity_score_threshold":
        if (
            not isinstance(score_threshold, float)
            or not math.isfinite(score_threshold)
            or not 0 <= score_threshold <= 1
        ):
            raise ValueError("score_threshold must be a finite float between 0 and 1.")

    if search_type == "mmr" and fetch_k is not None:
        if isinstance(fetch_k, bool) or not isinstance(fetch_k, int) or fetch_k < k:
            raise ValueError("fetch_k must be an integer greater than or equal to k.")


def build_search_kwargs_for_user(
    *,
    user_id: int,
    k: int,
    search_type: str,
    score_threshold: float | None,
    fetch_k: int | None,
) -> dict[str, object]:
    validate_retrieval_settings(
        k=k,
        search_type=search_type,
        score_threshold=score_threshold,
        fetch_k=fetch_k,
    )

    search_kwargs: dict[str, object] = {"k": k, "filter": {"user_id": user_id}}
    if search_type == "similarity_score_threshold":
        search_kwargs["score_threshold"] = score_threshold
    elif search_type == "mmr" and fetch_k is not None:
        search_kwargs["fetch_k"] = fetch_k

    return search_kwargs


@lru_cache(maxsize=8)
def _build_cached_store(
    collection_name: str,
    chroma_host: str,
    chroma_port: int,
    embedding_model_name: str,
):
    import chromadb
    from langchain_chroma import Chroma
    from langchain_huggingface import HuggingFaceEmbeddings

    try:
        client = chromadb.HttpClient(host=chroma_host, port=chroma_port)
    except ValueError as exc:
        if not str(exc).startswith("Could not connect to a Chroma server."):
            raise
        raise IngestionError("Failed to parse document content.") from exc
    embeddings = HuggingFaceEmbeddings(model_name=embedding_model_name)
    return Chroma(
        client=client,
        collection_name=collection_name,
        embedding_function=embeddings,
    )


class DocumentVectorStore:
    def __init__(self, collection_name: str | None = None):
        self.collection_name = collection_name or settings.VECTOR_COLLECTION_NAME

    def replace_document_chunks(
        self,
        *,
        user_id: int,
        document_id: str,
        chunks: Sequence[Chunk],
    ) -> None:
        if not chunks:
            raise IngestionError("Failed to parse document content.")
        if isinstance(user_id, bool) or not isinstance(user_id, int):
            raise IngestionError("Failed to parse document content.")
        if not isinstance(document_id, str) or not document_id:
            raise IngestionError("Failed to parse document content.")
        for chunk in chunks:
            metadata_user_id = chunk.metadata.get("user_id")
            chunk_index = chunk.metadata.get("chunk_index")
            expected_id = f"document-{document_id}-chunk-{chunk_index}"
            if (
                type(metadata_user_id) is not int
                or metadata_user_id != user_id
                or chunk.metadata.get("document_id") != document_id
                or type(chunk_index) is not int
                or chunk_index < 0
                or chunk.id != expected_id
            ):
                raise IngestionError("Failed to parse document content.")

        store = self._build_store()
        ids = [chunk.id for chunk in chunks]
        where = {
            "$and": [
                {"user_id": {"$eq": user_id}},
                {"document_id": {"$eq": document_id}},
            ]
        }

        try:
            lookup = store.get(where=where, include=[])
            old_ids = self._validate_lookup_ids(lookup)
            incoming_lookup = store.get(ids=ids, include=["metadatas"])
            self._validate_incoming_id_ownership(
                incoming_lookup,
                user_id=user_id,
                document_id=document_id,
            )
            if old_ids:
                store.delete(ids=old_ids)
            store.add_texts(
                texts=[chunk.text for chunk in chunks],
                metadatas=[chunk.metadata for chunk in chunks],
                ids=ids,
            )
        except IngestionError:
            raise
        except ValueError as exc:
            if not self._is_chroma_connection_error(exc):
                raise
            raise IngestionError("Failed to parse document content.") from exc
        except (self._chroma_error_type(), httpx.TransportError, OSError) as exc:
            raise IngestionError("Failed to parse document content.") from exc

    def as_retriever_for_user(
        self,
        *,
        user_id: int,
        k: int,
        search_type: str = "similarity",
        score_threshold: float | None = None,
        fetch_k: int | None = None,
    ) -> BaseRetriever:
        if isinstance(user_id, bool) or not isinstance(user_id, int):
            raise ValueError("user_id must be an integer.")
        search_kwargs = build_search_kwargs_for_user(
            user_id=user_id,
            k=k,
            search_type=search_type,
            score_threshold=score_threshold,
            fetch_k=fetch_k,
        )

        try:
            return self._build_store().as_retriever(
                search_type=search_type,
                search_kwargs=search_kwargs,
            )
        except IngestionError as exc:
            raise VectorRetrievalError("Vector retrieval is unavailable.") from exc

    def retrieve_for_user(
        self,
        *,
        user_id: int,
        query: str,
        k: int,
        search_type: str,
        score_threshold: float | None = None,
        fetch_k: int | None = None,
    ) -> list[Document]:
        retriever = self.as_retriever_for_user(
            user_id=user_id,
            k=k,
            search_type=search_type,
            score_threshold=score_threshold,
            fetch_k=fetch_k,
        )
        try:
            documents = retriever.invoke(query)
        except (self._chroma_error_type(), httpx.TransportError, OSError) as exc:
            raise VectorRetrievalError("Vector retrieval is unavailable.") from exc

        if not isinstance(documents, list) or any(
            isinstance(document.metadata.get("user_id"), bool)
            or not isinstance(document.metadata.get("user_id"), int)
            or document.metadata.get("user_id") != user_id
            for document in documents
        ):
            raise VectorRetrievalError("Vector retrieval is unavailable.")
        return documents

    @staticmethod
    def _validate_lookup_ids(lookup) -> list[str]:
        if not isinstance(lookup, dict):
            raise IngestionError("Failed to parse document content.")
        ids = lookup.get("ids")
        if (
            not isinstance(ids, list)
            or any(not isinstance(item, str) or not item for item in ids)
            or len(ids) != len(set(ids))
        ):
            raise IngestionError("Failed to parse document content.")
        return ids

    @staticmethod
    def _validate_incoming_id_ownership(
        lookup,
        *,
        user_id: int,
        document_id: str,
    ) -> None:
        if not isinstance(lookup, dict):
            raise IngestionError("Failed to parse document content.")
        ids = lookup.get("ids")
        metadatas = lookup.get("metadatas")
        if (
            not isinstance(ids, list)
            or not isinstance(metadatas, list)
            or len(ids) != len(metadatas)
        ):
            raise IngestionError("Failed to parse document content.")
        for metadata in metadatas:
            if (
                not isinstance(metadata, dict)
                or type(metadata.get("user_id")) is not int
                or metadata.get("user_id") != user_id
                or metadata.get("document_id") != document_id
            ):
                raise IngestionError("Failed to parse document content.")

    @staticmethod
    def _is_chroma_connection_error(exc: ValueError) -> bool:
        return str(exc).startswith("Could not connect to a Chroma server.")

    @staticmethod
    def _chroma_error_type():
        try:
            from chromadb.errors import ChromaError
        except ImportError as exc:
            raise VectorRetrievalError("Vector retrieval is unavailable.") from exc
        return ChromaError

    def _build_store(self):
        try:
            from chromadb.errors import ChromaError
        except ImportError as exc:
            raise IngestionError("Failed to parse document content.") from exc

        try:
            with _STORE_BUILD_LOCK:
                return _build_cached_store(
                    self.collection_name,
                    settings.CHROMA_HOST,
                    settings.CHROMA_PORT,
                    settings.EMBEDDING_MODEL_NAME,
                )
        except (ImportError, OSError, ChromaError, httpx.TransportError) as exc:
            raise IngestionError("Failed to parse document content.") from exc


def get_vector_store() -> DocumentVectorStore:
    return DocumentVectorStore()
