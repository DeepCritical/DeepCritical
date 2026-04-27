from typing import Any

import pymilvus  # type: ignore[import-not-found]

from ..datatypes.chunk_dataclass import Chunk
from ..datatypes.rag import (
    Document,
    Embeddings,
    SearchResult,
    SearchType,
    VectorStore,
    VectorStoreConfig,
)
from .milvus_config import MilvusVectorStoreConfig


class MilvusVectorStore(VectorStore):
    """Milvus-backed vector store implementation."""

    def __init__(self, config: VectorStoreConfig, embeddings: Embeddings):
        super().__init__(config, embeddings)
        if not isinstance(config, MilvusVectorStoreConfig):
            raise TypeError("config must be an instance of MilvusVectorStoreConfig")

        self.config = config
        self._collection_name = config.collection_name or "research_docs"

        # Connect to Milvus
        self._client = pymilvus.MilvusClient(
            uri=self.config.uri, token=self.config.token or self.config.api_key
        )
        self._ensure_collection()

    def _ensure_collection(self):
        if not self._client.has_collection(self._collection_name):
            self._client.create_collection(
                collection_name=self._collection_name,
                dimension=self.config.embedding_dimension,
                primary_field_name="id",
                id_type="string",
                vector_field_name="embedding",
                auto_id=False,
                enable_dynamic_field=True,
            )

    async def add_documents(
        self, documents: list[Document], **kwargs: Any
    ) -> list[str]:
        if not documents:
            return []

        contents = [doc.content for doc in documents]
        vectors = await self.embeddings.vectorize_documents(contents)

        data = []
        for doc, vector in zip(documents, vectors, strict=True):
            record = {"id": doc.id, "content": doc.content, "embedding": vector}
            if doc.metadata:
                record.update(doc.metadata)
            data.append(record)

        self._client.insert(collection_name=self._collection_name, data=data)
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

        self._client.delete(collection_name=self._collection_name, pks=document_ids)
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
        filters = kwargs.get("filters", {})

        filter_expr = ""
        if filters:
            conditions = []
            for k, v in filters.items():
                if isinstance(v, str):
                    conditions.append(f"{k} == '{v}'")
                else:
                    conditions.append(f"{k} == {v}")
            filter_expr = " and ".join(conditions)

        res = self._client.search(
            collection_name=self._collection_name,
            data=[query_embedding],
            limit=top_k,
            filter=filter_expr,
            output_fields=["content", "*"],
        )

        results = []
        if res and len(res) > 0:
            for rank, hit in enumerate(res[0], 1):
                entity = hit.get("entity", {})
                content = entity.pop("content", "")
                doc_id = hit.get("id")
                score = hit.get("distance", 0.0)
                doc = Document(id=str(doc_id), content=content, metadata=entity)
                results.append(SearchResult(document=doc, score=score, rank=rank))

        return results

    async def get_document(self, document_id: str) -> Document | None:
        res = self._client.query(
            collection_name=self._collection_name,
            filter=f"id == '{document_id}'",
            output_fields=["content", "*"],
        )
        if not res:
            return None

        entity = res[0]
        content = entity.pop("content", "")
        doc_id = entity.pop("id", document_id)
        return Document(id=str(doc_id), content=content, metadata=entity)

    async def update_document(self, document: Document) -> bool:
        await self.add_documents([document])
        return True
