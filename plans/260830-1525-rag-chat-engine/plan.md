---
title: "Part 2: RAG Chat Engine"
description: "Implement authenticated RAG querying with owner-scoped retrieval, free-tier OpenRouter generation, and local subscription/token-credit gates."
status: completed
priority: P1
branch: "main"
tags: [feature, backend, api, auth, database]
blockedBy: []
blocks: []
created: "2026-08-30T08:26:38.382Z"
createdBy: "ck:plan"
source: skill
---

# Part 2: RAG Chat Engine

## Overview

Implement Part 2 on top of the completed Part 1 ingestion pipeline. Deliver
`POST /api/chat/query/`: authenticate the caller, verify an active local subscription and remaining
daily token quota, retrieve only that user's Chroma chunks, compose a grounded LangChain chain,
call an OpenRouter free-tier model, account for usage, and return `{"answer": "..."}`.

The subscription is application-owned access state, not an OpenRouter or payment subscription.
OpenRouter still requires an API key, but the baseline accepts only `openrouter/free` or a model ID
ending in `:free`; buying credits is out of scope. Bonus HyDE, payments, streaming, memory,
neighbor expansion/reranking, and multi-tenant billing remain out of scope.

## Current Repository State

- Part 1 ingestion is implemented. Chunks store integer `user_id`, `document_id`, `chunk_index`,
  and `source_filename`; `DocumentVectorStore` now supports owner-scoped retrieval as well as
  writes.
- Django built-in `auth.User`, SimpleJWT, and `load_test_accounts` remain the identity and reviewer
  seeding foundation. `apps.accounts` now owns local subscription and daily token usage state.
- `apps.rag` now exposes `POST /api/chat/query/` with subscription checks, quota accounting,
  owner-scoped retrieval, bounded prompt construction, and OpenRouter free-tier generation.
- Modular LangChain/OpenRouter dependencies are direct; the umbrella `langchain` package remains
  absent. The CPU-only Torch resolution is preserved.
- README and architecture docs describe the implemented Part 2 reviewer flow and runtime boundary.

## Scope Challenge

- Existing code to reuse: JWT/DRF patterns, secure idempotent test-account seeding, Part 1 metadata,
  Chroma adapter, settings helpers, Compose image and OpenAPI tooling.
- Minimum change set: two account-domain models, atomic quota service, owner-scoped retriever,
  free-tier OpenRouter LCEL chain, one DRF endpoint, focused tests, and reviewer docs.
- Complexity: five phases and roughly 25-30 touched/created files are justified by persistence,
  retrieval, provider orchestration, HTTP, and validation boundaries. No payment system or custom
  user model is introduced.
- Selected mode: HOLD SCOPE; hard current-state reconciliation.

## Architecture Decisions

- Keep built-in `auth.User` for authentication. Add `accounts.Subscription` (one per user) and
  `DailyTokenUsage` (one per user per UTC date); do not add subscription/credit columns to User.
- Extend `load_test_accounts` with explicit fixture fields for subscription state and token limit.
  Never infer subscription state from `User.is_active`; chat traffic fails closed and cannot grant
  access.
- Verify subscription before retrieval. After formatting the actual bounded context, reserve a
  conservative UTF-8-byte input bound plus explicit chat overhead and capped output before the
  provider call. Refund provider failures and finalize actual usage. Remaining quota is derived.
- Declare every runtime import directly: `langchain-core`, `langchain-openrouter`, `openrouter`
  (exception taxonomy only), and `httpx` (transport-error taxonomy). The latter two are already
  required transitively by the integration, so direct declaration adds ownership without adding
  packages. Do not install the `langchain` umbrella or `langchain-openai`.
- Use native `VectorStoreRetriever`, then format bounded context through LangChain runnable
  composition. Owner filtering lives in the adapter and cannot be supplied by the request.
- Cache the Chroma client/store and Hugging Face embedding model in a bounded, process-local,
  cold-construction lock so synchronous chat does not reload model weights per request.
- Bound synchronous OpenRouter calls to a 10-second request budget with provider retries disabled;
  callers can retry after the safe `503` response without occupying both Gunicorn workers for minutes.
- HTTP decisions: missing/inactive subscription `403`; exhausted daily quota `429`; empty retrieval
  `200` with a fixed no-context answer and no LLM call; known retrieval/provider failures `503`.

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Account Entitlement and Credit Gate](./phase-01-account-entitlement-and-credit-gate.md) | Completed |
| 2 | [Vector Retriever Service](./phase-02-vector-retriever-service.md) | Completed |
| 3 | [OpenRouter RAG Answer Pipeline](./phase-03-openrouter-rag-answer-pipeline.md) | Completed |
| 4 | [Chat Query API Contract](./phase-04-chat-query-api-contract.md) | Completed |
| 5 | [Validation Documentation and Reviewer Workflow](./phase-05-validation-documentation-and-reviewer-workflow.md) | Completed |

## Cross-Plan Dependencies

