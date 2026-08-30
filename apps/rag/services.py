from dataclasses import dataclass

from django.conf import settings

from apps.accounts.entitlements import (
    ensure_active_subscription,
    finalize_daily_tokens,
    refund_daily_tokens,
    reserve_daily_tokens,
)
from apps.documents.vector_store import VectorRetrievalError, get_vector_store
from apps.rag.exceptions import (
    ProviderTransportError,
    RagConfigurationError,
    RagProviderError,
    RagRetrievalError,
)
from apps.rag.llm import (
    build_openrouter_chat_model,
    invoke_prompt_model,
    validate_openrouter_configuration,
)
from apps.rag.prompts import (
    NO_CONTEXT_ANSWER,
    build_rag_prompt,
    format_documents,
    render_prompt_for_bound,
)
from apps.rag.tokens import estimate_prompt_bound, usage_or_fallback


@dataclass(frozen=True)
class RagAnswer:
    answer: str
    estimated_tokens: int
    actual_tokens: int


def normalize_answer_content(content) -> str:
    if isinstance(content, str):
        answer = content.strip()
    elif isinstance(content, list):
        text_parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text")
                if isinstance(text, str):
                    text_parts.append(text)
        answer = "".join(text_parts).strip()
    else:
        answer = ""

    if not answer:
        raise RagProviderError("LLM provider returned an invalid answer.")
    return answer


class RagService:
    def __init__(
        self,
        *,
        vector_store_factory=get_vector_store,
        model_builder=build_openrouter_chat_model,
        prompt_builder=build_rag_prompt,
        model_invoker=invoke_prompt_model,
    ):
        self.vector_store_factory = vector_store_factory
        self.model_builder = model_builder
        self.prompt_builder = prompt_builder
        self.model_invoker = model_invoker

    def answer_query(self, *, user, query: str) -> RagAnswer:
        ensure_active_subscription(user)
        validate_openrouter_configuration()

        try:
            documents = self.vector_store_factory().retrieve_for_user(
                user_id=user.id,
                query=query,
                k=settings.RAG_RETRIEVAL_K,
            )
        except VectorRetrievalError as exc:
            raise RagRetrievalError("Vector retrieval is unavailable.") from exc

        if not documents:
            return RagAnswer(answer=NO_CONTEXT_ANSWER, estimated_tokens=0, actual_tokens=0)

        context = format_documents(documents, max_chars=settings.RAG_MAX_CONTEXT_CHARS)
        prompt_text = render_prompt_for_bound(question=query, context=context)
        estimated_tokens = estimate_prompt_bound(
            prompt_text,
            chat_overhead_tokens=settings.RAG_CHAT_OVERHEAD_TOKENS,
            max_output_tokens=settings.RAG_MAX_OUTPUT_TOKENS,
        )
        reservation = reserve_daily_tokens(user, estimated_tokens)

        try:
            model = self.model_builder()
            message = self.model_invoker(
                self.prompt_builder(),
                model,
                {"question": query, "context": context},
            )
            answer = normalize_answer_content(message.content)
        except RagConfigurationError:
            refund_daily_tokens(reservation)
            raise
        except ProviderTransportError as exc:
            refund_daily_tokens(reservation)
            raise RagProviderError("Unable to generate answer right now.") from exc
        except RagProviderError:
            refund_daily_tokens(reservation)
            raise

        actual_tokens = usage_or_fallback(message, prompt_text=prompt_text, answer=answer)
        finalize_daily_tokens(reservation, actual_tokens)
        return RagAnswer(
            answer=answer,
            estimated_tokens=estimated_tokens,
            actual_tokens=actual_tokens,
        )
