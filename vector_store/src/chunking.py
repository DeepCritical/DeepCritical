from typing import List


class Chunking:
    """A class for splitting text into chunks."""

    def __init__(self, chunk_size: int = 1024, chunk_overlap: int = 200):
        """
        Initializes the Chunking class.

        Args:
            chunk_size (int): The size of each chunk.
            chunk_overlap (int): The overlap between chunks.
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk(self, text: str) -> list[str]:
        """
        Splits a text into chunks.

        Args:
            text (str): The text to split.

        Returns:
            List[str]: A list of text chunks.
        """
        chunks = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            chunks.append(text[start:end])
            start += self.chunk_size - self.chunk_overlap
        return chunks
