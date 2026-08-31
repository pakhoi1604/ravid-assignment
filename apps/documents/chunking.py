from apps.documents.exceptions import IngestionError


def split_text(
    text: str,
    *,
    chunk_size: int,
    chunk_overlap: int,
    max_chunks: int | None = None,
) -> list[str]:
    if max_chunks is not None:
        stride = max(1, chunk_size - chunk_overlap)
        max_materialized_chars = (max_chunks * stride) + chunk_overlap
        if len(text) > max_materialized_chars:
            raise IngestionError("Failed to parse document content.")

    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
    except ImportError as exc:
        raise IngestionError("Failed to parse document content.") from exc

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    chunks = []
    for chunk in splitter.split_text(text):
        if not chunk.strip():
            continue
        chunks.append(chunk)
        if max_chunks is not None and len(chunks) > max_chunks:
            raise IngestionError("Failed to parse document content.")
    return chunks
