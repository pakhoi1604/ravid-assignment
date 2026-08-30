---
title: "RAG Chat Engine Adversarial Re-review"
date: "2026-08-30"
agent: adversarial-reviewer
scope: "plans/260830-1525-rag-chat-engine"
follow_up_to: "adversarial-260830-2015-rag-chat-engine.md"
decision: BLOCKED
---

# Adversarial Re-review — RAG Chat Engine

## Decision

**BLOCKED.** The Chroma outage and process-local cache fixes work, strict UTF-8 validation works,
and focused/full QA is green. However, the claimed no-retry OpenRouter policy is not effective with
the locked SDK, and the broadened Chroma construction boundary now hides unrelated `ValueError`
programming defects.

Fresh focused regression command passed: **57 passed in 0.88s**.

## Blocking findings

### HIGH — `max_retries=0` activates the OpenRouter SDK's one-hour operation default

`apps/rag/llm.py:28-38` passes `timeout=10000` and `max_retries=0` to `ChatOpenRouter`. The unit test
at `tests/rag/test_llm.py:28-46` replaces `ChatOpenRouter` with a function and verifies only those
constructor kwargs; it never inspects the locked client's effective policy.

With `langchain-openrouter==0.2.8`, `_build_client()` adds an SDK `retry_config` only when
`max_retries > 0`. Zero therefore leaves `sdk_configuration.retry_config` as `Unset`. The locked
`openrouter==0.11.46` `chat.send()` treats `Unset` as a request for its operation default:

```text
lc.request_timeout=10000
lc.max_retries=0
sdk.timeout_ms=10000
sdk.retry_config=Unset()
effective_retry_strategy=backoff
effective_retry_connection_errors=True
effective_retry_initial_ms=500
effective_retry_max_interval_ms=60000
effective_retry_max_elapsed_ms=3600000
```

The effective policy was captured before network I/O by instrumenting the locked SDK's retry seam.
A persistent connection/5xx failure can retry for up to one hour, tying up the synchronous request
and retaining its quota reservation. With two Gunicorn workers, two failures can exhaust the web
service. This disproves the post-review QA claim that retry count is effectively zero.

Required correction: configure the SDK with an explicit retry policy that disables retries rather
than relying on LangChain's `max_retries=0` omission, or invoke with an explicit SDK `retries`
override. Add an integration-level construction test that inspects/captures the locked SDK policy,
not a fake-class kwargs test.

### HIGH — The Chroma construction catch now hides unrelated `ValueError` defects

`apps/documents/vector_store.py:100-109` catches `ValueError` around the entire cached construction
of the Chroma client, embedding model, and LangChain store. This is necessary for the locked
client's specific connection `ValueError`, but it also translates unrelated constructor defects to
`IngestionError` and then `VectorRetrievalError`.

Fresh reproduction injected `ValueError("implementation defect")` from the `Chroma(...)`
constructor and observed:

```text
VectorRetrievalError Vector retrieval is unavailable. programming_error_propagated=False
```

The existing programming-error test covers only a `TypeError` from retriever invocation; it does
not test unrelated `ValueError` during construction. This violates the accepted boundary that
expected Chroma/network failures map safely while programming errors propagate.

Required correction: isolate the locked HttpClient connection `ValueError` at that exact call (and
prefer its known connection prefix/type), while catching only `ChromaError`, `httpx.TransportError`,
and the explicitly accepted embedding-cache error around later construction stages. Add an
unrelated-constructor-`ValueError` propagation test.

## Prior-claim revalidation

| Claim | Result | Evidence |
| --- | --- | --- |
| Concurrent quota cannot overspend | PASS | Subscription row serialization remains intact; post-review PostgreSQL race passed. |
| Refund/finalize cannot underflow or leak access | PASS | Locked/clamped settlement remains intact; mutation timestamps now update explicitly. |
| Inactive/missing subscription stops before retrieval | PASS | Entitlement check remains first and reservation rechecks under lock. |
| Request cannot control owner/filter/model/budget | PASS | Only strict UTF-8 query is accepted; identity/filter and budgets remain server-derived. |
| Entire Chroma/OpenRouter expected outage boundary is safe without hiding bugs | **FAIL** | Expected Chroma transport/cache failures now map, but unrelated construction `ValueError` is hidden; effective OpenRouter retry policy remains unsafe. |
| No-context uses no provider/quota | PASS | Empty retrieval still returns before reservation/model construction. |
| Only accepted free model IDs pass | PASS | Exact free router / `:free` rule unchanged. |
| Context/token/input bounds are conservative | PASS | Strict UTF-8 rejects unpaired surrogates; query/context/output bounds remain enforced. |
| Secrets reach only web | PASS | Compose secret boundary unchanged and post-review build did not expose dotenv data. |
| Runtime/test dependencies remain separated | PASS | Rebuilt runtime excludes pytest; profile test image contains dev tools. |
| API bodies do not leak internals | PASS | Fixed 400/403/429/503 bodies remain generic; strict-input errors are safe. |
| Process-local cache/cold lock preserves owner isolation | PASS | Cache key is configuration-only, cold build is locked, and a fresh retriever receives the authenticated integer owner filter on every call. Real two-owner Chroma test passed after rebuild. |
| Safe 503 and refund behavior | PASS for mapped failures | Chroma failures happen before reservation; mapped provider failures refund and expose a fixed 503. The effective retry defect delays that mapping unacceptably. |

## Unverified claims

- No live credentialed OpenRouter request was run, intentionally. Real free-router availability,
  usage metadata, and final response shape remain outside offline proof.
- The process-local cached Hugging Face/Chroma objects are assumed safe for concurrent inference;
  the cold-build test proves single construction but does not stress simultaneous retrieval calls.
- Coverage percentage remains uncollected because the accepted plan defines no threshold.
