---
title: "Clean Module Boundaries Completion Report"
status: completed
created: "2026-08-31T11:38:39+07:00"
---

# Clean Module Boundaries Completion Report

## Summary

All four phases are implemented and verified. Document ingestion no longer depends on a monolithic
services module, vector access is explicitly owner-scoped and fail-closed, and RAG orchestration now
delegates immutable contracts, provider parsing, prompt binding, and stage accounting to focused
modules.

## Verification

- Local suite: 233 passed, 3 infrastructure-only skips.
- Production Compose: both HTTP-Chroma tests and the PostgreSQL row-locking test passed.
- Focused collision proof: an existing foreign-owner deterministic Chroma ID is rejected before
  mutation and remains unchanged.
- Ruff, formatting, Django checks, migration drift, Compose configuration, and whitespace checks
  passed.
- Final code review and adversarial review: PASS_WITH_RISK, zero critical/high findings.

## Maintainer Impact

- `apps.documents`: contracts, constants, exceptions, ingestion orchestration, and vector access have
  explicit ownership; `apps.documents.services` is removed.
- `apps.rag`: the public service remains the query orchestrator while accounting, response parsing,
  prompt binding, and result contracts are independently testable.
- Public HyDE additions from the preceding accepted plan are preserved; this refactor introduces no
  additional public API or configuration contract change.

## Remaining Limitations

- Chroma replacement is check/delete/add rather than atomic.
- Quota settlement is request-local rather than crash-idempotent.
- Duplicate or concurrent Celery ingestion delivery remains unguarded.
- Embedding and vector writes are not batched.

## Next Steps

No implementation work remains in this plan. Treat the listed limitations as separate production
hardening work if the assignment scope expands.
