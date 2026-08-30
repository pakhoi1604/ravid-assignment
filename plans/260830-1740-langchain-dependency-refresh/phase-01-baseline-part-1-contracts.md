---
phase: 1
title: Baseline Part 1 Contracts
status: completed
priority: P1
dependencies: []
---

# Phase 1: Baseline Part 1 Contracts

## Overview

Protect current Part 1 behavior before changing the dependency graph. Extend focused tests only
where the existing suite does not exercise the actual LangChain component boundaries.

## Requirements

- Functional: preserve extraction, chunk constraints, deterministic vector IDs/metadata, Chroma
  constructor wiring, delete-before-add behavior, and ingestion status contracts.
- Non-functional: baseline tests run offline without Chroma, Redis, Celery, or model downloads.

## Architecture

Tests stay at the existing seams. Mock external constructors, not the Part 1 orchestration being
protected. Avoid exact snapshots of LangChain-internal chunk output unless the exact output is a
published project contract; assert stable invariants instead.

## Related Code Files

- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/tests/documents/test_chunking.py` - add
  representative separator, size, overlap, and blank-output invariants.
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/tests/documents/test_vector_store.py` -
  cover `_build_store` client/embedding/collection wiring and adapter errors.
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/tests/documents/test_ingestion_pipeline.py`
  - retain metadata, IDs, and end-to-end service-boundary coverage.

## Implementation Steps

1. Record current resolved versions for the relevant package family from `uv.lock`.
2. Run focused Part 1 tests before edits and preserve the result as the migration baseline.
3. Extend chunking tests around public invariants: non-empty chunks, maximum size, requested
   overlap behavior on a representative input, and whitespace filtering.
4. Extend vector-store tests so `_build_store` proves `chromadb.HttpClient`,
   `HuggingFaceEmbeddings`, and `langchain_chroma.Chroma` receive the expected configuration.
5. Confirm ingestion tests protect owner/document/task metadata and stable vector IDs.
6. Run the focused test set again before dependency changes.

## Success Criteria

- [x] Baseline focused tests pass on the existing 0.3 component family.
- [x] Tests fail meaningfully if a required LangChain integration import or constructor contract
  disappears.
- [x] Tests do not require network, a model download, or a running Chroma server.
- [x] No production behavior or public API is changed in this phase.

## Risk Assessment

Over-specific chunk snapshots can create false failures across safe splitter releases. Prefer
assignment-level invariants and isolate exact expectations to project-owned metadata and IDs.

## Security Considerations

No auth or data-access behavior changes. Tests must continue proving `user_id` metadata reaches
the vector record boundary.
