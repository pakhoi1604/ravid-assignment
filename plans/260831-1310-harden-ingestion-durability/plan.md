---
title: "Harden Ingestion Durability and Resource Bounds"
description: "Make document ingestion replay-safe, recoverable, generation-aware, and bounded without changing the modular-monolith or public upload contract."
status: pending
priority: P1
branch: "main"
tags: [backend, database, celery, refactor, critical]
blockedBy: [260831-1306-harden-docker-reviewer-stack]
blocks: []
created: "2026-08-31T06:19:50.845Z"
createdBy: "ck:plan"
source: skill
---

# Harden Ingestion Durability and Resource Bounds

## Overview

Harden the PostgreSQL-Celery-Chroma workflow against duplicate delivery, worker loss, broker
failure, partial vector writes, and hostile document workloads. Keep the existing Django modular
monolith and API endpoints. PostgreSQL owns job state and the active vector-generation pointer;
Chroma stores immutable generation-qualified chunks; Celery remains at-least-once infrastructure.

Normal duplicate delivery must never rerun a `SUCCESS` job. Recovery rotates a generation token,
so a stale worker may finish local work but cannot activate or overwrite a newer attempt. New
vectors are written and verified before PostgreSQL activation; old generations are deleted only
after activation and remain invisible if cleanup fails.

## Scope Challenge

- Existing code reused: `IngestionJob`, `transaction.on_commit`, Celery task, document orchestrator,
  owner-scoped vector adapter, DRF status API, settings split, and focused test suites.
- Minimum reliable design: generation pointers plus a cleanup manifest, one retrieval facade,
  fenced transitions, bounded recovery, three ingestion ceilings, and a durable dispatch outbox.
- Justified complexity: five sequential phases isolate schema rollout, cross-store visibility,
  execution recovery, broker durability, and resource limits behind separate regression gates.
- Selected mode: **HOLD SCOPE**, hard mode. No microservice, Kafka, vector-store replacement,
  automatic reprocessing of successful jobs, batching rewrite, or generic workflow framework.

## Architecture Decisions

- `Document.active_generation` is the authoritative visibility pointer.
- `IngestionJob.generation` is the fencing token for the current attempt.
- `IngestionGeneration` records immutable generation lifecycle and exact cleanup ownership; cleanup
  never means "delete every non-current generation".
- Chroma chunk IDs and metadata include generation; retrieval accepts only generations currently
  active for that authenticated owner.
- Per the current user request, `PENDING` is returned truthfully. This is an intentional extension
  of the assignment-facing status contract and requires OpenAPI/README/test updates.
- A `SUCCESS` or already-`PROCESSING` duplicate is a no-op. Retry/recovery must rotate generation.
- Activation is a PostgreSQL transaction after Chroma write verification. Cleanup is post-activation
  and retryable; it cannot downgrade a successfully activated job.
- The production outbox provides durable at-least-once dispatch, not exactly-once execution and not
  a distributed transaction with Chroma.
- Existing generation-less vectors are reindexed through a bounded, restartable operator command
  before generation-filtered code serves chat. Django migrations must not call Chroma.

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Define Durable Ingestion State](./phase-01-define-durable-ingestion-state.md) | Pending |
| 2 | [Implement Generation-Safe Vector Activation](./phase-02-implement-generation-safe-vector-activation.md) | Pending |
| 3 | [Enforce Idempotent Execution and Stale Recovery](./phase-03-enforce-idempotent-execution-and-stale-recovery.md) | Pending |
| 4 | [Add Transactional Dispatch Outbox](./phase-04-add-transactional-dispatch-outbox.md) | Pending |
| 5 | [Bound Ingestion Work and Validate](./phase-05-bound-ingestion-work-and-validate.md) | Pending |

## Dependencies

- No unfinished plan modifies the same ingestion model, vector adapter, or task workflow.
- `260831-1306-harden-docker-reviewer-stack` must complete first because it owns the shared Compose
  environment and contract-test structure; this plan adds recovery and resource knobs afterward.
