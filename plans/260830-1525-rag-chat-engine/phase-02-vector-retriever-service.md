---
phase: 2
title: "Vector Retriever Service"
status: pending
priority: P1
dependencies: [1]
effort: "M"
---

# Phase 2: Vector Retriever Service

## Overview

Extend the Part 1 vector store adapter with owner-scoped retrieval primitives that the RAG engine
can use without knowing Chroma internals.

## Requirements

- Functional: retrieve top matching chunks from the existing Chroma collection.
- Functional: every retrieval must filter by authenticated user's `user_id` metadata.
- Functional: empty retrieval returns an empty context list, not a server error.
- Non-functional: tests must use fakes/mocks and never require a running Chroma server.
- Non-functional: retrieval result shape must preserve source metadata needed for prompts and future
  HyDE debugging.

## Architecture

Add a small retrieval result type next to the existing vector adapter:

```python
@dataclass(frozen=True)
class RetrievedChunk:
    text: str
    metadata: dict[str, str | int | float]
    score: float | None = None
```

Extend `DocumentVectorStore` with:

```python
def similarity_search_for_user(
    self,
    *,
    user_id: int,
    query: str,
    k: int,
) -> list[RetrievedChunk]:
    raise NotImplementedError
```

Implementation uses the store's relevance-score similarity search API when available, with
`filter={"user_id": user_id}`. If the Chroma/LangChain adapter returns plain documents, normalize to
the same `RetrievedChunk` shape. The RAG layer never passes raw request data directly to Chroma.

## Related Code Files

- Modify: `apps/documents/vector_store.py` - add `RetrievedChunk` and owner-scoped search.
- Create: `tests/documents/test_vector_retrieval.py` - search call shape and normalization tests.
- Modify: `config/settings/base.py` - add `RAG_RETRIEVAL_K` and `RAG_MAX_CONTEXT_CHARS`.
- Modify: environment example template - expose retrieval tunables.

## Implementation Steps

1. Add `RAG_RETRIEVAL_K = env_int("RAG_RETRIEVAL_K", 4)` and
   `RAG_MAX_CONTEXT_CHARS = env_int("RAG_MAX_CONTEXT_CHARS", 6000)`.
2. Add `RetrievedChunk` dataclass in `apps/documents/vector_store.py`.
3. Implement `similarity_search_for_user` with early validation:
   - stripped query must be non-empty;
   - `k` must be positive;
   - `user_id` must be an integer.
4. Call Chroma with a metadata filter:

   ```python
   results = store.similarity_search_with_relevance_scores(
       query,
       k=k,
       filter={"user_id": user_id},
   )
   ```

5. Normalize each result into `RetrievedChunk(text=doc.page_content, metadata=doc.metadata,
   score=score)`.
6. Catch Chroma/provider exceptions and raise `VectorRetrievalError` from
   `apps.documents.vector_store` rather than leaking adapter stack traces.
7. Add tests that fake `_build_store()` and assert the exact `filter={"user_id": user.id}` call.
8. Add an owner-isolation test where fake store returns only chunks matching the filter, proving the
   service never queries without the filter.

## Tests Before

- Add failing tests in `tests/documents/test_vector_retrieval.py` for `similarity_search_for_user`.
- Expected initial failure: method and `RetrievedChunk` do not exist.

## Tests After

- `uv run pytest tests/documents/test_vector_store.py tests/documents/test_vector_retrieval.py`
- `uv run python manage.py check --settings=config.settings.test`

## Success Criteria

- [ ] Retrieval calls Chroma with authenticated-user metadata filter.
- [ ] Retrieval returns normalized chunk text, metadata, and optional score.
- [ ] Empty result sets are represented as `[]`.
- [ ] Chroma errors are converted to `VectorRetrievalError`.
- [ ] Existing Part 1 vector-store write tests still pass.

## Risk Assessment

- Risk: Chroma metadata filter typing can be sensitive to numeric vs string values. Mitigation:
  Part 1 stores `user_id` as integer; retrieval tests assert integer filter and integration smoke can
  validate Docker path.
- Risk: LangChain adapter method names may vary by version. Mitigation: dependency is locked;
  verify against installed package and keep adapter isolated to one file.
- Risk: retrieval scores differ across stores. Mitigation: do not make API behavior depend on score
  thresholds in Part 2.

## Security Considerations

- Owner filter is mandatory and belongs inside the adapter method signature.
- Do not accept user-supplied `user_id`, collection name, or metadata filter from the API request.
