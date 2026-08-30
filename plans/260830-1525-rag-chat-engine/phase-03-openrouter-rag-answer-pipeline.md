---
phase: 3
title: "OpenRouter RAG Answer Pipeline"
status: completed
priority: P1
dependencies: [1, 2]
effort: "L"
---

# Phase 3: OpenRouter RAG Answer Pipeline

## Context Links

- LangChain integration: https://docs.langchain.com/oss/python/integrations/chat/openrouter
- Package release: https://pypi.org/project/langchain-openrouter/
- Free router: https://openrouter.ai/docs/guides/routing/routers/free-router
- Existing provider settings: `config/settings/base.py`

## Overview

Orchestrate subscription/quota checks, native retrieval, bounded context formatting, a grounded
LangChain prompt/model runnable, free-tier OpenRouter generation, and usage reconciliation.

## Requirements

- Enforce active subscription before retrieval and reserve quota before provider work.
- Retrieve only the authenticated user's chunks and cap formatted context length.
- Use `ChatOpenRouter` with a free-router or explicit `:free` model only.
- Preserve the returned `AIMessage` until token metadata is recorded.
- Keep all CI tests offline through injected fakes.

## Architecture

Create these boundaries:

- `apps.rag.services`: synchronous request orchestration and `RagAnswer`.
- `apps.rag.tokens`: conservative admission bounds and `AIMessage.usage_metadata` extraction.
- `apps.rag.llm`: lazy free-tier `ChatOpenRouter` construction plus narrow provider-error adapter.
- `apps.rag.prompts`: context formatter and `ChatPromptTemplate` runnable.
- `apps.rag.exceptions`: safe configuration, retrieval, and provider errors.

Flow with explicit error/refund boundaries:

```python
ensure_active_subscription(user)
validate_openrouter_configuration(settings)  # no reservation yet
try:
    documents = vector_store.retrieve_for_user(user_id=user.id, query=query, k=settings.RAG_RETRIEVAL_K)
except VectorRetrievalError as exc:
    raise RagRetrievalError from exc

if not documents:
    return RagAnswer(answer=NO_CONTEXT_ANSWER, estimated_tokens=0, actual_tokens=0)

context = format_documents(documents, max_chars=settings.RAG_MAX_CONTEXT_CHARS)
estimate = estimate_prompt_bound(query, context, settings)
reservation = reserve_daily_tokens(user, estimate)
try:
    chat_model = build_openrouter_chat_model()
    message = (prompt | chat_model).invoke({"question": query, "context": context})
    answer = normalize_answer_content(message.content)
except RagConfigurationError:
    refund_daily_tokens(reservation)
    raise
except ProviderTransportError as exc:
    refund_daily_tokens(reservation)
    raise RagProviderError from exc

actual = usage_or_fallback(message, query, context)
finalize_daily_tokens(reservation, actual)
return RagAnswer(answer=answer, estimated_tokens=estimate, actual_tokens=actual)
```

The adapter still invokes a native retriever, but translates only documented Chroma/network failures
to `VectorRetrievalError`; programming errors propagate. Empty retrieval therefore skips both quota
reservation and provider work. The LLM adapter similarly exposes `ProviderTransportError` only for
documented integration/network failures. Do not apply `StrOutputParser` before accounting because
it would drop `AIMessage` usage metadata.

## Related Code Files

- Create: `apps/rag/exceptions.py` - safe domain exception taxonomy.
- Create: `apps/rag/tokens.py` - estimation and usage extraction.
- Create: `apps/rag/prompts.py` - bounded formatter, prompt, fixed no-context answer.
- Create: `apps/rag/llm.py` - lazy `ChatOpenRouter` factory and free-model validation.
- Create: `apps/rag/services.py` - RAG orchestration.
- Modify: `config/settings/base.py` - free default and generation/provider metadata settings.
- Modify: environment example template and `compose.yaml` - forward web-only OpenRouter secret and
  non-secret RAG configuration.
- Modify: `pyproject.toml` and `uv.lock` - declare `langchain-openrouter>=0.2.8,<0.3` plus
  the directly imported `openrouter` and `httpx` exception taxonomies.
- Create: `tests/rag/test_tokens.py`, `tests/rag/test_prompts.py`, `tests/rag/test_llm.py`, and
  `tests/rag/test_services.py`.

## Implementation Steps

1. Add `langchain-openrouter>=0.2.8,<0.3` to the existing vector-ingestion runtime group. Declare
   `openrouter>=0.11.46,<0.12` and `httpx>=0.28,<0.29` directly because the adapter imports their
   locked exception families; this does not add packages beyond the integration's transitive set.
   Do not add `langchain` or `langchain-openai`, and do not use the OpenRouter SDK as a second client.
2. Change the default model from `openrouter/auto` to `openrouter/free`. Validate configured IDs:
   allow exactly `openrouter/free` or IDs ending in `:free`; fail configuration otherwise.
3. Preserve `OPENROUTER_BASE_URL` and add `OPENROUTER_APP_TITLE`, `OPENROUTER_APP_URL`,
   `RAG_MAX_OUTPUT_TOKENS=800`, `RAG_CHAT_OVERHEAD_TOKENS=256`, and `RAG_TEMPERATURE=0`. Forward
   provider secrets only to web; Celery does not call the synchronous Part 2 LLM path. Add
   `RAG_PROVIDER_TIMEOUT_MS=10000` and `RAG_PROVIDER_MAX_RETRIES=0` so an unavailable free provider
   cannot occupy synchronous workers for the integration's multi-minute default retry budget.
