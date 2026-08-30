from types import SimpleNamespace

import pytest
from django.contrib.auth import get_user_model
from langchain_core.documents import Document
from langchain_core.messages import AIMessage

from apps.accounts.entitlements import InactiveSubscriptionError, InsufficientCreditsError
from apps.accounts.models import DailyTokenUsage, Subscription
from apps.documents.vector_store import VectorRetrievalError
from apps.rag.exceptions import (
    ProviderTransportError,
    RagConfigurationError,
    RagProviderError,
    RagRetrievalError,
)
from apps.rag.prompts import NO_CONTEXT_ANSWER
from apps.rag.services import RagService, normalize_answer_content


@pytest.fixture
def subscribed_user(db):
    user = get_user_model().objects.create_user(username="rag-user", password="password-123")
    Subscription.objects.create(
        user=user,
        status=Subscription.Status.ACTIVE,
        daily_token_limit=20_000,
    )
    return user


def document():
    return Document(
        page_content="The cancellation period is fourteen days.",
        metadata={
            "document_id": "document-1",
            "chunk_index": 0,
            "source_filename": "handbook.md",
        },
    )


@pytest.mark.django_db
def test_service_returns_answer_and_finalizes_provider_usage(subscribed_user, settings):
    settings.OPENROUTER_API_KEY = "test-key"
    settings.OPENROUTER_MODEL = "openrouter/free"
    vector_store = SimpleNamespace(retrieve_for_user=lambda **kwargs: [document()])
    message = AIMessage(
        content="Fourteen days.",
        usage_metadata={"input_tokens": 30, "output_tokens": 2, "total_tokens": 32},
    )
    service = RagService(
        vector_store_factory=lambda: vector_store,
        model_builder=lambda: object(),
        model_invoker=lambda prompt, model, values: message,
    )

    result = service.answer_query(user=subscribed_user, query="What is the cancellation period?")

    assert result.answer == "Fourteen days."
    assert result.actual_tokens == 32
    assert result.estimated_tokens >= result.actual_tokens
    assert DailyTokenUsage.objects.get(user=subscribed_user).used_tokens == 32


@pytest.mark.django_db
def test_empty_context_returns_fixed_answer_without_usage(subscribed_user, settings):
    settings.OPENROUTER_API_KEY = "test-key"
    settings.OPENROUTER_MODEL = "openrouter/free"
    vector_store = SimpleNamespace(retrieve_for_user=lambda **kwargs: [])
    service = RagService(
        vector_store_factory=lambda: vector_store,
        model_builder=lambda: pytest.fail("model must not be built"),
    )

    result = service.answer_query(user=subscribed_user, query="Unknown?")

    assert result.answer == NO_CONTEXT_ANSWER
    assert result.actual_tokens == 0
    assert DailyTokenUsage.objects.count() == 0


@pytest.mark.django_db
def test_missing_provider_config_stops_before_retrieval(subscribed_user, settings):
    settings.OPENROUTER_API_KEY = ""
    service = RagService(vector_store_factory=lambda: pytest.fail("retrieval must not run"))

    with pytest.raises(RagConfigurationError):
        service.answer_query(user=subscribed_user, query="Question")
    assert DailyTokenUsage.objects.count() == 0


@pytest.mark.django_db
def test_inactive_subscription_stops_before_retrieval(subscribed_user, settings):
    subscribed_user.subscription.delete()
    settings.OPENROUTER_API_KEY = "test-key"
    service = RagService(vector_store_factory=lambda: pytest.fail("retrieval must not run"))

    with pytest.raises(InactiveSubscriptionError):
        service.answer_query(user=subscribed_user, query="Question")
    assert DailyTokenUsage.objects.count() == 0


@pytest.mark.django_db
def test_exhausted_quota_stops_before_model_construction(subscribed_user, settings):
    settings.OPENROUTER_API_KEY = "test-key"
    settings.OPENROUTER_MODEL = "openrouter/free"
    subscribed_user.subscription.daily_token_limit = 1
    subscribed_user.subscription.save(update_fields=["daily_token_limit"])
    vector_store = SimpleNamespace(retrieve_for_user=lambda **kwargs: [document()])
    service = RagService(
        vector_store_factory=lambda: vector_store,
        model_builder=lambda: pytest.fail("model must not be built"),
    )

    with pytest.raises(InsufficientCreditsError):
        service.answer_query(user=subscribed_user, query="Question")


