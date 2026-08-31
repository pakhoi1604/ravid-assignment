---
phase: 3
title: "Enforce Idempotent Execution and Stale Recovery"
status: completed
priority: P1
dependencies: [2]
---

# Phase 3: Enforce Idempotent Execution and Stale Recovery

## Overview

Fence duplicate and stale workers with atomic claims, then add bounded recovery for stale `PENDING`
and `PROCESSING` jobs. This is the take-home-safe baseline before the durable outbox.

## Requirements

- `SUCCESS`, mismatched-generation, and already-`PROCESSING` deliveries are no-ops.
- A task finalizes only while its generation still owns the job lease.
- Stale recovery rotates generation before republishing, fencing surviving old workers.
- Fresh/terminal jobs are excluded by default; deterministic failures are not auto-retried.
- Broker publish exceptions are sanitized and leave durable retryable state.

## Architecture

Pass `(task_id, generation)` in every Celery payload. Claim with `transaction.atomic()` and
`select_for_update()` only for matching `PENDING`. Claim increments attempt count, sets
`PROCESSING`, resets timestamps, and creates a lease beyond the Celery hard limit.

Finalization locks job+document and rechecks status/generation before pointer activation or failure.
A stale G1 worker may create inactive chunks after recovery rotated to G2, but cannot finalize G1.
Lease expiry makes a job eligible for recovery; it does not itself revoke ownership. Only an atomic
generation rotation revokes ownership, avoiding a race where an otherwise valid result expires
milliseconds before finalization.

Add a recovery service plus `recover_ingestion_jobs` command. It uses `skip_locked` on PostgreSQL,
rotates generation, resets stale work to `PENDING`, and publishes after commit. Automatic scans are
manual in this baseline and cap recoveries per job; exhaustion records a manual-intervention failure
code. `--task-id` is the explicit operator retry after root-cause repair.

Add a bounded, restartable `reindex_legacy_documents` operator command. It explicitly transitions
legacy `SUCCESS` jobs to a fresh `PENDING` generation; normal duplicate delivery still cannot rerun
success. No generation-filtered deployment may serve chat until this command completes or the
assignment volumes are intentionally reset.

## Related Code Files

- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/apps/documents/tasks.py`
- Create: `/home/khoipham/Projects/ravid-assignment/Ravid/apps/documents/recovery.py`
- Create: `/home/khoipham/Projects/ravid-assignment/Ravid/apps/documents/management/commands/recover_ingestion_jobs.py`
- Create: `/home/khoipham/Projects/ravid-assignment/Ravid/apps/documents/management/commands/reindex_legacy_documents.py`
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/apps/documents/views.py`
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/config/settings/base.py`
- Modify: project root environment template
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/compose.yaml`
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/tests/documents/test_tasks.py`
- Create: `/home/khoipham/Projects/ravid-assignment/Ravid/tests/documents/test_recovery.py`
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/tests/documents/test_api.py`
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/tests/smoke/test_configuration.py`
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/tests/smoke/test_compose_contracts.py`

## Implementation Steps

1. Write replay/fencing tests: success duplicate, processing duplicate, mismatched generation, and
   stale G1 completion after G2 recovery.
2. Extract small private claim/finalize functions; avoid a generic state-machine framework.
3. Activate pointer+success transactionally, then run cleanup without downgrading success.
4. Add positive pending/processing stale and maximum-recovery settings. Require threshold to exceed
   `CELERY_TASK_TIME_LIMIT` plus an explicit safety margin.
5. Implement bounded limit/dry-run/explicit retry. Before the outbox exists, stale `PENDING`
   recovery is operator-triggered and uses a fail-fast producer configuration; do not run a periodic
   timer that mistakes normal queue latency for lost dispatch.
6. Wrap upload callback publication. On broker error, log identifiers only, leave `PENDING`, and
   preserve `202`; disable producer retries and enforce a short connection/operation budget.
7. Give every delivery a unique Celery message ID while carrying logical task/generation in payload;
   set ingestion tasks `ignore_result=True` because PostgreSQL is authoritative.
8. Add restartable legacy reindex/reset command and a no-chat deployment gate before generation
   filtering is enabled in a live environment.
9. Keep early acknowledgement; do not enable `acks_late` or worker-loss rejection yet.

## Tests Before

- Preserve current success/failure transitions and upload rollback callback behavior.
- Add a failing test proving current code reruns `SUCCESS`.

## Tests After

- Only one matching pending generation claims execution.
- Fresh jobs excluded; stale jobs recovered; limit/dry-run/explicit retry honored.
- Retry exhaustion becomes manual-intervention failure instead of an infinite loop.
- Broker failure leaves `PENDING`; later recovery succeeds.
- Old worker cannot alter current pointer/status.
- Legacy reindex is restartable and normal `SUCCESS` duplicate remains a no-op.
- PostgreSQL proves locking behavior unavailable under SQLite.

## Success Criteria

- [x] Duplicate deliveries perform no vector or terminal-state mutation.
- [x] Stale jobs have bounded generation-rotating recovery.
- [x] Dispatch failure is observable and recoverable.
- [x] Thresholds are coherent with the Celery hard limit.

## Risk Assessment

Short leases can overlap attempts. Fencing protects activation but wastes CPU and leaves inactive
chunks. Use conservative defaults, validation, dry-run, bounded recovery, and PostgreSQL tests.

## Security Considerations

Recovery is operator-only. Never disclose broker exceptions, file paths, content, or another
owner's task identifiers.
