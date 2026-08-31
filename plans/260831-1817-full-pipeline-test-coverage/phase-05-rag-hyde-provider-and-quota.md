---
phase: 5
title: "RAG HyDE Provider and Quota"
status: pending
priority: P1
dependencies: [1, 4]
---

# Phase 5: RAG HyDE Provider and Quota

## Overview

Kiểm thử standard RAG và HyDE xuyên real active-generation retrieval bằng deterministic provider,
đồng thời phủ provider faults, fallback, prompt bounds, quota/accounting và PostgreSQL races.

## Context Links

- [Phase 4](./phase-04-vector-retrieval-isolation-and-data-integrity.md)
- `docs/2026-08-30 R.A.V.I.D.md:152`, `:205`, `:236`
- `apps/rag/services.py:123`, `:241`, `:298`; `apps/accounts/entitlements.py:61`
- Privacy: `docs/system-architecture.md:139`; accounting limitation: `:166`.

## Requirements

- Functional: strict query/toggle, standard/HyDE/fallback/no-context, original final question plus
  real-only context, provider translation/timeouts/no retry, subscription/quota settlement/races.
- Non-functional: deterministic fake provider is merge gate; live OpenRouter opt-in synthetic-only;
  context/output bounded; no prompt/chunk/key logging.

## Architecture

L1 provider là injected adapter. L2 provider là OpenRouter-compatible network stub có shared ledger,
để HTTP qua Gunicorn vẫn deterministic; không mock retrieval. PostgreSQL active pairs + real Chroma
vẫn chạy. HyDE và final synthesis có reservation độc lập. Expected HyDE failure falls back once;
programming/config/accounting errors fail closed. Synthetic-only live lane chứng minh fixture hygiene,
không được mô tả như application-enforced consent vì API hiện không có consent field/policy gate.

## Related Code Files

| Action | Absolute path | Nội dung | Impact |
| --- | --- | --- | --- |
| Modify | `/home/khoipham/Projects/ravid-assignment/Ravid/tests/rag/test_api.py` | payload/error contract | chat API |
| Modify | `/home/khoipham/Projects/ravid-assignment/Ravid/tests/rag/test_services.py` | stages/fallback/quota | service |
| Modify | `/home/khoipham/Projects/ravid-assignment/Ravid/tests/accounts/test_entitlements_postgres.py` | quota races/day | account |
| Create | `/home/khoipham/Projects/ravid-assignment/Ravid/tests/pipeline/test_rag_real_retrieval.py` | real Chroma + fake provider | integration |
| Create | `/home/khoipham/Projects/ravid-assignment/Ravid/tests/live/test_openrouter_smoke.py` | opt-in synthetic | live |
| Read | `/home/khoipham/Projects/ravid-assignment/Ravid/apps/rag/services.py` | orchestration | oracle |

## Function / Interface Checklist

- [ ] `StrictUTF8CharField` / `StrictBooleanField` (`apps/rag/serializers.py:4`, `apps/rag/serializers.py:16`).
- [ ] `RagService` (`apps/rag/services.py:40`): standard, HyDE, final orchestration.
- [ ] `build_openrouter_chat_model` / `invoke_prompt_model` (`apps/rag/llm.py:30`, `apps/rag/llm.py:74`).
- [ ] `RagStageReservation` (`apps/rag/accounting.py:12`): one terminal attempt.
- [ ] reserve/refund/finalize (`apps/accounts/entitlements.py:61`, `apps/accounts/entitlements.py:93`, `apps/accounts/entitlements.py:100`).
- [ ] context bound (`apps/rag/prompts.py:52`) and provider normalization (`provider_responses.py:15`).

## Dependency Map

Phase 1 + Phase 4 -> Phase 5 -> Phase 6; quota PostgreSQL lane có thể chạy song song vector lane.

## Test Scenario Matrix

