---
phase: 6
title: "Runnable Compose End to End and Recovery"
status: pending
priority: P1
dependencies: [2, 3, 4, 5]
---

# Phase 6: Runnable Compose End to End and Recovery

## Overview

Tạo runnable full-Compose suite từ empty volumes, chạy JWT -> upload -> worker/Chroma -> status ->
chat, sau đó kiểm restart và dependency-degraded recovery với process thật.

## Context Links

- [Plan flow](./plan.md#end-to-end-flow)
- `README.md:10`, `Makefile:41`, `compose.yaml:1`
- `config/settings/base.py:121`, `:132`; static tests: `tests/smoke/test_compose_contracts.py:8`.

## Requirements

- Functional: fresh image/start/migrate/seed idempotent; readiness; standard E2E; Redis, Celery,
  Beat, Chroma, web và DB restart/outage; persisted DB/media/vector verification.
- Non-functional: one-command, bounded deadline, cleanup; không xóa volume ngoài isolated project;
  deterministic provider mặc định.

## Architecture

Host runner tạo unique Compose project/volumes/ports, chờ health rồi seed. API driver không exec
business code; DB/Chroma inspection chỉ làm postcondition. Fault controller stop/kill/pause từng
service và luôn restore. Deterministic provider chỉ gắn web; live provider không thuộc merge gate.

## Related Code Files

| Action | Absolute path | Nội dung | Impact |
| --- | --- | --- | --- |
| Create | `/home/khoipham/Projects/ravid-assignment/Ravid/tests/e2e/test_full_pipeline.py` | HTTP flow | E2E |
| Create | `/home/khoipham/Projects/ravid-assignment/Ravid/tests/e2e/test_compose_recovery.py` | outages | resilience |
| Create | `/home/khoipham/Projects/ravid-assignment/Ravid/scripts/test-full-pipeline.sh` | isolated runner | CI |
| Modify | `/home/khoipham/Projects/ravid-assignment/Ravid/compose.yaml` | test profile if needed | topology |
| Modify | `/home/khoipham/Projects/ravid-assignment/Ravid/Makefile` | pipeline targets | commands |
| Modify | `/home/khoipham/Projects/ravid-assignment/Ravid/README.md` | gates | reviewer |

## Function / Interface Checklist

- [ ] public/JWT routes (`config/urls.py:7`): health/schema/docs/auth.
- [ ] Beat schedules (`config/settings/base.py:132`): publish/recovery cadence.
- [ ] upload/status (`apps/documents/views.py:42`, `apps/documents/views.py:92`): HTTP truth.
- [ ] publish/recovery tasks (`apps/documents/tasks.py:226`, `apps/documents/tasks.py:239`).
- [ ] chat endpoint (`apps/rag/views.py:23`): retrieval/provider/quota response.
- [ ] health checks (`compose.yaml:76`, `compose.yaml:156`, `compose.yaml:204`, `compose.yaml:212`, `compose.yaml:225`).

## Dependency Map

Phase 2-5 -> Phase 6 -> Phase 7. Phối hợp `260830-1608-part-1-endpoint-smoke-tests`: một canonical
command, reuse fixture/verifier, không duplicate flow.

## Test Scenario Matrix

| ID | Pri | Layer | Precondition / input / fault | Expected oracle | Automation target |
| --- | --- | --- | --- | --- | --- |
| E2E-01 | P0 | L2 | empty isolated volumes, image + up | migration và all healthchecks succeed | runner |
| E2E-02 | P0 | L2 | seed twice | idempotent accounts/subscriptions; no privilege drift | runner |
| E2E-03 | P0 | L2 | JWT + synthetic MD upload | `202`; outbox commits; status SUCCESS | E2E |
| E2E-04 | P0 | L2 | inspect success | media + active manifest + verified chunks | verifier |
| E2E-05 | P0 | L2 | standard known-fact chat | owner chunks, correct fact, exact quota | E2E |
| E2E-06 | P0 | L2 | owner B queries owner A fact | no-context; zero leaked excerpt | isolation |
| E2E-07 | P0 | L2 | Redis down at upload/publish | intent PENDING; restore reaches terminal | recovery |
| E2E-08 | P0 | L2 | kill worker PROCESSING | no false success; recovery; old gen invisible | recovery |
| E2E-09 | P1 | L2 | Beat stop/restart | outbox waits then effectively publishes once | recovery |
| E2E-10 | P0 | L2 | Chroma down at write/retrieve | safe failure/503; no activate/leak; recoverable | degrade |
| E2E-11 | P1 | L2 | restart each service | DB/media/vector persist; health returns | restart |
| E2E-12 | P1 | L2 | DB unavailable | API fails safely; no phantom success | degrade |
| E2E-13 | P1 | L2 | corrupt PDF/TXT/MD subset | terminal FAILURE; worker stays healthy | negative |
| E2E-14 | P1 | L2 | schema/docs/Flower/internal ports | intended public only; Flower loopback/auth | smoke |
| E2E-15 | P1 | L2 | rerun after interrupted run | isolated cleanup; no stale collision | idempotency |

## Implementation Steps

1. Tạo isolated project name/volumes và trap cleanup có target validation.
2. Start empty state; health deadline + diagnostics on failure.
3. Chạy JWT/upload/poll/vector/chat/two-owner flow.
4. Fault từng service; restore và assert eventual authoritative state.
5. Verify migration/seed/restart idempotency và persistence.
6. Nối Make/README, reuse Part 1 artifacts nếu đã có.

## Commands / Gates

```bash
docker compose config --quiet
make test-pipeline
make test-pipeline-recovery
docker compose ps
```

## Success Criteria

- [ ] Fresh isolated stack hoàn tất P0 E2E trong deadline.
- [ ] Outages không mất durable intent hoặc expose partial data.
- [ ] Restart giữ DB/media/vector; seed/migration idempotent.
- [ ] Diagnostics không chứa token/key/chunks.

## Risk Assessment

Fault tests có thể đụng developer stack: unique project, validate resolved target, không `down -v`
default project. Model cold-start: cache riêng, ghi cold/warm duration. Security: synthetic-only,
redact curl/JWT/env/logs.
