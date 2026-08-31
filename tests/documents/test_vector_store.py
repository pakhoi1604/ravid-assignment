import pytest

from apps.documents.contracts import Chunk
from apps.documents.exceptions import IngestionError
from apps.documents.vector_store import DocumentVectorStore


def chunk(*, user_id=1, document_id="doc", index=0):
    return Chunk(
        text=f"chunk {index}",
        metadata={"user_id": user_id, "document_id": document_id, "chunk_index": index},
        id=f"document-{document_id}-chunk-{index}",
    )


def test_replace_document_chunks_resolves_all_old_ids_before_delete_and_add(monkeypatch):
    calls = []

    class Store:
        def get(self, *, include, where=None, ids=None):
            if ids is not None:
                calls.append(("get_ids", ids, include))
                return {
                    "ids": ["document-doc-chunk-0"],
                    "metadatas": [{"user_id": 1, "document_id": "doc"}],
                }
            calls.append(("get", where, include))
            return {"ids": ["document-doc-chunk-0", "document-doc-chunk-1", "stale-tail"]}

        def delete(self, *, ids):
            calls.append(("delete", ids))

        def add_texts(self, *, texts, metadatas, ids):
            calls.append(("add", texts, metadatas, ids))

    vector_store = DocumentVectorStore(collection_name="test")
    monkeypatch.setattr(vector_store, "_build_store", lambda: Store())
    chunks = [chunk()]

    vector_store.replace_document_chunks(user_id=1, document_id="doc", chunks=chunks)

    assert calls == [
        (
            "get",
            {"$and": [{"user_id": {"$eq": 1}}, {"document_id": {"$eq": "doc"}}]},
            [],
        ),
        ("get_ids", ["document-doc-chunk-0"], ["metadatas"]),
        ("delete", ["document-doc-chunk-0", "document-doc-chunk-1", "stale-tail"]),
        (
            "add",
            ["chunk 0"],
            [{"user_id": 1, "document_id": "doc", "chunk_index": 0}],
            ["document-doc-chunk-0"],
        ),
    ]


def test_replace_document_chunks_requires_chunks(monkeypatch):
    vector_store = DocumentVectorStore(collection_name="test")

    with pytest.raises(IngestionError):
        vector_store.replace_document_chunks(user_id=1, document_id="doc", chunks=[])


@pytest.mark.parametrize(
    "chunks",
    [
        [chunk(user_id=2)],
        [chunk(user_id=1.0)],
        [chunk(user_id="1")],
        [chunk(document_id="other")],
        [chunk(user_id=True)],
    ],
)
def test_replace_document_chunks_rejects_untrusted_metadata(monkeypatch, chunks):
    vector_store = DocumentVectorStore(collection_name="test")
    monkeypatch.setattr(vector_store, "_build_store", lambda: pytest.fail("must not build store"))

    with pytest.raises(IngestionError):
        vector_store.replace_document_chunks(user_id=1, document_id="doc", chunks=chunks)


def test_replace_document_chunks_rejects_chunk_id_that_disagrees_with_metadata(monkeypatch):
    invalid = Chunk(
        text="chunk",
        metadata={"user_id": 1, "document_id": "doc", "chunk_index": 0},
        id="another-owner-id",
    )
    vector_store = DocumentVectorStore(collection_name="test")
    monkeypatch.setattr(vector_store, "_build_store", lambda: pytest.fail("must not build store"))

    with pytest.raises(IngestionError):
        vector_store.replace_document_chunks(user_id=1, document_id="doc", chunks=[invalid])


def test_replace_document_chunks_adds_without_delete_when_document_is_new(monkeypatch):
    calls = []

    class Store:
        def get(self, **kwargs):
            if "ids" in kwargs:
                return {"ids": [], "metadatas": []}
            return {"ids": []}

        def delete(self, **kwargs):
            pytest.fail("delete must not run")

        def add_texts(self, **kwargs):
            calls.append(kwargs)

    vector_store = DocumentVectorStore(collection_name="test")
    monkeypatch.setattr(vector_store, "_build_store", lambda: Store())

    vector_store.replace_document_chunks(user_id=1, document_id="doc", chunks=[chunk()])

    assert len(calls) == 1


@pytest.mark.parametrize(
    "lookup_result",
    [{}, {"ids": None}, {"ids": [1]}, {"ids": ["same", "same"]}],
)
def test_replace_document_chunks_rejects_malformed_lookup(monkeypatch, lookup_result):
    class Store:
        def get(self, **kwargs):
            return lookup_result

        def delete(self, **kwargs):
            pytest.fail("delete must not run")

        def add_texts(self, **kwargs):
            pytest.fail("add must not run")

    vector_store = DocumentVectorStore(collection_name="test")
    monkeypatch.setattr(vector_store, "_build_store", lambda: Store())

    with pytest.raises(IngestionError):
        vector_store.replace_document_chunks(user_id=1, document_id="doc", chunks=[chunk()])


