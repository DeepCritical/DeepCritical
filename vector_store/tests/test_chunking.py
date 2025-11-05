import pytest

from vector_store.src.chunking import Chunking


def test_chunking():
    """
    Tests that the chunk method correctly splits a text into chunks.
    """
    chunking = Chunking(chunk_size=10, chunk_overlap=3)
    text = "This is a test sentence for chunking."
    chunks = chunking.chunk(text)

    assert isinstance(chunks, list)
    assert len(chunks) == 6
    assert chunks[0] == "This is a "
    assert chunks[1] == " a test se"
    assert chunks[2] == " sentence "
    assert chunks[3] == "ce for chu"
    assert chunks[4] == "chunking."
    assert chunks[5] == "g."
