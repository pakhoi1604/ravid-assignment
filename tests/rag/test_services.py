from types import SimpleNamespace

import pytest
from django.contrib.auth import get_user_model
from langchain_core.documents import Document

from apps.accounts.entitlements import (
    InsufficientCreditsError,
    finalize_daily_tokens,
    refund_daily_tokens,
)
from apps.accounts.models import DailyTokenUsage, Subscription
from apps.documents.exceptions import VectorRetrievalError
from apps.rag.accounting import RagStageAccounting
from apps.rag.exceptions import (
    ProviderTransportError,
    RagAccountingError,
    RagConfigurationError,
    RagProviderError,
    RagRetrievalError,
)
from apps.rag.prompts import (
    NO_CONTEXT_ANSWER,
    chunk_documents_for_prompt,
    render_hyde_prompt_for_bound,
    render_prompt_for_bound,
)
from apps.rag.services import RagService
from apps.rag.tokens import estimate_prompt_bound


@pytest.fixture
def subscribed_user(db):
    user = get_user_model().objects.create_user(username="rag-user", password="password-123")
    Subscription.objects.create(
        user=user,
        status=Subscription.Status.ACTIVE,
        daily_token_limit=20_000,
    )
    return user


@pytest.fixture
def accounting_spy():
    calls = []

    def finalize(reservation, actual_tokens):
        calls.append("finalize")
        return finalize_daily_tokens(reservation, actual_tokens)

    def refund(reservation):
        calls.append("refund")
        return refund_daily_tokens(reservation)

    return SimpleNamespace(
        accounting=RagStageAccounting(finalize=finalize, refund=refund),
        calls=calls,
    )


def document(text="The cancellation period is fourteen days."):
    return Document(
        page_content=text,
        metadata={
            "document_id": "document-1",
            "chunk_index": 0,
            "source_filename": "handbook.md",
        },
    )


def provider_message(content, *, total_tokens=None):
    usage_metadata = None
    if total_tokens is not None:
        usage_metadata = {
            "input_tokens": max(total_tokens - 1, 0),
            "output_tokens": min(total_tokens, 1),
            "total_tokens": total_tokens,
        }
    return SimpleNamespace(content=content, usage_metadata=usage_metadata)


def _hyde_estimated_tokens(query: str, *, settings) -> int:
    return estimate_prompt_bound(
        render_hyde_prompt_for_bound(query=query),
        chat_overhead_tokens=settings.RAG_CHAT_OVERHEAD_TOKENS,
        max_output_tokens=settings.RAG_HYDE_MAX_OUTPUT_TOKENS,
    )


def _final_estimated_tokens(documents, query: str, *, settings) -> int:
    _, context = chunk_documents_for_prompt(
        documents,
        max_chars=settings.RAG_MAX_CONTEXT_CHARS,
    )
    return estimate_prompt_bound(
        render_prompt_for_bound(question=query, context=context),
        chat_overhead_tokens=settings.RAG_CHAT_OVERHEAD_TOKENS,
        max_output_tokens=settings.RAG_MAX_OUTPUT_TOKENS,
    )


@pytest.mark.django_db
def test_service_standard_query_uses_final_stage_and_returns_metadata(subscribed_user, settings):
    settings.OPENROUTER_API_KEY = "test-key"
    settings.OPENROUTER_MODEL = "openrouter/free"
    retrieval_calls = []

    vector_store = SimpleNamespace(
        retrieve_for_user=lambda **kwargs: (
            retrieval_calls.append(kwargs),
            [document(), document("Second chunk")],
        )[1]
    )

    calls = []

    def model_invoker(prompt, model, values):
        calls.append(values)
        return provider_message("Fourteen days.", total_tokens=42)

    result = RagService(
        vector_store_factory=lambda: vector_store,
        model_builder=lambda: object(),
        model_invoker=model_invoker,
    ).answer_query(user=subscribed_user, query="What is the cancellation period?")

    first_chunk = (
        "[1] document_id=document-1 chunk_index=0 source_filename=handbook.md\n"
        "The cancellation period is fourteen days."
    )
    second_chunk = (
        "[2] document_id=document-1 chunk_index=0 source_filename=handbook.md\nSecond chunk"
    )
    assert retrieval_calls == [
        {
            "user_id": subscribed_user.id,
            "query": "What is the cancellation period?",
            "k": settings.RAG_RETRIEVAL_K,
            "search_type": settings.RAG_RETRIEVAL_SEARCH_TYPE,
            "score_threshold": settings.RAG_RETRIEVAL_SCORE_THRESHOLD,
            "fetch_k": settings.RAG_RETRIEVAL_FETCH_K,
        }
    ]
    assert calls == [
        {
            "question": "What is the cancellation period?",
            "context": f"{first_chunk}\n\n{second_chunk}",
        }
    ]
    assert result.answer == "Fourteen days."
    assert result.actual_tokens == 42
    assert result.estimated_tokens >= result.actual_tokens
    assert result.retrieval_metadata.mode == "standard"
    assert result.retrieval_metadata.hypothetical_passage is None
    assert result.retrieval_metadata.fallback_reason is None
    assert result.retrieval_metadata.retrieved_chunks == (first_chunk, second_chunk)
    assert result.retrieval_metadata.retrieved_chunks_count == 2


