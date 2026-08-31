class RagConfigurationError(Exception):
    """Raised when the configured LLM provider cannot be used safely."""


class RagRetrievalError(Exception):
    """Raised when owner-scoped context retrieval is unavailable."""


class ProviderTransportError(Exception):
    """Raised by the provider adapter for documented OpenRouter failures."""


class RagProviderError(Exception):
    """Raised when the RAG answer provider cannot complete a request."""


class RagAccountingError(Exception):
    """Raised when final token settlement cannot be safely completed."""
