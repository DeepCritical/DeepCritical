from typing import List

from sentence_transformers import SentenceTransformer


class Embedding:
    """A class for embedding text using sentence-transformers."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initializes the Embedding class.

        Args:
            model_name (str): The name of the sentence-transformer model to use.
        """
        self.model = SentenceTransformer(model_name)

    def embed(self, texts: list[str]) -> list[list[float]]:
        """
        Embeds a list of texts.

        Args:
            texts (List[str]): A list of texts to embed.

        Returns:
            List[List[float]]: A list of embeddings, where each embedding is a list of floats.
        """
        return self.model.encode(texts).tolist()