@pytest.mark.django_db
def test_service_standard_empty_retrieval_returns_no_context_without_model(
    subscribed_user, settings
):
    settings.OPENROUTER_API_KEY = "test-key"
    settings.OPENROUTER_MODEL = "openrouter/free"

    vector_store = SimpleNamespace(retrieve_for_user=lambda **kwargs: [])

    result = RagService(
        vector_store_factory=lambda: vector_store,
        model_builder=lambda: pytest.fail("model must not be built"),
        model_invoker=lambda prompt, model, values: pytest.fail("invocation must not happen"),
    ).answer_query(user=subscribed_user, query="Unknown?")

    assert result.answer == NO_CONTEXT_ANSWER
    assert result.actual_tokens == 0
    assert result.estimated_tokens == 0
    assert result.retrieval_metadata.mode == "standard"
    assert result.retrieval_metadata.hypothetical_passage is None
    assert result.retrieval_metadata.fallback_reason is None
    assert result.retrieval_metadata.retrieved_chunks_count == 0
    assert result.retrieval_metadata.retrieved_chunks == ()
    assert DailyTokenUsage.objects.count() == 0


@pytest.mark.django_db
def test_service_validate_retrieval_settings_prevents_hyde_charge(subscribed_user, settings):
    settings.OPENROUTER_API_KEY = "test-key"
    settings.OPENROUTER_MODEL = "openrouter/free"
    settings.RAG_RETRIEVAL_SEARCH_TYPE = "invalid"

    with pytest.raises(RagConfigurationError, match="retrieval"):
        RagService(vector_store_factory=lambda: pytest.fail("must not fetch")).answer_query(
            user=subscribed_user,
            query="Question",
            use_hyde=True,
        )

    assert DailyTokenUsage.objects.count() == 0


@pytest.mark.django_db
def test_service_snapshots_retrieval_policy_before_hyde_charge(subscribed_user, settings):
    settings.OPENROUTER_API_KEY = "test-key"
    settings.OPENROUTER_MODEL = "openrouter/free"
    original_policy = {
        "k": settings.RAG_RETRIEVAL_K,
        "search_type": settings.RAG_RETRIEVAL_SEARCH_TYPE,
        "score_threshold": settings.RAG_RETRIEVAL_SCORE_THRESHOLD,
        "fetch_k": settings.RAG_RETRIEVAL_FETCH_K,
    }
    retrieval_calls = []
    vector_store = SimpleNamespace(
        retrieve_for_user=lambda **kwargs: retrieval_calls.append(kwargs) or []
    )

    def model_invoker(prompt, model, values):
        settings.RAG_RETRIEVAL_SEARCH_TYPE = "invalid-after-validation"
        return provider_message("hypothetical passage", total_tokens=10)

    RagService(
        vector_store_factory=lambda: vector_store,
        model_builder=lambda **kwargs: object(),
        model_invoker=model_invoker,
    ).answer_query(user=subscribed_user, query="Question", use_hyde=True)

    assert retrieval_calls == [
        {
            "user_id": subscribed_user.id,
            "query": "hypothetical passage",
            **original_policy,
        }
    ]


