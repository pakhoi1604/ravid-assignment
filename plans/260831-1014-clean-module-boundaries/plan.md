---
title: "Refactor RAG and Document Module Boundaries"
description: "Refactor internal document and RAG boundaries without changing the modular-monolith or public API contracts."
status: completed
priority: P1
branch: "main"
tags: [refactor, backend, tech-debt, test]
blockedBy: []
blocks: []
created: "2026-08-31T03:15:27.593Z"
createdBy: "ck:plan"
source: skill
---

# Refactor RAG and Document Module Boundaries

## Overview

Make `apps.documents` and `apps.rag` easier to reason about through tests-first, behavior-preserving
module extraction. Break hidden document import cycles, correct stale-vector replacement, make
retrieval policy explicit, and reduce `RagService` to one cohesive query orchestrator.

## Scope Challenge

- Existing strengths: sound `accounts`/`documents`/`rag`/`common` app ownership, one-way app
  dependencies, focused prompt/token/provider adapters, atomic account-domain quota operations.
- Minimum change: internal modules and explicit collaborators only; fix the proven shrinking
  re-ingestion defect. Preserve endpoint schemas, statuses, settings, HyDE fallback, quota policy,
  owner filtering, and current tests.
- Complexity: four sequential phases and several files are justified by hidden document cycles and
  two independently risky contracts: vector replacement and per-stage accounting.
- Selected scope: HOLD. Production hardening is documented, not implemented.

## Decisions

- Keep the Django modular monolith. Add no app, microservice, `shared`/`core`, repository framework,
  event bus, or DI container.
- `documents` owns ingestion and fail-closed owner-scoped vector access; `rag` explicitly chooses the
  retrieval policy; `accounts` remains the quota persistence authority.
- Keep one public `RagService` query orchestrator. Extract only immutable contracts, provider
  response handling, and stage accounting.
- Public behavior changes only for the identified stale-tail vector defect.

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Protect Contracts and Break Document Cycles](./phase-01-protect-contracts-and-break-document-cycles.md) | Completed |
| 2 | [Correct Vector Store Boundaries and Replacement](./phase-02-correct-vector-store-boundaries-and-replacement.md) | Completed |
| 3 | [Extract RAG Contracts Accounting and Response Handling](./phase-03-extract-rag-contracts-accounting-and-response-handling.md) | Completed |
| 4 | [Validate Architecture and Document Limitations](./phase-04-validate-architecture-and-document-limitations.md) | Completed |

## Dependencies

## Cross-Plan Dependencies

- `blockedBy: []`; `blocks: []`.
- Pending hook migration is unrelated. Pending Part 1 smoke work observes overlapping ingestion
  behavior but neither blocks nor requires this internal refactor.

## Acceptance Criteria

- No hidden `documents` leaf-module import back to its ingestion orchestrator.
- Shrinking re-ingestion removes every old chunk for the trusted owner/document pair; write
  metadata, delete lookup, native retrieval filters, and returned metadata are owner-validated.
- Retrieval policy crosses the `rag` → `documents` boundary explicitly and is validated at the
  store-supported boundary before provider/quota work.
- `RagService` has frozen result contracts, isolated response parsing, injected accounting and one
  bound prompt specification per stage, with at most one terminal settlement call per stage in one
  execution.
- All API/OpenAPI, HyDE, quota, document-status, configuration, lint, and regression checks pass.

## Open Questions

None.

## Validation Log

- Red team: 24 findings reviewed; 12 material findings accepted and deduplicated into owner-scoped
  writes/deletes, fail-closed reads, exact Chroma lookup/error semantics, import-matrix tests,
  explicit monkeypatch seams, HyDE timing, settlement wording/failure matrix, and one bound prompt
  source. Broader atomic replacement, durable settlement, task idempotency, extraction bounds, and
  prompt-injection hardening remain explicit accepted limitations rather than hidden guarantees.
- TDD/contract validation: completed across all four phases. Final verification produced 233 local
  passes; all three infrastructure-only scenarios also passed under production settings in Compose.
- Contract baseline: HyDE request/response and retrieval-setting additions belong to the preceding
  accepted HyDE plan. This refactor preserved that accepted contract; it did not compare the
  combined working tree directly with pre-HyDE `HEAD` as if those additions were regressions.
- Final review: PASS_WITH_RISK with zero critical/high findings. Remaining limitations are
  non-atomic vector replacement, request-local quota settlement, and duplicate Celery delivery.
- Standard verification: 40 sampled claims; 40 verified, 0 failed, 0 unresolved.

## Red Team Review

### Session — 2026-08-31

**Findings:** 24 raw, 12 deduplicated/accepted; 0 unresolved plan contradictions.

### Whole-Plan Consistency Sweep

- Files reread: `plan.md` and all four phase files.
- Decision deltas checked: owner scope, retrieval timing, exception mapping, settlement semantics,
  prompt ownership, and deferred limitations.
- Reconciled stale references: 11.
- Unresolved contradictions: 0.
