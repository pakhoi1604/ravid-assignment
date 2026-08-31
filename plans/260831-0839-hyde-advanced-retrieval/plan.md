---
title: "Part 3: HyDE Advanced Retrieval"
description: "Add bounded, optional HyDE retrieval to the existing authenticated RAG endpoint with safe fallback, conservative token settlement, and grading metadata."
status: completed
priority: P2
branch: "main"
tags: [feature, backend, api, auth, experimental]
blockedBy: []
blocks: []
created: "2026-08-31T01:42:37.001Z"
createdBy: "ck:plan"
source: skill
---

# Part 3: HyDE Advanced Retrieval

## Overview

Extend `POST /api/chat/query/` with strict optional `use_hyde` while preserving the endpoint,
owner-scoped vector adapter, current standard retrieval, safe error statuses, and uncommitted
threshold/MMR work. HyDE generates a bounded hypothetical passage through the existing
ChatOpenRouter/LCEL boundary, retrieves real chunks with that passage, then synthesizes from only
the real chunks and original query.

## Scope Challenge

- Existing code: authenticated DRF endpoint, owner-filtered `retrieve_for_user`, LCEL invocation,
  safe provider translation, bounded prompts, and atomic quota reservations.
- Minimum change: extend RAG/retrieval modules, three purpose-specific settings and deployment surfaces,
  focused tests/evaluation, OpenAPI schema, README, and architecture documentation.
- Complexity: three phases; no new service, vector API, persistence model, or Python dependency.
- Selected mode: **HOLD SCOPE**, hard mode. Bonus HyDE only; no reranker, cache, streaming, or retry.

## Architecture Decisions

- `use_hyde` is an optional strict JSON boolean defaulting to `false`; omitted/false performs raw
  query retrieval and makes no HyDE provider call.
- Successful responses use the assignment-facing fields only: `answer`, then
  `retrieval_metadata.mode`, `hypothetical_passage`, nullable `fallback_reason`,
  `retrieved_chunks_count`, and bounded `retrieved_chunks`. The chunk strings are the exact
  owner-scoped excerpts supplied to final synthesis; content is returned only to the authenticated
  owner, never logged, and shares the final-context size bound.
- HyDE flow: original query -> injection-resistant HyDE prompt -> existing ChatOpenRouter LCEL
  invocation -> normalize/bound -> owner-scoped retrieval using the hypothetical -> existing final
  prompt with real chunks and original query. The hypothetical is retrieval input, never evidence.
- Expected timeout/transport or empty/invalid/oversized output still falls back to raw-query
  retrieval. Its response uses `mode: "standard"`, `hypothetical_passage: null`, and
  `fallback_reason: "hyde_unavailable"`; provider-specific detail is not exposed. Configuration
  errors remain `503`; unrelated programming errors propagate; retries remain zero.
- Add positive `RAG_HYDE_MAX_OUTPUT_TOKENS=256`, `RAG_HYDE_MAX_OUTPUT_CHARS=2000`, and
  `RAG_HYDE_TIMEOUT_MS=3000`; extend the existing model builder with explicit overrides rather than
  creating another provider integration. The character ceiling is independent of token heuristics.
- Reserve HyDE generation separately. Pre-dispatch configuration failures refund. Once dispatched,
  timeout/transport failures conservatively settle the reserved bound; returned messages settle
  bounded reported/fallback usage before content validation. Successful or dispatched HyDE usage
  remains charged if retrieval is empty or final synthesis later fails. The independent final-answer
  reservation may accurately return `429` after HyDE use.
- Guarantee one settlement call per in-process control path, not durable exactly-once semantics. A
  pending-reservation guard refunds unexpected pre-dispatch/programming failures; accounting failures
  map to a safe domain error. Worker death can still strand a conservative reservation because the
  existing aggregate quota model has no persisted reservation ledger; adding one is out of scope.
- Empty standard retrieval costs zero; empty retrieval after successful HyDE costs only actual HyDE
  usage and returns the fixed no-context answer plus zero-count metadata.

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Bounded HyDE Generation](./phase-01-bounded-hyde-generation.md) | Completed |
| 2 | [HyDE Orchestration and Fallback](./phase-02-hyde-orchestration-and-fallback.md) | Completed |
| 3 | [API Metadata and Validation](./phase-03-api-metadata-and-validation.md) | Completed |

## Cross-Plan Dependencies

- Completed prerequisite: `260830-1525-rag-chat-engine` supplies the endpoint and accounting model.
- Working-tree prerequisite: preserve current uncommitted threshold/MMR changes in settings,
  Compose, vector retrieval, and tests; HyDE only extracts shared validation from that adapter.
- Related, not blocking: `260830-1608-part-1-endpoint-smoke-tests` explicitly excludes chat/HyDE.
- `blockedBy: []`: no unfinished plan must complete before this work.

## Acceptance Criteria

- [x] Strict toggle, standard path, HyDE success/fallback, empty retrieval, assignment-shaped metadata,
  owner isolation, status mappings, and single-settlement two-stage accounting are tested.
- [x] Standard and HyDE successes return additive grading metadata without provider details or logs.
- [x] A controlled-embedding Chroma evaluation exercises real similarity retrieval for baseline and
  HyDE text without claiming universal quality improvement for the production embedding model.
- [x] Settings, Compose, OpenAPI, README, and architecture docs match runtime behavior.

## Validation Commands

```bash
uv run pytest tests/rag -q
uv run pytest tests/smoke/test_configuration.py tests/smoke/test_compose_contracts.py tests/smoke/test_health.py -q
uv run ruff check apps config tests
uv run ruff format --check apps config tests
uv run python manage.py check --settings=config.settings.test
uv run python manage.py spectacular --settings=config.settings.test --file /tmp/ravid-openapi.yaml --validate
uv run pytest
docker compose config --quiet
```

