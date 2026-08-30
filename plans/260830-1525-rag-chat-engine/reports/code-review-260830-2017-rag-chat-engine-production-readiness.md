---
title: "RAG Chat Engine Production-Readiness Review"
date: "2026-08-30"
agent: code-reviewer
scope: "plans/260830-1525-rag-chat-engine"
status: failed
base_commit: "25d68d920390a3ef6fcc5ca9e34e0f4d460074ff"
---

# Code Review Summary

## Scope

- Reviewed every tracked change against base commit `25d68d9`, all untracked implementation and
  test files, the complete plan and five phase files, the offline QA report, and the independent
  untracked Part 1 smoke-test plan.
- Tracked diff: 28 files, 1,175 insertions, 554 deletions, plus the new account/RAG modules,
  migration, integration tests, fixture, reports, journal, and unrelated Part 1 plan artifacts.
- Focus: spec conformance, concurrency, auth/authz, owner isolation, provider/retrieval exception
  boundaries, quota settlement, API contracts, dependency ownership, and production runtime cost.
- Scout findings rechecked: direct `openrouter`/`httpx` ownership is now declared; OpenRouter
  `OpenRouterError`, `NoResponseError`, `httpx.TransportError`, and the locked response-error
  prefixes are translated and regression-tested. Chroma `HttpClient` connection failures and
  invocation-time `httpx.TransportError` are also translated, but the construction boundary is
  still incomplete as described below.

## Overall Assessment

**FAIL — two High-priority production-readiness blockers remain.** Authentication, owner-derived
Chroma filtering, PostgreSQL quota serialization, narrow OpenRouter failure translation, generic
external error bodies, free-model validation, and Docker secret separation are implemented. The
retrieval factory can still leak normal infrastructure/model-load failures as HTTP 500, and every
chat query reconstructs the sentence-transformer model in the synchronous web process.

## Critical Issues

None found.

## High Priority — Blocking

### 1. Store-construction outages bypass the retrieval error boundary

- Evidence: [`apps/documents/vector_store.py:47`](../../../apps/documents/vector_store.py) catches
  only `IngestionError` around `_build_store().as_retriever(...)`. `_build_store` wraps the
  `chromadb.HttpClient` call at lines 77-80, but neither `HuggingFaceEmbeddings(...)` at line 81 nor
  `Chroma(...)` at lines 82-86. A `httpx.ConnectError` raised by the locked `Chroma` constructor was
  reproduced and escaped as raw `ConnectError` (`isinstance(VectorRetrievalError) == False`); an
  embedding-load `OSError` escaped the same way.
- Impact: a Chroma outage between client creation and collection creation, an unreadable/cold model
  cache, or a Hugging Face download failure produces an unhandled HTTP 500. This violates the
  accepted `503` retrieval contract and Phase 2/3 requirement that expected retriever construction
  failures be normalized safely.
- Test gap: [`tests/documents/test_vector_retrieval.py:50`](../../../tests/documents/test_vector_retrieval.py)
  covers only `HttpClient`'s `ValueError`; the real-Chroma test replaces `_build_store` with a ready
  store at line 48, so neither test reaches these failure points.
- Required fix: translate the locked Chroma constructor's `ChromaError`/`httpx.TransportError` and
  documented embedding model/cache operational failures into `IngestionError` or directly into
  `VectorRetrievalError`, without broad-catching programming errors. Add regression tests at both
  constructor boundaries and prove the API returns the generic 503 response.

### 2. The synchronous chat path reloads the embedding model on every request

- Evidence: [`apps/rag/services.py:77`](../../../apps/rag/services.py) calls a new
  `DocumentVectorStore` factory for each query; [`apps/documents/vector_store.py:69`](../../../apps/documents/vector_store.py)
  then constructs `HuggingFaceEmbeddings` at line 81 every time. The locked class constructor
  immediately constructs a `sentence_transformers.SentenceTransformer`, which loads model weights.
