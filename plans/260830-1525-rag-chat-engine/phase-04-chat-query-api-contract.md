---
phase: 4
title: "Chat Query API Contract"
status: completed
priority: P1
dependencies: [1, 2, 3]
effort: "M"
---

# Phase 4: Chat Query API Contract

## Context Links

- Assignment endpoint: `docs/2026-08-30 R.A.V.I.D.md`
- Existing DRF pattern: `apps/documents/views.py`, `apps/documents/serializers.py`
- Root routing: `config/urls.py`
- OpenAPI smoke: `tests/smoke/test_health.py`

## Overview

Expose the required authenticated endpoint with the repository's existing APIView/serializer
patterns, stable safe errors, and explicit OpenAPI coverage.

## Requirements

- `POST /api/chat/query/` accepts only a required non-blank string `query`.
- Success, including deterministic no-context behavior, returns `200 {"answer": "..."}`.
- The request cannot choose user, document, filter, model, or token budget.
- API tests remain offline and mock only the Phase 3 service boundary.

## Architecture

- `ChatQuerySerializer`: trim and validate `query`, maximum 2000 characters.
- `ChatAnswerSerializer`: document the exact success body.
- `ChatQueryView(APIView)`: explicit `IsAuthenticated`, local `first_error`, and
  `RagService().answer_query(user=request.user, query=...)`.
- `apps.rag.urls`: named `chat-query`; `config.urls`: mount at `api/chat/`.

Error contract:

| Condition | Status | Body |
| --- | --- | --- |
| Missing/blank/too-long query | 400 | `{"error": "..."}` |
| Unauthenticated | 401 | DRF default authentication body |
| Missing/inactive subscription | 403 | `{"error": "Active subscription required."}` |
| Daily quota exhausted | 429 | `{"error": "Insufficient daily token credits."}` |
| Empty owner-scoped retrieval | 200 | `{"answer": "I could not find relevant information in your uploaded documents."}` |
| Provider configuration unavailable | 503 | `{"error": "LLM provider is not configured."}` |
| Known provider/retrieval failure | 503 | `{"error": "Unable to generate answer right now."}` |

`402` is intentionally not used: this plan has no payment transaction or payment provider. Empty
retrieval is not `404` because the endpoint exists and returns a valid grounded no-answer result.

## Related Code Files

- Create: `apps/rag/serializers.py` - request/response validation and `first_error`.
- Create: `apps/rag/views.py` - endpoint and domain-error mapping.
- Create: `apps/rag/urls.py` - application route.
- Modify: `config/urls.py` - include `api/chat/`.
- Create: `tests/rag/test_api.py` - HTTP contract.
- Modify: `tests/smoke/test_health.py` - assert OpenAPI path/method/schemas.

## Implementation Steps

1. Add request/response serializers and trim the query during validation.
2. Implement `ChatQueryView` with explicit `IsAuthenticated`; pass the user object from the JWT
   request, never a payload identifier.
3. Catch only known subscription/quota/RAG exceptions and map them to the table above. Do not catch
   programming errors as normal API responses.
4. Mount the named route at exactly `/api/chat/query/`.
5. Add `@extend_schema` request, success, and error response definitions.
6. Add API tests for 401; missing/blank/whitespace/too-long 400; success 200; subscription 403;
   quota 429; fixed no-context 200; configuration/provider/retrieval 503; and user propagation.
7. Assert error bodies do not expose exception text, provider responses, retrieved content, or
   credentials.
8. Extend schema tests to inspect `paths["/api/chat/query/"]["post"]`, request schema, and 200
   response. Run drf-spectacular validation.

## Tests Before

- Add failing `tests/rag/test_api.py`; initial `reverse("chat-query")` should not resolve.

## Tests After

- `uv run pytest tests/rag/test_api.py tests/smoke/test_health.py`
- `uv run python manage.py spectacular --settings=config.settings.test --file /tmp/ravid-openapi.yaml --validate`
- `uv run python manage.py check --settings=config.settings.test`

## Success Criteria

- [x] Endpoint resolves at exactly `/api/chat/query/` and requires JWT auth.
- [x] Request/success shapes match the assignment.
- [x] Subscription, quota, no-context, and service-failure behavior matches the table.
- [x] No request field can influence owner scope or provider configuration.
- [x] OpenAPI includes and validates the POST operation and its 200 response.

## Risk Assessment

- `429` can also represent provider rate limits. The local quota response is deterministic; upstream
  free-tier availability is mapped to generic 503 to avoid conflating ownership.
- API tests can over-mock orchestration. Keep accounting/retrieval/provider behavior in Phase 1-3
  tests and HTTP mapping only here.

## Security Considerations

- Authenticate before accessing subscription, vectors, or provider services.
- Never return retrieved chunks, internal IDs, provider payloads, or stack traces.
