import pickle
from typing import Dict, List, Tuple

import faiss
import numpy as np

from .chunking import Chunking
from .embeddings import Embedding


class VectorStore:
    """A vector store using FAISS for indexing."""

    def __init__(self, embedding: Embedding, chunking: Chunking):
        """
        Initializes the VectorStore class.

        Args:
            embedding (Embedding): An instance of the Embedding class.
            chunking (Chunking): An instance of the Chunking class.
        """
        self.embedding = embedding
        self.chunking = chunking
        self.index = None
        self.doc_id_to_chunks: dict[str, list[int]] = {}
        self.chunk_id_to_text: dict[int, str] = {}
        self.chunk_id_to_doc_id: dict[int, str] = {}
        self._next_chunk_id = 0

    def add_documents(self, documents: dict[str, str]):
        """
        Adds documents to the vector store.

        Args:
            documents (Dict[str, str]): A dictionary of documents, where the keys are document IDs and the values are the document texts.
        """
        if not documents:
            return

        all_chunks = []
        for doc_id, text in documents.items():
            chunks = self.chunking.chunk(text)
            chunk_ids = list(range(self._next_chunk_id, self._next_chunk_id + len(chunks)))
            self.doc_id_to_chunks[doc_id] = chunk_ids
            for chunk_id, chunk_text in zip(chunk_ids, chunks, strict=True):
                self.chunk_id_to_text[chunk_id] = chunk_text
                self.chunk_id_to_doc_id[chunk_id] = doc_id
            self._next_chunk_id += len(chunks)
            all_chunks.extend(chunks)

        if not all_chunks:
            return

        embeddings = np.array(self.embedding.embed(all_chunks)).astype("float32")

        if self.index is None:
            self.index = faiss.IndexIDMap(faiss.IndexFlatL2(embeddings.shape[1]))

        ids = np.array(list(range(self._next_chunk_id - len(all_chunks), self._next_chunk_id)))
        if self.index is not None:
            self.index.add_with_ids(embeddings, ids)

    def delete_documents(self, doc_ids: list[str]):
        """
        Deletes documents from the vector store.

        Args:
            doc_ids (List[str]): A list of document IDs to delete.
        """
        if self.index is None:
            return

        chunk_ids_to_delete = []
        for doc_id in doc_ids:
            if doc_id in self.doc_id_to_chunks:
                chunk_ids_to_delete.extend(self.doc_id_to_chunks[doc_id])
                del self.doc_id_to_chunks[doc_id]

        if chunk_ids_to_delete:
            self.index.remove_ids(np.array(chunk_ids_to_delete))
            for chunk_id in chunk_ids_to_delete:
                del self.chunk_id_to_text[chunk_id]
                del self.chunk_id_to_doc_id[chunk_id]

    def search(self, query: str, k: int = 5) -> list[tuple[str, str, float]]:
        """
        Searches the vector store for the most similar documents to a query.

        Args:
            query (str): The query text.
            k (int): The number of results to return.

        Returns:
            List[Tuple[str, float]]: A list of tuples, where each tuple contains the document chunk and the similarity score.
        """
        if self.index is None:
            return []

        query_embedding = np.array(self.embedding.embed([query])).astype("float32")
        distances, ids = self.index.search(query_embedding, k)

        results = []
        for i in range(len(ids[0])):
            chunk_id = ids[0][i]
            if chunk_id in self.chunk_id_to_text:
                results.append((self.chunk_id_to_doc_id[chunk_id], self.chunk_id_to_text[chunk_id], distances[0][i]))
        return results

    def save(self, index_path: str, metadata_path: str):
        """
        Saves the vector store to disk.

        Args:
            index_path (str): The path to save the FAISS index to.
            metadata_path (str): The path to save the metadata to.
        """
        if self.index is not None:
            faiss.write_index(self.index, index_path)
        with open(metadata_path, "wb") as f:
            pickle.dump({
                "doc_id_to_chunks": self.doc_id_to_chunks,
                "chunk_id_to_text": self.chunk_id_to_text,
                "chunk_id_to_doc_id": self.chunk_id_to_doc_id,
                "_next_chunk_id": self._next_chunk_id
            }, f)

    @staticmethod
    def load(index_path: str, metadata_path: str, embedding: Embedding, chunking: Chunking) -> "VectorStore":
        """
        Loads a vector store from disk.

        Args:
            index_path (str): The path to the FAISS index file.
            metadata_path (str): The path to the metadata file.
            embedding (Embedding): An instance of the Embedding class.
            chunking (Chunking): An instance of the Chunking class.

        Returns:
            VectorStore: A new VectorStore instance.
        """
        store = VectorStore(embedding, chunking)
        try:
            store.index = faiss.read_index(index_path)
            with open(metadata_path, "rb") as f:
                metadata = pickle.load(f)
                store.doc_id_to_chunks = metadata["doc_id_to_chunks"]
                store.chunk_id_to_text = metadata["chunk_id_to_text"]
                store.chunk_id_to_doc_id = metadata["chunk_id_to_doc_id"]
                store._next_chunk_id = metadata["_next_chunk_id"]
        except (FileNotFoundError, EOFError):
            pass # Return a new store if files don't exist or are empty
        return store
