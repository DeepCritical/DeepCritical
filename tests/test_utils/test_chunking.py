import pytest

from DeepResearch.src.utils.chunking import chunk_text_by_character


def test_chunk_text_by_character():
    """Tests basic functionality of chunk_text_by_character."""
    text = "This is a test string for chunking."
    chunks = chunk_text_by_character(text, chunk_size=10, chunk_overlap=2)
    assert chunks == [
        "This is a ",
        "a test str",
        "tring for ",
        "r chunking",
        "ng.",
    ]


def test_chunk_text_with_no_overlap():
    """Tests chunking with zero overlap."""
    text = "This is a test string for chunking."
    chunks = chunk_text_by_character(text, chunk_size=10, chunk_overlap=0)
    assert chunks == ["This is a ", "test strin", "g for chun", "king."]


def test_chunk_size_larger_than_text():
    """Tests when chunk size is larger than the text length."""
    text = "Short text."
    chunks = chunk_text_by_character(text, chunk_size=20, chunk_overlap=5)
    assert chunks == ["Short text."]


def test_invalid_overlap_raises_error():
    """Tests that an invalid overlap value raises a ValueError."""
    error_message = "chunk_overlap must be smaller than chunk_size."
    with pytest.raises(ValueError, match=error_message):
        chunk_text_by_character("some text", chunk_size=10, chunk_overlap=10)
    with pytest.raises(ValueError, match=error_message):
        chunk_text_by_character("some text", chunk_size=10, chunk_overlap=11)
