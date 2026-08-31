---
phase: 2
title: "HyDE Orchestration and Fallback"
status: completed
priority: P1
dependencies: [1]
effort: "high"
---

# Phase 2: HyDE Orchestration and Fallback

## Context Links

- Existing orchestration: `apps/rag/services.py:58`
- Atomic quota operations: `apps/accounts/entitlements.py:61`
- Owner-filtered retrieval: `apps/documents/vector_store.py:107`
- Existing service tests: `tests/rag/test_services.py:42`
- HyDE method: https://arxiv.org/html/2212.10496

## Overview

Extend `RagService` with an optional HyDE branch, narrow fallback, safe retrieval metadata, and
two independent conservatively settled token reservations while preserving standard behavior and
user isolation.

## Requirements

<!-- Updated: Validation Session 1 - keep fallback and one generic fallback_reason field. -->

- Functional: `answer_query(..., use_hyde=False)` retrieves with the raw query and never calls HyDE;
  true generates a hypothetical, retrieves with it, and always gives the final prompt the original
  query plus real chunks only.
- Functional: return only assignment-facing metadata for standard, HyDE, fallback, and empty
  retrieval plus the requested fallback field: `mode`, `hypothetical_passage`, nullable
  `fallback_reason`, `retrieved_chunks_count`, and `retrieved_chunks`. Each chunk is a bounded string
  from final synthesis; total returned text cannot exceed the final-context character bound.
- Functional: fallback only on HyDE timeout/transport or empty/invalid/oversized content. Preserve
  fallback behavior through effective `mode: "standard"`, a null hypothetical, and the single stable
  reason `hyde_unavailable`; do not return provider-specific classification.
- Non-functional: preserve auth/subscription ordering, owner-scoped adapter, existing `403`/`429`/
  `503` semantics, threshold/MMR behavior, and zero retries. Configuration errors remain `503`;
  programming errors propagate.

## Architecture

After subscription/provider validation, preflight retrieval settings before any HyDE reservation so
the dirty threshold/MMR configuration cannot fail after a paid generation. Standard mode then
proceeds directly to retrieval. HyDE mode renders and reserves a conservative generation bound,
builds the model, and invokes LCEL. Pre-dispatch configuration failure refunds and re-raises. An
ambiguous timeout/transport outcome conservatively finalizes at the reserved bound before fallback.
When a message exists, validate provider usage against the reservation and settle before validating
content; invalid/oversized/unsupported content therefore remains billable before baseline fallback.
Do not wrap the whole path in a blanket exception handler.

Treat provider usage as untrusted: a nonnegative value within the reserved bound is accepted;
missing usage uses the existing deterministic fallback; malformed and over-bound usage settle no
more than the reservation, record an internal anomaly without content, and follow the safe provider
failure path. Refactor extraction to preserve this missing/malformed distinction. A pending-reservation
guard refunds an unexpected exception before dispatch/response
and re-raises the original programming error. Settlement-operation failures become a safe
`RagAccountingError`/`503`; no second blind settlement attempt is made.

Extract retrieval-setting validation from the current vector adapter so service preflight and
`retrieve_for_user(user_id, query, k)` share one rule set; preserve native owner filtering and the
uncommitted search strategy behavior. Empty retrieval returns the fixed answer immediately. A valid
HyDE passage retains actual usage and passage metadata; an expected post-dispatch/content fallback
retains conservative or actual generation usage with a null passage. Standard mode uses zero before
retrieval. Non-empty retrieval uses the existing final synthesis and its separate reservation.
The second reservation can return `429` after a successful HyDE call; that accurately records already
consumed provider usage.

Metadata state is exact: standard and fallback return `mode: "standard"` with
`hypothetical_passage: null`; standard uses `fallback_reason: null`, while fallback uses
`fallback_reason: "hyde_unavailable"`. Successful HyDE returns `mode: "hyde"`, the generated passage,
and `fallback_reason: null`.
`retrieved_chunks` is the exact ordered, bounded string list supplied to synthesis, including any
final truncated excerpt, and `retrieved_chunks_count = len(retrieved_chunks)`; omitted documents are
not counted. The API intentionally does not distinguish requested-standard from HyDE fallback.

## Related Code Files

- Modify: `apps/rag/services.py` - mode selection, generation/fallback, minimal metadata DTOs,
  and independent reservation lifecycles.
