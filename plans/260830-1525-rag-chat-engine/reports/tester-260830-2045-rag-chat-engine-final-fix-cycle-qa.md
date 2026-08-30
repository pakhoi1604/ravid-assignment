---
title: "RAG Chat Engine Final Fix-Cycle QA"
date: "2026-08-30"
agent: tester
scope: "plans/260830-1525-rag-chat-engine"
status: passed
follow_up_to:
  - "adversarial-re-review-260830-2034-rag-chat-engine.md"
  - "code-re-review-260830-2036-rag-chat-engine-production-readiness.md"
---

# Test Report — 2026-08-30 — RAG Chat Engine Final Fix-Cycle QA

## Summary

**PASS.** Exact SDK retry-policy and vector exception-boundary regressions, the full local suite,
fresh runtime/test image builds, runtime dependency checks, real PostgreSQL/Chroma invariants, and
the rebuilt full-stack smoke gate all passed. No dotenv file, credential, JWT, or expanded Compose
configuration was inspected or printed. No live OpenRouter request ran.

## Test Results Overview

| Scope | Passed | Failed | Skipped | Pytest duration |
| --- | ---: | ---: | ---: | ---: |
| Final SDK/vector regressions | 27 | 0 | 0 | 0.50s |
| Full local suite | 144 | 0 | 2 | 4.16s |
| PostgreSQL entitlement race | 1 | 0 | 0 | 0.84s |
| Real Chroma owner isolation | 1 | 0 | 0 | 1.61s |

The two local skips were the backend-specific PostgreSQL and Chroma tests. Both passed separately
inside the freshly rebuilt profile-gated test image.

## Findings

### Exact Final Regressions

Targeted command:

```text
pytest tests/rag/test_llm.py tests/documents/test_vector_retrieval.py
```

Result: `27 passed in 0.50s`.

- Actual `build_openrouter_chat_model()` construction passed without network I/O. Its locked SDK
  configuration reported `timeout_ms == 10000` and `retry_config is None`.
- A nonzero configured provider retry count failed closed with `RagConfigurationError`.
- An unrelated embedding-constructor `ValueError("implementation defect")` propagated and was not
  translated into a normal retrieval outage.
- The locked Chroma connection `ValueError`, Chroma collection `httpx.ConnectError`, embedding
  cache `OSError`, `ChromaError`, and transport failures remained mapped to the safe retrieval
  domain error.
- Resource-cache reuse, owner-derived retriever filters, free-model validation, and narrow provider
  response translation remained green in the same targeted files.

### Full Regression Suite

- Collected: 146.
- Result: `144 passed, 2 skipped in 4.16s`.
- Failures: none.
- Full-suite wall time including runner startup: 5.96s.

### Fresh Image and Runtime Verification

- `docker compose build web`: passed; runtime image rebuilt from current source.
- `docker compose --profile test build test`: passed; test image rebuilt from current source.
- Runtime imports passed for `ChatOpenRouter`, `Document`, `ChatPromptTemplate`, and
  `BaseRetriever`.
- Runtime image confirmed pytest is absent.
- Runtime construction with an explicit synthetic test key reverified the actual SDK
  `timeout_ms=10000` and `retry_config=None`; it performed no provider request.

Docker Compose emitted the existing buildx-missing warning and successfully used the classic
builder for both images.

### Docker Invariants and Rebuilt Full Stack

- PostgreSQL and Chroma reached healthy state before backend-specific tests.
- Real PostgreSQL quota race: `1 passed in 0.84s`; simultaneous reservations did not overspend.
- Real Chroma owner isolation: `1 passed in 1.61s`; cross-owner chunks were excluded.
- Web, Celery, and Flower were force-recreated from the freshly rebuilt runtime image.
- Web, Celery, Flower, PostgreSQL, Redis, and Chroma all reached healthy state.
- `make smoke`: passed in 2.58s wall time for health, schema, docs, database readiness, Redis,
  Chroma, Celery, and Flower.
- Healthy reviewer services remain running; no volumes or user data were removed.

## Coverage Metrics

Coverage percentages were not collected because the accepted plan specifies no threshold or
required coverage command. No failure was suppressed.

## Critical Issues

None found by final fix-cycle QA.

## Recommendations

1. Proceed to final independent code/adversarial re-review using this fresh evidence.
2. Low priority: install Docker buildx to remove the classic-builder warning.
3. Keep live OpenRouter verification conditional on a rotated reviewer key and explicit network
   authorization.

## Unresolved Questions

- Credentialed free-router response/usage behavior remains intentionally outside offline QA.