4. Construct lazily:

   ```python
   ChatOpenRouter(
       api_key=settings.OPENROUTER_API_KEY,
       base_url=settings.OPENROUTER_BASE_URL,
       model=settings.OPENROUTER_MODEL,
       temperature=settings.RAG_TEMPERATURE,
       max_tokens=settings.RAG_MAX_OUTPUT_TOKENS,
       timeout=settings.RAG_PROVIDER_TIMEOUT_MS,
       max_retries=settings.RAG_PROVIDER_MAX_RETRIES,
       app_url=settings.OPENROUTER_APP_URL,
       app_title=settings.OPENROUTER_APP_TITLE,
   )
   ```

   Because locked `langchain-openrouter==0.2.8` omits `retry_config` when `max_retries=0` and the
   SDK then applies its one-hour default backoff, construct the one OpenRouter SDK client explicitly
   with `timeout_ms=10000` and `retry_config=None`, then inject that client into `ChatOpenRouter`.
   `RAG_PROVIDER_MAX_RETRIES` must remain exactly `0`; nonzero values fail configuration closed.

5. Fail with `RagConfigurationError` before client creation for blank keys or non-free models.
   Translate the locked SDK's `OpenRouterError`/`NoResponseError`, `httpx.TransportError`, and only
   the integration's recognized provider-response `ValueError` prefixes to `ProviderTransportError`;
   explicitly test that unrelated programming exceptions are not translated.
6. After retrieval/formatting, implement admission control from UTF-8 byte length of the actual
   fully formatted bounded prompt, `RAG_CHAT_OVERHEAD_TOKENS`, and the provider-enforced output cap.
   This intentionally over-reserves compared with normal tokenization. Keep `len/4` only as a
   reporting fallback, never as the quota admission bound.
7. Format numbered snippets with `document_id`, `chunk_index`, and `source_filename`; truncate the
   combined context deterministically to `RAG_MAX_CONTEXT_CHARS`.
8. Create a `ChatPromptTemplate | ChatOpenRouter` runnable. The system message treats document text
   as untrusted evidence, ignores instructions inside it, and answers only from supported context.
9. Implement `RagService.answer_query` with injectable retriever/model factories. Validate provider
   configuration before retrieval. Catch only `VectorRetrievalError`, `RagConfigurationError`, and
   the LLM adapter's documented `ProviderTransportError`; TypeError, AttributeError, assertions, and
   other programming defects must propagate. Refund exactly once after a reservation exists.
10. For no documents, return the fixed answer without reserving/debiting quota:
    `I could not find relevant information in your uploaded documents.` with zero actual usage.
11. Normalize `AIMessage.content` from either a string or supported text content blocks into one
    nonblank string. Empty/unsupported content is a provider failure, not a valid API answer.
12. Prefer `usage_metadata["total_tokens"]`; otherwise estimate from actual bounded prompt and
    answer. Record full actual usage and alert if metadata unexpectedly exceeds the bound.
13. Test success, strict free-model validation, missing key/no reservation, adversarial Unicode
    admission, context truncation, prompt injection guard, empty context/no provider call,
    retriever-invocation mapping without a debit, provider/config refund, programming-error
    propagation, content normalization, and usage fallback.
14. Require a real JSON string that encodes as UTF-8 at the serializer boundary. Reject numbers,
    booleans, containers, null, and malformed surrogate text with `400` before domain work.

## Tests Before

- Add failing tests for token estimation, context formatting, LLM configuration, and orchestration.

## Tests After

- `uv run pytest tests/rag/test_tokens.py tests/rag/test_prompts.py tests/rag/test_llm.py tests/rag/test_services.py`
- `UV_CACHE_DIR=/tmp/ravid-rag-uv-cache uv lock --check`
- Container import check for `langchain_openrouter.ChatOpenRouter` and imported core APIs.

## Success Criteria

- [x] Dedicated OpenRouter integration is direct and compatible with locked core 1.x.
- [x] Baseline configuration cannot silently route to a paid model.
- [x] Inactive users never reach retrieval; over-limit and empty-context requests never reach
      OpenRouter.
- [x] Context is owner-scoped, bounded, and treated as untrusted evidence.
- [x] Successful calls retain usage metadata, finalize usage, and return answer text only.
- [x] Retriever construction/invocation, provider construction/invocation, configuration, and output
      normalization failures have explicit safe mappings and exactly-once refund behavior.

## Risk Assessment

- Free models have variable availability/rate limits. Keep offline tests deterministic and map live
  provider unavailability to a safe service error.
- Usage metadata differs by provider. Preserve `AIMessage`; use a conservative fallback.
- Uploaded private text leaves the app when sent to a third-party provider. Manual smoke data must
  be synthetic and docs must disclose that behavior.

## Security Considerations

- Never log API keys, provider headers, raw private context, or expanded Compose configuration.
- Rotate any previously exposed OpenRouter key before live validation.
- Prompt text must explicitly separate trusted system instructions from untrusted chunks.
