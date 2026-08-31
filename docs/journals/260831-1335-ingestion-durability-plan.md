---
date: 2026-08-31
session: ingestion-durability-plan
type: journal
---

# Journal: 2026-08-31 — Ingestion Durability Plan

## Context

Planned hardening of the PostgreSQL–Celery–Chroma ingestion workflow against duplicate delivery,
worker loss, broker failure, partial vector writes, stale attempts, and oversized documents. The
design preserves the Django modular monolith and existing upload endpoints while truthfully exposing
`PENDING`. This session produced planning artifacts only; no source implementation occurred.

## What Happened

- Produced a five-phase implementation plan covering durable state, generation-safe vector
  activation, idempotent execution and recovery, transactional dispatch, and bounded workloads.
- Kept PostgreSQL authoritative for job state and vector visibility while treating Celery as
  at-least-once infrastructure and Chroma generations as immutable, externally stored data.
- Defined focused PostgreSQL/Chroma integration tests, migration and Compose checks, API regression
  gates, and a full-suite validation gate before documentation or rollout is considered complete.
- Completed an adversarial review with 15 deduplicated findings: 13 accepted into the plan and 2
  retained as explicit deferred risks. A final consistency sweep found no unresolved contradictions.

## Key Architecture Decisions

| Decision | Rationale | Impact |
| --- | --- | --- |
| Make `Document.active_generation` the visibility pointer and `IngestionJob.generation` the fencing token | Cross-store writes cannot be one transaction | Stale workers may write inactive data but cannot activate or finalize it |
| Write and verify a complete immutable generation before PostgreSQL activation | Delete-before-add can make previously valid retrieval unavailable | The prior generation remains visible until the replacement is ready |
| Track exact generation lifecycle and cleanup ownership in a durable manifest | Broad non-current cleanup can delete live or in-flight data | Cleanup targets one known generation, is delayed, retryable, and cannot downgrade success |
| Route retrieval through one owner-aware facade | Relational visibility must constrain Chroma results | Queries filter by owner and active generation, then fail closed on metadata mismatch |
| Use a leased transactional outbox with claim-token compare-and-swap | An upload commit and broker publication cannot be atomic | Web requests avoid broker I/O; publication is durable, bounded, and explicitly at least once |
| Bound PDF pages, extracted characters, and chunks before vector writes | Worker time and memory must be capped for hostile inputs | Exact limits pass; overflow fails early with sanitized errors |

## Red-Team Corrections

- Added a maintenance/no-chat rollout gate plus restartable legacy reindex or intentional reset to
  prevent generation filtering from causing a retrieval blackout.
- Replaced broad cleanup with exact manifest ownership, grace periods, active/live-generation
  exclusions, and reconciliation for inactive stale-worker writes.
- Added leased outbox claims, bounded backoff and retry exhaustion, unique delivery identities, and
  no synchronous broker publication on the upload path.
- Prevented queued `PENDING` work from being mistaken for stale dispatch; recovery rotates the
  generation and remains bounded and operator-visible.
- Added compensating upload cleanup and a bounded orphan-media reconciler for rollback and crash
  windows.
- Required chunk ceilings during splitting rather than after unbounded list allocation, trimmed
  operational Chroma metadata, specified the retrieval injection protocol, and made operational
  admin surfaces read-only.

## Deferred Risks

- Parser process isolation, MIME/malware containment, and per-tenant document quotas remain outside
  this hardening scope; application limits reduce exposure but are not a sandbox.
- Celery late acknowledgement remains deferred until fencing and PostgreSQL concurrency behavior are
  proven. Vector batching, object storage, multi-node Chroma, metrics, and tracing are also deferred.
- A live deployment still requires an explicit maintenance window and verified legacy reindex; no
  automatic live-vector backfill is planned.

## Next Step

Implement the five phases strictly in order, beginning with schema and contract tests for generation
state. Do not enable active-generation retrieval until migration, legacy reindex/reset verification,
and the phase-specific regression gates pass.

## Status

Plan complete and pending implementation.

## Summary

The accepted design makes ingestion replay-safe and recoverable through generation fencing,
PostgreSQL-controlled visibility, exact cleanup ownership, durable at-least-once dispatch, and hard
resource ceilings without changing the service topology.

## Concerns

Correctness depends on disciplined rollout and real PostgreSQL/Chroma concurrency validation. The
outbox closes dispatch loss but does not create exactly-once execution or a distributed transaction,
and deferred parser containment remains the largest workload-security gap.