| ID | Pri | Layer | Precondition / input / fault | Expected oracle | Automation target |
| --- | --- | --- | --- | --- | --- |
| RAG-01 | P0 | L1 | standard query with active real chunks | original query retrieves; final sees bounded real chunks; correct metadata | integration |
| RAG-02 | P0 | L1 | no owner context | fixed no-context answer; zero provider/quota | integration |
| RAG-03 | P0 | L1 | HyDE success | hypothetical used only retrieval; original question final; mode hyde | integration |
| RAG-04 | P0 | L0/L1 | HyDE timeout/transport/empty/invalid/oversize | one standard fallback; safe reason; no provider retry | service |
| RAG-05 | P0 | L1 | HyDE fallback then final | only real owner chunks in context; hypothetical never evidence | ledger |
| RAG-06 | P0 | L0 | provider final transport before response | generic `503`; final reservation refunded | service |
| RAG-07 | P0 | L0 | provider returns usage invalid/content invalid | bounded settlement semantics; safe `503` if invalid answer | service |
| RAG-08 | P1 | L0 | missing key/paid model/timeout<=0/retries!=0 | `503` before provider dispatch | config |
| RAG-09 | P0 | L0 | inactive/no credits/HyDE then final insufficient | `403/429`; exact call count and quota delta | API/service |
| RAG-10 | P0 | L1 | concurrent reservations near limit | total never exceeds limit; one loser `429` | PG concurrency |
| RAG-11 | P1 | L1 | concurrent finalize/refund; UTC rollover | no negative/overcount; separate usage day | PG concurrency |
| RAG-12 | P1 | L0 | settlement called twice/accounting DB error | one terminal attempt; safe accounting error | accounting |
| RAG-13 | P1 | L0 | query empty/2000/2001, invalid UTF-8 surrogate, toggle types | strict `400`; no side effect | API matrix |
| RAG-14 | P1 | L1 | max context with long chunks | returned excerpts exactly equal final prompt order/bound | prompt oracle |
| RAG-15 | P2 | L3 | opt-in live free router + synthetic handbook | schema compatible, bounded timeout, no private data | live smoke |
| RAG-16 | P1 | L2 | crash after reserve/finalize ambiguity | limitation evidenced; conservative reservation retained | recovery note/test |
| RAG-17 | P0 | L2 | stub scripts success/timeout/invalid usage | exact network calls, prompt hash, quota delta; no egress | stub ledger |
| RAG-18 | P1 | L2/L3 | unapproved private document query | record operational-only consent gap; no false enforcement claim | privacy defect |

## Implementation Steps

1. Giữ service unit matrix, thêm missing provider/config/accounting edges và exact quota delta.
2. Nối real active Chroma retrieval với deterministic provider ledger cho standard/HyDE.
3. Test prompt inputs, returned chunks/order/bounds và hypothetical exclusion.
4. Chạy PostgreSQL reservation/finalize/refund races với barriers + frozen UTC date.
5. Tạo live marker cần explicit env opt-in; fail/skip reason rõ, synthetic fixture duy nhất.
6. Ghi crash-settlement ambiguity là residual risk, không tuyên bố exactly-once.

## Commands / Gates

```bash
uv run pytest tests/rag tests/accounts/test_entitlements.py -q
docker compose --profile test run --rm test pytest --ds=config.settings.production tests/accounts/test_entitlements_postgres.py tests/pipeline/test_rag_real_retrieval.py -q
RAVID_RUN_LIVE_PROVIDER=1 uv run pytest tests/live/test_openrouter_smoke.py -q
```

## Success Criteria

- [ ] Standard/HyDE/fallback với real retrieval đúng query/prompt/metadata/call counts.
- [ ] Owner chunks và hypothetical không thể lẫn vai trò evidence.
- [ ] Provider/config/quota faults đúng status và exact settlement delta.
- [ ] PostgreSQL concurrency/day rollover không vượt quota; live lane optional/private-safe.

## Risk Assessment

Live free router nondeterministic và rate limited nên chỉ assert transport/schema, không exact prose.
Crash accounting chưa có durable ledger: test ghi rõ conservative residual. Security: prompt injection
fixture phải được xem như data; provider call không log request/response, key hoặc retrieved chunks.
