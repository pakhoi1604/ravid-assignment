---
phase: 2
title: "Implement Generation-Safe Vector Activation"
status: completed
priority: P1
dependencies: [1]
---

# Phase 2: Implement Generation-Safe Vector Activation

## Overview

Replace delete-before-add indexing with immutable generation writes, verified activation, active-only
retrieval, and best-effort post-activation cleanup. Preserve the vector adapter as an ORM-free leaf.

## Requirements

- Fully write and observe exact IDs/metadata before activation.
- Exclude incomplete, failed, stale, and legacy generation-less vectors from retrieval.
- Keep the old active generation visible until PostgreSQL switches the pointer.
- Cleanup failure cannot change `SUCCESS` or the active pointer.
- Owner/document/generation metadata mismatch fails closed.

## Architecture

Chunk IDs become `document-{document_id}-generation-{generation}-chunk-{index}` and metadata gains
`generation`. `write_document_generation()` performs validated add plus exact post-write readback;
it never deletes the current generation first. The task later activates
`Document.active_generation=G` and job `SUCCESS` in one PostgreSQL transaction.

Add `apps.documents.retrieval` as the one facade joining relational visibility with the ORM-free
Chroma leaf. It resolves the owner's `(document_id, active_generation)` map, passes UUIDs into a
native `$and(user_id, generation $in [...])` filter, then validates every returned pair. Empty map
returns without querying Chroma.

Activation records the exact superseded generation in the manifest. Cleanup may delete only that
manifest generation, never "all non-current" records. It is delayed beyond the maximum prior-worker
lifetime and excludes both `Document.active_generation` and every live `IngestionJob.generation`.
Late stale-worker finalization schedules cleanup of its own exact generation.

## Related Code Files

- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/apps/documents/ingestion.py`
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/apps/documents/vector_store.py`
- Create: `/home/khoipham/Projects/ravid-assignment/Ravid/apps/documents/retrieval.py`
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/apps/rag/services.py`
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/tests/documents/test_ingestion_pipeline.py`
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/tests/documents/test_vector_store.py`
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/tests/documents/test_vector_retrieval.py`
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/tests/documents/test_vector_retrieval_chroma.py`
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/tests/documents/test_module_boundaries.py`
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/tests/rag/test_services.py`

## Implementation Steps

1. Add failing tests for inactive exclusion, previous-generation visibility, exact readback, and
   cleanup ordering.
2. Change `run_ingestion_pipeline(job, generation)` to create immutable generation-qualified chunks
   and return readiness without mutating relational activation.
3. Replace `replace_document_chunks` with focused write, verify, and cleanup adapter operations.
   Retain trusted owner/document collision checks.
4. Extend retrieval kwargs and returned-result validation with active generations.
5. Define an `ActiveDocumentRetriever` protocol matching the existing `retrieve_for_user` method;
   preserve `vector_store_factory` injection and serialize UUID metadata as strings.
6. Update the module matrix: `retrieval -> {models, vector_store}`; keep vector store ORM-free.
7. Prove locked Chroma `$in` filtering and cleanup in the infrastructure-backed test.
8. Remove Chroma `ingestion_job_id` and `task_id` metadata unless a verified consumer requires them.
   Keep filename only while existing prompt/debug contracts require it; never add operational IDs.

## Tests Before

- Preserve owner isolation and cross-owner ID-collision tests.
- Add a failing test showing delete-before-add loses old index availability on add failure.

## Tests After

- Partial write/readback failure cannot change active pointer.
- Old generation before activation; new generation after activation.
- Cleanup targets one manifest generation and never deletes current/live/in-flight generations or
  another owner's records, including delayed G1-cleanup vs G2-write interleavings.
- Cleanup failure preserves successful retrieval.
- Missing/wrong generation metadata fails closed.

## Success Criteria

- [x] No normal indexing path deletes active vectors before new-generation verification.
- [x] Retrieval reads only owner-scoped active generations.
- [x] Locked-version Chroma test passes without undocumented atomicity claims.
- [x] Adapter remains ORM-free and module-boundary tests pass.

## Risk Assessment

Chroma writes are not assumed atomic. Readback proves observed completeness, not a distributed
transaction. PostgreSQL filtering is the visibility guarantee. Crash after activation and before
cleanup leaves invisible data for later reconciliation.

## Security Considerations

Use native owner filtering plus exact document-generation post-validation. Never trust Chroma
metadata solely because it matched a generation UUID.
