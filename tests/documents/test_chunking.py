from apps.documents.chunking import split_text


def test_split_text_uses_requested_chunk_settings():
    chunks = split_text("alpha beta gamma delta", chunk_size=10, chunk_overlap=2)

    assert chunks
    assert all(chunk.strip() for chunk in chunks)
    assert all(len(chunk) <= 10 for chunk in chunks)
