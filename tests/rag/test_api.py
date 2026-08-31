from types import SimpleNamespace

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.accounts.entitlements import InactiveSubscriptionError, InsufficientCreditsError
from apps.rag.exceptions import (
    RagAccountingError,
    RagConfigurationError,
    RagProviderError,
    RagRetrievalError,
)


@pytest.fixture
def user(db):
    return get_user_model().objects.create_user(username="chat-owner", password="password")


def auth_headers_for(client, user):
    response = client.post(
        reverse("token_obtain_pair"),
        {"username": user.username, "password": "password"},
        content_type="application/json",
    )
    return {"HTTP_AUTHORIZATION": f"Bearer {response.json()['access']}"}


@pytest.mark.django_db
def test_chat_query_requires_authentication(client):
    response = client.post(
        reverse("chat-query"),
        {"query": "Question"},
        content_type="application/json",
    )

    assert response.status_code == 401


@pytest.mark.django_db
@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"query": ""},
        {"query": "   "},
        {"query": "x" * 2001},
        {"query": 123},
        {"query": 1.5},
        {"query": True},
        {"query": []},
        {"query": {}},
        {"query": None},
        {"query": "x", "use_hyde": 0},
        {"query": "x", "use_hyde": 1},
        {"query": "x", "use_hyde": "true"},
        {"query": "x", "use_hyde": "1"},
        {"query": "x", "use_hyde": None},
        {"query": "x", "use_hyde": []},
        {"query": "x", "use_hyde": {}},
    ],
)
def test_chat_query_validates_request_payload(client, user, payload):
    response = client.post(
        reverse("chat-query"),
        payload,
        content_type="application/json",
        **auth_headers_for(client, user),
    )

    assert response.status_code == 400
    assert response.json()["error"]


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"query": "  What does handbook say?  "}, False),
        ({"query": "What does handbook say?", "use_hyde": False}, False),
        ({"query": "What does handbook say?", "use_hyde": True}, True),
    ],
)
def test_chat_query_forwards_use_hyde_toggle(client, user, payload, expected, monkeypatch):
    calls = []

    def answer_query(service, *, user, query, use_hyde):  # pragma: no cover - signature contract
        calls.append((query, use_hyde))
        return SimpleNamespace(
            answer="Grounded answer",
            retrieval_metadata=SimpleNamespace(
                mode="standard",
                hypothetical_passage=None,
                fallback_reason=None,
                retrieved_chunks_count=0,
                retrieved_chunks=[],
            ),
        )

    monkeypatch.setattr("apps.rag.views.RagService.answer_query", answer_query)
    response = client.post(
        reverse("chat-query"),
        payload,
        content_type="application/json",
        **auth_headers_for(client, user),
    )

    assert response.status_code == 200
    assert calls == [("What does handbook say?", expected)]
    body = response.json()
    assert body == {
        "answer": "Grounded answer",
        "retrieval_metadata": {
            "mode": "standard",
            "hypothetical_passage": None,
            "fallback_reason": None,
            "retrieved_chunks_count": 0,
            "retrieved_chunks": [],
        },
    }


@pytest.mark.django_db
def test_chat_query_returns_full_metadata_on_success(client, user, monkeypatch):
    def answer_query(service, *, user, query, use_hyde):  # pragma: no cover - signature contract
        return SimpleNamespace(
            answer="Fourteen days",
            retrieval_metadata=SimpleNamespace(
                mode="hyde",
                hypothetical_passage="Hypothetical passage about deadlines.",
                fallback_reason=None,
                retrieved_chunks_count=2,
                retrieved_chunks=["chunk 1", "chunk 2"],
            ),
        )

    monkeypatch.setattr("apps.rag.views.RagService.answer_query", answer_query)
    response = client.post(
        reverse("chat-query"),
        {"query": "What is the cancellation period?", "use_hyde": True},
        content_type="application/json",
        **auth_headers_for(client, user),
    )

    assert response.status_code == 200
    assert set(response.json().keys()) == {"answer", "retrieval_metadata"}
    metadata = response.json()["retrieval_metadata"]
    assert set(metadata.keys()) == {
        "mode",
        "hypothetical_passage",
        "fallback_reason",
        "retrieved_chunks_count",
        "retrieved_chunks",
    }
    assert metadata["mode"] == "hyde"
    assert metadata["fallback_reason"] is None
    assert metadata["retrieved_chunks_count"] == 2
    assert metadata["retrieved_chunks"] == ["chunk 1", "chunk 2"]


@pytest.mark.django_db
def test_chat_query_serializes_hyde_fallback_metadata(client, user, monkeypatch):
    def answer_query(service, **kwargs):
        return SimpleNamespace(
            answer="Fallback answer",
            retrieval_metadata=SimpleNamespace(
                mode="standard",
                hypothetical_passage=None,
                fallback_reason="hyde_unavailable",
                retrieved_chunks_count=1,
                retrieved_chunks=["owner-scoped chunk"],
            ),
        )

    monkeypatch.setattr("apps.rag.views.RagService.answer_query", answer_query)
    response = client.post(
        reverse("chat-query"),
        {"query": "Question", "use_hyde": True},
        content_type="application/json",
        **auth_headers_for(client, user),
    )

    assert response.status_code == 200
    assert response.json()["retrieval_metadata"] == {
        "mode": "standard",
        "hypothetical_passage": None,
        "fallback_reason": "hyde_unavailable",
        "retrieved_chunks_count": 1,
        "retrieved_chunks": ["owner-scoped chunk"],
    }


@pytest.mark.django_db
@pytest.mark.parametrize(
    (
        "exception",
        "expected_status",
        "expected_error",
    ),
    [
        (InactiveSubscriptionError(), 403, "Active subscription required."),
        (InsufficientCreditsError(), 429, "Insufficient daily token credits."),
        (RagConfigurationError(), 503, "LLM provider is not configured."),
        (RagProviderError("private provider detail"), 503, "Unable to generate answer right now."),
        (RagRetrievalError("private context detail"), 503, "Unable to generate answer right now."),
        (RagAccountingError("accounting failure"), 503, "Unable to generate answer right now."),
    ],
)
def test_chat_query_maps_safe_domain_errors(
    client,
    user,
    monkeypatch,
    exception,
    expected_status,
    expected_error,
):
    def fail(service, **kwargs):
        raise exception

    monkeypatch.setattr("apps.rag.views.RagService.answer_query", fail)
    response = client.post(
        reverse("chat-query"),
        {"query": "Question"},
        content_type="application/json",
        **auth_headers_for(client, user),
    )

    assert response.status_code == expected_status
    assert response.json() == {"error": expected_error}
    assert "private" not in response.content.decode()
