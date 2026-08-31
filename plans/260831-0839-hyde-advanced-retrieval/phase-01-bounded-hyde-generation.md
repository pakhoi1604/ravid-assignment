---
phase: 1
title: "Bounded HyDE Generation"
status: completed
priority: P1
dependencies: []
effort: "medium"
---

# Phase 1: Bounded HyDE Generation

## Context Links

- Assignment HyDE flow: `docs/2026-08-30 R.A.V.I.D.md:197`
- Existing prompt and LCEL boundaries: `apps/rag/prompts.py:8`, `apps/rag/llm.py:23`
- Existing settings/deployment contracts: `config/settings/base.py:130`, &#46;env.example,
  and `compose.yaml:25`
- Primary APIs: https://reference.langchain.com/python/langchain-core/runnables and
  https://reference.langchain.com/python/langchain-openrouter/chat_models/ChatOpenRouter

## Overview

Add a purpose-specific, bounded HyDE generation primitive using the current OpenRouter model builder
and LCEL invocation. This phase does not alter retrieval or the public endpoint.

## Requirements

- Functional: build a HyDE prompt that treats the original query as untrusted data and requests one
  answer-like passage; require valid UTF-8, normalize supported text content, reject empty/unsupported
  and oversized output, and expose prompt text for conservative admission accounting.
- Functional: add configurable positive `RAG_HYDE_MAX_OUTPUT_TOKENS=256`,
  `RAG_HYDE_MAX_OUTPUT_CHARS=2000`, and `RAG_HYDE_TIMEOUT_MS=3000`; retain
  `RAG_PROVIDER_MAX_RETRIES=0`.
- Non-functional: reuse `ChatOpenRouter` and `(prompt | model).invoke`; no second SDK/provider
  integration, retries, new Python dependency, or evidence use of hypothetical text.

## Architecture

`build_hyde_prompt()` creates a system/human `ChatPromptTemplate`. The system message confines the
model to a neutral hypothetical passage and tells it to ignore instructions embedded in the query.
`render_hyde_prompt_for_bound()` mirrors the rendered content for `estimate_prompt_bound`.
`build_openrouter_chat_model()` gains explicit keyword overrides for timeout and max output tokens;
defaults preserve final-answer behavior. HyDE passes the three new settings. Normalize through a
purpose-specific helper or parameterized existing helper, require `passage.encode("utf-8")`, then
enforce `RAG_HYDE_MAX_OUTPUT_CHARS`. This independent safety bound must not reuse the `/4` reporting
heuristic in `tokens.py`; reject rather than silently truncate provider output.

## Related Code Files

- Modify: `apps/rag/prompts.py` - HyDE prompt and bound rendering.
- Modify: `apps/rag/llm.py` - explicit timeout/max-token overrides and positive configuration checks.
- Modify: `config/settings/base.py` - three positive HyDE settings.
- Modify: &#46;env.example, `compose.yaml` - document/forward defaults while preserving
  retrieval edits.
- Modify: `tests/rag/test_prompts.py`, `tests/rag/test_llm.py` - prompt safety, bounds, overrides,
  provider-failure translation, and no-retry assertions.
- Modify: `tests/smoke/test_configuration.py`, `tests/smoke/test_compose_contracts.py` - configuration
  and deployment contract assertions.
- No change: `pyproject.toml`, `uv.lock`, `apps/documents/vector_store.py`.

## Implementation Steps

1. Add failing prompt tests for injection-like query content, original-query interpolation, and a
   deterministic rendered string suitable for token reservation.
2. Add settings/default tests, including non-positive HyDE limit/timeout rejection and Compose web
   forwarding. Preserve all existing threshold/MMR keys and tests in the dirty worktree.
3. Implement the HyDE prompt and render helper beside the final RAG prompt; keep hypothetical text
   entirely outside `format_documents` and final evidence context.
4. Extend `build_openrouter_chat_model` with explicit optional keyword overrides, compute effective
   values, validate them, and configure SDK `timeout_ms` plus `ChatOpenRouter` max tokens/timeout.
   Verify the locked wrapper's timeout unit from its installed signature/source before wiring the
   override; do not assume the SDK millisecond unit also applies to the wrapper.
5. Keep `invoke_prompt_model` narrow. Existing provider/HTTP transport failures remain one internal
   family and map to one stable public fallback reason. Do not swallow unrelated `ValueError`/
   `TypeError`.
6. Run prompt, LLM, and smoke configuration tests, then lint/format checks.

## Todo

- [x] Write prompt/config/model tests first.
- [x] Add bounded injection-resistant HyDE prompt.
- [x] Add positive token, character, and timeout settings plus deployment propagation.
- [x] Add model-builder overrides with zero retries.
- [x] Verify no dependency or vector-store diff is introduced by this phase.

## Success Criteria

- [x] HyDE uses existing LCEL/ChatOpenRouter integration with a 3-second timeout, 256-token cap, and
  independent 2,000-character safety ceiling.
- [x] Standard model construction remains behaviorally unchanged when overrides are omitted.
- [x] Empty, unsupported, and over-limit content is detectable before retrieval.
- [x] Tests prove known provider failures and programming-error propagation remain distinct.

## Risk Assessment

- Prompt injection could make the hypothetical instruction-like. Mitigation: mark query as untrusted,
  constrain output shape, and never use the output as final evidence.
- SDK and wrapper timeout units may diverge. Mitigation: assert the effective SDK millisecond value
  and wrapper argument against the locked integration.
- Broad exception handling could hide defects. Mitigation: translate only locked provider/transport
  families and let unrelated errors propagate.

## Security Considerations

The query may contain hostile instructions and leaves the application for OpenRouter only when HyDE
is requested. Never log credentials or provider bodies. This phase handles no document chunks.

## Next Steps

Phase 2 consumes the prompt/model primitive and owns fallback, retrieval, and token settlement.