@pytest.mark.django_db
def test_model_configuration_failure_after_reservation_refunds_usage(subscribed_user, settings):
    settings.OPENROUTER_API_KEY = "test-key"
    settings.OPENROUTER_MODEL = "openrouter/free"
    vector_store = SimpleNamespace(retrieve_for_user=lambda **kwargs: [document()])

    def fail_model_builder():
        raise RagConfigurationError("invalid provider configuration")

    service = RagService(
        vector_store_factory=lambda: vector_store,
        model_builder=fail_model_builder,
    )

    with pytest.raises(RagConfigurationError):
        service.answer_query(user=subscribed_user, query="Question")
    assert DailyTokenUsage.objects.get(user=subscribed_user).used_tokens == 0


@pytest.mark.django_db
def test_retrieval_failure_is_safe_and_creates_no_usage(subscribed_user, settings):
    settings.OPENROUTER_API_KEY = "test-key"
    settings.OPENROUTER_MODEL = "openrouter/free"

    class VectorStore:
        def retrieve_for_user(self, **kwargs):
            raise VectorRetrievalError("backend detail")

    with pytest.raises(RagRetrievalError, match="unavailable"):
        RagService(vector_store_factory=VectorStore).answer_query(
            user=subscribed_user,
            query="Question",
        )
    assert DailyTokenUsage.objects.count() == 0


@pytest.mark.django_db
def test_provider_failure_refunds_reservation(subscribed_user, settings):
    settings.OPENROUTER_API_KEY = "test-key"
    settings.OPENROUTER_MODEL = "openrouter/free"
    vector_store = SimpleNamespace(retrieve_for_user=lambda **kwargs: [document()])

    def fail_provider(prompt, model, values):
        raise ProviderTransportError("provider detail")

    service = RagService(
        vector_store_factory=lambda: vector_store,
        model_builder=lambda: object(),
        model_invoker=fail_provider,
    )

    with pytest.raises(RagProviderError, match="Unable to generate"):
        service.answer_query(user=subscribed_user, query="Question")
    assert DailyTokenUsage.objects.get(user=subscribed_user).used_tokens == 0


@pytest.mark.django_db
def test_invalid_provider_content_refunds_reservation(subscribed_user, settings):
    settings.OPENROUTER_API_KEY = "test-key"
    settings.OPENROUTER_MODEL = "openrouter/free"
    vector_store = SimpleNamespace(retrieve_for_user=lambda **kwargs: [document()])
    service = RagService(
        vector_store_factory=lambda: vector_store,
        model_builder=lambda: object(),
        model_invoker=lambda prompt, model, values: AIMessage(content=""),
    )

    with pytest.raises(RagProviderError, match="invalid answer"):
        service.answer_query(user=subscribed_user, query="Question")
    assert DailyTokenUsage.objects.get(user=subscribed_user).used_tokens == 0


@pytest.mark.django_db
def test_missing_usage_metadata_uses_fallback_and_settles_usage(subscribed_user, settings):
    settings.OPENROUTER_API_KEY = "test-key"
    settings.OPENROUTER_MODEL = "openrouter/free"
    vector_store = SimpleNamespace(retrieve_for_user=lambda **kwargs: [document()])
    service = RagService(
        vector_store_factory=lambda: vector_store,
        model_builder=lambda: object(),
        model_invoker=lambda prompt, model, values: AIMessage(content="Fallback answer"),
    )

    result = service.answer_query(user=subscribed_user, query="Question")

    assert result.actual_tokens > 0
    assert DailyTokenUsage.objects.get(user=subscribed_user).used_tokens == result.actual_tokens


@pytest.mark.django_db
def test_programming_error_propagates_through_service(subscribed_user, settings):
    settings.OPENROUTER_API_KEY = "test-key"
    settings.OPENROUTER_MODEL = "openrouter/free"
    vector_store = SimpleNamespace(retrieve_for_user=lambda **kwargs: [document()])

    def fail_with_programming_error(prompt, model, values):
        raise TypeError("implementation defect")

    service = RagService(
        vector_store_factory=lambda: vector_store,
        model_builder=lambda: object(),
        model_invoker=fail_with_programming_error,
    )

    with pytest.raises(TypeError, match="implementation defect"):
        service.answer_query(user=subscribed_user, query="Question")


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        (" answer ", "answer"),
        ([{"type": "text", "text": "answer"}], "answer"),
    ],
)
def test_answer_content_normalization(content, expected):
    assert normalize_answer_content(content) == expected


@pytest.mark.parametrize("content", ["", [], [{"type": "image", "url": "x"}], None])
def test_answer_content_normalization_rejects_empty_or_unsupported(content):
    with pytest.raises(RagProviderError, match="invalid answer"):
        normalize_answer_content(content)