- `260830-1608-part-1-endpoint-smoke-tests` remains independent; this plan must preserve its public
  upload/status contracts when that smoke plan is resumed.
- Dependency audit on 2026-08-31: the endpoint-smoke plan no longer hard-blocks Docker hardening;
  Docker hardening is ready to start, while this ingestion plan remains pending behind it.
- Phase order is strict: `1 -> 2 -> 3 -> 4 -> 5`.

## Success Criteria

- Duplicate/stale tasks cannot activate vectors or terminal state for the wrong generation.
- Failed or partial generations are invisible to authenticated retrieval.
- Previous active vectors remain queryable until a complete new generation is activated.
- Stale jobs and failed dispatches have bounded, operator-visible recovery paths.
- Upload transaction and outbox creation are atomic; broker publication remains at-least-once.
- PDF page count, extracted characters, and chunk count are hard bounded before vector writes.
- Existing API authentication, ownership isolation, response messages, and success/failure shapes
  remain compatible; status may now truthfully expose `PENDING`.
- Focused, PostgreSQL/Chroma integration, migration, lint, Django check, and full pytest gates pass.

## Deferred Work

- Automatic backfill of live legacy vectors without an explicit maintenance window.
- Vector write batching, object storage, multi-node Chroma, metrics backend, or tracing platform.
- Celery late acknowledgements until generation fencing and PostgreSQL concurrency tests are proven.
- PDF parser process isolation/sandboxing and per-tenant document quotas. Current work adds hard
  application ceilings and retains the Celery hard time limit, but does not claim parser containment.

## Open Questions

- None. Rollout assumption: this assignment environment may be reset/reindexed. A live environment
  must run the explicit legacy reindex workflow before generation-filtered retrieval is enabled.

## Red Team Review

### Session — 2026-08-31

**Findings:** 15 deduplicated (13 accepted, 2 rejected)
**Severity:** 3 Critical, 9 High, 3 Medium

| # | Finding | Severity | Disposition | Applied To |
|---|---|---|---|---|
| 1 | Legacy rollout causes retrieval blackout | Critical | Accept | Phases 3, 5 |
| 2 | Broad cleanup can delete in-flight generation | Critical | Accept | Phases 1, 2, 4 |
| 3 | Inactive generation has no durable reconciliation owner | Critical | Accept | Phases 1, 4 |
| 4 | Synchronous publish can block accepted upload | High | Accept | Phases 3, 4 |
| 5 | Outbox lacks leased claim/CAS boundary | High | Accept | Phase 4 |
| 6 | PENDING recovery can churn queued work | High | Accept | Phases 3, 4 |
| 7 | Recovery/publisher retries are unbounded | High | Accept | Phases 3, 4 |
| 8 | Uploaded file can outlive rolled-back DB rows | High | Accept | Phases 4, 5 |
| 9 | Chunk ceiling occurs after list allocation | High | Accept | Phase 5 |
| 10 | Celery delivery identity/result contract ambiguous | Medium | Accept | Phases 3, 4 |
| 11 | Retrieval facade injection contract unspecified | Medium | Accept | Phase 2 |
| 12 | Outbox admin surface could be mutable | Medium | Accept | Phase 4 |
| 13 | Chroma metadata retains unnecessary operational IDs | High | Accept | Phase 2 |
| 14 | PDF parser requires separate process sandbox | High | Reject | Deferred; outside requested ceilings |
| 15 | Active-generation filter needs tenant document quota | High | Reject | Deferred; no product quota requirement |

Rejected findings remain documented risks. They do not invalidate the requested take-home hardening;
they become production capacity/security work when workload and tenancy requirements are known.

### Whole-Plan Consistency Sweep

- Files reread: `plan.md` and all five phase files.
- Decision deltas checked: generation manifest, exact cleanup target, cleanup grace period, legacy
  reindex gate, leased outbox claim, bounded retries/dead state, no web broker I/O, Celery delivery
  identity, bounded splitting, orphan-media cleanup, read-only admin, facade protocol, metadata trim.
- Reconciled stale references: 13.
- Unresolved contradictions: 0.
- Validation interview: not run; project configuration is `prompt` mode.
