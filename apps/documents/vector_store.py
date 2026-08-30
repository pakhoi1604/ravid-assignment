from collections.abc import Sequence

from django.conf import settings

from apps.documents.services import Chunk, IngestionError


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

    def _build_store(self):
        try:
            import chromadb
            from langchain_chroma import Chroma
            from langchain_huggingface import HuggingFaceEmbeddings
        except ImportError as exc:
            raise IngestionError("Failed to parse document content.") from exc

        client = chromadb.HttpClient(host=settings.CHROMA_HOST, port=settings.CHROMA_PORT)
        embeddings = HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL_NAME)
        return Chroma(
            client=client,
            collection_name=self.collection_name,
            embedding_function=embeddings,
        )


def get_vector_store() -> DocumentVectorStore:
    return DocumentVectorStore()
