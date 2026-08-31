from django.conf import settings

from apps.documents import chunking, extraction, vector_store
from apps.documents.contracts import Chunk
from apps.documents.exceptions import IngestionError
from apps.documents.models import IngestionJob


def run_ingestion_pipeline(job: IngestionJob) -> int:
    document = job.document
    text = extraction.extract_text(document.file.path, document.original_filename)
    if not text.strip():
        raise IngestionError("Failed to parse document content.")

    texts = chunking.split_text(
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

    store = vector_store.get_vector_store()
    store.replace_document_chunks(
        user_id=document.owner_id,
        document_id=str(document.public_id),
        chunks=chunks,
    )
    return len(chunks)
