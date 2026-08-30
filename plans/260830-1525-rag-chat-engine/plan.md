---
title: "Part 2: RAG Chat Engine"
description: "Implement authenticated RAG querying with owner-scoped vector retrieval, OpenRouter answer generation, and subscription/token-credit gates."
status: pending
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

Implement Part 2 of the RAVID assignment on top of the completed Part 1 ingestion pipeline.
The deliverable is `POST /api/chat/query/`: authenticate the caller, verify an active local
subscription entitlement and sufficient daily token credits, retrieve only that user's indexed
document chunks, call an OpenRouter-backed LangChain chat model, debit token usage, and return a
plain answer.

Bonus HyDE, real payment gateway integration, streaming responses, conversation memory, and
multi-tenant admin billing are out of scope for this plan.

## Scope Challenge

- Existing code: `apps.rag` exists as a stub; `apps.documents.vector_store.DocumentVectorStore`
  already builds the Chroma/LangChain vector store; document chunks already include `user_id`,
  `document_id`, `chunk_index`, and `source_filename` metadata; JWT auth is wired globally.
- Minimum change set: account entitlement/usage models, retriever method, RAG service boundary,
  chat serializer/view/url, config/environment docs, focused tests.
- Complexity: expected 12-16 touched files and two account data models. This is justified because
  the assignment requires both access gating and a public RAG API; compressing into fewer files would
  mix persistence, provider calls, and HTTP concerns.
- Selected mode: HOLD SCOPE, hard planning depth. No external research required beyond local docs.

## Architecture Decisions

- Keep Django's built-in `User`; add local account-side entitlement and daily usage tables instead
  of introducing a custom user model.
- Treat subscription/payment as local entitlement state for Part 2. Actual payment gateway work
  remains a separate Part 4/future plan unless the user expands scope.
- Reserve estimated tokens before the LLM call, refund on provider failure, and reconcile to actual
  provider usage when LangChain exposes it.
- Use `langchain-openai` `ChatOpenAI` against `OPENROUTER_BASE_URL`; do not hand-roll HTTP unless
  LangChain integration blocks the assignment.
- Keep all provider imports lazy so unit tests and local checks pass without provider credentials or
  network access.
- Return only `{"answer": "<answer text>"}` for baseline Part 2. Retrieval metadata is deferred to
  HyDE/Part 3.

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Account Entitlement and Credit Gate](./phase-01-account-entitlement-and-credit-gate.md) | Pending |
| 2 | [Vector Retriever Service](./phase-02-vector-retriever-service.md) | Pending |
| 3 | [OpenRouter RAG Answer Pipeline](./phase-03-openrouter-rag-answer-pipeline.md) | Pending |
| 4 | [Chat Query API Contract](./phase-04-chat-query-api-contract.md) | Pending |
| 5 | [Validation Documentation and Reviewer Workflow](./phase-05-validation-documentation-and-reviewer-workflow.md) | Pending |

## Dependencies

- Completed prerequisite: `plans/260830-1329-document-management-vector-storage/`.
- Completed foundation: `plans/260830-1115-ravid-backend-skeleton/`.
- Requirement source: `docs/2026-08-30 R.A.V.I.D.md`.
- No blocking relationship with unfinished `plans/260830-1417-migrate-claude-hooks-to-codex/`; it
  affects agent tooling only.
- Runtime provider: OpenRouter-compatible API configured by existing OpenRouter settings.

## Acceptance Criteria

- [ ] `POST /api/chat/query/` requires JWT auth and accepts JSON body `{"query": "<question>"}`.
- [ ] Requests fail before retrieval/LLM when the user has no active entitlement.
- [ ] Requests fail before retrieval/LLM when estimated prompt + answer budget exceeds remaining
      daily credits.
- [ ] Retrieval uses the existing Chroma collection and filters by authenticated `user_id`.
- [ ] User A cannot retrieve context from User B's documents.
- [ ] Successful requests call OpenRouter through LangChain and return
      `200 {"answer": "<answer text>"}`.
- [ ] LLM/provider/config failures return safe 5xx responses and refund any pre-reserved credits.
- [ ] Unit/API tests cover success, invalid body, auth, inactive subscription, insufficient credits,
      owner isolation, empty retrieval, provider failure, and token accounting.
- [ ] OpenAPI docs and README show the Part 2 request/response and required environment settings.
- [ ] Validation commands pass under `config.settings.test` without network access.

## Validation Commands

```bash
uv run python manage.py makemigrations --check --dry-run --settings=config.settings.test
uv run python manage.py check --settings=config.settings.test
uv run pytest tests/accounts tests/documents tests/rag tests/smoke
docker compose config --quiet
```

## Open Questions

None. This plan assumes Part 2 should implement local subscription/credit enforcement only, not a
real payment provider.

## Validation Log

### Planner Fact Check

- Verified: `apps.rag` exists as an installed app in `config/settings/base.py`.
- Verified: `config/urls.py` currently includes `api/documents/` but not `api/chat/`.
- Verified: `apps.documents.vector_store.DocumentVectorStore` currently supports writes only; read
  retrieval must be added.
- Verified: Part 1 chunk metadata includes `user_id`, `document_id`, `chunk_index`, and
  `source_filename`.
- Verified: OpenRouter base/model/key settings already exist in base settings and environment
  template.
