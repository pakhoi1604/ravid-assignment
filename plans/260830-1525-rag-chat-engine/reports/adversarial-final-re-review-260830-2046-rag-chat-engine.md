---
title: "RAG Chat Engine Final Adversarial Re-review"
date: "2026-08-30"
agent: adversarial-reviewer
scope: "plans/260830-1525-rag-chat-engine"
follow_up_to: "adversarial-re-review-260830-2034-rag-chat-engine.md"
decision: PASS
---

# Final Adversarial Re-review — RAG Chat Engine

## Decision

**PASS.** No original claim was disproven against the final fix cycle. The locked OpenRouter client
now has an effective ten-second per-operation timeout and no retry helper invocation; expected
vector construction failures map safely while unrelated `ValueError` defects propagate. Cache
reuse does not weaken per-request owner filtering.

Fresh focused validation: **75 passed in 0.91s** across entitlement, vector-retrieval, RAG service,
LLM, and API tests. The supplied final QA report independently records **144 passed, 2 expected
local skips**, followed by passing PostgreSQL/Chroma Docker invariants and full-stack smoke.

## Adversarial evidence

### Effective locked OpenRouter policy

The review exercised the real `langchain-openrouter==0.2.8` and `openrouter==0.11.46` objects rather
than a fake constructor. `apps/rag/llm.py:29-36` supplies an explicit SDK client with
`timeout_ms=10000` and `retry_config=None`; `ChatOpenRouter` reuses that client.

A synthetic 503 was returned from the SDK's HTTP seam without network I/O while the SDK retry
helper was replaced with a fail-if-called function:

```text
exception=ServiceUnavailableResponseError
send_calls=1
timeout_extension={'connect': 10.0, 'read': 10.0, 'write': 10.0, 'pool': 10.0}
```

The retry helper was not called. The resulting SDK exception is an `OpenRouterError`, which the
provider adapter maps to `ProviderTransportError`; `RagService` refunds the reservation and the API
returns its fixed 503 body. Nonzero configured retries fail closed before retrieval.

### Narrow vector construction boundary

`apps/documents/vector_store.py:31-36` translates only the locked HttpClient's recognized Chroma
connection `ValueError` prefix. Later construction catches are limited to dependency/cache,
`ChromaError`, and transport families at lines 99-114. An unrelated embedding/store constructor
`ValueError` now propagates; Chroma collection `ConnectError`, embedding-cache `OSError`, and the
locked connection error remain mapped to `VectorRetrievalError`.

### Cache and owner isolation

The process-local cache key contains collection and embedding/Chroma configuration only. The
cached object is the vector store, not a retriever. Every call still creates a new retriever at
lines 77-80 with `filter={"user_id": authenticated_integer_id}`. The cold-build lock prevents
duplicate model construction without retaining owner state. The final rebuilt real-Chroma test
again returned only each of two owners' chunks.

## Final claim matrix

| # | Claim | Result | Evidence |
| --- | --- | --- | --- |
| 1 | Concurrent quota cannot overspend | PASS | Subscription row lock serializes admission; final real PostgreSQL race passed. |
| 2 | Refund/finalize cannot underflow or leak access | PASS | Settlement locks the usage row and clamps decrements; active entitlement is rechecked under the reservation lock. |
| 3 | Inactive/missing subscription stops before retrieval | PASS | Entitlement check is first; focused tests use a fail-if-called retriever. |
| 4 | Request cannot influence owner/filter/model/budget | PASS | Strict serializer exposes only query; owner/filter and all model/budget values are server-derived. |
| 5 | Expected Chroma/OpenRouter outages map safely without hiding programming bugs | PASS | Entire expected construction/invocation taxonomy maps; unrelated constructor/invocation defects propagate; effective SDK retry behavior was exercised. |
| 6 | No-context uses no provider/quota | PASS | Empty retrieval exits before reservation/model construction and creates no usage row. |
| 7 | Only accepted free model IDs pass | PASS | Exactly `openrouter/free` or the accepted `:free` suffix is allowed. |
| 8 | Context/token/input bounds are conservative | PASS | Strict UTF-8 rejects surrogates/non-string values; context is capped and admission uses UTF-8 bytes plus chat/output bounds. |
| 9 | Secrets reach only web | PASS | Compose forwards the OpenRouter key only to web; dotenv files remain outside image context. |
| 10 | Runtime/test dependencies remain separated | PASS | Fresh runtime build excludes pytest; test target carries dev dependencies. |
| 11 | API bodies leak no internals | PASS | Known validation, entitlement, retrieval, configuration, and provider failures expose fixed safe bodies only. |

## Production-readiness checklist

- Concurrency: PostgreSQL admission race, usage-row settlement, cold cache build, and owner-specific
  retriever construction checked.
- Error boundaries: pre-reservation retrieval failures and post-reservation provider/config/output
  failures checked; expected errors are translated and programming errors remain visible.
- API/input/authz: JWT identity, subscription status, strict query input, server-owned filter, and
  fixed response contracts checked.
- Performance: the embedding/Chroma resource is reused per process; no DB N+1 path found.
- Data exposure: no context, provider detail, credentials, or expanded Compose configuration is
  returned by the API or included in non-web service environments.
- Plan compliance: named symbols, paths, dependency versions, Docker targets, and backend-specific
  claims were verified against current source and fresh QA evidence.

## Intentionally unverified

- No credentialed live OpenRouter call was made. Free-router availability, live response shape, and
  live usage metadata remain conditional on a rotated key and explicit network authorization.
- Coverage percentage remains uncollected because the accepted plan specifies no threshold.
