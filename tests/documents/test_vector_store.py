import pytest

from apps.documents.services import Chunk, IngestionError
from apps.documents.vector_store import DocumentVectorStore


def test_replace_document_chunks_deletes_then_adds(monkeypatch):
    calls = []

    class Store:
        def delete(self, *, ids):
            calls.append(("delete", ids))

        def add_texts(self, *, texts, metadatas, ids):
            calls.append(("add", texts, metadatas, ids))

    vector_store = DocumentVectorStore(collection_name="test")
    monkeypatch.setattr(vector_store, "_build_store", lambda: Store())
    chunks = [
        Chunk(
            text="hello",
            metadata={"user_id": 1, "document_id": "doc", "chunk_index": 0},
            id="document-doc-chunk-0",
        )
    ]

    vector_store.replace_document_chunks("doc", chunks)

    assert calls == [
        ("delete", ["document-doc-chunk-0"]),
        (
            "add",
            ["hello"],
            [{"user_id": 1, "document_id": "doc", "chunk_index": 0}],
            ["document-doc-chunk-0"],
        ),
    ]


def test_replace_document_chunks_requires_chunks(monkeypatch):
    vector_store = DocumentVectorStore(collection_name="test")

    with pytest.raises(IngestionError):
        vector_store.replace_document_chunks("doc", [])