@pytest.mark.django_db
def test_service_hyde_success_uses_hypothetical_and_orig_query_for_final_prompt(
    subscribed_user, settings, accounting_spy
):
    settings.OPENROUTER_API_KEY = "test-key"
    settings.OPENROUTER_MODEL = "openrouter/free"
    retrieval_queries = []

    vector_store = SimpleNamespace(
        retrieve_for_user=lambda **kwargs: (
            retrieval_queries.append(kwargs["query"]),
            [document()],
        )[1]
    )
    model_builder_calls = []

    def model_builder(timeout_ms=None, max_output_tokens=None):
        model_builder_calls.append((timeout_ms, max_output_tokens))
        return object()

    def model_invoker(prompt, model, values):
        if "context" not in values:
            if values["query"] != "What is policy?":
                raise AssertionError("hyde query must match original query")
            return provider_message("hypothetical passage", total_tokens=100)

        if values["question"] != "What is policy?":
            raise AssertionError("final question must remain original")
        return provider_message("Final answer", total_tokens=150)

    result = RagService(
        vector_store_factory=lambda: vector_store,
        model_builder=model_builder,
        model_invoker=model_invoker,
        accounting=accounting_spy.accounting,
    ).answer_query(user=subscribed_user, query="What is policy?", use_hyde=True)

    assert retrieval_queries == ["hypothetical passage"]
    assert model_builder_calls == [
        (settings.RAG_HYDE_TIMEOUT_MS, settings.RAG_HYDE_MAX_OUTPUT_TOKENS),
        (None, None),
    ]
    assert result.retrieval_metadata.mode == "hyde"
    assert result.retrieval_metadata.hypothetical_passage == "hypothetical passage"
    assert result.retrieval_metadata.fallback_reason is None
    assert result.answer == "Final answer"
    assert result.actual_tokens == 250
    assert accounting_spy.calls == ["finalize", "finalize"]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "hyde_content",
    [
        None,
        "",
        "\ud800",
        "A" * 2_001,
        [{"type": "image", "url": "x"}],
    ],
)
def test_service_hyde_fallback_uses_standard_metadata_and_original_query(
    subscribed_user, settings, hyde_content, accounting_spy
):
    settings.OPENROUTER_API_KEY = "test-key"
    settings.OPENROUTER_MODEL = "openrouter/free"
    retrieval_queries = []

    vector_store = SimpleNamespace(
        retrieve_for_user=lambda **kwargs: (
            retrieval_queries.append(kwargs["query"]),
            [document()],
        )[1]
    )

    def model_invoker(prompt, model, values):
        if "context" not in values:
            return provider_message(hyde_content, total_tokens=77)
        return provider_message("Fallback answer", total_tokens=31)

    result = RagService(
        vector_store_factory=lambda: vector_store,
        model_builder=lambda timeout_ms=None, max_output_tokens=None: object(),
        model_invoker=model_invoker,
        accounting=accounting_spy.accounting,
    ).answer_query(user=subscribed_user, query="Policy question", use_hyde=True)

    assert retrieval_queries == ["Policy question"]
    assert result.retrieval_metadata.mode == "standard"
    assert result.retrieval_metadata.fallback_reason == "hyde_unavailable"
    assert result.retrieval_metadata.hypothetical_passage is None
    assert result.actual_tokens == 108
    assert result.answer == "Fallback answer"
    assert DailyTokenUsage.objects.get(user=subscribed_user).used_tokens == 108
    assert accounting_spy.calls == ["finalize", "finalize"]


@pytest.mark.django_db
def test_service_hyde_transport_fallback_sets_reserved_usage_then_standard(
    subscribed_user, settings, accounting_spy
):
    settings.OPENROUTER_API_KEY = "test-key"
    settings.OPENROUTER_MODEL = "openrouter/free"
    retrieval_queries = []

    vector_store = SimpleNamespace(
        retrieve_for_user=lambda **kwargs: (
            retrieval_queries.append(kwargs["query"]),
            [document()],
        )[1]
    )

    def model_invoker(prompt, model, values):
        if "context" not in values:
            raise ProviderTransportError("transport")
        return provider_message("Recovered answer", total_tokens=31)

    result = RagService(
        vector_store_factory=lambda: vector_store,
        model_builder=lambda timeout_ms=None, max_output_tokens=None: object(),
        model_invoker=model_invoker,
        accounting=accounting_spy.accounting,
    ).answer_query(user=subscribed_user, query="Policy question", use_hyde=True)

    expected_hyde = _hyde_estimated_tokens("Policy question", settings=settings)
    expected_final = _final_estimated_tokens([document()], "Policy question", settings=settings)
    assert result.estimated_tokens == expected_hyde + expected_final
    assert result.actual_tokens == expected_hyde + 31
    assert result.retrieval_metadata.mode == "standard"
    assert result.retrieval_metadata.fallback_reason == "hyde_unavailable"
    assert result.retrieval_metadata.hypothetical_passage is None
    assert retrieval_queries == ["Policy question"]
    assert accounting_spy.calls == ["finalize", "finalize"]