| Relationship | Plan | Current state |
| --- | --- | --- |
| Completed prerequisite | `260830-1740-langchain-dependency-refresh` | Completed; established modular LangChain 1.x family |
| Completed prerequisite | `260830-1830-cpu-only-torch-runtime` | Completed; CPU-only Torch resolution must be preserved |
| Completed prerequisite | `260830-1329-document-management-vector-storage` | Completed Part 1 ingestion/vector storage |
| Related, not blocking | `260830-1608-part-1-endpoint-smoke-tests` | May supply reviewer tooling, but explicitly excludes Part 2 |

Both declared prerequisites now resolve as completed in `ck plan status`; no active cross-plan
blocker remains. No relationship exists with the unfinished Claude-hooks migration plan because it
affects agent tooling only.

## Acceptance Criteria

- [x] Authenticated `POST /api/chat/query/` accepts `{"query": "..."}` and returns
      `200 {"answer": "..."}`.
- [x] Explicit local `Subscription` and per-day usage models enforce active access and daily quota;
      no payment subscription is required.
- [x] `load_test_accounts` transactionally and idempotently provisions explicit reviewer
      subscriptions without pre-creating dated usage.
- [x] Inactive/missing subscription stops before retrieval; exhausted quota stops before OpenRouter.
- [x] Retrieval uses the existing Chroma collection and an authenticated integer `user_id` filter;
      cross-owner chunks cannot be returned.
- [x] Empty retrieval returns the fixed no-context answer, creates no reservation/debit, and does not
      call OpenRouter.
- [x] The LLM path uses `ChatOpenRouter`, `openrouter/free` or an explicit `:free` model, and a
      LangChain runnable prompt/model chain; no umbrella `langchain` package is added.
- [x] Provider/config/retrieval failures are safe, refund reservations, and never leak context or
      credentials.
- [x] Offline tests, migration checks, OpenAPI validation, full pytest, Compose validation, and
      Docker image checks pass; a credentialed free-tier smoke is documented separately.
- [x] Docker-backed PostgreSQL concurrency and two-user Chroma owner-isolation integration tests
      pass; SQLite/mock-only tests cannot close these invariants.

## Validation Commands

```bash
UV_CACHE_DIR=/tmp/ravid-rag-uv-cache uv lock --check
UV_CACHE_DIR=/tmp/ravid-rag-uv-cache uv sync --all-extras --dev --frozen
uv run ruff check apps config tests
uv run ruff format --check apps config tests
uv run python manage.py check --settings=config.settings.test
uv run python manage.py makemigrations --check --dry-run --settings=config.settings.test
uv run python manage.py spectacular --settings=config.settings.test --file /tmp/ravid-openapi.yaml --validate
uv run pytest tests/accounts tests/documents tests/rag tests/smoke
uv run pytest
docker compose config --quiet
docker compose build web
docker compose --profile test build test
docker compose --profile test up -d db chroma
docker compose --profile test run --rm test pytest --ds=config.settings.production tests/accounts/test_entitlements_postgres.py -q
docker compose --profile test run --rm test pytest --ds=config.settings.production tests/documents/test_vector_retrieval_chroma.py -q
make smoke
```

## Open Questions

None. Assignment-undefined HTTP and empty-context behavior is resolved above to keep the baseline
free-tier, deterministic, and compatible with the required success response.

## References

- Assignment: `docs/2026-08-30 R.A.V.I.D.md`
- LangChain OpenRouter integration: https://docs.langchain.com/oss/python/integrations/chat/openrouter
- `langchain-openrouter` package: https://pypi.org/project/langchain-openrouter/
- OpenRouter free router: https://openrouter.ai/docs/guides/routing/routers/free-router
- OpenRouter auto router pricing: https://openrouter.ai/docs/guides/routing/routers/auto-router

## Validation Log

### Current-State Reconciliation - 2026-08-30

- **Tier:** Full (five phases).
- Verified all named current files/settings/routes against the repository.
- Reconciled model naming to explicit `Subscription`; kept built-in Django User for identity.
- Reconciled seed policy: explicit fixture subscription state, never `User.is_active` inference.
- Reconciled dependency ownership: completed LangChain refresh and CPU-only Torch plans retained as
  prerequisites; future lock edits must preserve the CPU-only resolution already in the worktree.
- Reconciled provider policy: `openrouter/auto` is not guaranteed free; baseline uses free router or
  explicit `:free` model IDs only.
- Reconciled API decisions: `403`, `429`, deterministic no-context `200`, and safe `503` mappings.
- Adversarial review accepted four findings: token-bound correctness, explicit refund/error
  boundaries, executable PostgreSQL concurrency validation, and real Chroma owner isolation.
- Final adversarial re-check confirmed admission/default viability, narrow exception translation,
  output normalization, and the profile-gated dev-test image workflow are internally consistent.
- Whole-plan consistency sweep: all six files reread; superseded model naming, HTTP mappings,
  auto-router default, seed inference, dependency state, accounting, and integration gates
  reconciled.
- Status follow-up: public status responses intentionally serialize queued internal `PENDING` jobs
  as `PROCESSING`; this is accepted for assignment-facing status and is not a remaining blocker.
- Private-PDF Lab 9 top-k retrieval miss is explicitly out of scope for this plan-finalization pass.
- Unresolved contradictions: 0.
