---
phase: 4
title: "Add Transactional Dispatch Outbox"
status: pending
priority: P1
dependencies: [3]
---

# Phase 4: Add Transactional Dispatch Outbox

## Overview

Close the PostgreSQL-commit-to-broker-publish loss window with a transactional outbox and periodic
publisher. Reuse generation fencing so ambiguous publish outcomes and duplicates are harmless.

## Requirements

- Upload/retry state and dispatch intent commit in one PostgreSQL transaction.
- Multiple publishers use bounded row claims and backoff.
- Mark published only after `apply_async` succeeds.
- Failed/ambiguous publication remains durable and retryable.
- Periodic work also invokes stale-job and inactive-generation reconciliation.

## Architecture

Add `IngestionDispatch`, unique by `(job, generation)`, with
`PENDING|PUBLISHING|PUBLISHED|DEAD`, attempts, `available_at`, opaque claim token,
`claim_expires_at`, `published_at`, and sanitized error code. Upload/recovery create it in the same
transaction that creates/rotates the job. The final web request path does not perform broker I/O.

Publisher performs a short transaction to claim rows as `PUBLISHING`, commits, publishes outside
the transaction with bounded producer timeouts, then compare-and-swaps the same token to
`PUBLISHED` or retry/dead state. Expired claims are recoverable. Backoff and max attempts are
bounded/configurable. Celery Beat runs publisher, stale recovery, and exact-generation cleanup.

Semantics are **at least once**. Ambiguous acceptance may duplicate publication; Phase 3 makes that
safe. The outbox is not a PostgreSQL-Chroma transaction.

## Related Code Files

- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/apps/documents/models.py`
- Create: `/home/khoipham/Projects/ravid-assignment/Ravid/apps/documents/migrations/0003_ingestion_dispatch_outbox.py`
- Create: `/home/khoipham/Projects/ravid-assignment/Ravid/apps/documents/dispatch.py`
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/apps/documents/tasks.py`
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/apps/documents/views.py`
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/apps/documents/recovery.py`
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/apps/documents/vector_store.py`
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/apps/documents/admin.py`
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/config/settings/base.py`
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/compose.yaml`
- Modify: project root environment template
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/tests/documents/test_models.py`
- Create: `/home/khoipham/Projects/ravid-assignment/Ravid/tests/documents/test_dispatch.py`
- Create: `/home/khoipham/Projects/ravid-assignment/Ravid/tests/documents/test_generation_cleanup.py`
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/tests/documents/test_api.py`
- Modify: `/home/khoipham/Projects/ravid-assignment/Ravid/tests/smoke/test_compose_contracts.py`

## Implementation Steps

1. Add failing transaction tests proving no durable dispatch intent survives current callback failure.
2. Add model, constraints, admin visibility, and migration. Never store raw exception strings.
3. Create outbox rows in upload, explicit retry, and stale-recovery transactions.
4. Implement leased selection, publish outside DB transaction, claim-token CAS, capped backoff,
   max attempts, `DEAD`, and explicit operator retry.
5. Remove broker I/O from upload request. Commit job+outbox and return `202` promptly.
6. Make admin operational records read-only: no add/delete/change; explicit view permission and
   redacted relations. Add authorization tests.
7. Implement bounded generation reconciliation from the manifest. Cleanup after a grace period
   greater than the old worker lifetime; exclude active and all live job generations; retry safely.
8. Register periodic publisher/recovery/cleanup and Compose Beat without LLM credentials.
9. Add PostgreSQL tests for unique intent, concurrent publishers, rollback, ambiguous duplicates,
   retry backoff, and correct generation payload.

## Tests Before

- Preserve upload row durability and callback timing from Phase 3.
- Failing test: committed job has no durable publish intent after callback failure.

## Tests After

- Rollback persists neither job nor outbox; commit persists both.
- Upload performs no synchronous broker call and leaves due outbox work.
- Two publishers cannot claim the same due row.
- Expired publisher claims recover; permanent errors reach `DEAD`; operator retry is explicit.
- Duplicate publish reaches an idempotent claim and does no duplicate vector work.
- Late stale-worker writes are removed by exact-manifest cleanup after the grace period.
- Beat/web/worker environments exclude unrelated secrets.

## Success Criteria

- [ ] Every retryable generation has exactly one durable dispatch intent and bounded attempts.
- [ ] Broker downtime cannot erase committed ingestion work.
- [ ] Periodic publisher drains due rows after broker recovery.
- [ ] Docs consistently say at-least-once, never exactly-once.

## Risk Assessment

Success marking can be ambiguous after broker acceptance. Duplicate delivery is expected and made
safe by fencing. Beat is convenient, not durable; PostgreSQL rows are the durability boundary.

## Security Considerations

Outbox payload contains only task, generation, and delivery UUIDs. No paths, usernames, content,
raw errors, or LLM credentials. Admin surfaces are view-only.
