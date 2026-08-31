---
date: 2026-08-31
session: clean-module-boundaries
---

# Journal: 2026-08-31 — Clean Module Boundaries

## Context

The document-ingestion and RAG paths had sound app-level ownership but blurred internal boundaries:
document leaf modules depended on a monolithic service module, while RAG orchestration also owned
contracts, provider parsing, prompt binding, and accounting details. The goal was a behavior-preserving
refactor with one explicit owner for each concern, plus a fix for stale vectors after shrinking
re-ingestion.

## What Happened

- `apps.documents` now owns ingestion through a one-way dependency chain: tasks call the ingestion
  orchestrator, which depends on leaf extraction, chunking, and vector-store modules; shared constants,
  contracts, and exceptions are dependency-free.
- `apps.rag.services` remains the query orchestrator while frozen result contracts, provider-response
  normalization, prompt binding, and request-local stage accounting moved to focused modules.
- Vector replacement now validates trusted owner/document metadata, resolves all prior owner-scoped
  chunk IDs, and rejects malformed or mismatched retrieval results.
- Adversarial review found a cross-owner Chroma collision: deterministic incoming chunk IDs could
  already belong to another owner. The replacement path now checks existing IDs and ownership before
  deletion or insertion; a focused embedded-Chroma test proves the foreign record is rejected without
  mutation.
- Verification completed with 233 local passes and three infrastructure-only skips, followed by all
  three production Compose scenarios passing. Ruff, formatting, Django checks, migration drift,
  Compose configuration, OpenAPI, whitespace checks, and 40 sampled claims also passed. Final review
  was `PASS_WITH_RISK` with no critical or high findings.

## Reflection

The strongest result is clearer ownership without adding apps, services, or framework abstractions.
The collision finding also justified adversarial review: owner-scoped lookup alone was insufficient
because globally deterministic IDs form a second cross-owner boundary. The fix makes that boundary
explicit and fail-closed, while the documentation avoids overstating guarantees that remain local to
one process or one replacement attempt.

## Decisions

| Decision | Rationale | Impact |
| --- | --- | --- |
| Keep the Django modular monolith and extract only focused internal modules. | Existing app boundaries were correct; the problem was mixed ownership inside two apps. | Dependencies are easier to inspect and test without new operational complexity. |
| Make `documents` authoritative for owner-scoped vector validation and let `rag` pass retrieval policy explicitly. | Storage safety belongs at the adapter boundary; query policy belongs to RAG orchestration. | Reads and writes fail closed, including cross-owner deterministic-ID collisions. |
| Accept check/delete/add Chroma replacement as non-atomic. | Atomic or versioned replacement exceeds the assignment scope. | An add failure after deletion requires service recovery and re-ingestion. |
| Keep quota settlement request-local rather than durable. | The refactor isolates existing accounting behavior but adds no ledger or reconciliation worker. | One execution prevents duplicate terminal settlement, but crashes and ambiguous database outcomes are not exactly-once. |
| Defer duplicate/concurrent Celery delivery guards and batching. | These are production-hardening concerns independent of module ownership. | The limitations remain explicit follow-up work, not implied guarantees. |

## Next

- Treat atomic/versioned vector replacement and a durable, reconcilable quota ledger as separate
  production-hardening projects if scope expands.
- Add Celery idempotency/concurrency protection and batched embedding/vector writes before increasing
  ingestion throughput.
