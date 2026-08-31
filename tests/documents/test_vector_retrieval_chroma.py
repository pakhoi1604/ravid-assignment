import uuid

import pytest
from django.db import connection

from apps.documents.contracts import Chunk
from apps.documents.vector_store import DocumentVectorStore


class DeterministicEmbeddings:
    def embed_documents(self, texts):
        return [self._embed(text) for text in texts]

    def embed_query(self, text):
        return self._embed(text)

    @staticmethod
    def _embed(text):
        lowered = text.lower()
        return [
            1.0 if "amber-orchid" in lowered else 0.0,
            1.0 if "silver-cactus" in lowered else 0.0,
            0.1,
        ]


@pytest.mark.django_db
def test_chroma_retriever_keeps_two_users_isolated(settings):
    if connection.vendor != "postgresql":
        pytest.skip("Compose Chroma integration runs with production settings.")

    import chromadb
    from langchain_chroma import Chroma

    collection_name = f"ravid-owner-{uuid.uuid4().hex}"
    client = chromadb.HttpClient(host=settings.CHROMA_HOST, port=settings.CHROMA_PORT)
    store = Chroma(
        client=client,
        collection_name=collection_name,
        embedding_function=DeterministicEmbeddings(),
    )
    store.add_texts(
        texts=["User one fact: amber-orchid.", "User two fact: silver-cactus."],
        metadatas=[{"user_id": 101}, {"user_id": 202}],
        ids=["owner-101", "owner-202"],
    )

    vector_store = DocumentVectorStore(collection_name=collection_name)
    vector_store._build_store = lambda: store
    try:
        first = vector_store.retrieve_for_user(
            user_id=101, query="amber-orchid", k=4, search_type="similarity"
        )
        second = vector_store.retrieve_for_user(
            user_id=202, query="silver-cactus", k=4, search_type="similarity"
        )
    finally:
        store.delete_collection()

    assert [document.metadata["user_id"] for document in first] == [101]
    assert [document.metadata["user_id"] for document in second] == [202]


@pytest.mark.django_db
def test_chroma_replacement_shrinks_only_the_trusted_owner_document(settings):
    if connection.vendor != "postgresql":
        pytest.skip("Compose Chroma integration runs with production settings.")

    import chromadb
    from langchain_chroma import Chroma

    collection_name = f"ravid-replace-{uuid.uuid4().hex}"
    client = chromadb.HttpClient(host=settings.CHROMA_HOST, port=settings.CHROMA_PORT)
    store = Chroma(
        client=client,
        collection_name=collection_name,
        embedding_function=DeterministicEmbeddings(),
    )
    shared_document_id = "shared-document"
    store.add_texts(
        texts=["old 0", "old 1", "other owner"],
        metadatas=[
            {"user_id": 101, "document_id": shared_document_id, "chunk_index": 0},
            {"user_id": 101, "document_id": shared_document_id, "chunk_index": 1},
            {"user_id": 202, "document_id": shared_document_id, "chunk_index": 0},
        ],
        ids=["owner-101-old-0", "owner-101-old-1", "owner-202-old-0"],
    )
    vector_store = DocumentVectorStore(collection_name=collection_name)
    vector_store._build_store = lambda: store

    try:
        vector_store.replace_document_chunks(
            user_id=101,
            document_id=shared_document_id,
            chunks=[
                Chunk(
                    text="replacement",
                    metadata={
                        "user_id": 101,
                        "document_id": shared_document_id,
                        "chunk_index": 0,
                    },
                    id=f"document-{shared_document_id}-chunk-0",
                )
            ],
        )
        result = store.get(where={"document_id": shared_document_id}, include=["metadatas"])
    finally:
        store.delete_collection()

    assert sorted(result["ids"]) == [
        f"document-{shared_document_id}-chunk-0",
        "owner-202-old-0",
    ]
