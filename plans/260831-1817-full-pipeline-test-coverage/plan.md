---
title: "RAVID Full Pipeline Test Coverage"
description: "Kịch bản kiểm thử toàn pipeline RAVID từ JWT, upload, outbox/Celery, ingestion/Chroma đến RAG/HyDE, quota và Docker recovery."
status: pending
priority: P1
branch: "feat/harden-docker-reviewer-stack"
tags: [test, backend, api, auth, database, infra, critical]
blockedBy: []
blocks: []
created: "2026-08-31T11:21:16.402Z"
createdBy: "ck:plan"
source: skill
---

# RAVID Full Pipeline Test Coverage

## Overview

Xây dựng bộ kiểm thử nhiều lớp để chứng minh pipeline thật, không chỉ từng module bị mock: JWT ->
multipart upload -> PostgreSQL outbox -> Redis/Celery -> extract/chunk/embed/Chroma -> activation ->
status -> owner-scoped retrieval -> standard RAG/HyDE -> provider/quota. Kế hoạch ưu tiên invariant
và fault injection. Test harness không thay đổi public contract; finding đòi hỏi product fix hoặc
instrumentation phải tạo defect/plan riêng, không được âm thầm sửa behavior để làm test xanh.

Baseline 2026-08-31: `274 passed, 3 skipped`; SQLite/eager Celery là lane nhanh, chưa thay thế
PostgreSQL/Redis/Chroma/worker thật. Hai gate production đang skip gồm concurrency quota và Chroma.

## Scope

**In scope**

- Contract/API, auth, file validation/extraction limits, transaction rollback và orphan media.
- Outbox lease/CAS, at-least-once delivery, worker crash/race, generation activation/recovery/cleanup.
- Owner isolation, active-generation vector integrity, standard RAG, HyDE/fallback, quota/accounting.
- Docker fresh/restart/degraded dependency, opt-in live provider bằng dữ liệu synthetic.
- Security, privacy, performance budget, structured logs/metrics và evidence artifact.
- Test-topology contract: process lifetime, Compose-local provider stub, collection/port/timing
  isolation, resource ownership và cleanup sau interrupted run.

**Out of scope**

- Thay đổi API/public behavior, billing/payment, antivirus/MIME hardening, durable quota ledger.
- Exactly-once distributed transaction giữa PostgreSQL, Redis, Chroma và OpenRouter.
- Dùng tài liệu private/assignment PDF làm payload gửi live provider.
- Tuyên bố automatic retry cho terminal ingestion `FAILURE`, distributed rate limiting,
  application-enforced provider consent hoặc lifecycle metrics khi code hiện tại chưa có.

## Coverage Lanes

| Lane | Runtime | Mục tiêu | Merge gate |
| --- | --- | --- | --- |
| L0 | SQLite + eager Celery + fakes | contract, branch, deterministic fault | Mỗi PR |
| L1 | PostgreSQL + real Chroma | locking, native filters, generation integrity | Mỗi PR nếu Docker khả dụng |
| L2 | Full Compose + Redis/Celery/Beat | runnable E2E, restart/degradation | Trước release/submission |
| L3 | Opt-in OpenRouter | provider compatibility, synthetic-only privacy | Thủ công, không bắt buộc CI |
| L4 | k6/pytest benchmark + log capture | latency, throughput, resource/telemetry | Nightly/release evidence |

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Coverage Model Fixtures and Oracles](./phase-01-coverage-model-fixtures-and-oracles.md) | Pending |
| 2 | [API Auth Upload and Status Contracts](./phase-02-api-auth-upload-and-status-contracts.md) | Pending |
| 3 | [Durable Ingestion and Failure Injection](./phase-03-durable-ingestion-and-failure-injection.md) | Pending |
| 4 | [Vector Retrieval Isolation and Data Integrity](./phase-04-vector-retrieval-isolation-and-data-integrity.md) | Pending |
| 5 | [RAG HyDE Provider and Quota](./phase-05-rag-hyde-provider-and-quota.md) | Pending |
| 6 | [Runnable Compose End to End and Recovery](./phase-06-runnable-compose-end-to-end-and-recovery.md) | Pending |
| 7 | [Security Performance Observability and Evidence](./phase-07-security-performance-observability-and-evidence.md) | Pending |

## Dependencies

- Phối hợp, không blocking: `plans/260830-1608-part-1-endpoint-smoke-tests/` có thể tạo fixture,
  script host và Chroma verifier dùng lại. Khi triển khai sau phải merge ý tưởng, không tạo hai flow
  reviewer cạnh tranh và không ghi đè `Makefile`/`README.md`.
- Nền tảng hiện hữu: `plans/260831-1306-harden-docker-reviewer-stack/` và
  `plans/260831-1310-harden-ingestion-durability/`; plan này xác minh behavior, không thiết kế lại.
- Phase 1 là nền chung; Phase 2-5 có thể chạy song song sau Phase 1; Phase 6 phụ thuộc 2-5; Phase 7
  tổng hợp evidence sau toàn bộ lane.

