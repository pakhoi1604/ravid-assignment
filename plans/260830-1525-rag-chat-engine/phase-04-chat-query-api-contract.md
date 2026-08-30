---
phase: 4
title: "Chat Query API Contract"
status: pending
priority: P1
dependencies: [1, 2, 3]
effort: "M"
---

# Phase 4: Chat Query API Contract

## Overview

Expose the Part 2 public API endpoint with DRF serializers, owner/auth enforcement, deterministic
error shapes, and OpenAPI coverage.

## Requirements

- Functional: `POST /api/chat/query/` accepts JSON body with required string `query`.
- Functional: success response is `200 {"answer": "<generated answer>"}`.
- Functional: invalid input returns `400 {"error": "<message>"}`.
- Functional: inactive subscription or insufficient credits returns a client-safe non-2xx response
  before RAG work.
- Functional: missing context and provider/config failures return stable safe errors.
- Non-functional: API tests must not require OpenRouter, Chroma, Redis, or Celery.

## Architecture

Create a conventional DRF endpoint under `apps.rag`:

- `serializers.py`: `ChatQuerySerializer`, `ChatAnswerSerializer`, and `first_error` helper.
- `views.py`: `ChatQueryView(APIView)` with `IsAuthenticated`.
- `urls.py`: `path("query/", ChatQueryView.as_view(), name="chat-query")`.
- `config/urls.py`: `path("api/chat/", include("apps.rag.urls"))`.

Error mapping:

| Condition | Status | Body |
| --- | --- | --- |
| Missing/blank/too-long `query` | 400 | `{"error": "query is required."}` or validation message |
| Unauthenticated | 401 | DRF default auth body |
| Inactive entitlement | 402 | `{"error": "Active subscription required."}` |
| Insufficient credits | 402 | `{"error": "Insufficient daily token credits."}` |
| No retrieved context | 404 | `{"error": "No indexed context found for this query."}` |
| OpenRouter not configured | 503 | `{"error": "LLM provider is not configured."}` |
| Provider/retrieval failure | 503 | `{"error": "Unable to generate answer right now."}` |

Use `402 Payment Required` for subscription and credit failures because the assignment frames the
gate as subscription and daily credits.

## Related Code Files

- Create: `apps/rag/serializers.py` - request/response validation.
- Create: `apps/rag/views.py` - endpoint controller and error mapping.
- Create: `apps/rag/urls.py` - app route.
- Modify: `config/urls.py` - include `api/chat/`.
- Create: `tests/rag/test_api.py` - public API contract.
- Modify: `tests/smoke/test_health.py` or add schema test - confirm OpenAPI includes chat route.

## Implementation Steps

1. Add `ChatQuerySerializer` with:
   - `query = serializers.CharField(required=True, allow_blank=False, max_length=2000)`.
2. Normalize validation errors with a local `first_error` helper matching the documents app pattern.
3. Implement `ChatQueryView.post`:

   ```python
   serializer = ChatQuerySerializer(data=request.data)
   if not serializer.is_valid():
       return Response({"error": first_error(serializer)}, status=400)
   answer = RagService().answer_query(user=request.user, query=serializer.validated_data["query"])
   return Response({"answer": answer.answer}, status=200)
   ```

4. Catch account/RAG exceptions explicitly and map them to the status table above.
5. Register `apps.rag.urls` under `api/chat/` in `config/urls.py`.
6. Add `@extend_schema` annotations so `/api/schema/` documents request and response examples.
7. Add API tests with monkeypatched `RagService.answer_query`:
   - unauthenticated request returns 401;
   - missing query returns 400;
   - valid request returns 200 answer;
   - inactive subscription maps to expected error;
   - insufficient credits maps to expected error;
   - no context maps to 404;
   - provider/config failure maps to 503;
   - service receives `request.user`, not a user ID from payload.
8. Add a schema assertion that `POST /api/chat/query/` appears in OpenAPI output.

## Tests Before

- Add failing `tests/rag/test_api.py` before implementing endpoint files.
- Expected initial failure: `reverse("chat-query")` does not resolve.

## Tests After

- `uv run pytest tests/rag/test_api.py`
- `uv run pytest tests/smoke/test_health.py`
- `uv run python manage.py check --settings=config.settings.test`

## Success Criteria

- [ ] `POST /api/chat/query/` route resolves under `/api/chat/query/`.
- [ ] Endpoint requires JWT auth through existing DRF settings.
- [ ] Request and response shapes match Part 2 assignment.
- [ ] Error responses are stable and do not leak provider/internal details.
- [ ] OpenAPI schema includes the chat endpoint.

## Risk Assessment

- Risk: 402 may surprise clients because many APIs use 403 for inactive subscription. Mitigation:
  document the choice in tests and README; 402 is semantically aligned with subscription/credit
  failure.
- Risk: API tests over-mock service behavior. Mitigation: Phase 3 service tests cover orchestration;
  API tests focus on HTTP contract and exception mapping.

## Security Considerations

- Do not accept `user_id`, `document_id`, metadata filter, model name, or token budget from request.
- Keep all chat API views authenticated.
- Avoid returning retrieved context in baseline Part 2 response.
