from __future__ import annotations

import re
from typing import Any

from neo4j import GraphDatabase

from ..datatypes.neo4j_types import Neo4jConnectionConfig
from .base import ExecutionResult, ToolRunner, ToolSpec, registry


class KeywordExtractTool(ToolRunner):
    def __init__(self, conn_cfg: Neo4jConnectionConfig | None = None):
        super().__init__(
            ToolSpec(
                name="semantic_extract_keywords",
                description="Extract keywords from text and optionally store in Neo4j",
                inputs={
                    "text": "TEXT",
                    "store_in_neo4j": "BOOL",
                    "document_id": "TEXT",
                },
                outputs={"keywords": "JSON"},
            )
        )
        self._conn = conn_cfg

    def run(self, params: dict[str, Any]) -> ExecutionResult:
        ok, err = self.validate(params)
        if not ok:
            return ExecutionResult(success=False, error=err or "invalid params")

        text = params["text"].strip()
        store_in_neo4j = params.get("store_in_neo4j", False)
        document_id = params.get("document_id")

        # Extract keywords using simple NLP techniques
        keywords = self._extract_keywords(text)

        # Store in Neo4j if requested
        if store_in_neo4j and self._conn and document_id:
            try:
                self._store_keywords_in_neo4j(keywords, document_id)
            except Exception as e:
                return ExecutionResult(
                    success=False,
                    error=f"Keyword extraction succeeded but storage failed: {e!s}",
                )

        return ExecutionResult(success=True, data={"keywords": keywords})

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract keywords from text using simple NLP techniques."""
        # Convert to lowercase
        text = text.lower()

        # Remove punctuation and split into words
        words = re.findall(r"\b\w+\b", text)

        # Filter out stop words and short words
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "must",
            "can",
            "this",
            "that",
            "these",
            "those",
            "i",
            "you",
            "he",
            "she",
            "it",
            "we",
            "they",
            "me",
            "him",
            "her",
            "us",
            "them",
            "my",
            "your",
            "his",
            "its",
            "our",
            "their",
        }

        # Filter and count word frequencies
        word_freq = {}
        for word in words:
            if len(word) > 3 and word not in stop_words:
                word_freq[word] = word_freq.get(word, 0) + 1

        # Sort by frequency and return top keywords
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        keywords = [word for word, freq in sorted_words[:20]]  # Top 20 keywords

        return keywords

    def _store_keywords_in_neo4j(self, keywords: list[str], document_id: str):
        """Store keywords as relationships to document in Neo4j."""
        if not self._conn:
            raise ValueError("Neo4j connection not configured")

        driver = GraphDatabase.driver(
            self._conn.uri,
            auth=(self._conn.username, self._conn.password)
            if self._conn.username
            else None,
            encrypted=self._conn.encrypted,
        )

        try:
            with driver.session(database=self._conn.database) as session:
                # Ensure document exists
                session.run("MERGE (d:Document {id: $doc_id})", doc_id=document_id)

                # Create keyword nodes and relationships
                for keyword in keywords:
                    session.run(
                        """
                        MERGE (k:Keyword {name: $keyword})
                        MERGE (d:Document {id: $doc_id})
                        MERGE (d)-[:HAS_KEYWORD]->(k)
                        """,
                        keyword=keyword,
                        doc_id=document_id,
                    )
        finally:
            driver.close()


class TopicModelingTool(ToolRunner):
    def __init__(self, conn_cfg: Neo4jConnectionConfig | None = None):
        super().__init__(
            ToolSpec(
                name="semantic_topic_modeling",
                description="Perform topic modeling on documents in Neo4j",
                inputs={
                    "num_topics": "INT",
                    "limit": "INT",
                },
                outputs={"topics": "JSON"},
            )
        )
        self._conn = conn_cfg

    def run(self, params: dict[str, Any]) -> ExecutionResult:
        ok, err = self.validate(params)
        if not ok:
            return ExecutionResult(success=False, error=err or "invalid params")
        if not self._conn:
            return ExecutionResult(
                success=False, error="Neo4j connection not configured"
            )

        num_topics = params.get("num_topics", 5)
        limit = params.get("limit", 1000)

        try:
            driver = GraphDatabase.driver(
                self._conn.uri,
                auth=(self._conn.username, self._conn.password)
                if self._conn.username
                else None,
                encrypted=self._conn.encrypted,
            )

            with driver.session(database=self._conn.database) as session:
                # Get keyword co-occurrence data
                result = session.run(
                    """
                    MATCH (d:Document)-[:HAS_KEYWORD]->(k1:Keyword),
                          (d:Document)-[:HAS_KEYWORD]->(k2:Keyword)
                    WHERE k1.name < k2.name
                    WITH k1.name AS keyword1, k2.name AS keyword2, count(d) AS co_occurrences
                    ORDER BY co_occurrences DESC
                    LIMIT $limit
                    RETURN keyword1, keyword2, co_occurrences
                    """,
                    limit=limit,
                )

                # Simple clustering-based topic modeling
                topics = self._cluster_keywords_into_topics(result, num_topics)

            driver.close()
            return ExecutionResult(success=True, data={"topics": topics})

        except Exception as e:
            return ExecutionResult(success=False, error=f"Topic modeling failed: {e!s}")

    def _cluster_keywords_into_topics(
        self, co_occurrence_result, num_topics: int
    ) -> list[dict[str, Any]]:
        """Simple clustering of keywords into topics based on co-occurrence."""
        # This is a simplified implementation
        # In practice, you'd use proper topic modeling algorithms

        keywords = set()
        co_occurrences = {}

        for record in co_occurrence_result:
            k1 = record["keyword1"]
            k2 = record["keyword2"]
            count = record["co_occurrences"]

            keywords.add(k1)
            keywords.add(k2)

            key = tuple(sorted([k1, k2]))
            co_occurrences[key] = count

        # Simple topic assignment (this is very basic)
        topics = []
        keyword_list = list(keywords)

        for i in range(num_topics):
            topic_keywords = keyword_list[
                i::num_topics
            ]  # Distribute keywords across topics
            topics.append(
                {
                    "topic_id": i + 1,
                    "keywords": topic_keywords,
                    "keyword_count": len(topic_keywords),
                }
            )

        return topics


def _register() -> None:
    registry.register("semantic_extract_keywords", lambda: KeywordExtractTool())
    registry.register("semantic_topic_modeling", lambda: TopicModelingTool())


_register()
