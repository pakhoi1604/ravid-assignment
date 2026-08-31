import math
from typing import Any


def estimate_text_tokens(text: str) -> int:
    """Return a deterministic reporting fallback, never an admission-control value."""
    return max(1, math.ceil(len(text) / 4))


def estimate_prompt_bound(
    prompt_text: str,
    *,
    chat_overhead_tokens: int,
    max_output_tokens: int,
) -> int:
    if chat_overhead_tokens < 0 or max_output_tokens <= 0:
        raise ValueError("RAG token limits must be valid positive bounds.")
    return len(prompt_text.encode("utf-8")) + chat_overhead_tokens + max_output_tokens


def extract_total_tokens(message: Any) -> int | None:
    usage_metadata = getattr(message, "usage_metadata", None)
    if not isinstance(usage_metadata, dict):
        return None
    total_tokens = usage_metadata.get("total_tokens")
    if isinstance(total_tokens, bool) or not isinstance(total_tokens, int) or total_tokens < 0:
        return None
    return total_tokens


def usage_or_fallback(message: Any, *, prompt_text: str, answer: str) -> int:
    total_tokens = extract_total_tokens(message)
    if total_tokens is not None:
        return total_tokens
    return estimate_text_tokens(prompt_text) + estimate_text_tokens(answer)


def bound_usage_to_reservation(usage: int, *, reservation_tokens: int) -> int:
    if reservation_tokens < 0:
        raise ValueError("reservation_tokens must be a non-negative integer.")
    return usage if usage <= reservation_tokens else reservation_tokens