@pytest.mark.django_db
def test_service_retrieval_failure_after_hyde_keeps_hyde_billable(
    subscribed_user,
    settings,
    accounting_spy,
):
    settings.OPENROUTER_API_KEY = "test-key"
    settings.OPENROUTER_MODEL = "openrouter/free"

    vector_store = SimpleNamespace(
        retrieve_for_user=lambda **kwargs: (_ for _ in ()).throw(VectorRetrievalError("backend"))
    )

    def model_invoker(prompt, model, values):
        return provider_message("hypothetical passage", total_tokens=77)

    with pytest.raises(RagRetrievalError):
        RagService(
            vector_store_factory=lambda: vector_store,
            model_builder=lambda timeout_ms=None, max_output_tokens=None: object(),
            model_invoker=model_invoker,
            accounting=accounting_spy.accounting,
        ).answer_query(user=subscribed_user, query="What is policy?", use_hyde=True)

    assert DailyTokenUsage.objects.get(user=subscribed_user).used_tokens == 77
    assert accounting_spy.calls == ["finalize"]


@pytest.mark.django_db
def test_service_final_transport_failure_refunds_only_final_reservation(
    subscribed_user,
    settings,
    accounting_spy,
):
    settings.OPENROUTER_API_KEY = "test-key"
    settings.OPENROUTER_MODEL = "openrouter/free"
    vector_store = SimpleNamespace(retrieve_for_user=lambda **kwargs: [document()])

    def model_invoker(prompt, model, values):
        if "context" not in values:
            return provider_message("hypothetical passage", total_tokens=77)
        raise ProviderTransportError("final transport failure")

    with pytest.raises(RagProviderError, match="Unable to generate"):
        RagService(
            vector_store_factory=lambda: vector_store,
            model_builder=lambda timeout_ms=None, max_output_tokens=None: object(),
            model_invoker=model_invoker,
            accounting=accounting_spy.accounting,
        ).answer_query(user=subscribed_user, query="Question", use_hyde=True)

    assert DailyTokenUsage.objects.get(user=subscribed_user).used_tokens == 77
    assert accounting_spy.calls == ["finalize", "refund"]


@pytest.mark.django_db
def test_service_hyde_empty_retrieval_keeps_only_generation_usage(subscribed_user, settings):
    settings.OPENROUTER_API_KEY = "test-key"
    settings.OPENROUTER_MODEL = "openrouter/free"
    vector_store = SimpleNamespace(retrieve_for_user=lambda **kwargs: [])

    result = RagService(
        vector_store_factory=lambda: vector_store,
        model_builder=lambda timeout_ms=None, max_output_tokens=None: object(),
        model_invoker=lambda prompt, model, values: provider_message(
            "hypothetical passage",
            total_tokens=77,
        ),
    ).answer_query(user=subscribed_user, query="Question", use_hyde=True)

    assert result.answer == NO_CONTEXT_ANSWER
    assert result.actual_tokens == 77
    assert result.retrieval_metadata.mode == "hyde"
    assert result.retrieval_metadata.retrieved_chunks_count == 0
    assert DailyTokenUsage.objects.get(user=subscribed_user).used_tokens == 77


@pytest.mark.django_db
def test_service_hyde_quota_rejection_happens_before_model_call(subscribed_user, settings):
    settings.OPENROUTER_API_KEY = "test-key"
    settings.OPENROUTER_MODEL = "openrouter/free"
    subscribed_user.subscription.daily_token_limit = 1
    subscribed_user.subscription.save(update_fields=["daily_token_limit"])

    with pytest.raises(InsufficientCreditsError):
        RagService(
            vector_store_factory=lambda: pytest.fail("retrieval must not run"),
            model_builder=lambda **kwargs: pytest.fail("model must not be built"),
        ).answer_query(user=subscribed_user, query="Question", use_hyde=True)


