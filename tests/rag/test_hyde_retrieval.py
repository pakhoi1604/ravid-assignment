import uuid

import chromadb
from langchain_chroma import Chroma

from apps.documents.vector_store import DocumentVectorStore


class ControlledEmbeddings:
    def embed_documents(self, texts):
        return [self._embed(text) for text in texts]

    def embed_query(self, text):
        return self._embed(text)

    @staticmethod
    def _embed(text):
        lowered = text.lower()
        if "cancel" in lowered or "fourteen days" in lowered:
            return [1.0, 0.0]
        return [0.0, 1.0]


def test_controlled_hyde_text_changes_real_similarity_retrieval(settings):
    settings.RAG_RETRIEVAL_SEARCH_TYPE = "similarity"
    collection_name = f"ravid-hyde-eval-{uuid.uuid4().hex}"
    store = Chroma(
        client=chromadb.Client(),
        collection_name=collection_name,
        embedding_function=ControlledEmbeddings(),
    )
    store.add_texts(
        texts=[
            "Employees may cancel an enrollment within fourteen days.",
            "The employee handbook describes general workplace benefits.",
            "Another owner's cancellation terms are confidential.",
        ],
        metadatas=[
            {"user_id": 101, "label": "target"},
            {"user_id": 101, "label": "baseline"},
            {"user_id": 202, "label": "other-owner"},
        ],
        ids=["owner-101-target", "owner-101-baseline", "owner-202-target"],
    )

    vector_store = DocumentVectorStore(collection_name=collection_name)
    vector_store._build_store = lambda: store
    try:
        baseline = vector_store.retrieve_for_user(
            user_id=101,
            query="What does the policy say?",
            k=1,
            search_type="similarity",
        )
        hyde = vector_store.retrieve_for_user(
            user_id=101,
            query="The policy permits cancellation within fourteen days.",
            k=1,
            search_type="similarity",
        )
    finally:
        store.delete_collection()

    assert [item.metadata["label"] for item in baseline] == ["baseline"]
    assert [item.metadata["label"] for item in hyde] == ["target"]
    assert all(item.metadata["user_id"] == 101 for item in baseline + hyde)