## End-to-End Flow

```text
JWT -> POST upload (202) -> atomic Document/Job/Dispatch + media
    -> Beat claims outbox -> Redis -> Celery claims generation
    -> extract -> split -> embed -> Chroma write/readback
    -> PostgreSQL activates generation -> GET status SUCCESS
    -> owner-scoped active pairs -> Chroma retrieve
    -> standard query OR HyDE query/fallback -> bounded real context
    -> reserve/finalize/refund quota -> safe API response + metadata
```

Mỗi fault point phải có oracle ở cả ba mặt: HTTP contract, PostgreSQL authoritative state và
external side effect (media/Redis/Chroma/provider call count). Polling dùng deadline hữu hạn, không
`sleep` mù; mọi test tạo namespace/user/document riêng và cleanup idempotent.

L0/L1 chỉ chứng minh component integration trong process pytest; chỉ L2 được gọi là real
Redis/Celery/HTTP pipeline. L2 dùng OpenRouter-compatible stub service có ledger qua network, không
dùng monkeypatch. Expected current limitations được ghi `observed-residual`, không biến thành pass
cho một guarantee chưa tồn tại.

## Acceptance Criteria

- [ ] Một synthetic MD đi xuyên JWT đến `SUCCESS`, verified active Chroma chunks và standard chat trả fact đúng.
- [ ] PDF/TXT/MD thật cùng toàn bộ boundary/corrupt/empty/encoding/limit cases có terminal oracle rõ.
- [ ] Rollback không để DB/media orphan; reconciliation chỉ xóa orphan quá grace period.
- [ ] PostgreSQL chứng minh outbox CAS/concurrency, duplicate delivery và stale generation fail closed.
- [ ] Hai owner/two generation không thể đọc chéo; stale/legacy/forged metadata không rời vector boundary.
- [ ] Standard/HyDE/fallback/no-context/provider faults đúng prompt, metadata, call count và quota delta.
- [ ] Full Compose chạy từ empty volumes, restart được, và dependency outage phục hồi không mất intent.
- [ ] Chroma retrieval outage phục hồi bằng request sau; Chroma write outage kết thúc `FAILURE` an
  toàn và yêu cầu re-upload/reindex thủ công theo contract hiện tại.
- [ ] Live provider chỉ opt-in, synthetic-only, không log prompt/chunks/key và không là merge gate.
- [ ] Báo cáo cuối ghi command, duration, pass/fail/skip reason, logs đã redacted và residual risks.
- [ ] Default credentials, auth throttling, private-data consent, parser isolation/backpressure,
  WRITING-generation leak và lifecycle telemetry đều có test/evidence hoặc defect disposition rõ.

## Open Questions

None. Quyết định mặc định: Compose-local OpenRouter stub; recovery profile <= 120 giây; per-run
Chroma collection và dynamic host ports; observability gate chỉ assert state/current logs. Mọi
limitation cần product change được ghi residual + defect, không âm thầm đổi semantics.

## Red Team Review

### Session - 2026-08-31

**Findings:** 15 accepted after deduplication (2 Critical, 10 High, 3 Medium).

| # | Finding | Severity | Disposition | Applied To |
| --- | --- | --- | --- | --- |
| 1 | Missing cross-process deterministic provider | Critical | Accept | Phases 1, 5, 6 |
| 2 | Chroma write failure is terminal, not recoverable | Critical | Accept | Phases 3, 6 |
| 3 | Worker recovery timing is not runnable | High | Accept | Phases 1, 6 |
| 4 | Max-attempt WRITING generation may leak | High | Accept | Phases 3, 7 |
| 5 | L1 Chroma collection is not isolated | High | Accept | Phases 1, 4, 6 |
| 6 | Fixed host ports defeat Compose isolation | High | Accept | Phases 1, 6 |
| 7 | Pytest-local failpoints cannot control Celery | High | Accept | Phases 1, 3, 6 |
| 8 | Missing product-remediation disposition | High | Accept | All phases |
| 9 | Default credentials are accepted | High | Accept | Phases 6, 7 |
| 10 | Auth throttling/revocation absent | High | Accept | Phase 7 |
| 11 | Parser DoS/backpressure is not guaranteed | High | Accept | Phase 7 |
| 12 | Provider privacy approval is operational only | High | Accept | Phases 5, 7 |
| 13 | Observability/event claims exceed current code | High | Accept | Phase 7 |
| 14 | Prompt-injection oracle is non-mechanical | Medium | Accept | Phase 7 |
| 15 | L1/L2 and per-process cache claims were blurred | Medium | Accept | Phases 4, 7 |

### Whole-Plan Consistency Sweep

- Files reread: `plan.md` and all seven phase files.
- Decision deltas checked: 15.
- Reconciled stale references: recovery, provider, failpoint, isolation, queue, cache, privacy,
  security and observability claims.
- Unresolved contradictions: 0.
