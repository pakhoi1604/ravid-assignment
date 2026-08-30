---
title: "RAG Chat Engine Post-Review QA"
date: "2026-08-30"
agent: tester
scope: "plans/260830-1525-rag-chat-engine"
status: passed
follow_up_to:
  - "adversarial-260830-2015-rag-chat-engine.md"
  - "code-review-260830-2017-rag-chat-engine-production-readiness.md"
---

# Test Report — 2026-08-30 — RAG Chat Engine Post-Review QA

## Summary

**PASS.** All requested post-review regression, full-suite, rebuild, runtime, Docker integration,
and full-stack smoke gates passed. The tests now cover the reported store-construction/cache,
OpenRouter availability-policy, strict query-input, and quota-timestamp gaps. No dotenv file,
secret, JWT, or expanded Compose configuration was inspected or printed. No live OpenRouter call
ran.

## Test Results Overview

| Scope | Passed | Failed | Skipped | Pytest duration |
| --- | ---: | ---: | ---: | ---: |
| Targeted post-review regressions | 57 | 0 | 0 | 0.84s |
| Full local suite | 143 | 0 | 2 | 3.84s |
| PostgreSQL entitlement race | 1 | 0 | 0 | 0.83s |
| Real Chroma owner isolation | 1 | 0 | 0 | 1.69s |

The two local skips were exactly the backend-specific PostgreSQL and Chroma tests. Both passed in
the rebuilt profile-gated Docker test image.

## Findings

### Review Regression Coverage

- Vector construction error translation: passed for Chroma collection transport failure and
  embedding-cache `OSError`; unrelated programming errors remain unsuppressed.
- Process-local vector resource reuse: passed; repeated stores with the same configuration built
  one client, one embedding object, and one Chroma store.
- OpenRouter availability policy: passed; configured timeout was forwarded and retry count was
  explicitly zero. Free-model validation and narrow provider exception translation also passed.
- Strict API input: passed for integer, float, boolean, list, object, null, and unpaired-surrogate
  input; each returned HTTP 400.
- Quota audit timestamp: passed; refund mutation advanced `DailyTokenUsage.updated_at` to the
  controlled future timestamp.

Targeted command:

```text
pytest tests/documents/test_vector_retrieval.py tests/rag/test_llm.py \
  tests/rag/test_api.py tests/accounts/test_entitlements.py
```

Result: `57 passed in 0.84s`.

### Full Regression Suite

- Collected: 145.
- Result: `143 passed, 2 skipped in 3.84s`.
- Failures: none.
- Full-suite wall time including runner startup: 5.83s.

### Rebuilt Image and Runtime Gates

- `docker compose build web`: passed; `ravid-app:local` rebuilt from current source and lock.
- `docker compose --profile test build test`: passed; `ravid-app:test` rebuilt from current source
  and lock.
- Rebuilt runtime imports passed for `ChatOpenRouter`, `Document`, `ChatPromptTemplate`, and
  `BaseRetriever`.
- Rebuilt runtime image confirmed pytest is absent.
- Build logs resolved CPU-only `torch==2.13.0+cpu`, `langchain-core==1.6.1`, and
  `langchain-openrouter==0.2.8`.

Docker Compose again warned that buildx is unavailable and used the classic builder. Both rebuilds
completed successfully; the warning is local-tooling-only.

### Docker Invariants and Full-Stack Smoke

- PostgreSQL and Chroma reached healthy state before test execution.
- Real PostgreSQL concurrency invariant: `1 passed in 0.83s`; simultaneous reservations did not
  overspend quota.
- Real Chroma owner-isolation invariant: `1 passed in 1.69s`; cross-owner documents were excluded.
- Web, Celery, and Flower were force-recreated against the rebuilt runtime image; PostgreSQL,
  Redis, and Chroma remained healthy.
- `make smoke`: passed in 2.44s wall time for health, schema, docs, PostgreSQL readiness, Redis,
  Chroma, Celery, and Flower.
- Healthy review services remain running; no volumes or user data were deleted.

## Coverage Metrics

Coverage percentages were not collected because the accepted plan defines no coverage threshold
or required coverage command. No test or failure was suppressed.

## Critical Issues

None.

## Recommendations

1. The fixed review blockers are ready for independent code re-review.
2. Low priority: install Docker buildx to remove the classic-builder warning.
3. Run live OpenRouter smoke only with an explicitly rotated reviewer key and separate network
   authorization.

## Unresolved Questions

- Credentialed OpenRouter behavior remains intentionally outside this offline verification.
