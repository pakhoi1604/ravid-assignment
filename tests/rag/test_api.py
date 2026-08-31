from types import SimpleNamespace

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone
from langchain_core.documents import Document

from apps.accounts.entitlements import InactiveSubscriptionError, InsufficientCreditsError
from apps.accounts.models import DailyTokenUsage
from apps.rag.exceptions import (
    RagAccountingError,
    RagConfigurationError,
    RagProviderError,
    RagRetrievalError,
)
from apps.rag.services import RagService


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


def auth_headers_for_credentials(client, *, username, password):
    response = client.post(
        reverse("token_obtain_pair"),
        {"username": username, "password": password},
        content_type="application/json",
    )
    assert response.status_code == 200
    return {"HTTP_AUTHORIZATION": f"Bearer {response.json()['access']}"}


def guard_rag_external_adapters(monkeypatch, *, vector_store_factory):
    original_init = RagService.__init__

    def init_with_guarded_adapters(service):
        original_init(
            service,
            vector_store_factory=vector_store_factory,
            model_builder=lambda **kwargs: pytest.fail("answer model must not be built"),
        )

    monkeypatch.setattr(RagService, "__init__", init_with_guarded_adapters)


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
    ("username", "password", "expected_remaining"),
    [
        ("reviewer_no_tokens", "reviewer-no-tokens-password-123", 0),
        (
            "reviewer_insufficient_tokens",
            "reviewer-insufficient-tokens-password-123",
            1,
        ),
    ],
)
def test_seeded_insufficient_credit_accounts_are_rejected_before_answer_rendering(
    client,
    settings,
    monkeypatch,
    username,
    password,
    expected_remaining,
):
    monkeypatch.setenv("ALLOW_TEST_ACCOUNT_SEED", "true")
    settings.OPENROUTER_API_KEY = "test-key"
    settings.OPENROUTER_MODEL = "openrouter/free"
    call_command("load_test_accounts")

    vector_store = SimpleNamespace(
        retrieve_for_user=lambda **kwargs: [
            Document(page_content="Owner-scoped context", metadata={"user_id": kwargs["user_id"]})
        ]
    )
    guard_rag_external_adapters(
        monkeypatch,
        vector_store_factory=lambda: vector_store,
    )

    response = client.post(
        reverse("chat-query"),
        {"query": "What does the document say?", "use_hyde": False},
        content_type="application/json",
        **auth_headers_for_credentials(client, username=username, password=password),
    )

    assert response.status_code == 429
    assert response.json() == {"error": "Insufficient daily token credits."}
    user = get_user_model().objects.get(username=username)
    usage = DailyTokenUsage.objects.get(user=user, usage_date=timezone.localdate())
    assert user.subscription.daily_token_limit - usage.used_tokens == expected_remaining


@pytest.mark.django_db
def test_seeded_unsubscribed_account_is_rejected_before_provider_or_retrieval(
    client,
    monkeypatch,
):
    monkeypatch.setenv("ALLOW_TEST_ACCOUNT_SEED", "true")
    call_command("load_test_accounts")
    guard_rag_external_adapters(
        monkeypatch,
        vector_store_factory=lambda: pytest.fail("retrieval must not run"),
    )

    response = client.post(
        reverse("chat-query"),
        {"query": "What does the document say?", "use_hyde": False},
        content_type="application/json",
        **auth_headers_for_credentials(
            client,
            username="reviewer_unsubscribed",
            password="reviewer-unsubscribed-password-123",
        ),
    )

    assert response.status_code == 403
    assert response.json() == {"error": "Active subscription required."}


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
