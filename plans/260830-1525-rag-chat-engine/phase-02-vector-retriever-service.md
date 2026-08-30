---
phase: 2
title: "Vector Retriever Service"
status: completed
priority: P1
dependencies: [1]
effort: "M"
---

# Phase 2: Vector Retriever Service

## Context Links

- Existing adapter: `apps/documents/vector_store.py`
- Part 1 metadata source: `apps/documents/ingestion.py`
- Completed dependency refresh: `../260830-1740-langchain-dependency-refresh/plan.md`
- Completed CPU prerequisite: `../260830-1830-cpu-only-torch-runtime/plan.md`

## Overview

Extend the Part 1 adapter with an owner-scoped native LangChain retriever. Declare the core package
directly because this phase imports `BaseRetriever`; preserve the completed CPU-only Torch
resolution when extending the shared lockfile.

## Requirements

- Retrieve top-k chunks from the existing collection with a mandatory authenticated-user filter.
- Return native LangChain `Document` values; an empty result is valid.
- Reject invalid `user_id` and `k` values before constructing the retriever.
- Keep unit tests offline with a fake vector store; add one real Chroma owner-isolation smoke later.

## Architecture

Extend `DocumentVectorStore`:

```python
def as_retriever_for_user(self, *, user_id: int, k: int) -> BaseRetriever:
    return self._build_store().as_retriever(
        search_kwargs={"k": k, "filter": {"user_id": user_id}},
    )
```

`user_id` must be an integer but not `bool`; `k` must be positive. The caller receives no generic
filter parameter. Wrap only documented Chroma/network construction and invocation failures as
`VectorRetrievalError`; programming errors must propagate to fail tests loudly.

## Related Code Files

- Modify: `apps/documents/vector_store.py` - owner-scoped retriever and retrieval exception.
- Create: `tests/documents/test_vector_retrieval.py` - exact filter and failure tests.
- Create: `tests/documents/test_vector_retrieval_chroma.py` - two-user real-Chroma filter test.
- Modify: `config/settings/base.py` - `RAG_RETRIEVAL_K`, `RAG_MAX_CONTEXT_CHARS`.
- Modify: environment example template and `compose.yaml` - expose/forward retrieval settings.
- Modify: `pyproject.toml` and `uv.lock` - declare `langchain-core>=1.6,<2` directly while preserving
  the CPU-only Torch source and resolution.

## Implementation Steps

1. Confirm both dependency prerequisites resolve as completed and inspect the current CPU-only Torch
   diff before changing dependency files; never regenerate it back to CUDA wheels.
2. Add only `langchain-core>=1.6,<2` to the existing vector-ingestion optional group, then refresh
   the lock without changing the resolved modular family or CPU-only Torch source unexpectedly.
3. Add positive integer settings with defaults `RAG_RETRIEVAL_K=4` and
   `RAG_MAX_CONTEXT_CHARS=6000`; forward them to the web service.
4. Add `VectorRetrievalError`, the typed `as_retriever_for_user` method, and an adapter invocation
   method that translates only documented Chroma/network failures to `VectorRetrievalError`.
   Translate Chroma client/collection construction, transport, and embedding cache/model-load
   operational failures while allowing programming exceptions such as `TypeError` to propagate.
5. Validate `user_id` (`int`, excluding `bool`) and positive `k`.
6. Call `store.as_retriever(search_kwargs={"k": k, "filter": {"user_id": user_id}})` exactly.
7. Unit-test the exact constructor arguments, return identity, invalid inputs, constructor errors,
   invocation error translation, programming-error propagation, and empty invocation results.
8. Protect existing write-path tests and verify Part 1 metadata remains unchanged.
9. Add a Docker-backed Chroma integration using a unique collection and deterministic fake
   embeddings: index distinct facts for two user IDs, invoke each owner-scoped retriever, and assert
   neither result set contains the other owner's chunks. Clean up only the unique test collection.
10. Cache the constructed Chroma store and embedding model by collection/host/port/model in a
    process-local cache capped at eight entries. Serialize cold construction so concurrent requests
    cannot duplicate heavyweight model loads; owner filters remain per-retriever request.

## Tests Before

- Add failing `tests/documents/test_vector_retrieval.py` before the adapter method.
- Add a dependency-contract assertion before declaring the direct core package.

## Tests After

- `uv run pytest tests/documents/test_vector_store.py tests/documents/test_vector_retrieval.py`
- `UV_CACHE_DIR=/tmp/ravid-rag-uv-cache uv lock --check`
- `uv run python manage.py check --settings=config.settings.test`
- `docker compose --profile test up -d chroma`
- `docker compose --profile test run --rm test pytest --ds=config.settings.production tests/documents/test_vector_retrieval_chroma.py -q`

## Success Criteria

- [x] `langchain-core` is direct; umbrella `langchain` remains absent.
- [x] Factory returns a native retriever configured with integer authenticated `user_id` and top-k.
- [x] No call path can construct this RAG retriever without the owner filter.
- [x] Empty results remain an empty list of documents.
- [x] Construction errors become `VectorRetrievalError`; existing Part 1 writes still pass.
- [x] A real Chroma two-user test proves backend metadata filtering, independent of LLM output.
- [x] Repeated retrievals reuse one process-local embedding/store resource, and expected failures at
      every construction stage map to `VectorRetrievalError`.

## Risk Assessment

- Chroma filter typing is strict. Part 1 stores integer `user_id`; tests assert the same type.
- Shared dependency files contain the completed CPU plan's work. Preserve its source pin and lock
  result when adding RAG packages.
- Adapter APIs can drift. Keep the integration in one method and protect the exact locked API.

## Security Considerations

- Derive user identity only from `request.user` downstream.
- Never accept collection name, owner ID, or metadata filter from the chat payload.
