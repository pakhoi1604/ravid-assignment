from pathlib import Path

from apps.documents.services import IngestionError


def extract_text(file_path: str, original_filename: str) -> str:
    extension = Path(original_filename).suffix.lower()
    if extension == ".pdf":
        return extract_pdf_text(file_path)
    if extension in {".txt", ".md", ".markdown"}:
        return extract_plain_text(file_path)
    raise IngestionError("Invalid file format. Only PDF, TXT, and Markdown files are allowed.")


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
