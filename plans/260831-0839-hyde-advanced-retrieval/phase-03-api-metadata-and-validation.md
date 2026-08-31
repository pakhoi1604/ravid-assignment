---
phase: 3
title: "API Metadata and Validation"
status: completed
priority: P1
dependencies: [2]
effort: "medium"
---

# Phase 3: API Metadata and Validation

## Context Links

- Current request/response serializers: `apps/rag/serializers.py:16`
- Authenticated endpoint and safe mappings: `apps/rag/views.py:18`
- API tests/schema checks: `tests/rag/test_api.py:25`, `tests/smoke/test_health.py:11`
- Documentation requiring scope correction: `README.md:3`, `docs/system-architecture.md:97`
- Assignment response example: `docs/2026-08-30 R.A.V.I.D.md:246`

## Overview

Publish the additive toggle/metadata contract, update generated OpenAPI and maintainer/reviewer docs,
then run focused and broad offline validation plus an optional synthetic live smoke.

## Requirements

<!-- Updated: Validation Session 1 - exact schema adds only one generic fallback_reason field. -->

- Functional: request accepts only JSON boolean `use_hyde`; omission defaults false. Strings,
  integers, null, arrays, and objects return the existing safe `400` shape.
- Functional: every successful standard/HyDE/fallback response contains `answer` and complete
  `retrieval_metadata` with only `mode`, `hypothetical_passage`, nullable `fallback_reason`,
  `retrieved_chunks_count`, and `retrieved_chunks`.
- Functional: serialize bounded owner-scoped chunk strings with count/order matching the chunks
  actually supplied to final synthesis.
- Non-functional: keep authentication and existing `400`/`401`/`403`/`429`/`503` responses; schema
  and docs must not claim HyDE remains out of scope.

## Architecture

`ChatQuerySerializer` adds a strict boolean field with `required=False, default=False`. DRF's default
BooleanField accepts non-boolean primitives, so a mandatory strict field must require
`type(data) is bool` while retaining a boolean OpenAPI schema. Nested response serializers model
the minimal metadata/chunk shape and mode/nullability for drf-spectacular. The view passes the validated
toggle to its sole `answer_query` caller and serializes the service result. Existing status/body
mappings remain stable; `RagAccountingError` joins the generic safe `503` branch. Additive metadata
intentionally changes prior exact-success tests and public schema while leaving error bodies stable.

## Related Code Files

- Modify: `apps/rag/serializers.py` - strict toggle plus minimal retrieval metadata response schema.
- Modify: `apps/rag/views.py` - pass toggle and serialize the additive service result.
- Modify: `tests/rag/test_api.py` - strict input, all success metadata modes, bounded fields, status
  regression coverage, and safe accounting failures.
- Modify: `tests/smoke/test_health.py` - OpenAPI request/response structure assertions.
- Modify: `README.md` - standard/HyDE examples, settings, fallback, accounting/privacy, optional smoke.
- Modify: `docs/system-architecture.md` - two-stage flow, trust boundary, fallback, and quota lifecycle.
- No change: URL routing, database models/migrations, dependencies, or lockfile.

## Implementation Steps

1. Add API tests for omitted/false/true toggle forwarding and rejection of every non-boolean JSON
   type, including `0`, `1`, `"true"`, and `null`.
2. Add response tests for standard, HyDE success, fallback, and empty retrieval. Assert exact field
   names/mode/nullability, fallback reason, count/chunk consistency, total content bounds, and absence
   of private exception/provider data or other fallback fields.
3. Implement the mandatory strict request field and nested response serializers; update `first_error`
   so toggle validation returns a stable generic request error without leaking internals.
4. Update the view's only service call with `use_hyde`, return serialized result metadata, and retain
   the current authentication and domain-error mapping branches.
5. Extend schema tests to inspect `use_hyde`, default/boolean type, minimal metadata/chunk schemas,
   mode/fallback values, and all existing response statuses; generate and validate OpenAPI.
6. Update README's live-chat instructions and configuration table/text. State that both query modes
   expose owner-scoped bounded chunks for grading, HyDE may fall back, responses must not be logged,
   and dispatched generation consumes quota independently from final synthesis.
7. Update architecture docs that currently mark HyDE out of scope. Document original vs hypothetical
   query roles, owner filtering, private-document/provider boundary, no retries, and empty-context
   accounting.
8. Run focused tests, Ruff, Django checks, schema validation, full pytest, and Compose config. Review
   diffs to ensure current threshold/MMR changes remain intact.
9. Optionally run a credentialed free-router comparison using only the repository's synthetic
   handbook; record observations as non-gating because free-router model choice/latency varies.

## Todo

- [x] Define strict request and nested response contracts in tests.
- [x] Wire toggle and metadata through the authenticated view.
- [x] Validate OpenAPI shape and existing safe status responses.
- [x] Correct README and architecture scope/security/accounting text.
- [x] Run focused, broad, and Compose validation; optional synthetic smoke only.

## Success Criteria

- [x] Omitted/false remains standard and true selects HyDE; no coercion ambiguity exists.
- [x] All `200` responses expose complete bounded grading metadata only to the authenticated owner.
- [x] Existing error status/body privacy and authenticated-user isolation remain unchanged.
- [x] OpenAPI, README, architecture docs, settings, and runtime contracts agree.
- [x] Offline suite passes; optional live variability is not represented as guaranteed improvement.

## Risk Assessment

- DRF boolean coercion may accept unintended inputs. Mitigation: strict custom field plus parameterized
  API tests.
- Schema/runtime drift may add or omit fields. Mitigation: nested serializers and exact structural
  OpenAPI assertions.
- Grading metadata returns private document excerpts. Mitigation: existing authentication/owner
  filter, shared context-size bound, no logs, and cross-user negative tests.

## Security Considerations

Authentication remains `IsAuthenticated`; the request never supplies an owner identifier. Metadata
contains bounded document excerpts and identifiers, which are owner-scoped and must never cross
users. Do not log response metadata, credentials, provider errors, or private live-smoke content.

## Next Steps

After all gates pass, perform the Standard-tier whole-plan consistency sweep. Implement with
`/ck:cook plans/260831-0839-hyde-advanced-retrieval/plan.md`; no unresolved product decision remains.