def test_replace_document_chunks_does_not_add_after_delete_failure(monkeypatch):
    class ExpectedBackendError(Exception):
        pass

    class Store:
        def get(self, **kwargs):
            if "ids" in kwargs:
                return {
                    "ids": ["document-doc-chunk-0"],
                    "metadatas": [{"user_id": 1, "document_id": "doc"}],
                }
            return {"ids": ["old"]}

        def delete(self, **kwargs):
            raise ExpectedBackendError("unavailable")

        def add_texts(self, **kwargs):
            pytest.fail("add must not run")

    vector_store = DocumentVectorStore(collection_name="test")
    monkeypatch.setattr(vector_store, "_build_store", lambda: Store())
    monkeypatch.setattr(vector_store, "_chroma_error_type", lambda: ExpectedBackendError)

    with pytest.raises(IngestionError):
        vector_store.replace_document_chunks(user_id=1, document_id="doc", chunks=[chunk()])


@pytest.mark.parametrize("failing_operation", ["get", "add"])
def test_replace_document_chunks_normalizes_expected_store_failures(monkeypatch, failing_operation):
    class ExpectedBackendError(Exception):
        pass

    class Store:
        def get(self, **kwargs):
            if failing_operation == "get":
                raise ExpectedBackendError("unavailable")
            if "ids" in kwargs:
                return {"ids": [], "metadatas": []}
            return {"ids": []}

        def add_texts(self, **kwargs):
            raise ExpectedBackendError("unavailable")

    vector_store = DocumentVectorStore(collection_name="test")
    monkeypatch.setattr(vector_store, "_build_store", lambda: Store())
    monkeypatch.setattr(vector_store, "_chroma_error_type", lambda: ExpectedBackendError)

    with pytest.raises(IngestionError):
        vector_store.replace_document_chunks(user_id=1, document_id="doc", chunks=[chunk()])


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


def test_real_chroma_replacement_removes_stale_tail_without_crossing_owner():
    import uuid

    import chromadb
    from langchain_chroma import Chroma

    class Embeddings:
        def embed_documents(self, texts):
            return [[float(index), 1.0] for index, _text in enumerate(texts, start=1)]

        def embed_query(self, text):
            return [1.0, 1.0]

    collection_name = f"ravid-replace-{uuid.uuid4().hex}"
    store = Chroma(
        client=chromadb.Client(),
        collection_name=collection_name,
        embedding_function=Embeddings(),
    )
    store.add_texts(
        texts=["old 0", "old 1", "other owner"],
        metadatas=[
            {"user_id": 1, "document_id": "doc"},
            {"user_id": 1, "document_id": "doc"},
            {"user_id": 2, "document_id": "doc"},
        ],
        ids=["owner-1-old-0", "owner-1-old-1", "owner-2-old-0"],
    )
    vector_store = DocumentVectorStore(collection_name=collection_name)
    vector_store._build_store = lambda: store

    try:
        vector_store.replace_document_chunks(
            user_id=1,
            document_id="doc",
            chunks=[chunk()],
        )
        result = store.get(where={"document_id": "doc"}, include=["metadatas"])
    finally:
        store.delete_collection()

    assert sorted(result["ids"]) == ["document-doc-chunk-0", "owner-2-old-0"]


def test_real_chroma_replacement_rejects_foreign_owner_id_collision():
    import uuid

    import chromadb
    from langchain_chroma import Chroma

    class Embeddings:
        def embed_documents(self, texts):
            return [[1.0, 1.0] for _text in texts]

        def embed_query(self, text):
            return [1.0, 1.0]

    collection_name = f"ravid-collision-{uuid.uuid4().hex}"
    store = Chroma(
        client=chromadb.Client(),
        collection_name=collection_name,
        embedding_function=Embeddings(),
    )
    store.add_texts(
        texts=["foreign owner"],
        metadatas=[{"user_id": 2, "document_id": "doc", "chunk_index": 0}],
        ids=["document-doc-chunk-0"],
    )
    vector_store = DocumentVectorStore(collection_name=collection_name)
    vector_store._build_store = lambda: store

    try:
        with pytest.raises(IngestionError):
            vector_store.replace_document_chunks(
                user_id=1,
                document_id="doc",
                chunks=[chunk()],
            )
        result = store.get(ids=["document-doc-chunk-0"], include=["metadatas"])
    finally:
        store.delete_collection()

    assert result["metadatas"] == [{"user_id": 2, "document_id": "doc", "chunk_index": 0}]
