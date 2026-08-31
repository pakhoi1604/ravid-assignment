import pytest

from apps.documents.chunking import split_text
from apps.documents.exceptions import IngestionError


def test_split_text_uses_requested_chunk_settings():
    chunks = split_text("alpha beta gamma delta", chunk_size=10, chunk_overlap=2)

    assert chunks
    assert all(chunk.strip() for chunk in chunks)
    assert all(len(chunk) <= 10 for chunk in chunks)


def test_split_text_preserves_requested_overlap_for_long_text():
    chunks = split_text("abcdefghijklmnopqrstuvwxyz", chunk_size=10, chunk_overlap=3)

    assert len(chunks) > 1
    assert all(
        previous[-3:] == current[:3] for previous, current in zip(chunks, chunks[1:], strict=False)
    )


def test_split_text_filters_blank_chunks():
    assert split_text("   \n\n", chunk_size=10, chunk_overlap=2) == []


def test_split_text_rejects_over_chunk_limit():
    with pytest.raises(IngestionError):
        split_text("alpha beta gamma delta", chunk_size=5, chunk_overlap=0, max_chunks=1)


def test_split_text_allows_exact_chunk_limit():
    chunks = split_text("alpha beta", chunk_size=5, chunk_overlap=0, max_chunks=2)

    assert len(chunks) == 2
