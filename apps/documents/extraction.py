from pathlib import Path

from apps.documents.constants import INVALID_FORMAT_ERROR, PDF_EXTENSION, PLAIN_TEXT_EXTENSIONS
from apps.documents.exceptions import IngestionError


def extract_text(
    file_path: str,
    original_filename: str,
    *,
    max_pdf_pages: int | None = None,
    max_chars: int | None = None,
) -> str:
    extension = Path(original_filename).suffix.lower()
    if extension == PDF_EXTENSION:
        return extract_pdf_text(file_path, max_pages=max_pdf_pages, max_chars=max_chars)
    if extension in PLAIN_TEXT_EXTENSIONS:
        return extract_plain_text(file_path, max_chars=max_chars)
    raise IngestionError(INVALID_FORMAT_ERROR)


def extract_plain_text(file_path: str, *, max_chars: int | None = None) -> str:
    try:
        if max_chars is None:
            return Path(file_path).read_text(encoding="utf-8")
        with Path(file_path).open("r", encoding="utf-8") as handle:
            text = handle.read(max_chars + 1)
    except UnicodeDecodeError as exc:
        raise IngestionError("Failed to parse document content.") from exc
    if len(text) > max_chars:
        raise IngestionError("Failed to parse document content.")
    return text


def extract_pdf_text(
    file_path: str,
    *,
    max_pages: int | None = None,
    max_chars: int | None = None,
) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise IngestionError("Failed to parse document content.") from exc

    try:
        reader = PdfReader(file_path)
        if max_pages is not None and len(reader.pages) > max_pages:
            raise IngestionError("Failed to parse document content.")

        parts = []
        total_chars = 0
        for page in reader.pages:
            page_text = page.extract_text() or ""
            total_chars += len(page_text)
            if max_chars is not None and total_chars > max_chars:
                raise IngestionError("Failed to parse document content.")
            parts.append(page_text)
        return "\n".join(parts)
    except IngestionError:
        raise
    except Exception as exc:
        raise IngestionError("Failed to parse document content.") from exc
