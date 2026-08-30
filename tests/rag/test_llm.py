import httpx
import pytest
from openrouter.errors import NoResponseError, OpenRouterError

from apps.rag.exceptions import ProviderTransportError, RagConfigurationError
from apps.rag.llm import (
    build_openrouter_chat_model,
    invoke_prompt_model,
    validate_openrouter_configuration,
)


def test_openrouter_configuration_requires_key_and_free_model(settings):
    settings.OPENROUTER_API_KEY = ""
    settings.OPENROUTER_MODEL = "openrouter/free"
    with pytest.raises(RagConfigurationError, match="not configured"):
        validate_openrouter_configuration()

    settings.OPENROUTER_API_KEY = "test-key"
    settings.OPENROUTER_MODEL = "openrouter/auto"
    with pytest.raises(RagConfigurationError, match="free-tier"):
        validate_openrouter_configuration()

    settings.OPENROUTER_MODEL = "example/model:free"
    validate_openrouter_configuration()

    settings.RAG_PROVIDER_MAX_RETRIES = 1
    with pytest.raises(RagConfigurationError, match="not configured"):
        validate_openrouter_configuration()


def test_openrouter_model_uses_effective_bounded_timeout_and_no_retries(settings):
    settings.OPENROUTER_API_KEY = "test-key"
    settings.OPENROUTER_MODEL = "openrouter/free"
    settings.RAG_PROVIDER_TIMEOUT_MS = 10_000
    settings.RAG_PROVIDER_MAX_RETRIES = 0

    model = build_openrouter_chat_model()
    sdk_configuration = model.client.sdk_configuration

    assert sdk_configuration.timeout_ms == 10_000
    assert sdk_configuration.retry_config is None


def test_provider_adapter_translates_openrouter_error():
    error = OpenRouterError(
        "provider failed",
        httpx.Response(503, request=httpx.Request("POST", "https://example.test")),
    )

    class Chain:
        def invoke(self, values):
            raise error

    class Prompt:
        def __or__(self, model):
            return Chain()

    with pytest.raises(ProviderTransportError, match="OpenRouter request failed"):
        invoke_prompt_model(Prompt(), object(), {"question": "q", "context": "c"})


@pytest.mark.parametrize(
    "error",
    [
        NoResponseError("No response received"),
        httpx.ConnectError(
            "connection failed",
            request=httpx.Request("POST", "https://example.test"),
        ),
        ValueError("OpenRouter API returned an error: provider unavailable (code: 503)"),
        ValueError("OpenRouter API returned a response with no choices."),
    ],
)
def test_provider_adapter_translates_locked_transport_and_response_errors(error):
    class Chain:
        def invoke(self, values):
            raise error

    class Prompt:
        def __or__(self, model):
            return Chain()

    with pytest.raises(ProviderTransportError, match="OpenRouter request failed"):
        invoke_prompt_model(Prompt(), object(), {"question": "q", "context": "c"})


def test_provider_adapter_does_not_hide_unrelated_value_errors():
    class Chain:
        def invoke(self, values):
            raise ValueError("implementation defect")

    class Prompt:
        def __or__(self, model):
            return Chain()

    with pytest.raises(ValueError, match="implementation defect"):
        invoke_prompt_model(Prompt(), object(), {"question": "q", "context": "c"})


def test_provider_adapter_does_not_hide_programming_errors():
    class Chain:
        def invoke(self, values):
            raise TypeError("implementation defect")

    class Prompt:
        def __or__(self, model):
            return Chain()

    with pytest.raises(TypeError, match="implementation defect"):
        invoke_prompt_model(Prompt(), object(), {"question": "q", "context": "c"})
