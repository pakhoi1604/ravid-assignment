---
phase: 3
title: "Extract RAG Contracts Accounting and Response Handling"
status: completed
priority: P1
dependencies: [2]
---

# Phase 3: Extract RAG Contracts Accounting and Response Handling

## Overview

Reduce `RagService` to top-level query orchestration by extracting immutable result contracts,
provider response parsing, and request-local stage accounting. Preserve all HyDE/final ordering,
charging, fallback, and safe-error semantics.

## Requirements

- Preserve standard/HyDE metadata, original-query final synthesis, fallback reasons, quota bounds,
  transport policy, malformed-usage handling, and API serialization.
- At most one terminal settlement call per stage during one `RagService` execution; no claim of
  crash-safe exactly-once settlement; no accounting-global monkeypatches in service
  tests; prompt dispatch and quota representations cannot drift.

## Architecture

```text
RagService -> prompts -> provider_responses
           -> RagStageAccounting -> accounts.entitlements
           -> immutable RagAnswer / RetrievalMetadata
```

Keep HyDE and final synthesis as private stages of one query use case. Inject accounting plus one
prompt specification per stage that binds values once and supplies both provider messages and a
canonical accounting serialization. Do not inject independently drifting dispatch/render seams.

## Related Code Files

| Action | File | Purpose |
| --- | --- | --- |
| Create | `apps/rag/contracts.py` | Frozen result and metadata DTOs with tuple chunks. |
| Create | `apps/rag/provider_responses.py` | Content normalization and usage classification. |
| Create | `apps/rag/accounting.py` | Reserve/finalize/refund one RAG stage. |
| Modify | `apps/rag/services.py` | Keep validation, stage order, retrieval, fallback, assembly. |
| Modify | `apps/rag/prompts.py` | Unify dispatch/bound prompt representation. |
| Modify | `apps/rag/serializers.py` | Preserve serialization after contract move. |
| Modify | `apps/rag/views.py` | Update internal imports only if required. |
| Modify | `tests/rag/test_services.py` | Inject fakes/spies and assert stage order. |
| Create | `tests/rag/test_accounting.py` | Cover every settlement path. |
| Create | `tests/rag/test_provider_responses.py` | Cover content/usage parsing. |
| Modify | `tests/rag/test_prompts.py` | Prove prompt equivalence. |
| Modify | `tests/rag/test_api.py` | Protect response/error contract. |
| Modify | `tests/smoke/test_health.py` | Protect OpenAPI schema. |

## Implementation Steps

1. **Tests Before:** characterize standard/no-context, HyDE success/fallback, quota rejection,
   retrieval failure after HyDE, malformed usage, transport, programming/accounting failures, and
   invalid returned content. Add a settlement failure matrix for reserve/finalize/refund covering
   attempted calls, API error precedence, exception chaining/logging, and persisted quota state.
2. Add tests for frozen contracts, provider blocks, UTF-8/size rules, usage classification, and
   prompt bound/dispatch equivalence.
3. **Refactor:** move contracts and pure parsing; add injected `RagStageAccounting` over existing
   account functions; move no persistence and add no durable ledger.
4. Inject accounting and one bound prompt specification per stage; remove accounting globals/parsing helpers from
   `services.py`; retain one `answer_query` surface and private stage methods.
5. **Tests After:** replace module-global monkeypatches with constructor fakes/spies; assert the
   hypothetical is retrieval-only and final synthesis receives only real owner chunks.
6. **Regression Gate:** run RAG, account, API/OpenAPI, lint, and format checks.

## Validation Commands

```bash
uv run pytest tests/rag/test_accounting.py tests/rag/test_provider_responses.py tests/rag/test_prompts.py -q
uv run pytest tests/rag/test_services.py tests/rag/test_api.py tests/smoke/test_health.py -q
uv run pytest tests/accounts tests/rag tests/smoke -q
rg -n "apps\.rag\.services\.(reserve|finalize|refund)" tests/rag
uv run ruff check apps/rag tests/rag tests/smoke
uv run ruff format --check apps/rag tests/rag tests/smoke
```

## Success Criteria

- [x] Result contracts are frozen and chunks are immutable tuples internally.
- [x] Content/usage parsing and accounting no longer live in `RagService`.
- [x] Each reserved HyDE/final stage makes at most one finalize or refund call in one service
  execution, including failure paths; durable exactly-once settlement remains deferred.
- [x] Tests inject collaborators instead of patching service accounting globals.
- [x] Prompt dispatch and reservation representations come from one bound prompt specification.
- [x] API/OpenAPI, HyDE fallback, quota, and safe-error behavior are unchanged.

## Risk Assessment

- Settlement timing can drift during extraction. Freeze call order before moving code; rollback the
  phase atomically if parity fails.
- Request-local settlement guards are not crash idempotency; document ambiguous finalize/refund
  failure states and durable reconciliation as deferred limitations.
- Never log prompts, hypothetical passages, retrieved chunks, provider payloads, or account data.