Optional manual smoke: use only synthetic indexed documents and a credentialed OpenRouter free-tier
key; compare the same query with `use_hyde` false/true. It is not an offline acceptance gate.

## Open Questions

None. The public metadata and fallback/accounting decisions are fixed above.

## References

- Assignment: `docs/2026-08-30 R.A.V.I.D.md:197`
- HyDE paper: https://arxiv.org/html/2212.10496
- LangChain runnables: https://reference.langchain.com/python/langchain-core/runnables
- ChatOpenRouter: https://reference.langchain.com/python/langchain-openrouter/chat_models/ChatOpenRouter
- OpenRouter free router: https://openrouter.ai/docs/guides/routing/routers/free-router

## Validation Log

### Implementation Results - 2026-08-31

- Implemented all three phases and their public/API, retrieval, accounting, deployment, and
  documentation contracts.
- `uv run pytest`: 189 passed, 2 infrastructure-only tests skipped.
- Ruff check/format, Django system check, validated OpenAPI generation, Compose config, and
  `git diff --check` passed.

### Verification Results - 2026-08-31

- **Tier:** Standard (Fact Checker + Contract Verifier)
- **Claims checked:** 30
- **Verified:** 30 | **Failed:** 0 | **Unverified:** 0
- Verified assignment flow and API contract at `docs/2026-08-30 R.A.V.I.D.md:205` and
  `docs/2026-08-30 R.A.V.I.D.md:217`.
- Verified current production consumers: `ChatQueryView` is the sole `answer_query` caller;
  `RagService` is the sole production consumer of model construction, LCEL invocation, and
  owner-scoped retrieval.
- Verified current subscription, retrieval-filter, provider-error, prompt-bound, usage-settlement,
  serializer, response, OpenAPI, settings, Compose, README, and architecture-doc claims against the
  cited repository files.
- Resolved the prior timeout-unit uncertainty from installed `langchain-openrouter`: its
  `ChatOpenRouter.timeout` field is milliseconds and maps to SDK `timeout_ms`.
- **Failures:** None.

- Standard tier (3 phases): Fact Checker + Contract Verifier; initial factual claims verified against
  current files and consumers.
- Verified endpoint/serializer flow (`apps/rag/views.py:21`, `apps/rag/serializers.py:16`), service
  retrieval/accounting (`apps/rag/services.py:72`), provider LCEL adapter (`apps/rag/llm.py:23`),
  owner filter (`apps/documents/vector_store.py:88`), and quota settlement
  (`apps/accounts/entitlements.py:61`).
- Contract consumers verified: one production `answer_query` caller (`apps/rag/views.py:41`), one
  production model-builder caller (`apps/rag/services.py:98`), and existing focused tests listed in
  phase files.
- Hard-mode red team accepted corrections for accounting guarantees, ambiguous dispatch charging,
  provider-usage bounds, safe fallback handling, strict boolean handling, UTF-8/content bounds,
  grading-visible chunks, retrieval-setting preflight, and real retrieval evaluation.
  A persistent reservation ledger and provider-host allowlist were rejected as unrelated expansion.
- Post-red-team validation checked 30 claims: 27 verified, two contradictions corrected (bounded
  chunk-count semantics and additive accounting-error mapping), and one implementation-time wrapper
  timeout-unit check retained as an explicit Phase 1 gate.
- Whole-plan consistency sweep: four files reread; metadata, fallback, accounting, privacy, and test
  decisions reconciled; zero unresolved contradictions.

### Session 1 - 2026-08-31

**Trigger:** User-requested `/ck:plan validate` interview.
**Questions asked:** 1

#### Questions & Answers

1. **[API contract]** Should the plan retain retrieval metadata with bounded source excerpts on every
   successful response, including standard-mode requests?
   - Options: expanded diagnostic metadata | assignment-facing fields only while retaining fallback
   - **Answer:** Assignment-facing fields plus one generic fallback reason while retaining fallback.
   - **Custom input:** "just return field in the decription", "keep the fallback", and
     "keep fallback-reason"
   - **Rationale:** Match the assignment response surface without exposing internal fallback state;
     still return the hypothetical passage and final source chunks required for grading visibility.

#### Confirmed Decisions

- Every successful standard, HyDE, or fallback response returns `answer` plus only
  `retrieval_metadata.mode`, `hypothetical_passage`, nullable `fallback_reason`,
  `retrieved_chunks_count`, and `retrieved_chunks`.
- Expected HyDE generation failures/timeouts still run standard retrieval. Fallback is represented by
  `mode: "standard"`, `hypothetical_passage: null`, and `fallback_reason: "hyde_unavailable"`.

#### Action Items

- [x] Remove `requested_mode` and `fallback_applied`; keep one generic nullable `fallback_reason`.
- [x] Preserve bounded final source chunks for the explicit debugging/grading rule.
- [x] Propagate the minimal shape through service, serializer, OpenAPI, tests, and docs phases.

#### Impact on Phases

- Phase 2: simplified result DTO and fallback metadata; orchestration/accounting behavior unchanged.
- Phase 3: exact nested serializer/OpenAPI assertions now reject unrequested diagnostic fields.

#### Whole-Plan Consistency Sweep

- Files reread: `plan.md` and all three `phase-*.md` files.
- Decision deltas checked: response fields, fallback representation, chunk-count invariant.
- Reconciled stale references: expanded fallback fields removed; generic `fallback_reason` retained.
- Unresolved contradictions: 0.