- Modify: `apps/rag/exceptions.py`, `apps/rag/views.py` - safe accounting failure contract/mapping.
- Modify: `apps/rag/tokens.py` - bound provider usage to the conservative reservation.
- Modify: `apps/documents/vector_store.py` - shared retrieval-setting validation/preflight while
  preserving current uncommitted threshold/MMR behavior.
- Modify: `tests/rag/test_services.py` - orchestration, isolation arguments, fallback matrix, empty
  retrieval, quota sequencing, single settlement, and exact metadata shape.
- Modify: `tests/rag/test_tokens.py`, `tests/documents/test_vector_retrieval.py` - usage bounds and
  retrieval preflight/error normalization.
- Create: `tests/rag/test_hyde_retrieval.py` - controlled-embedding Chroma comparison.
- Reuse unchanged: `apps/accounts/entitlements.py` and database models/migrations.

## Implementation Steps

1. Add tests for omitted/false mode proving one raw-query retrieval and zero HyDE model invocations.
2. Add HyDE-success tests proving generation before retrieval, hypothetical retrieval input, original
   final question, real-only context, bounded returned chunks, and total usage settlement.
3. Add a parameterized fallback matrix for timeout, non-timeout transport, empty/unsupported output,
   invalid UTF-8, and oversized output. Assert conservative dispatch charging or returned-message
   settlement, raw-query retrieval, effective standard mode, null passage, stable fallback reason,
   and no provider detail.
4. Add negative tests: `RagConfigurationError` refunds pre-dispatch and remains a `503`; unrelated
   programming errors propagate after pending-reservation cleanup; settlement failures map safely;
   retries are not added.
5. Add accounting tests for HyDE quota rejection before call (`429`), final-stage reservation `429`
   after successful HyDE, successful HyDE followed by retrieval/final failure, over-bound provider
   usage, and one finalize/refund call per in-process outcome. Assert dispatched generation remains
   charged after later failure.
6. Add empty-retrieval tests: standard has no usage/model call; HyDE success retains only actual HyDE
   usage and returns count zero. Cover retrieval failure after successful HyDE similarly.
7. Add a controlled embedding function and actual Chroma similarity-selection fixture where the raw
   question and hypothetical passage rank different synthetic chunks. Mark infrastructure needs
   explicitly; call service fakes orchestration tests, not retrieval evaluation.
8. Implement immutable result/metadata/chunk structures and small helpers for generation,
   retrieval, and settlement; keep `answer_query` orchestration readable and existing injected
   factories usable by offline tests.
9. Bound returned chunk strings using the same selected, truncated real context used for synthesis;
   never log them.
10. Run service, token, account, and document retrieval suites to prove no isolation/accounting
    regression.

## Todo

- [x] Protect standard path before refactor.
- [x] Implement bounded HyDE generation and narrow fallback.
- [x] Preserve owner filter and real-only evidence path.
- [x] Implement bounded grading metadata and conservative single settlement.
- [x] Add controlled-embedding comparative retrieval evaluation and failure matrix.

## Success Criteria

- [x] Standard mode has no HyDE latency/cost and preserves raw-query retrieval.
- [x] Standard, HyDE success, and fallback return the declared effective `mode` value.
- [x] Hypothetical text never enters final context; returned real chunks are owner-scoped and bounded.
- [x] Every in-process generation outcome invokes settlement once; ambiguous dispatch and returned
  invalid content remain charged, and later failures do not erase successful HyDE usage.
- [x] Existing owner-isolation and threshold/MMR tests remain green without vector API changes.

## Risk Assessment

- The aggregate quota API is not crash-idempotent. Mitigation: separate stage state, pending guards,
  single-settlement tests, and explicit acceptance that worker death can strand the bound; a durable
  reservation ledger is deferred.
- Fallback can accidentally mask defects. Mitigation: enumerate only expected provider/content cases.
- HyDE may worsen retrieval for some queries/models. Mitigation: toggle defaults off, report effective
  mode, run controlled-embedding retrieval comparison, and make no universal accuracy claim.

## Security Considerations

Pass authenticated `user.id` internally exactly as today; never accept an owner from request data.
Treat query/hypothetical as untrusted, use only retrieved real chunks as evidence, and return bounded
real chunks only to that owner. Do not include exception strings or provider details in metadata or
logs.

## Next Steps

Phase 3 exposes the service contract through strict serializers/OpenAPI and completes documentation
and repository-wide validation.
