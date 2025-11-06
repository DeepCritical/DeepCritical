from typing import List


def chunk_text_by_character(
    text: str, chunk_size: int, chunk_overlap: int
) -> list[str]:
    """
    Splits a text into chunks of a specified size with a specified overlap.

    Args:
        text: The text to be chunked.
        chunk_size: The desired size of each chunk in characters.
        chunk_overlap: The number of characters to overlap between chunks.

    Returns:
        A list of text chunks.
    """
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size.")

    chunks = []
    start_index = 0
    while start_index < len(text):
        end_index = start_index + chunk_size
        chunks.append(text[start_index:end_index])
        start_index += chunk_size - chunk_overlap
    return chunks
