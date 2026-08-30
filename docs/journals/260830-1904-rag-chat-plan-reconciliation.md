---
date: 2026-08-30
session: rag-chat-plan-current-state-reconciliation
---

# Journal: 2026-08-30 — RAG Chat Plan Current-State Reconciliation

## Context

The Part 2 RAG chat plan was reconciled with the repository after the modular LangChain refresh
and CPU-only Torch runtime work completed. This session changed planning artifacts only; no chat,
account, retrieval, or provider code was implemented.

## What Happened

- Replaced the generic entitlement concept with an explicit local `Subscription` model and a
  separate `DailyTokenUsage` model. These represent application access and daily quota, not paid
  billing.
- Kept Django's built-in user model for authentication while making subscription state explicit in
  seed data instead of deriving it from `User.is_active`.
- Updated the provider baseline to LangChain's dedicated OpenRouter integration and a free-only
  model selector, with no subscription purchase or paid-credit requirement.
- Reconciled prerequisites with the completed modular LangChain dependency refresh and CPU-only
  Torch runtime work; the independent Part 1 endpoint smoke plan remains optional reuse rather
  than a blocker.
- Fixed the API decisions at `403` for missing or inactive subscriptions, `429` for exhausted daily
  credit, deterministic `200` without an LLM call when owner-scoped retrieval finds no context, and
  `503` for safe provider or configuration failures.

## Reflection

The original phase split remained useful, but several boundaries needed to be made executable.
The revised plan now separates login state from product access, free-provider routing from local
quota accounting, and offline acceptance tests from credential-dependent live verification.

## Decisions Made

| Decision | Rationale | Impact |
| --- | --- | --- |
| Reserve a conservative token upper bound before the provider call, then finalize or refund only inside the reserved boundary | The quota gate must run before generation without permitting negative usage or unbounded post-call debt | Keeps daily accounting deterministic across success and failure paths |
| Serialize usage updates with PostgreSQL transactions, row locks, and a first-use uniqueness retry | Concurrent requests can otherwise overspend one user's daily limit | Makes the daily limit enforceable under request races |
| Apply the authenticated owner's metadata filter inside the native Chroma retriever | Application-side filtering could retrieve or expose another user's chunks | Preserves tenant isolation before context reaches the prompt |
| Use `openrouter/free` or an explicit `:free` model only | The assignment must remain usable without purchased model credit | Prevents the default reviewer workflow from silently routing to paid models |

## Next Steps

- Validate the reconciled plan as a whole, then implement its phases after confirming the working
  tree contains no unrelated dependency edits.
- Use mocked provider tests for deterministic CI and a newly rotated OpenRouter key only for the
  final live free-tier smoke test; never record or log the key.
