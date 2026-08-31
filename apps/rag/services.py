import logging

from django.conf import settings

from apps.accounts.entitlements import ensure_active_subscription
from apps.documents.exceptions import VectorRetrievalError
from apps.documents.retrieval import retrieve_active_documents_for_user
from apps.documents.vector_store import get_vector_store, validate_retrieval_settings
from apps.rag.accounting import RagStageAccounting
from apps.rag.contracts import RagAnswer, RetrievalMetadata, RetrievalPolicy
from apps.rag.exceptions import (
    ProviderTransportError,
    RagAccountingError,
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
    bind_hyde_prompt,
    bind_rag_prompt,
    chunk_documents_for_prompt,
)
from apps.rag.provider_responses import (
    classify_provider_usage,
    extract_response_text,
    normalize_answer_content,
    normalize_hyde_content,
)
from apps.rag.tokens import estimate_prompt_bound

logger = logging.getLogger(__name__)


class RagService:
    def __init__(
        self,
        *,
        vector_store_factory=get_vector_store,
        model_builder=build_openrouter_chat_model,
        model_invoker=invoke_prompt_model,
        rag_prompt_binder=bind_rag_prompt,
        hyde_prompt_binder=bind_hyde_prompt,
        accounting=None,
    ):
        self.vector_store_factory = vector_store_factory
        self.model_builder = model_builder
        self.model_invoker = model_invoker
        self.rag_prompt_binder = rag_prompt_binder
        self.hyde_prompt_binder = hyde_prompt_binder
        self.accounting = accounting if accounting is not None else RagStageAccounting()
        self._uses_default_vector_store = vector_store_factory is get_vector_store

    def _validated_retrieval_policy(self) -> RetrievalPolicy:
        policy = RetrievalPolicy(
            k=settings.RAG_RETRIEVAL_K,
            search_type=settings.RAG_RETRIEVAL_SEARCH_TYPE,
            score_threshold=settings.RAG_RETRIEVAL_SCORE_THRESHOLD,
            fetch_k=settings.RAG_RETRIEVAL_FETCH_K,
        )
        try:
            validate_retrieval_settings(
                k=policy.k,
                search_type=policy.search_type,
                score_threshold=policy.score_threshold,
                fetch_k=policy.fetch_k,
            )
        except ValueError as exc:
            raise RagConfigurationError("RAG retrieval is not configured.") from exc
        return policy

    def _validate_hyde_settings(self) -> None:
        values = (
            settings.RAG_HYDE_MAX_OUTPUT_TOKENS,
            settings.RAG_HYDE_MAX_OUTPUT_CHARS,
            settings.RAG_HYDE_TIMEOUT_MS,
        )
        if any(
            isinstance(value, bool) or not isinstance(value, int) or value <= 0 for value in values
        ):
            raise RagConfigurationError("LLM provider is not configured.")

    def _settle_stage(
        self,
        *,
        stage,
        message,
        prompt_text: str,
        answer_for_estimate: str,
    ) -> tuple[int, bool]:
        assessment = classify_provider_usage(
            message,
            prompt_text=prompt_text,
            answer=answer_for_estimate,
            reservation_tokens=stage.reserved_tokens,
        )
        if assessment.warning == "invalid_usage":
            logger.warning(
                "Invalid provider token usage metadata from OpenRouter.",
                extra={"usage_id": stage.usage_id},
            )
        elif assessment.warning == "exceeded_reservation":
            logger.warning(
                "Provider usage metadata exceeded reservation bound.",
                extra={"usage_id": stage.usage_id},
            )
        stage.finalize(assessment.actual_tokens)
        return assessment.actual_tokens, assessment.is_acceptable

    @staticmethod
    def _refund_unsettled_stage(stage) -> None:
        try:
            stage.refund()
        except RagAccountingError:
            logger.exception("Unable to refund a RAG stage reservation.")
            raise

    def _run_hyde_generation(self, *, user, query: str) -> tuple[str | None, int, int]:
        self._validate_hyde_settings()
        bound_prompt = self.hyde_prompt_binder(query=query)
        estimated_tokens = estimate_prompt_bound(
            bound_prompt.accounting_text,
            chat_overhead_tokens=settings.RAG_CHAT_OVERHEAD_TOKENS,
            max_output_tokens=settings.RAG_HYDE_MAX_OUTPUT_TOKENS,
        )
        stage = self.accounting.reserve(user, estimated_tokens)

        try:
            model = self.model_builder(
                timeout_ms=settings.RAG_HYDE_TIMEOUT_MS,
                max_output_tokens=settings.RAG_HYDE_MAX_OUTPUT_TOKENS,
            )
            message = self.model_invoker(bound_prompt.prompt, model, bound_prompt.values)
            settled, usage_is_acceptable = self._settle_stage(
                stage=stage,
                message=message,
                prompt_text=bound_prompt.accounting_text,
                answer_for_estimate=extract_response_text(message.content),
            )
            if not usage_is_acceptable:
                return None, estimated_tokens, settled
            try:
                passage = normalize_hyde_content(
                    message.content,
                    max_chars=settings.RAG_HYDE_MAX_OUTPUT_CHARS,
                )
            except RagProviderError:
                return None, estimated_tokens, settled
            return passage, estimated_tokens, settled
        except ProviderTransportError:
            stage.finalize(stage.reserved_tokens)
            return None, estimated_tokens, stage.reserved_tokens
        except RagAccountingError:
            raise
        except Exception:
            if not stage.terminal_attempted:
                self._refund_unsettled_stage(stage)
            raise

    def _fetch_documents_for_query(
        self,
        *,
        user_id: int,
        query: str,
        policy: RetrievalPolicy,
    ):
        return self.vector_store_factory().retrieve_for_user(
            user_id=user_id,
            query=query,
            k=policy.k,
            search_type=policy.search_type,
            score_threshold=policy.score_threshold,
            fetch_k=policy.fetch_k,
        )

    def _fetch_active_documents_for_query(
        self,
        *,
        user_id: int,
        query: str,
        policy: RetrievalPolicy,
    ):
        return retrieve_active_documents_for_user(
            user_id=user_id,
            query=query,
            k=policy.k,
            search_type=policy.search_type,
            score_threshold=policy.score_threshold,
            fetch_k=policy.fetch_k,
            vector_store_factory=self.vector_store_factory,
        )

    def _run_final_answer(
        self,
        *,
        user,
        query: str,
        documents,
    ) -> tuple[int, int, str, list[str]]:
        chunks, context = chunk_documents_for_prompt(
            documents,
            max_chars=settings.RAG_MAX_CONTEXT_CHARS,
        )
        bound_prompt = self.rag_prompt_binder(question=query, context=context)
        estimated_tokens = estimate_prompt_bound(
            bound_prompt.accounting_text,
            chat_overhead_tokens=settings.RAG_CHAT_OVERHEAD_TOKENS,
            max_output_tokens=settings.RAG_MAX_OUTPUT_TOKENS,
        )
        stage = self.accounting.reserve(user, estimated_tokens)

        try:
            model = self.model_builder()
            message = self.model_invoker(bound_prompt.prompt, model, bound_prompt.values)
            settled, usage_is_acceptable = self._settle_stage(
                stage=stage,
                message=message,
                prompt_text=bound_prompt.accounting_text,
                answer_for_estimate=extract_response_text(message.content),
            )
            if not usage_is_acceptable:
                raise RagProviderError("LLM provider returned invalid usage metadata.")
            answer = normalize_answer_content(message.content)
            return estimated_tokens, settled, answer, chunks
        except ProviderTransportError as exc:
            if not stage.terminal_attempted:
                self._refund_unsettled_stage(stage)
            raise RagProviderError("Unable to generate answer right now.") from exc
        except (RagAccountingError, RagProviderError):
            raise
        except Exception:
            if not stage.terminal_attempted:
                self._refund_unsettled_stage(stage)
            raise

    def answer_query(self, *, user, query: str, use_hyde: bool = False) -> RagAnswer:
        ensure_active_subscription(user)
        validate_openrouter_configuration()
        retrieval_policy = self._validated_retrieval_policy()

        retrieval_query = query
        mode = "standard"
        hypothetical_passage = None
        fallback_reason = None

        if use_hyde:
            passage, hyde_estimated_tokens, hyde_actual_tokens = self._run_hyde_generation(
                user=user,
                query=query,
            )
            if passage is not None:
                retrieval_query = passage
                mode = "hyde"
                hypothetical_passage = passage
            else:
                fallback_reason = "hyde_unavailable"
            total_estimated_tokens = hyde_estimated_tokens
            total_actual_tokens = hyde_actual_tokens
        else:
            total_estimated_tokens = 0
            total_actual_tokens = 0

        try:
            if self._uses_default_vector_store:
                documents = self._fetch_active_documents_for_query(
                    user_id=user.id,
                    query=retrieval_query,
                    policy=retrieval_policy,
                )
            else:
                documents = self._fetch_documents_for_query(
                    user_id=user.id,
                    query=retrieval_query,
                    policy=retrieval_policy,
                )
        except VectorRetrievalError as exc:
            raise RagRetrievalError("Vector retrieval is unavailable.") from exc

        if not documents:
            return RagAnswer(
                answer=NO_CONTEXT_ANSWER,
                estimated_tokens=total_estimated_tokens,
                actual_tokens=total_actual_tokens,
                retrieval_metadata=RetrievalMetadata(
                    mode=mode,
                    hypothetical_passage=hypothetical_passage,
                    fallback_reason=fallback_reason,
                    retrieved_chunks_count=0,
                    retrieved_chunks=(),
                ),
            )

        final_estimated, final_actual, answer, chunks = self._run_final_answer(
            user=user,
            query=query,
            documents=documents,
        )
        return RagAnswer(
            answer=answer,
            estimated_tokens=total_estimated_tokens + final_estimated,
            actual_tokens=total_actual_tokens + final_actual,
            retrieval_metadata=RetrievalMetadata(
                mode=mode,
                hypothetical_passage=hypothetical_passage,
                fallback_reason=fallback_reason,
                retrieved_chunks_count=len(chunks),
                retrieved_chunks=tuple(chunks),
            ),
        )
