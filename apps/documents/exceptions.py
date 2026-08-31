class IngestionError(Exception):
    """Raised for expected document ingestion failures."""


class VectorRetrievalError(Exception):
    """Raised when owner-scoped vector retrieval is unavailable or unsafe."""