@pytest.mark.django_db
def test_service_final_quota_rejection_preserves_hyde_usage(subscribed_user, settings):
    settings.OPENROUTER_API_KEY = "test-key"
    settings.OPENROUTER_MODEL = "openrouter/free"
    subscribed_user.subscription.daily_token_limit = _hyde_estimated_tokens(
        "Question",
        settings=settings,
    )
    subscribed_user.subscription.save(update_fields=["daily_token_limit"])
    vector_store = SimpleNamespace(retrieve_for_user=lambda **kwargs: [document()])

    with pytest.raises(InsufficientCreditsError):
        RagService(
            vector_store_factory=lambda: vector_store,
            model_builder=lambda timeout_ms=None, max_output_tokens=None: object(),
            model_invoker=lambda prompt, model, values: provider_message(
                "hypothetical passage",
                total_tokens=10,
            ),
        ).answer_query(user=subscribed_user, query="Question", use_hyde=True)

    assert DailyTokenUsage.objects.get(user=subscribed_user).used_tokens == 10


@pytest.mark.django_db
@pytest.mark.parametrize(
    "invalid_usage",
    [
        {"total_tokens": True},
        {"total_tokens": -1},
        {"total_tokens": "12"},
        {"total_tokens": 10**9},
        {},
        "invalid",
    ],
)
def test_service_invalid_hyde_usage_falls_back_with_bounded_charge(
    subscribed_user,
    settings,
    invalid_usage,
):
    settings.OPENROUTER_API_KEY = "test-key"
    settings.OPENROUTER_MODEL = "openrouter/free"
    retrieval_queries = []
    vector_store = SimpleNamespace(
        retrieve_for_user=lambda **kwargs: (
            retrieval_queries.append(kwargs["query"]),
            [document()],
        )[1]
    )

    def model_invoker(prompt, model, values):
        if "context" not in values:
            return SimpleNamespace(
                content="hypothetical passage",
                usage_metadata=invalid_usage,
            )
        return provider_message("Fallback answer", total_tokens=31)

    result = RagService(
        vector_store_factory=lambda: vector_store,
        model_builder=lambda timeout_ms=None, max_output_tokens=None: object(),
        model_invoker=model_invoker,
    ).answer_query(user=subscribed_user, query="Question", use_hyde=True)

    assert retrieval_queries == ["Question"]
    assert result.retrieval_metadata.mode == "standard"
    assert result.retrieval_metadata.fallback_reason == "hyde_unavailable"
    assert result.actual_tokens <= result.estimated_tokens
    assert DailyTokenUsage.objects.get(user=subscribed_user).used_tokens == result.actual_tokens


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("setting_name", "invalid_value"),
    [
        ("RAG_HYDE_MAX_OUTPUT_TOKENS", 0),
        ("RAG_HYDE_MAX_OUTPUT_CHARS", -1),
        ("RAG_HYDE_TIMEOUT_MS", True),
    ],
)
def test_service_invalid_hyde_settings_fail_before_reservation(
    subscribed_user,
    settings,
    setting_name,
    invalid_value,
):
    settings.OPENROUTER_API_KEY = "test-key"
    settings.OPENROUTER_MODEL = "openrouter/free"
    setattr(settings, setting_name, invalid_value)

    with pytest.raises(RagConfigurationError):
        RagService(
            vector_store_factory=lambda: pytest.fail("retrieval must not run"),
            model_builder=lambda **kwargs: pytest.fail("model must not be built"),
        ).answer_query(user=subscribed_user, query="Question", use_hyde=True)

    assert DailyTokenUsage.objects.count() == 0


@pytest.mark.django_db
def test_service_hyde_programming_error_refunds_and_propagates(
    subscribed_user,
    settings,
    accounting_spy,
):
    settings.OPENROUTER_API_KEY = "test-key"
    settings.OPENROUTER_MODEL = "openrouter/free"

    def fail_invocation(prompt, model, values):
        raise TypeError("implementation defect")

    with pytest.raises(TypeError, match="implementation defect"):
        RagService(
            vector_store_factory=lambda: pytest.fail("retrieval must not run"),
            model_builder=lambda **kwargs: object(),
            model_invoker=fail_invocation,
            accounting=accounting_spy.accounting,
        ).answer_query(user=subscribed_user, query="Question", use_hyde=True)

    assert DailyTokenUsage.objects.get(user=subscribed_user).used_tokens == 0
    assert accounting_spy.calls == ["refund"]


