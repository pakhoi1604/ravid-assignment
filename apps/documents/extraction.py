from pathlib import Path

from apps.documents.constants import INVALID_FORMAT_ERROR, PDF_EXTENSION, PLAIN_TEXT_EXTENSIONS
from apps.documents.exceptions import IngestionError


def extract_text(file_path: str, original_filename: str) -> str:
    extension = Path(original_filename).suffix.lower()
    if extension == PDF_EXTENSION:
        return extract_pdf_text(file_path)
    if extension in PLAIN_TEXT_EXTENSIONS:
        return extract_plain_text(file_path)
    raise IngestionError(INVALID_FORMAT_ERROR)


def extract_plain_text(file_path: str) -> str:
    try:
        return Path(file_path).read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise IngestionError("Failed to parse document content.") from exc


def extract_pdf_text(file_path: str) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise IngestionError("Failed to parse document content.") from exc

    try:
        reader = PdfReader(file_path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:
        raise IngestionError("Failed to parse document content.") from exc
