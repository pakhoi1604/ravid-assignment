from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievalPolicy:
    k: int
    search_type: str
    score_threshold: float | None
    fetch_k: int | None


@dataclass(frozen=True)
class RetrievalMetadata:
    mode: str
    hypothetical_passage: str | None
    fallback_reason: str | None
    retrieved_chunks_count: int
    retrieved_chunks: tuple[str, ...]


@dataclass(frozen=True)
class RagAnswer:
    answer: str
    estimated_tokens: int
    actual_tokens: int
    retrieval_metadata: RetrievalMetadata