@pytest.mark.django_db
def test_service_final_model_configuration_error_refunds_usage(
    subscribed_user,
    settings,
    accounting_spy,
):
    settings.OPENROUTER_API_KEY = "test-key"
    settings.OPENROUTER_MODEL = "openrouter/free"
    vector_store = SimpleNamespace(retrieve_for_user=lambda **kwargs: [document()])

    def fail_model_builder():
        raise RagConfigurationError("invalid")

    with pytest.raises(RagConfigurationError):
        RagService(
            vector_store_factory=lambda: vector_store,
            model_builder=fail_model_builder,
            accounting=accounting_spy.accounting,
        ).answer_query(user=subscribed_user, query="Question")

    assert DailyTokenUsage.objects.get(user=subscribed_user).used_tokens == 0
    assert accounting_spy.calls == ["refund"]


@pytest.mark.django_db
def test_service_accounting_error_is_safe_error(subscribed_user, settings):
    settings.OPENROUTER_API_KEY = "test-key"
    settings.OPENROUTER_MODEL = "openrouter/free"
    vector_store = SimpleNamespace(retrieve_for_user=lambda **kwargs: [document()])

    finalize_calls = []

    def fail_finalize(_reservation, _actual):
        finalize_calls.append("finalize")
        raise RuntimeError("ledger unavailable")

    accounting = RagStageAccounting(finalize=fail_finalize)

    with pytest.raises(RagAccountingError):
        RagService(
            vector_store_factory=lambda: vector_store,
            model_builder=lambda: object(),
            model_invoker=lambda prompt, model, values: provider_message(
                "answer",
                total_tokens=42,
            ),
            accounting=accounting,
        ).answer_query(user=subscribed_user, query="Question")

    assert finalize_calls == ["finalize"]
    assert DailyTokenUsage.objects.get(user=subscribed_user).used_tokens == _final_estimated_tokens(
        [document()],
        "Question",
        settings=settings,
    )


@pytest.mark.django_db
def test_service_refund_failure_preserves_reserved_quota_and_error_chain(
    subscribed_user,
    settings,
):
    settings.OPENROUTER_API_KEY = "test-key"
    settings.OPENROUTER_MODEL = "openrouter/free"
    vector_store = SimpleNamespace(retrieve_for_user=lambda **kwargs: [document()])
    refund_calls = []

    def fail_refund(_reservation):
        refund_calls.append("refund")
        raise RuntimeError("ledger unavailable")

    accounting = RagStageAccounting(refund=fail_refund)

    with pytest.raises(RagAccountingError) as error:
        RagService(
            vector_store_factory=lambda: vector_store,
            model_builder=lambda: (_ for _ in ()).throw(TypeError("model defect")),
            accounting=accounting,
        ).answer_query(user=subscribed_user, query="Question")

    assert isinstance(error.value.__cause__, RuntimeError)
    assert refund_calls == ["refund"]
    assert DailyTokenUsage.objects.get(user=subscribed_user).used_tokens == _final_estimated_tokens(
        [document()],
        "Question",
        settings=settings,
    )


@pytest.mark.django_db
def test_service_invalid_final_content_stays_billed_without_refund(
    subscribed_user,
    settings,
    accounting_spy,
):
    settings.OPENROUTER_API_KEY = "test-key"
    settings.OPENROUTER_MODEL = "openrouter/free"
    vector_store = SimpleNamespace(retrieve_for_user=lambda **kwargs: [document()])

    with pytest.raises(RagProviderError, match="invalid answer"):
        RagService(
            vector_store_factory=lambda: vector_store,
            model_builder=lambda: object(),
            model_invoker=lambda prompt, model, values: provider_message(""),
            accounting=accounting_spy.accounting,
        ).answer_query(user=subscribed_user, query="Question")

    assert DailyTokenUsage.objects.get(user=subscribed_user).used_tokens > 0
    assert accounting_spy.calls == ["finalize"]