- Impact: each authenticated query performs heavyweight CPU/model initialization inside a Gunicorn
  request. On a cold cache it can download the model and exceed the worker timeout; on a warm cache
  it still repeatedly loads weights, increasing latency, memory churn, and concurrent-request
  pressure. Unit tests replace `_build_store`, and the Chroma integration injects a deterministic
  ready store, so CI does not exercise this production path.
- Required fix: reuse a process-local embedding instance (keyed by configured model) or an
  equivalent lifecycle-managed vector-store dependency, while keeping owner filters per request.
  Add a test proving repeated retrievals do not reconstruct the embedding model.

## Medium Priority — Non-blocking

### 3. The JSON boundary silently accepts numeric queries

- Evidence: [`apps/rag/serializers.py:5`](../../../apps/rag/serializers.py) uses DRF
  `CharField`, which coerces integer/float primitives. A direct check with `{"query": 123}` returned
  `is_valid() == True` and `validated_data == {"query": "123"}`.
- Impact: the endpoint does not enforce the plan's string-only request contract and silently changes
  caller data types. Existing API tests cover missing/blank/long values but no non-string primitive.
- Fix: use a strict string field or reject non-`str` input before `CharField` coercion; add boolean,
  number, list, object, and null API cases.

### 4. Usage timestamps do not track quota mutations

- Evidence: [`apps/accounts/entitlements.py:76`](../../../apps/accounts/entitlements.py), line 83,
  and line 111 mutate `used_tokens` through `QuerySet.update()`. Django's `auto_now=True` does not run
  for `QuerySet.update()`, yet `DailyTokenUsage.updated_at` is exposed in the admin as the apparent
  last-update time.
- Impact: operational/admin data reports the row-creation timestamp after reserve, refund, and
  finalize activity, which is misleading during quota incident analysis.
- Fix: include `updated_at=timezone.now()` in each atomic update and assert it advances.

## Low Priority

- The independent untracked `plans/260830-1608-part-1-endpoint-smoke-tests/` artifacts are unrelated
  to this RAG implementation. Preserve them, but do not accidentally land them in the same focused
  implementation commit unless the user explicitly wants the planning artifacts bundled.

## Edge Cases Found and Verified

- Concurrent first reservations are serialized by the locked subscription row and the unique
  `(user, usage_date)` constraint; the real PostgreSQL race test passed in prior Docker QA.
- Missing/inactive subscriptions stop before retrieval; quota exhaustion stops before model
  construction; provider/config/invalid-content paths refund the reservation.
- The request cannot supply owner ID, collection, metadata filter, model, or token budget. Owner
  scope comes from `request.user.id`, and the real Chroma two-owner test passed in prior Docker QA.
- API errors do not expose provider text, retrieved context, quota row IDs, or credentials.
- No unbounded DB loop or N+1 query was introduced in the chat path.

## Recommended Actions

1. Fix and regression-test both uncovered retrieval construction failures.
2. Reuse the embedding model across requests and verify constructor call count.
3. Enforce strict string query input.
4. Keep `DailyTokenUsage.updated_at` accurate during atomic updates.
5. Re-run focused tests, full pytest, Docker Chroma/PostgreSQL invariants, and this review.

## Plan Status Recommendation

- Phases 1-4 are materially implemented but should not be marked complete until the two High
  findings are fixed and re-reviewed.
- Phase 5 offline gates are evidenced. The credentialed OpenRouter smoke remains intentionally
  unrun because no rotated credential was authorized; this is allowed by the plan's conditional
  live-smoke rule.

## Metrics

- Fresh verification: Ruff passed; `131 passed, 2 skipped` in 5.66 seconds for
  `tests/accounts tests/documents tests/rag tests/smoke`.
- Type coverage: not measured; the project has no configured static type-check gate.
- Test coverage: not measured; the accepted plan defines no coverage threshold.
- Linting issues: 0.

## Unresolved Questions

None. The High findings are reproducible implementation defects, not product-policy questions.
