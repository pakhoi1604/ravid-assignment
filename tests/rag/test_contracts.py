from dataclasses import FrozenInstanceError

import pytest

from apps.rag.contracts import RagAnswer, RetrievalMetadata, RetrievalPolicy


def test_rag_result_contracts_are_frozen_and_use_tuple_chunks():
    metadata = RetrievalMetadata(
        mode="standard",
        hypothetical_passage=None,
        fallback_reason=None,
        retrieved_chunks_count=1,
        retrieved_chunks=("chunk",),
    )
    answer = RagAnswer(
        answer="answer",
        estimated_tokens=10,
        actual_tokens=8,
        retrieval_metadata=metadata,
    )

    with pytest.raises(FrozenInstanceError):
        answer.answer = "changed"

    assert answer.retrieval_metadata.retrieved_chunks == ("chunk",)


def test_retrieval_policy_is_an_immutable_snapshot():
    policy = RetrievalPolicy(
        k=4,
        search_type="similarity",
        score_threshold=0.2,
        fetch_k=20,
    )

    with pytest.raises(FrozenInstanceError):
        policy.k = 5
