from typing import Any

import pinecone  # type: ignore[import-not-found]

from ..datatypes.chunk_dataclass import Chunk
from ..datatypes.rag import (
    Document,
    Embeddings,
    SearchResult,
    SearchType,
    VectorStore,
    VectorStoreConfig,
)
from .pinecone_config import PineconeVectorStoreConfig


class PineconeVectorStore(VectorStore):
    """Pinecone-backed vector store implementation."""

    def __init__(self, config: VectorStoreConfig, embeddings: Embeddings):
        super().__init__(config, embeddings)
        if not isinstance(config, PineconeVectorStoreConfig):
            raise TypeError("config must be an instance of PineconeVectorStoreConfig")

        self.config = config
        self._pc = pinecone.Pinecone(api_key=self.config.api_key)

        index_name = (
            self.config.index_name or self.config.collection_name or "research-docs"
        )
        self._index = self._pc.Index(index_name)

    async def add_documents(
        self, documents: list[Document], **kwargs: Any
    ) -> list[str]:
        if not documents:
            return []

        contents = [doc.content for doc in documents]
        vectors = await self.embeddings.vectorize_documents(contents)

        records = []
        for doc, vector in zip(documents, vectors, strict=True):
            metadata = doc.metadata.copy() if doc.metadata else {}
            metadata["content"] = doc.content
            records.append({"id": doc.id, "values": vector, "metadata": metadata})

        self._index.upsert(vectors=records)
        return [doc.id for doc in documents]

    async def add_document_chunks(
        self, chunks: list[Chunk], **kwargs: Any
    ) -> list[str]:
        docs = [
            Document(
                id=chunk.id,
                content=chunk.text,
                metadata={"chunk_index": chunk.start_index},
            )
            for chunk in chunks
        ]
        return await self.add_documents(docs, **kwargs)

    async def add_document_text_chunks(
        self, document_texts: list[str], **kwargs: Any
    ) -> list[str]:
        from ..datatypes.chunk_dataclass import generate_id

        docs = [
            Document(id=generate_id("chunk"), content=text) for text in document_texts
        ]
        return await self.add_documents(docs, **kwargs)

    async def delete_documents(self, document_ids: list[str]) -> bool:
        if not document_ids:
            return True

        self._index.delete(ids=document_ids)
        return True

    async def search(
        self,
        query: str,
        search_type: SearchType,
        retrieval_query: str | None = None,
        **kwargs: Any,
    ) -> list[SearchResult]:
        query_embedding = await self.embeddings.vectorize_query(query)
        return await self.search_with_embeddings(
            query_embedding, search_type, retrieval_query, **kwargs
        )

    async def search_with_embeddings(
        self,
        query_embedding: list[float],
        search_type: SearchType,
        retrieval_query: str | None = None,
        **kwargs: Any,
    ) -> list[SearchResult]:
        top_k = kwargs.get("top_k", 5)
        filters = kwargs.get("filters")

        res = self._index.query(
            vector=query_embedding,
            top_k=top_k,
            filter=filters,
            include_metadata=True,
        )

        results = []
        for rank, match in enumerate(res.get("matches", []), 1):
            metadata = match.get("metadata", {})
            content = metadata.pop("content", "")
            score = match.get("score", 0.0)
            doc = Document(id=match["id"], content=content, metadata=metadata)
            results.append(SearchResult(document=doc, score=score, rank=rank))

        return results

    async def get_document(self, document_id: str) -> Document | None:
        res = self._index.fetch(ids=[document_id])
        vectors = res.get("vectors", {})
        if document_id not in vectors:
            return None

        vector_data = vectors[document_id]
        metadata = vector_data.get("metadata", {})
        content = metadata.pop("content", "")
        return Document(id=document_id, content=content, metadata=metadata)

    async def update_document(self, document: Document) -> bool:
        await self.add_documents([document])
        return True
