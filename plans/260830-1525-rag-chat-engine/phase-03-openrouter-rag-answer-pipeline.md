---
phase: 3
title: "OpenRouter RAG Answer Pipeline"
status: pending
priority: P1
dependencies: [1, 2]
effort: "L"
---

# Phase 3: OpenRouter RAG Answer Pipeline

## Overview

Build the RAG service that estimates credits, retrieves context, composes a guarded prompt, calls
OpenRouter through LangChain, and reconciles token usage.

## Requirements

- Functional: answer a natural-language query using retrieved chunks from the caller's documents.
- Functional: use OpenRouter via a LangChain-compatible LLM class.
- Functional: enforce entitlement and credit checks before retrieval and LLM calls.
- Functional: refund reserved credits when retrieval or LLM generation fails.
- Non-functional: tests must monkeypatch the retriever and LLM client; no network calls in CI.
- Non-functional: prompts must instruct the model to answer only from retrieved context.

## Architecture

Create `apps.rag.services` as the orchestration boundary:

```python
@dataclass(frozen=True)
class RagAnswer:
    answer: str
    estimated_tokens: int
    actual_tokens: int

class RagService:
    def answer_query(self, *, user, query: str) -> RagAnswer:
        raise NotImplementedError
```

Supporting modules:

- `apps.rag.tokens`: cheap token estimator and provider-usage extraction.
- `apps.rag.llm`: lazy `ChatOpenAI` builder configured for OpenRouter.
- `apps.rag.prompts`: prompt template and context formatter.
- `apps.rag.exceptions`: `RagConfigurationError`, `RagRetrievalError`, `RagProviderError`,
  `RagNoContextError`.

High-level flow:

```python
estimated_tokens = estimate_budget(query, max_context_chars, max_output_tokens)
reservation = reserve_daily_tokens(user, estimated_tokens)
try:
    chunks = retriever.similarity_search_for_user(user_id=user.id, query=query, k=settings.RAG_RETRIEVAL_K)
    if not chunks:
        raise RagNoContextError("No indexed context found for this query.")
    answer, provider_usage = llm.generate(prompt_for(query, chunks))
except Exception:
    refund_daily_tokens(reservation)
    raise
else:
    actual_tokens = usage_or_estimate(provider_usage, query, chunks, answer)
    finalize_daily_tokens(reservation, actual_tokens)
    return RagAnswer(answer=answer, estimated_tokens=estimated_tokens, actual_tokens=actual_tokens)
```

## Related Code Files

- Create: `apps/rag/exceptions.py` - explicit safe error taxonomy.
- Create: `apps/rag/tokens.py` - estimation and usage extraction.
- Create: `apps/rag/prompts.py` - context formatting and prompt template.
- Create: `apps/rag/llm.py` - OpenRouter LangChain client construction.
- Create: `apps/rag/services.py` - RAG orchestration.
- Modify: `config/settings/base.py` - add RAG/OpenRouter generation settings.
- Modify: `pyproject.toml` and `uv.lock` - add `langchain-openai` to vector/RAG extras.
- Modify: `docker/django/Dockerfile` - install the extra that includes `langchain-openai`.
- Create: `tests/rag/test_tokens.py` and `tests/rag/test_services.py`.

## Implementation Steps

1. Add settings:
   - `OPENROUTER_APP_TITLE = os.getenv("OPENROUTER_APP_TITLE", "RAVID Backend")`
   - `OPENROUTER_HTTP_REFERER = os.getenv("OPENROUTER_HTTP_REFERER", "")`
   - `RAG_MAX_OUTPUT_TOKENS = env_int("RAG_MAX_OUTPUT_TOKENS", 800)`
   - `RAG_TEMPERATURE = float(os.getenv("RAG_TEMPERATURE", "0"))`
2. Add `langchain-openai>=0.3,<0.4` to the existing `vector-ingestion` optional dependency group,
   then refresh `uv.lock` with the repository's normal `uv` command.
3. Implement `estimate_tokens(text: str) -> int` as a deterministic approximation:
   `max(1, ceil(len(text) / 4))`. This avoids adding tokenizer complexity for the assignment.
4. Implement `estimate_rag_budget(query, max_context_chars, max_output_tokens)` as query estimate +
   context budget estimate + output token budget + small fixed overhead.
5. Implement `build_openrouter_chat_model()`:

   ```python
   return ChatOpenAI(
       api_key=settings.OPENROUTER_API_KEY,
       base_url=settings.OPENROUTER_BASE_URL,
       model=settings.OPENROUTER_MODEL,
       temperature=settings.RAG_TEMPERATURE,
       max_tokens=settings.RAG_MAX_OUTPUT_TOKENS,
       default_headers={
           "HTTP-Referer": settings.OPENROUTER_HTTP_REFERER,
           "X-Title": settings.OPENROUTER_APP_TITLE,
       },
   )
   ```

6. Raise `RagConfigurationError` before provider construction when provider credentials are blank.
7. Build a prompt that contains:
   - system instruction: answer only from context; say not enough information if context does not
     support the answer;
   - numbered context snippets with `document_id`, `chunk_index`, and `source_filename`;
   - original user question.
8. Implement `RagService.answer_query` with dependency injection defaults for retriever and LLM
   builder so tests can pass fakes.
9. Convert provider exceptions to `RagProviderError`; convert `VectorRetrievalError` to
   `RagRetrievalError`; refund reservations on all failures after reservation.
10. Extract actual token usage from LangChain response metadata when present; otherwise estimate from
    prompt + answer.
11. Add service tests covering success, no context, missing provider credentials, provider failure
    refund, and final usage reconciliation.

## Tests Before

- Add failing `tests/rag/test_tokens.py` and `tests/rag/test_services.py` before implementation.
- Expected initial failure: `apps.rag.services`, `apps.rag.tokens`, and related modules do not exist.

## Tests After

- `uv run pytest tests/rag/test_tokens.py tests/rag/test_services.py`
- `uv run pytest tests/accounts/test_entitlements.py tests/documents/test_vector_retrieval.py tests/rag`

## Success Criteria

- [ ] RAG service never calls retriever or LLM for inactive/over-limit users.
- [ ] RAG service retrieves owner-scoped chunks and formats a context-grounded prompt.
- [ ] OpenRouter client is configured through LangChain and environment settings.
- [ ] Provider failures return safe internal errors through the service boundary and refund credits.
- [ ] Successful calls finalize token usage and return only the generated answer to the API layer.

## Risk Assessment

- Risk: OpenRouter free-tier model names change. Mitigation: keep model configurable and document
  the model setting; default remains existing auto-routing value.
- Risk: LangChain response usage metadata differs by provider. Mitigation: treat metadata as best
  effort and fall back to deterministic estimation.
- Risk: prompt injection in uploaded documents. Mitigation: system prompt states context is
  untrusted evidence, not instructions; do not pass secrets or system data into context.

## Security Considerations

- Never log provider credentials or raw provider headers.
- Do not include private document context in server errors.
- Treat uploaded document chunks as untrusted text; the system prompt must override document-level
  instructions.
