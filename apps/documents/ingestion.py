from django.conf import settings

from apps.documents import chunking, extraction, vector_store
from apps.documents.contracts import Chunk
from apps.documents.exceptions import IngestionError
from apps.documents.models import IngestionGeneration, IngestionJob


def run_ingestion_pipeline(job: IngestionJob, generation) -> int:
    document = job.document
    generation_text = str(generation)
    manifest, _created = IngestionGeneration.objects.update_or_create(
        document=document,
        generation=generation,
        defaults={
            "status": IngestionGeneration.Status.WRITING,
            "failure_code": "",
        },
    )

    text = extraction.extract_text(
        document.file.path,
        document.original_filename,
        max_pdf_pages=settings.INGESTION_MAX_PDF_PAGES,
        max_chars=settings.INGESTION_MAX_EXTRACTED_CHARS,
    )
    if not text.strip():
        raise IngestionError("Failed to parse document content.")

    texts = chunking.split_text(
        text,
        chunk_size=settings.VECTOR_CHUNK_SIZE,
        chunk_overlap=settings.VECTOR_CHUNK_OVERLAP,
        max_chunks=settings.INGESTION_MAX_CHUNKS,
    )
    if not texts:
        raise IngestionError("Failed to parse document content.")

    chunks = [
        Chunk(
            text=chunk_text,
            id=f"document-{document.public_id}-generation-{generation_text}-chunk-{index}",
            metadata={
                "user_id": document.owner_id,
                "document_id": str(document.public_id),
                "generation": generation_text,
                "chunk_index": index,
                "source_filename": document.original_filename,
            },
        )
        for index, chunk_text in enumerate(texts)
    ]
    manifest.expected_chunk_count = len(chunks)
    manifest.save(update_fields=["expected_chunk_count", "updated_at"])

    store = vector_store.get_vector_store()
    store.write_document_generation(
        user_id=document.owner_id,
        document_id=str(document.public_id),
        generation=generation_text,
        chunks=chunks,
    )
    manifest.observed_chunk_count = len(chunks)
    manifest.save(update_fields=["observed_chunk_count", "updated_at"])
    return len(chunks)
