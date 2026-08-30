---
title: "RAG Chat Engine Adversarial Validation"
date: "2026-08-30"
agent: adversarial-reviewer
scope: "plans/260830-1525-rag-chat-engine"
base_commit: "25d68d920390a3ef6fcc5ca9e34e0f4d460074ff"
decision: BLOCKED
---

# Adversarial Validation — RAG Chat Engine

## Decision

**BLOCKED.** Claim 5 is disproven by a reachable Chroma construction failure. Two additional
production-availability regressions are present in the synchronous request path. Passing unit and
healthy-backend integration tests do not exercise these paths.

## Scope and method

- Reviewed all tracked and untracked Part 2 implementation, tests, Compose/runtime changes, the
  accepted plan, and the prior offline QA report.
- Used edge-case scouting before review and checked the locked `chromadb==1.5.9`,
  `langchain-chroma`, `langchain-huggingface`, `langchain-openrouter==0.2.8`, and
  `openrouter==0.11.46` runtime behavior.
- Fresh focused gate: `67 passed in 1.00s` for entitlement, vector-retrieval, and RAG tests.
- Fresh reproduction proved that a collection-construction `httpx.ConnectError` escapes as that
  raw exception rather than `VectorRetrievalError`.

## Blocking findings

### HIGH — Chroma collection-construction outages escape the safe retrieval boundary

`DocumentVectorStore._build_store()` wraps only `chromadb.HttpClient(...)` at
`apps/documents/vector_store.py:77-80`. The subsequent `Chroma(...)` constructor at lines 82-86
calls `get_or_create_collection` and can raise `httpx.TransportError` or a Chroma error if the
server disappears after client creation. `as_retriever_for_user()` catches only `IngestionError`
at lines 47-52, so this expected backend outage escapes `RagService` and becomes HTTP 500 instead
of the plan's safe retrieval 503.

Reproduction against the current adapter, with the locked constructor replaced only at the
network-failure seam:

```text
ConnectError 'collection unavailable' safe_domain= False
```

This also leaves `HuggingFaceEmbeddings(...)` at line 81 outside any retrieval-domain translation;
an offline/missing model cache was separately reproduced as raw `OSError`. The Phase 2 success
criterion says construction errors become `VectorRetrievalError`, but the current test covers only
failure inside `HttpClient` and does not cover the later construction stages.

Required correction: translate documented Chroma/httpx failures around the entire store/retriever
construction path, while retaining the existing test that proves unrelated programming errors
propagate. Add a regression test for failure from `langchain_chroma.Chroma(...)`, not merely
`chromadb.HttpClient(...)`.

### HIGH — Every chat request reloads the embedding model in the web process

`ChatQueryView` creates a new `RagService` for every request (`apps/rag/views.py:40-43`), whose
default factory returns a new `DocumentVectorStore` (`apps/documents/vector_store.py:89-90`). Every
retrieval then calls `_build_store()` and constructs a new `HuggingFaceEmbeddings` instance at
line 81. The locked implementation constructs a fresh `SentenceTransformer` client in its
initializer; the disk cache avoids downloads but does not reuse the loaded model object.

This puts model load latency and large Torch allocations on every synchronous query and can cause
latency spikes or memory pressure under the two-worker Gunicorn process. The real owner-isolation
test replaces `_build_store` with a deterministic store, so it cannot detect this regression.

Required correction: reuse the embeddings/store resource per worker through a bounded,
thread-safe process-local factory, then test that repeated retrievals do not reconstruct the model.

### HIGH — Provider failures can occupy all web workers for minutes

`build_openrouter_chat_model()` does not configure a request timeout or bounded retry policy
(`apps/rag/llm.py:21-34`). With the locked integration, `ChatOpenRouter` defaults to
`max_retries=2`, but its SDK adapter converts that value to a retry **elapsed-time** budget of
`300000 ms`; the underlying HTTP client has a 5-second per-attempt timeout. Persistent 5xx or
connection failures can therefore keep one synchronous call retrying for up to five minutes.
Compose runs only two Gunicorn workers (`compose.yaml:9-10`), so two provider outages can exhaust
the public web service even though the eventual exception is safely mapped and refunded.

Required correction: explicitly configure a short request timeout and a tightly bounded/no-retry
policy appropriate for a synchronous free-tier endpoint, and test the constructed client policy.

## Claim matrix

| # | Claim | Result | Evidence |
| --- | --- | --- | --- |
| 1 | Concurrent quota cannot overspend | PASS | Subscription row is locked before usage read/update; real PostgreSQL race test previously passed one reservation and rejected one. |
| 2 | Refund/finalize cannot underflow or leak access | PASS | Usage row lock plus clamped SQL decrement prevents negative values; reservation occurs only after entitlement recheck. Exactly-once settlement remains a service invariant, not a persisted reservation identity. |
| 3 | Inactive/missing subscription stops before retrieval | PASS | `ensure_active_subscription` is first in `RagService.answer_query`; focused regression uses a fail-if-called retriever. Reservation rechecks under lock. |
| 4 | Request cannot influence owner/filter/model/budget | PASS | Serializer accepts only `query`; owner is `request.user.id`; filter, model, k, and budgets come from server settings. |
| 5 | Chroma/OpenRouter outages map safely without hiding programming bugs | **FAIL** | OpenRouter taxonomy now covers locked SDK/network exceptions narrowly, but post-client Chroma construction transport failures escape as raw exceptions. |
| 6 | No-context uses no provider/quota | PASS | Empty retrieval returns fixed answer before reservation/model construction; test proves no usage row and fail-if-called builder. Configuration validation is local and makes no provider call. |
| 7 | Only free model IDs pass | PASS | Validator allows exactly `openrouter/free` or the accepted `:free` suffix and rejects `openrouter/auto`. |
| 8 | Context/token bounds are conservative | PASS with missing edge proof | Context is hard-capped; admission uses UTF-8 bytes plus explicit chat/output allowance. Lone-surrogate JSON input is not tested and would raise during UTF-8 encoding. |
| 9 | Secrets only reach web | PASS | Compose forwards `OPENROUTER_API_KEY` only to web; Docker ignore excludes dotenv files from image context. |
| 10 | Runtime/test dependency separation | PASS | Runtime uses `--no-dev --extra vector-ingestion`; profile-gated test image uses dev dependencies. Offline QA confirmed pytest absent from runtime. |
| 11 | API bodies leak no internals | PASS | Known domain errors map to fixed messages; tests assert provider/retrieval details are absent. Production settings keep debug off by default. |

## Missing proof / non-blocking gaps

- No credentialed live OpenRouter call was run, by design; real free-router response shape and usage
  metadata remain unverified.
- The conservative-bound test uses a normal multibyte emoji, not malformed Unicode such as an
  unpaired surrogate accepted by Python's JSON decoder. That input currently produces a 500 before
  reservation rather than a validation error.
- No coverage percentage was collected and the accepted plan defines no threshold.

## Behavioral checklist

- Concurrency: checked PostgreSQL locking and concurrent settlement ordering.
- Error boundaries: checked pre/post-reservation translation and refund paths; Chroma construction
  gap is blocking.
- API contracts and backwards compatibility: checked route, response bodies, model migration, and
  explicit seed-fixture change.
- Input validation and auth/authz: checked query boundary, JWT identity, subscription recheck, and
  owner-derived filter.
- Query efficiency: no DB N+1 found; per-request embedding-model construction is blocking.
- Data exposure: no API-key/context/error-detail response leak found; Compose secret propagation is
  web-only.
- Plan fact check: file paths, symbols, exception families, Docker targets, and integration claims
  were verified against current code rather than accepted from plan text.
