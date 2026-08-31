---
phase: 1
title: "Define Durable Ingestion State"
status: pending
priority: P1
dependencies: []
---

# Phase 1: Define Durable Ingestion State

## Overview

Introduce the durable state and generation contracts required by later phases. Preserve existing
endpoint paths and terminal status values while making pending work truthful and retries fenceable.

## Requirements

- Persist one active generation per document and one current attempt generation per job.
- Retain `PENDING`, `PROCESSING`, `SUCCESS`, and `FAILURE`; stop mapping `PENDING` to `PROCESSING`.
- The migration must be backward-safe and must not contact Chroma.
- Authentication, owner filtering, upload response, and sanitized errors remain unchanged.

## Architecture

Add nullable `Document.active_generation` and non-null `IngestionJob.generation` UUID fields.
`generation` is a fencing token, not a counter: recovery creates a new UUID, making late completion
from an older worker detectable. Add `attempt_count`, `lease_expires_at`, and a bounded
`failure_code` for recovery/audit decisions; do not store exception messages from infrastructure.

Add `IngestionGeneration` as the durable cleanup manifest: document, generation UUID, lifecycle
(`WRITING`, `ACTIVE`, `STALE`, `CLEANED`), expected/observed chunk count, `cleanup_after`, attempts,
and sanitized error code. Unique `(document, generation)` prevents duplicate manifests. It exists
because `IngestionJob` only represents the current attempt and cannot safely own old-generation
cleanup history.

```text
PENDING(G) --claim--> PROCESSING(G) --activate--> SUCCESS(G)
    ^                     |
    |                     +--deterministic/runtime failure--> FAILURE(G)
    +--recover/retry: rotate G and reset timestamps/lease--+
```

`SUCCESS` is immutable under normal delivery. Explicit legacy reindex first rotates generation and
changes the job to `PENDING`; it is not a replay of `SUCCESS`.

## Related Code Files

- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/apps/documents/models.py`
- Create: `/home/khoipham/Projects/ravid-assignment/Ravid/apps/documents/migrations/0002_ingestion_generations.py`
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/apps/documents/serializers.py`
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/apps/documents/admin.py`
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/tests/documents/test_models.py`
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/tests/documents/test_api.py`

## Implementation Steps

1. Write model/API regression tests first: terminal responses stay stable; `PENDING` is returned
   directly; generation UUIDs are non-null and active generation starts null.
2. Add fields, generation manifest, and constraints. Add indexes only for active/cleanup queries;
   do not duplicate indexes already supplied by `unique=True`.
3. Generate migration `0002`. It changes PostgreSQL only and leaves existing active generation null.
4. Expose generation, lease, attempt, and failure code read-only in admin; never expose raw errors.
5. Remove the `PENDING -> PROCESSING` formatting rewrite. Update schema tests only if needed.
6. Run migration/check tests and record the live-data rollout requirement.

## Tests Before

- Lock current upload/status ownership and terminal response contracts.
- Add a failing test proving `PENDING` must no longer serialize as `PROCESSING`.

## Tests After

- Field defaults, UUID types, state choices, migration graph, admin read-only visibility.
- Manifest uniqueness, allowed lifecycle transitions, and cleanup scheduling fields.
- Existing rows migrate with a generated attempt token and null active pointer.
- `makemigrations --check --dry-run` reports no drift.

## Success Criteria

- [ ] Schema supports fencing and an authoritative active-generation pointer.
- [ ] Status endpoint reports `PENDING` truthfully without changing auth/ownership behavior.
- [ ] Migration never imports or calls Chroma/Celery.
- [ ] Existing upload and terminal status tests pass.

## Risk Assessment

Legacy vectors have no generation metadata and become ineligible once Phase 2 enables generation
filters. Mitigation: do not enable the filter without an operator reindex/reset procedure.

## Security Considerations

Generation is not an authorization secret. Later queries retain native `user_id` filtering and
post-query owner validation; generation filtering only strengthens visibility.
