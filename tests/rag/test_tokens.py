from types import SimpleNamespace

from apps.rag.tokens import (
    estimate_prompt_bound,
    estimate_text_tokens,
    extract_total_tokens,
    usage_or_fallback,
)


def test_prompt_bound_uses_utf8_bytes_and_explicit_caps():
    assert (
        estimate_prompt_bound(
            "🙂",
            chat_overhead_tokens=10,
            max_output_tokens=20,
        )
        == 34
    )


def test_usage_prefers_provider_metadata():
    message = SimpleNamespace(usage_metadata={"total_tokens": 123})

    assert extract_total_tokens(message) == 123
    assert usage_or_fallback(message, prompt_text="prompt", answer="answer") == 123


def test_usage_falls_back_to_deterministic_estimate():
    message = SimpleNamespace(usage_metadata=None)

    assert usage_or_fallback(message, prompt_text="12345678", answer="1234") == 3
    assert estimate_text_tokens("") == 1
