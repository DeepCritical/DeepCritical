import os
import sys
from pathlib import Path

import numpy as np

from vector_store.src import Chunking, Embedding, VectorStore


def main():
    """
    An example of a simple RAG pipeline using the VectorStore.
    """
    # 1. Initialize the components
    embedding_model = Embedding()
    chunking_strategy = Chunking(chunk_size=100, chunk_overlap=20)

    # Define file paths for the store
    index_path = "vector_store.index"
    metadata_path = "vector_store.metadata"

    # Clean up previous runs
    if Path(index_path).exists():
        Path(index_path).unlink()
    if Path(metadata_path).exists():
        Path(metadata_path).unlink()

    vector_store = VectorStore(embedding=embedding_model, chunking=chunking_strategy)

    # 2. Define some sample documents
    documents = {
        "doc1": "The quick brown fox jumps over the lazy dog.",
        "doc2": "The five boxing wizards jump quickly.",
        "doc3": "Alzheimer's disease is a progressive neurodegenerative disorder that slowly destroys memory and thinking skills.",
        "doc4": "Research on Alzheimer's is ongoing, with a focus on early detection, treatment, and prevention."
    }

    # 3. Add documents to the vector store
    print("Adding documents to the vector store...")
    vector_store.add_documents(documents)
    print("Documents added.")

    # 4. Define a query
    query = "What is Alzheimer's disease?"

    # 5. Search the vector store
    print(f"\\nSearching for: '{query}'")
    results = vector_store.search(query, k=2)

    # 6. Print the results
    print("\\nSearch results:")
    for doc, score in results:
        print(f"  - Document: '{doc}', Score: {score:.4f}")

    # 7. Demonstrate saving and loading
    print(f"\\nSaving vector store to '{index_path}' and '{metadata_path}'...")
    vector_store.save(index_path, metadata_path)
    print("Vector store saved.")

    # 8. Load the vector store from disk
    print("\\nLoading vector store from disk...")
    loaded_vector_store = VectorStore.load(index_path, metadata_path, embedding_model, chunking_strategy)
    print("Vector store loaded.")

    # 9. Search the loaded vector store
    print(f"\\nSearching the loaded store for: '{query}'")
    loaded_results = loaded_vector_store.search(query, k=2)

    print("\\nSearch results from loaded store:")
    for doc, score in loaded_results:
        print(f"  - Document: '{doc}', Score: {score:.4f}")

    # 10. Deleting documents
    print("\\nDeleting document 'doc3'...")
    loaded_vector_store.delete_documents(["doc3"])
    print("Document deleted.")

    # 11. Search again after deletion
    print(f"\\nSearching again for: '{query}'")
    results_after_delete = loaded_vector_store.search(query, k=2)
    print("\\nSearch results after deletion:")
    for doc, score in results_after_delete:
        print(f"  - Document: '{doc}', Score: {score:.4f}")

    # Clean up the created files
    if Path(index_path).exists():
        Path(index_path).unlink()
    if Path(metadata_path).exists():
        Path(metadata_path).unlink()

if __name__ == "__main__":
    main()
