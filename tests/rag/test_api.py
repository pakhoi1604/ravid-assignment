from types import SimpleNamespace

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.accounts.entitlements import InactiveSubscriptionError, InsufficientCreditsError
from apps.rag.exceptions import RagConfigurationError, RagProviderError, RagRetrievalError


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
@pytest.mark.parametrize("payload", [{}, {"query": ""}, {"query": "   "}, {"query": "x" * 2001}])
def test_chat_query_validates_request(client, user, payload):
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
    "query",
    [123, 1.5, True, [], {}, None, "\ud800"],
)
def test_chat_query_rejects_non_string_or_invalid_utf8(client, user, query):
    response = client.post(
        reverse("chat-query"),
        {"query": query},
        content_type="application/json",
        **auth_headers_for(client, user),
    )

    assert response.status_code == 400
    assert response.json()["error"]


@pytest.mark.django_db
def test_chat_query_returns_answer_and_passes_authenticated_user(client, user, monkeypatch):
    calls = []

    def answer_query(service, *, user, query):
        calls.append((user, query))
        return SimpleNamespace(answer="Grounded answer")

    monkeypatch.setattr("apps.rag.views.RagService.answer_query", answer_query)
    response = client.post(
        reverse("chat-query"),
        {"query": "  What does the handbook say?  "},
        content_type="application/json",
        **auth_headers_for(client, user),
    )

    assert response.status_code == 200
    assert response.json() == {"answer": "Grounded answer"}
    assert calls == [(user, "What does the handbook say?")]


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("exception", "expected_status", "expected_error"),
    [
        (InactiveSubscriptionError(), 403, "Active subscription required."),
        (InsufficientCreditsError(), 429, "Insufficient daily token credits."),
        (RagConfigurationError(), 503, "LLM provider is not configured."),
        (RagProviderError("private provider detail"), 503, "Unable to generate answer right now."),
        (RagRetrievalError("private context detail"), 503, "Unable to generate answer right now."),
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
