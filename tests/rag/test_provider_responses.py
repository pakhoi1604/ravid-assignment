from types import SimpleNamespace

import pytest

from apps.rag.exceptions import RagProviderError
from apps.rag.provider_responses import (
    classify_provider_usage,
    extract_response_text,
    normalize_answer_content,
    normalize_hyde_content,
)


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        (" answer ", "answer"),
        ([{"type": "text", "text": "one"}, {"type": "text", "text": " two"}], "one two"),
    ],
)
def test_answer_content_normalization(content, expected):
    assert normalize_answer_content(content) == expected
    assert extract_response_text(content).strip() == expected


@pytest.mark.parametrize("content", ["", [], [{"type": "image", "url": "x"}], None])
def test_answer_content_normalization_rejects_invalid_content(content):
    with pytest.raises(RagProviderError, match="invalid answer"):
        normalize_answer_content(content)


def test_hyde_content_enforces_utf8_and_size():
    assert normalize_hyde_content("passage", max_chars=7) == "passage"
    with pytest.raises(RagProviderError):
        normalize_hyde_content("too long", max_chars=7)
    with pytest.raises(RagProviderError):
        normalize_hyde_content("\ud800", max_chars=7)


@pytest.mark.parametrize(
    ("usage_metadata", "acceptable", "warning"),
    [
        (None, True, None),
        ({"total_tokens": 40}, True, None),
        ({"total_tokens": 101}, False, "exceeded_reservation"),
        ({"total_tokens": True}, False, "invalid_usage"),
        ({}, False, "invalid_usage"),
        ("invalid", False, "invalid_usage"),
    ],
)
def test_provider_usage_classification_is_bounded(usage_metadata, acceptable, warning):
    message = SimpleNamespace(content="answer", usage_metadata=usage_metadata)

    result = classify_provider_usage(
        message,
        prompt_text="prompt",
        answer="answer",
        reservation_tokens=100,
    )

    assert result.actual_tokens <= 100
    assert result.is_acceptable is acceptable
    assert result.warning == warning
