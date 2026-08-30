import httpx
import pytest

from apps.documents.services import IngestionError
from apps.documents.vector_store import DocumentVectorStore, VectorRetrievalError


def test_owner_scoped_retriever_uses_exact_integer_filter(monkeypatch):
    calls = []
    retriever = object()

    class Store:
        def as_retriever(self, **kwargs):
            calls.append(kwargs)
            return retriever

    vector_store = DocumentVectorStore(collection_name="documents-test")
    monkeypatch.setattr(vector_store, "_build_store", lambda: Store())

    result = vector_store.as_retriever_for_user(user_id=42, k=4)

    assert result is retriever
    assert calls == [{"search_kwargs": {"k": 4, "filter": {"user_id": 42}}}]


@pytest.mark.parametrize("user_id", [True, "42", None])
def test_owner_scoped_retriever_rejects_invalid_user_id(user_id):
    with pytest.raises(ValueError, match="user_id"):
        DocumentVectorStore().as_retriever_for_user(user_id=user_id, k=4)


@pytest.mark.parametrize("k", [True, 0, -1, 1.5])
def test_owner_scoped_retriever_rejects_invalid_k(k):
    with pytest.raises(ValueError, match="k"):
        DocumentVectorStore().as_retriever_for_user(user_id=1, k=k)


def test_owner_scoped_retriever_normalizes_store_construction_failure(monkeypatch):
    vector_store = DocumentVectorStore()

    def fail():
        raise IngestionError("Failed to parse document content.")

    monkeypatch.setattr(vector_store, "_build_store", fail)

    with pytest.raises(VectorRetrievalError, match="unavailable"):
        vector_store.as_retriever_for_user(user_id=1, k=4)


def test_owner_scoped_retriever_normalizes_locked_chroma_connection_failure(monkeypatch):
    import chromadb

    def fail_http_client(**kwargs):
        raise ValueError("Could not connect to a Chroma server. Are you sure it is running?")

    monkeypatch.setattr(chromadb, "HttpClient", fail_http_client)

    with pytest.raises(VectorRetrievalError, match="unavailable"):
        DocumentVectorStore().as_retriever_for_user(user_id=1, k=4)


def test_owner_scoped_retriever_normalizes_collection_construction_failure(monkeypatch):
    import chromadb
    import langchain_chroma
    import langchain_huggingface

    monkeypatch.setattr(chromadb, "HttpClient", lambda **kwargs: object())
    monkeypatch.setattr(
        langchain_huggingface,
        "HuggingFaceEmbeddings",
        lambda **kwargs: object(),
    )

    def fail_chroma(**kwargs):
        raise httpx.ConnectError("collection unavailable")

    monkeypatch.setattr(langchain_chroma, "Chroma", fail_chroma)

    with pytest.raises(VectorRetrievalError, match="unavailable"):
        DocumentVectorStore(
            collection_name="collection-construction-failure"
        ).as_retriever_for_user(user_id=1, k=4)


def test_owner_scoped_retriever_normalizes_embedding_cache_failure(monkeypatch):
    import chromadb
    import langchain_huggingface

    monkeypatch.setattr(chromadb, "HttpClient", lambda **kwargs: object())

    def fail_embeddings(**kwargs):
        raise OSError("embedding cache unavailable")

    monkeypatch.setattr(langchain_huggingface, "HuggingFaceEmbeddings", fail_embeddings)

    with pytest.raises(VectorRetrievalError, match="unavailable"):
        DocumentVectorStore(collection_name="embedding-cache-failure").as_retriever_for_user(
            user_id=1,
            k=4,
        )


def test_store_construction_does_not_hide_unrelated_value_errors(monkeypatch):
    import chromadb
    import langchain_huggingface

    monkeypatch.setattr(chromadb, "HttpClient", lambda **kwargs: object())

    def fail_embeddings(**kwargs):
        raise ValueError("implementation defect")

    monkeypatch.setattr(langchain_huggingface, "HuggingFaceEmbeddings", fail_embeddings)

    with pytest.raises(ValueError, match="implementation defect"):
        DocumentVectorStore(collection_name="programming-value-error").as_retriever_for_user(
            user_id=1,
            k=4,
        )


def test_vector_store_resource_is_reused_within_process(monkeypatch):
    import chromadb
    import langchain_chroma
    import langchain_huggingface

    calls = {"client": 0, "embeddings": 0, "store": 0}

    def build_client(**kwargs):
        calls["client"] += 1
        return object()

    def build_embeddings(**kwargs):
        calls["embeddings"] += 1
        return object()

    class Store:
        def as_retriever(self, **kwargs):
            return object()

    def build_store(**kwargs):
        calls["store"] += 1
        return Store()

    monkeypatch.setattr(chromadb, "HttpClient", build_client)
    monkeypatch.setattr(langchain_huggingface, "HuggingFaceEmbeddings", build_embeddings)
    monkeypatch.setattr(langchain_chroma, "Chroma", build_store)

    first = DocumentVectorStore(collection_name="cached-resource-test")
    second = DocumentVectorStore(collection_name="cached-resource-test")
    first.as_retriever_for_user(user_id=1, k=4)
    second.as_retriever_for_user(user_id=2, k=4)

    assert calls == {"client": 1, "embeddings": 1, "store": 1}


def test_retrieve_for_user_invokes_native_retriever(monkeypatch):
    documents = [object()]

    class Retriever:
        def invoke(self, query):
            assert query == "What is the policy?"
            return documents

    vector_store = DocumentVectorStore()
    monkeypatch.setattr(
        vector_store,
        "as_retriever_for_user",
        lambda **kwargs: Retriever(),
    )

    assert vector_store.retrieve_for_user(user_id=1, query="What is the policy?", k=4) == documents


def test_retrieve_for_user_normalizes_only_chroma_failures(monkeypatch):
    class ExpectedBackendError(Exception):
        pass

    class Retriever:
        def invoke(self, query):
            raise ExpectedBackendError

    vector_store = DocumentVectorStore()
    monkeypatch.setattr(
        vector_store,
        "as_retriever_for_user",
        lambda **kwargs: Retriever(),
    )
    monkeypatch.setattr(vector_store, "_chroma_error_type", lambda: ExpectedBackendError)

    with pytest.raises(VectorRetrievalError, match="unavailable"):
        vector_store.retrieve_for_user(user_id=1, query="query", k=4)


def test_retrieve_for_user_normalizes_http_transport_failures(monkeypatch):
    class Retriever:
        def invoke(self, query):
            raise httpx.ConnectError("connection failed")

    vector_store = DocumentVectorStore()
    monkeypatch.setattr(
        vector_store,
        "as_retriever_for_user",
        lambda **kwargs: Retriever(),
    )

    with pytest.raises(VectorRetrievalError, match="unavailable"):
        vector_store.retrieve_for_user(user_id=1, query="query", k=4)


def test_retrieve_for_user_does_not_hide_programming_errors(monkeypatch):
    class Retriever:
        def invoke(self, query):
            raise TypeError("implementation defect")

    vector_store = DocumentVectorStore()
    monkeypatch.setattr(
        vector_store,
        "as_retriever_for_user",
        lambda **kwargs: Retriever(),
    )

    with pytest.raises(TypeError, match="implementation defect"):
        vector_store.retrieve_for_user(user_id=1, query="query", k=4)
