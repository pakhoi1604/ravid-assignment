---
phase: 2
title: "Correct Vector Store Boundaries and Replacement"
status: completed
priority: P1
dependencies: [1]
---

# Phase 2: Correct Vector Store Boundaries and Replacement

## Overview

Fix the proven stale-tail defect when re-ingestion shrinks, make vector failure mappings explicit,
and make RAG pass retrieval policy explicitly. Keep native
owner filtering and all public failure mappings unchanged.

## Requirements

- Functional: replacement removes all prior vectors for the trusted `user_id` + `document_id`
  boundary before adding the new set; incoming chunk metadata must match both trusted parameters;
  standard and HyDE retrieval remain owner-scoped; RAG passes `k`, search type, threshold, and MMR
  fetch count explicitly.
- Non-functional: no broad exception swallowing; supported-value validation stays in `documents`;
  expected write/read failures translate to ingestion/retrieval errors respectively.

## Architecture

```text
RagService --retrieval policy values--> DocumentVectorStore
                                        | validate supported values
                                        | force filter {user_id: owner}
ingestion -> replace by owner+document -+ validate writes; translate -> IngestionError
retrieval ------------------------------+ translate store failure -> VectorRetrievalError
```

Use public `Chroma.get(where=compound_filter, include=[])` to resolve all old IDs, then public
`Chroma.delete(ids=...)` before adding replacement chunks. Treat malformed/partial lookup, lookup
failure, and delete failure as required-write failures; add must not run. Do not trust caller-supplied
filters or metadata: `DocumentVectorStore` constructs the owner/document filter and verifies every
incoming and returned document has matching integer `user_id` and `document_id` metadata.
The minimum delete-then-add fix is intentionally not atomic; versioned indexes are deferred.

## Related Code Files

| Action | File | Purpose |
| --- | --- | --- |
| Modify | `apps/documents/exceptions.py` | Own `IngestionError` and move `VectorRetrievalError` to a domain import path. |
| Modify | `apps/documents/vector_store.py` | Replace by document metadata; narrow failures; explicit retrieval options. |
| Modify | `apps/rag/services.py` | Pass all configured retrieval policy values explicitly. |
| Modify | `tests/documents/test_vector_store.py` | Add shrinking re-ingestion and deletion-failure tests. |
| Modify | `tests/documents/test_vector_retrieval.py` | Protect validation, option forwarding, and owner filter. |
| Modify | `tests/documents/test_vector_retrieval_chroma.py` | Preserve controlled two-owner isolation. |
| Modify | `tests/rag/test_hyde_retrieval.py` | Pass explicit policy in controlled HyDE retrieval. |
| Modify | `tests/rag/test_services.py` | Assert RAG-to-documents retrieval-policy contract. |

## Implementation Steps

1. **Tests Before:** replace the current incoming-ID deletion assertion with a shrinking scenario:
   seed three chunks for one `document_id`, re-ingest one, then prove only the replacement remains.
   Deliberately seed the same `document_id` metadata under a second owner and prove replacement and
   retrieval remain scoped to the trusted owner.
2. Add tests for mismatched incoming metadata; lookup failure/malformed IDs; no prior IDs; delete
   failure; add failure; and fail-closed rejection of missing, non-integer, or mismatched owner
   metadata in returned documents. No add may occur after incomplete lookup or failed delete.
3. Add service tests proving retrieval policy is validated/snapshotted before HyDE provider/quota
   work, then passed only after the standard or hypothetical retrieval query is known; keep
   threshold/MMR bounds and exact integer owner filters covered.
4. **Refactor:** require trusted `user_id` and `document_id` in replacement; resolve old IDs with
   the public Chroma API; narrow exception catches; preserve the known connection-error
   `ValueError` translation while unrelated `ValueError`/`TypeError` propagate. Move
   `VectorRetrievalError` to `documents.exceptions` and update its four consumer groups: vector
   adapter, RAG service, document retrieval tests, and RAG service tests.
5. Change `retrieve_for_user` to require explicit retrieval policy values and update every caller.
   Keep supported-value validation and owner-filter construction in `documents`.
6. **Tests After:** run controlled Chroma shrinking replacement and owner-isolation scenarios for
   original-query and hypothetical-query retrieval.
7. **Regression Gate:** run document + RAG retrieval suites, lint, and format checks.

## Validation Commands

```bash
uv run pytest tests/documents/test_vector_store.py tests/documents/test_vector_retrieval.py tests/rag/test_services.py -q
uv run pytest tests/rag/test_hyde_retrieval.py -q
uv run pytest tests/documents/test_vector_retrieval_chroma.py --ds=config.settings.production -q
uv run pytest tests/documents tests/rag -q
uv run ruff check apps/documents apps/rag tests/documents tests/rag
uv run ruff format --check apps/documents apps/rag tests/documents tests/rag
```

## Success Criteria

- [x] Shrinking re-ingestion leaves no stale tail chunks for the target owner/document pair.
- [x] Write metadata, replacement filters, native retrieval filters, and returned metadata are all
  fail-closed against the trusted owner.
- [x] RAG explicitly passes `k`, search type, threshold, and `fetch_k`; documents validates them.
- [x] Expected store failures map safely; unrelated defects are not swallowed.
- [x] Existing HyDE ranking and all retrieval tests pass.

## Risk Assessment

- Risk: delete then add can leave no vectors if add fails. Preserve clear ingestion failure and
  document the non-atomic window; code rollback cannot restore deleted data, so recovery requires
  service restoration followed by re-queuing ingestion for the affected document.
- Risk: backend exception taxonomy may be too broad/narrow. Catch only locked Chroma/httpx/import/
  OS failure families plus the exact known Chroma connection `ValueError`; test propagation of
  `TypeError` and unrelated `ValueError`.
- Security: owner isolation is non-negotiable. Validate with two users and similar text; never allow
  a caller-provided filter to replace the authenticated integer `user_id` filter.
