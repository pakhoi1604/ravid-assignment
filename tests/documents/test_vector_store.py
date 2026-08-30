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


def test_build_store_wires_chroma_and_embedding_settings(monkeypatch, settings):
    import chromadb
    import langchain_chroma
    import langchain_huggingface

    calls = []
    client = object()
    embeddings = object()
    store = object()

    settings.CHROMA_HOST = "chroma.internal"
    settings.CHROMA_PORT = 8765
    settings.EMBEDDING_MODEL_NAME = "sentence-transformers/test-model"

    def build_client(*, host, port):
        calls.append(("client", host, port))
        return client

    def build_embeddings(*, model_name):
        calls.append(("embeddings", model_name))
        return embeddings

    def build_store(*, client, collection_name, embedding_function):
        calls.append(("store", client, collection_name, embedding_function))
        return store

    monkeypatch.setattr(chromadb, "HttpClient", build_client)
    monkeypatch.setattr(langchain_huggingface, "HuggingFaceEmbeddings", build_embeddings)
    monkeypatch.setattr(langchain_chroma, "Chroma", build_store)

    result = DocumentVectorStore(collection_name="documents-test")._build_store()

    assert result is store
    assert calls == [
        ("client", "chroma.internal", 8765),
        ("embeddings", "sentence-transformers/test-model"),
        ("store", client, "documents-test", embeddings),
    ]
