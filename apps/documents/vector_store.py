from collections.abc import Sequence
from functools import lru_cache
from threading import Lock

import httpx
from django.conf import settings
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

from apps.documents.services import Chunk, IngestionError


class VectorRetrievalError(Exception):
    """Raised for expected Chroma failures during owner-scoped retrieval."""


_STORE_BUILD_LOCK = Lock()


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

    def replace_document_chunks(self, document_id: str, chunks: Sequence[Chunk]) -> None:
        if not chunks:
            raise IngestionError("Failed to parse document content.")

        store = self._build_store()
        ids = [chunk.id for chunk in chunks]

        try:
            store.delete(ids=ids)
        except Exception:
            # Missing ids are acceptable on first ingestion. Add still must succeed.
            pass

        try:
            store.add_texts(
                texts=[chunk.text for chunk in chunks],
                metadatas=[chunk.metadata for chunk in chunks],
                ids=ids,
            )
        except Exception as exc:
            raise IngestionError("Failed to parse document content.") from exc

    def as_retriever_for_user(self, *, user_id: int, k: int) -> BaseRetriever:
        if isinstance(user_id, bool) or not isinstance(user_id, int):
            raise ValueError("user_id must be an integer.")
        if isinstance(k, bool) or not isinstance(k, int) or k <= 0:
            raise ValueError("k must be a positive integer.")

        try:
            return self._build_store().as_retriever(
                search_kwargs={"k": k, "filter": {"user_id": user_id}}
            )
        except IngestionError as exc:
            raise VectorRetrievalError("Vector retrieval is unavailable.") from exc

    def retrieve_for_user(self, *, user_id: int, query: str, k: int) -> list[Document]:
        retriever = self.as_retriever_for_user(user_id=user_id, k=k)
        try:
            return retriever.invoke(query)
        except (self._chroma_error_type(), httpx.TransportError) as exc:
            raise VectorRetrievalError("Vector retrieval is unavailable.") from exc

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
