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


def build_openrouter_chat_model():
    validate_openrouter_configuration()
    try:
        import openrouter
        from langchain_openrouter import ChatOpenRouter

        sdk_client = openrouter.OpenRouter(
            api_key=settings.OPENROUTER_API_KEY,
            server_url=settings.OPENROUTER_BASE_URL,
            http_referer=settings.OPENROUTER_APP_URL or None,
            x_open_router_title=settings.OPENROUTER_APP_TITLE,
            timeout_ms=settings.RAG_PROVIDER_TIMEOUT_MS,
            retry_config=None,
        )
        return ChatOpenRouter(
            client=sdk_client,
            api_key=settings.OPENROUTER_API_KEY,
            base_url=settings.OPENROUTER_BASE_URL,
            model=settings.OPENROUTER_MODEL,
            temperature=settings.RAG_TEMPERATURE,
            max_tokens=settings.RAG_MAX_OUTPUT_TOKENS,
            timeout=settings.RAG_PROVIDER_TIMEOUT_MS,
            max_retries=settings.RAG_PROVIDER_MAX_RETRIES,
            app_url=settings.OPENROUTER_APP_URL or None,
            app_title=settings.OPENROUTER_APP_TITLE,
        )
    except (ImportError, ValueError) as exc:
        raise RagConfigurationError("LLM provider is not configured.") from exc


def invoke_prompt_model(prompt, model, values: dict[str, str]) -> Any:
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
