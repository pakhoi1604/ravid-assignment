from collections.abc import Mapping
from typing import Any

import httpx
from django.conf import settings

from apps.rag.exceptions import (
    ProviderTransportError,
    RagConfigurationError,
)


def validate_openrouter_configuration() -> None:
    if not settings.OPENROUTER_API_KEY:
        raise RagConfigurationError("LLM provider is not configured.")

    model = settings.OPENROUTER_MODEL
    if model != "openrouter/free" and not model.endswith(":free"):
        raise RagConfigurationError("LLM provider must use a free-tier model.")
    if settings.RAG_PROVIDER_TIMEOUT_MS <= 0 or settings.RAG_PROVIDER_MAX_RETRIES != 0:
        raise RagConfigurationError("LLM provider is not configured.")


def _as_positive_int(value: int, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise RagConfigurationError(f"{name} must be a positive integer.")
    return value


def build_openrouter_chat_model(
    *,
    timeout_ms: int | None = None,
    max_output_tokens: int | None = None,
):
    validate_openrouter_configuration()

    effective_timeout_ms = _as_positive_int(
        settings.RAG_PROVIDER_TIMEOUT_MS if timeout_ms is None else timeout_ms,
        name="RAG_PROVIDER_TIMEOUT_MS",
    )
    effective_max_output_tokens = _as_positive_int(
        settings.RAG_MAX_OUTPUT_TOKENS if max_output_tokens is None else max_output_tokens,
        name="max_output_tokens",
    )

    try:
        import openrouter
        from langchain_openrouter import ChatOpenRouter

        sdk_client = openrouter.OpenRouter(
            api_key=settings.OPENROUTER_API_KEY,
            server_url=settings.OPENROUTER_BASE_URL,
            http_referer=settings.OPENROUTER_APP_URL or None,
            x_open_router_title=settings.OPENROUTER_APP_TITLE,
            timeout_ms=effective_timeout_ms,
            retry_config=None,
        )
        return ChatOpenRouter(
            client=sdk_client,
            api_key=settings.OPENROUTER_API_KEY,
            base_url=settings.OPENROUTER_BASE_URL,
            model=settings.OPENROUTER_MODEL,
            temperature=settings.RAG_TEMPERATURE,
            max_tokens=effective_max_output_tokens,
            timeout=effective_timeout_ms,
            max_retries=settings.RAG_PROVIDER_MAX_RETRIES,
            app_url=settings.OPENROUTER_APP_URL or None,
            app_title=settings.OPENROUTER_APP_TITLE,
        )
    except (ImportError, ValueError) as exc:
        raise RagConfigurationError("LLM provider is not configured.") from exc


def invoke_prompt_model(prompt, model, values: Mapping[str, str]) -> Any:
    try:
        from openrouter.errors import NoResponseError, OpenRouterError

        return (prompt | model).invoke(values)
    except (OpenRouterError, NoResponseError, httpx.TransportError) as exc:
        raise ProviderTransportError("OpenRouter request failed.") from exc
    except ValueError as exc:
        message = str(exc)
        provider_response_prefixes = (
            "OpenRouter API returned an error:",
            "OpenRouter API returned a response with no choices.",
        )
        if not message.startswith(provider_response_prefixes):
            raise
        raise ProviderTransportError("OpenRouter request failed.") from exc
