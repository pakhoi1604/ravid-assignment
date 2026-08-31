---
phase: 3
title: "Durable Ingestion and Failure Injection"
status: pending
priority: P1
dependencies: [1]
---

# Phase 3: Durable Ingestion and Failure Injection

## Overview

Chứng minh ingestion durability trên PostgreSQL/Redis/Celery: outbox lease/CAS, at-least-once
duplicate, worker claim/crash, generation fencing, activation, recovery, cleanup và orphan.

## Context Links

- [Inventory](./research/codebase-pipeline-inventory.md)
- `docs/system-architecture.md:51`, `docs/system-architecture.md:66`
- `apps/documents/dispatch.py:38`, `apps/documents/tasks.py:32`, `apps/documents/recovery.py:15`

## Requirements

- Functional: retry/backoff/dead, publisher race, stale CAS, duplicate delivery, stage crashes,
  stale recovery rotation, safe cleanup/reconciliation.
- Non-functional: PostgreSQL cho locking; bounded waits; no wall-clock race; activation/status
  effectively once per generation dù delivery at-least-once.

## Architecture

L0 bao phủ state branches; L1 dùng independent DB connections/barriers cho locks/CAS và precise
in-process failpoints. L2 kill broker/worker chỉ sau khi DB oracle xác nhận transition quan sát được;
không claim chính xác instruction boundary trong Celery child. Recovery rotate generation trước
redispatch; terminal `FAILURE` không được recovery tự động.

## Related Code Files

| Action | Absolute path | Nội dung | Impact |
| --- | --- | --- | --- |
| Modify | `/home/khoipham/Projects/ravid-assignment/Ravid/tests/documents/test_dispatch.py` | errors/CAS | outbox |
| Create | `/home/khoipham/Projects/ravid-assignment/Ravid/tests/documents/test_dispatch_postgres.py` | races | DB |
| Modify | `/home/khoipham/Projects/ravid-assignment/Ravid/tests/documents/test_tasks.py` | duplicate/stale/crash | worker |
| Modify | `/home/khoipham/Projects/ravid-assignment/Ravid/tests/documents/test_recovery.py` | recovery/cleanup | ops |
| Modify | `/home/khoipham/Projects/ravid-assignment/Ravid/tests/documents/test_orphan_uploads.py` | grace/race | media |
| Create | `/home/khoipham/Projects/ravid-assignment/Ravid/tests/pipeline/test_ingestion_faults.py` | stage faults | pipeline |

## Function / Interface Checklist

- [ ] `claim_due_dispatches` (`apps/documents/dispatch.py:38`): due order, skip lock, lease.
- [ ] `publish_due_dispatches` (`apps/documents/dispatch.py:67`): broker error + token CAS.
- [ ] `reset_expired_dispatch_claims` (`apps/documents/dispatch.py:110`): pending/dead.
- [ ] `_claim_pending_job` (`apps/documents/tasks.py:32`): PENDING+generation.
- [ ] `_finalize_success` (`apps/documents/tasks.py:72`): atomic activation.
- [ ] `_finalize_failure` (`apps/documents/tasks.py:130`): sanitized/current-only.
- [ ] `recover_stale_ingestion_jobs` (`apps/documents/recovery.py:15`) và cleanup (`apps/documents/recovery.py:100`).

## Dependency Map

Phase 1 -> Phase 3; Phase 4 dùng chung generation oracle; Phase 6 chạy process kills.

## Test Scenario Matrix

| ID | Pri | Layer | Precondition / input / fault | Expected oracle | Automation target |
| --- | --- | --- | --- | --- | --- |
| DUR-01 | P0 | L1 | two publishers, one due row | exactly one claim/attempt; other skips | PG concurrency |
| DUR-02 | P0 | L0 | broker fail attempts below/at max | PENDING+backoff / DEAD; stable code | dispatch |
| DUR-03 | P0 | L1 | expired claim, newer claim, stale completion | old CAS updates zero; new state preserved | CAS |
| DUR-04 | P0 | L1/L2 | publish succeeds, DB mark crashes | duplicate allowed; one activation | fault integration |
| DUR-05 | P0 | L1 | simultaneous duplicate deliveries | one claim; pipeline once | worker race |
| DUR-06 | P0 | L0 | malformed/unknown/success/stale task | ignored; no mutation | task matrix |
| DUR-07 | P0 | L1 | recovery rotates while old worker writes | new current; old STALE/invisible | race |
| DUR-08 | P0 | L1 | crash after manifest/write/readback/pre-activation | no false SUCCESS; old active visible | stage faults |
| DUR-09 | P0 | L1 | partial write/readback mismatch | failure; partial never activates | vector fault |
| DUR-10 | P1 | L1 | stale/fresh jobs + dry-run | only eligible rotate; dry-run immutable | recovery |
| DUR-11 | P0 | L1 | max attempts after partial WRITING vector | FAILURE, no redispatch; raw leak measured + operator defect | recovery |
| DUR-12 | P0 | L1 | STALE due vs ACTIVE/live/current | delete exact safe stale only | cleanup |
| DUR-13 | P1 | L1 | cleanup error/retry/exhaustion | bounded attempts; manifest remains | cleanup |
| DUR-14 | P1 | L1 | old/new/referenced orphan + concurrent upload | delete only old unreferenced | orphan |
| DUR-15 | P0 | L0 | exception contains path/secret | client gets generic sanitized error | privacy |
| DUR-16 | P0 | L1/L2 | Chroma write/readback exception | terminal FAILURE; no activation; re-upload/reindex required | current contract |

## Implementation Steps

1. Bổ sung L0 transitions với frozen time và exact call counts.
2. Dùng separate PostgreSQL connections + barriers, không `sleep` để tạo race.
3. Inject precise faults quanh publish/claim/write/verify/activate/cleanup ở L0/L1; L2 dùng
   externally observable dependency outage hoặc process kill.
4. Assert previous active remains visible đến activation; failure không clear nó.
5. Bao phủ max recovery sau partial write: ghi nhận `WRITING` manifest hiện không vào cleanup query,
   mở defect/operator procedure thay vì tuyên bố leak được dọn tự động.
6. Reuse invariant IDs ở Phase 6 process-kill tests.

## Commands / Gates

```bash
uv run pytest tests/documents/test_dispatch.py tests/documents/test_tasks.py tests/documents/test_recovery.py -q
docker compose --profile test run --rm test pytest --ds=config.settings.production tests/documents/test_dispatch_postgres.py tests/pipeline/test_ingestion_faults.py -q
```

## Success Criteria

- [ ] Concurrent publishers/workers không double claim/activate.
- [ ] Mỗi crash có state auditable; chỉ PENDING/expired PROCESSING được gọi recoverable.
- [ ] Stale/partial generation invisible; cleanup không đụng active/live.
- [ ] Terminal Chroma failure và max-attempt WRITING leak có manual remediation/residual rõ.

## Risk Assessment

Thread test dễ dùng chung Django connection: mở/đóng per thread và barriers rõ. Kill tests phải có
namespace + teardown idempotent. Security: internal failure code chỉ trong DB/redacted log; client
không nhận traceback/path/credential.
