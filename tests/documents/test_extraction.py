import sys
import types

import pytest

from apps.documents.extraction import extract_pdf_text, extract_plain_text, extract_text
from apps.documents.services import IngestionError


def test_extract_plain_text_reads_utf8(tmp_path):
    path = tmp_path / "notes.md"
    path.write_text("# Hello\nWorld", encoding="utf-8")

    assert extract_text(str(path), "notes.md") == "# Hello\nWorld"


def test_extract_plain_text_rejects_invalid_utf8(tmp_path):
    path = tmp_path / "notes.txt"
    path.write_bytes(b"\xff")

    with pytest.raises(IngestionError):
        extract_plain_text(str(path))


def test_extract_rejects_unsupported_extension(tmp_path):
    path = tmp_path / "image.png"
    path.write_text("nope", encoding="utf-8")

    with pytest.raises(IngestionError, match="Invalid file format"):
        extract_text(str(path), "image.png")


def test_extract_pdf_text_uses_pdf_reader(monkeypatch, tmp_path):
    path = tmp_path / "doc.pdf"
    path.write_bytes(b"%PDF")

    class Page:
        def __init__(self, text):
            self.text = text

        def extract_text(self):
            return self.text

    class PdfReader:
        def __init__(self, file_path):
            assert file_path == str(path)
            self.pages = [Page("first"), Page(None), Page("second")]

    monkeypatch.setitem(sys.modules, "pypdf", types.SimpleNamespace(PdfReader=PdfReader))

    assert extract_pdf_text(str(path)) == "first\n\nsecond"
