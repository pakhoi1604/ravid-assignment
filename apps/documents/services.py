from dataclasses import dataclass

from django.conf import settings

from apps.documents.models import IngestionJob


class IngestionError(Exception):
    """Raised for expected document ingestion failures."""


@dataclass(frozen=True)
class Chunk:
    text: str
    metadata: dict[str, str | int]
    id: str


def run_ingestion_pipeline(job: IngestionJob) -> int:
    from apps.documents.chunking import split_text
    from apps.documents.extraction import extract_text
    from apps.documents.vector_store import get_vector_store

    document = job.document
    text = extract_text(document.file.path, document.original_filename)
    if not text.strip():
        raise IngestionError("Failed to parse document content.")

    texts = split_text(
        text,
        chunk_size=settings.VECTOR_CHUNK_SIZE,
        chunk_overlap=settings.VECTOR_CHUNK_OVERLAP,
    )
    if not texts:
        raise IngestionError("Failed to parse document content.")

    chunks = [
        Chunk(
            text=chunk_text,
            id=f"document-{document.public_id}-chunk-{index}",
            metadata={
                "user_id": document.owner_id,
                "document_id": str(document.public_id),
                "ingestion_job_id": job.pk,
                "task_id": str(job.task_id),
                "chunk_index": index,
                "source_filename": document.original_filename,
            },
        )
        for index, chunk_text in enumerate(texts)
    ]

    vector_store = get_vector_store()
    vector_store.replace_document_chunks(str(document.public_id), chunks)
    return len(chunks)
