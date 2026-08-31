---
phase: 7
title: "Security Performance Observability and Evidence"
status: pending
priority: P1
dependencies: [2, 3, 4, 5, 6]
---

# Phase 7: Security Performance Observability and Evidence

## Overview

Hoàn tất security/privacy abuse cases, performance/resource budgets, observability assertions và
evidence report để xác nhận plan bao phủ contract lẫn residual limitations.

## Context Links

- [Acceptance](./plan.md#acceptance-criteria)
- `docs/system-architecture.md:133`, `:159`; `config/settings/base.py:235`
- [Inventory](./research/codebase-pipeline-inventory.md)
- Gates: `Makefile:6`, `:9`, `:15`, `:18`.

## Requirements

- Functional: authz/privacy/prompt-injection/resource-abuse; structured event correlation;
  latency/load/resource budgets; traceability và redacted evidence.
- Non-functional: đo baseline trước threshold; không secret/private payload trong reports;
  external/flaky skip phải có reason, owner và rerun command.

## Architecture

Security matrix reuse L0-L2 với hostile metadata/query/filename, không pentest external provider.
Performance tách cold/warm, ingestion/chat/concurrency theo cùng machine class. Capture safe IDs,
state/code/timestamp; không capture chunk, prompt, JWT hay key. Report map requirement/edge ID tới
result/evidence.

## Related Code Files

| Action | Absolute path | Nội dung | Impact |
| --- | --- | --- | --- |
| Create | `/home/khoipham/Projects/ravid-assignment/Ravid/tests/security/test_pipeline_abuse.py` | abuse/isolation | security |
| Create | `/home/khoipham/Projects/ravid-assignment/Ravid/tests/performance/test_pipeline_budgets.py` | timing/resource | perf |
| Create | `/home/khoipham/Projects/ravid-assignment/Ravid/tests/observability/test_pipeline_events.py` | events/redaction | ops |
| Create | `/home/khoipham/Projects/ravid-assignment/Ravid/plans/260831-1817-full-pipeline-test-coverage/reports/final-test-evidence.md` | results | handoff |
| Modify | `/home/khoipham/Projects/ravid-assignment/Ravid/Makefile` | aggregate gates | CI |
| Read | `/home/khoipham/Projects/ravid-assignment/Ravid/config/settings/base.py` | limits/logs | oracle |

## Function / Interface Checklist

- [ ] JWT policy (`config/settings/base.py:100`) và public exceptions (`config/urls.py:13`).
- [ ] path sanitization (`apps/documents/models.py:9`) và safe error (`apps/documents/tasks.py:17`).
- [ ] vector fail closed (`apps/documents/vector_store.py:43`, `apps/documents/vector_store.py:273`).
- [ ] context bound (`apps/rag/prompts.py:52`) và strict query (`apps/rag/serializers.py:4`).
- [ ] provider free/no-retry validation (`apps/rag/llm.py:13`, `apps/rag/llm.py:30`).
- [ ] structured logging (`config/settings/base.py:235`).

## Dependency Map

Phase 2-6 -> Phase 7 audit/report. Complete chỉ khi mọi P0 pass; P1 skip phải justified; P2 defer
phải có owner/date.

## Test Scenario Matrix

| ID | Pri | Layer | Precondition / input / fault | Expected oracle | Automation target |
| --- | --- | --- | --- | --- | --- |
| SEC-01 | P0 | L0-L2 | owner B accesses owner A status/vector/chat | same not-found/no-context; zero leak | abuse |
| SEC-02 | P0 | L1 | forged metadata + prompt injection chunk | rejected hoặc treated as data; no escalation | abuse |
| SEC-03 | P1 | L0 | traversal/control/long filename | safe path; no header/log injection | upload |
| SEC-04 | P1 | L0 | error embeds secret/path/provider body | safe API + redacted structured log | log test |
| SEC-05 | P1 | L2 | oversized/rapid upload-query-poll | bounds hold; web/worker stay healthy | load |
| SEC-06 | P0 | L2/L3 | key/JWT/private canary | absent non-web env/log/report; live synthetic-only | privacy |
| SEC-07 | P1 | L2 | Flower/db/redis/chroma reachability | infra internal; Flower loopback/auth | network |
| PERF-01 | P1 | L4 | cold/warm MD/PDF ingestion | p50/p95/stages recorded; no growth | benchmark |
| PERF-02 | P1 | L4 | concurrent uploads at worker limit | bounded queue; no lost/double activation | load |
| PERF-03 | P1 | L4 | standard/HyDE/no-context | latency/call/quota profile matches mode | benchmark |
| PERF-04 | P2 | L4 | repeated retrieval/cache | stable memory/connections; cache <= 8 | soak |
| OBS-01 | P0 | L0-L2 | success/fail/retry/recovery | reconstruct via safe IDs/codes/time | log assertion |
| OBS-02 | P1 | L2 | dependency outage | actionable service/stage/code, no payload | log assertion |
| EVD-01 | P0 | all | aggregate gates | command/SHA/runtime/result mapped to IDs | report |
| EVD-02 | P0 | all | exactly-once/MIME/AV/quota crash limits | explicit non-claims/risk disposition | report |

## Implementation Steps

1. Thêm cross-owner, hostile metadata, prompt/file/log injection tests.
2. Assert network/secret placement và redaction bằng canaries.
3. Record cold/warm baseline; chốt budgets theo environment rồi enforce.
4. Chạy bounded concurrency/soak; collect CPU/RSS/queue/stage durations.
5. Assert events đủ reconstruct transition mà không log content.
6. Chạy gates, tạo evidence/traceability; red-team missing IDs và overclaims.

## Commands / Gates

```bash
uv run ruff check apps config tests
uv run python manage.py check --settings=config.settings.test
uv run python manage.py makemigrations --check --dry-run --settings=config.settings.test
uv run pytest -q
uv run pytest --cov=apps --cov=config --cov-branch --cov-report=term-missing
make test-pipeline
make test-pipeline-security
make test-pipeline-performance
```

## Success Criteria

- [ ] All P0 pass; mỗi skip có exact reason + rerun.
- [ ] Cross-owner/metadata/prompt/error paths không leak data/secrets.
- [ ] Cold/warm baseline reproducible; load không mất job/double activate.
- [ ] Evidence map 100% IDs và nêu residual/non-goals.

## Risk Assessment

Global percent có thể che branch nguy hiểm: dùng branch report + scenario P0; threshold chỉ sau
baseline. Performance nhiễu: classify machine, warmup, repetitions, tolerance. Evidence là
exfiltration surface: allowlist fields, scan canary/secrets, không attach raw API logs.
