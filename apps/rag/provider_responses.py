from dataclasses import dataclass
from typing import Any

from apps.rag.exceptions import RagProviderError
from apps.rag.tokens import bound_usage_to_reservation, usage_or_fallback


@dataclass(frozen=True)
class UsageAssessment:
    actual_tokens: int
    is_acceptable: bool
    warning: str | None


def extract_response_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text")
                if isinstance(text, str):
                    text_parts.append(text)
        return "".join(text_parts)
    return ""


def normalize_answer_content(content: Any) -> str:
    answer = extract_response_text(content).strip()
    if not answer:
        raise RagProviderError("LLM provider returned an invalid answer.")
    return answer


def normalize_hyde_content(content: Any, *, max_chars: int) -> str:
    passage = normalize_answer_content(content)
    try:
        passage.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise RagProviderError("LLM provider returned an invalid answer.") from exc
    if len(passage) > max_chars:
        raise RagProviderError("LLM provider returned an invalid answer.")
    return passage


def classify_provider_usage(
    message: Any,
    *,
    prompt_text: str,
    answer: str,
    reservation_tokens: int,
) -> UsageAssessment:
    usage_metadata = getattr(message, "usage_metadata", None)
    is_acceptable = usage_metadata is None
    warning = None

    if isinstance(usage_metadata, dict) and "total_tokens" in usage_metadata:
        total_tokens = usage_metadata["total_tokens"]
        if isinstance(total_tokens, bool) or not isinstance(total_tokens, int) or total_tokens < 0:
            warning = "invalid_usage"
        elif total_tokens > reservation_tokens:
            warning = "exceeded_reservation"
        else:
            is_acceptable = True
    elif usage_metadata is not None:
        warning = "invalid_usage"

    estimated = usage_or_fallback(
        message,
        prompt_text=prompt_text,
        answer=answer,
    )
    actual = bound_usage_to_reservation(
        estimated,
        reservation_tokens=reservation_tokens,
    )
    return UsageAssessment(
        actual_tokens=actual,
        is_acceptable=is_acceptable,
        warning=warning,
    )
