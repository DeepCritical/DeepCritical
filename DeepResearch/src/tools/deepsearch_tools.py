"""
Deep Search tools for DeepCritical research workflows.

This module implements tools for deep search functionality based on
Jina AI DeepResearch patterns, including web search, URL visiting,
reflection, and answer generation.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from DeepResearch.src.datatypes.deepsearch import (
    MAX_QUERIES_PER_STEP,
    MAX_REFLECT_PER_STEP,
    MAX_URLS_PER_STEP,
    ReflectionQuestion,
    SearchResult,
    SearchTimeFilter,
    URLVisitResult,
    WebSearchRequest,
)

from .base import ExecutionResult, ToolRunner, ToolSpec, registry

# Configure logging
logger = logging.getLogger(__name__)


class WebSearchTool(ToolRunner):
    """Tool for performing web searches."""

    def __init__(self):
        super().__init__(
            ToolSpec(
                name="web_search",
                description="Perform web search using various search engines and return structured results",
                inputs={
                    "query": "TEXT",
                    "time_filter": "TEXT",
                    "location": "TEXT",
                    "max_results": "INTEGER",
                },
                outputs={
                    "results": "JSON",
                    "total_found": "INTEGER",
                    "search_time": "FLOAT",
                },
            )
        )

    def run(self, params: dict[str, Any]) -> ExecutionResult:
        """Execute web search."""
        ok, err = self.validate(params)
        if not ok:
            return ExecutionResult(success=False, error=err)

        try:
            # Extract parameters
            query = str(params.get("query", "")).strip()
            time_filter_str = params.get("time_filter")
            location = params.get("location")
            max_results = int(params.get("max_results", 10))

            if not query:
                return ExecutionResult(success=False, error="Empty search query")

            # Parse time filter
            time_filter = None
            if time_filter_str:
                try:
                    time_filter = SearchTimeFilter(time_filter_str)
                except ValueError:
                    logger.warning("Invalid time filter: %s", time_filter_str)

            # Create search request
            search_request = WebSearchRequest(
                query=query,
                time_filter=time_filter,
                location=location,
                max_results=max_results,
            )

            # Perform search
            start_time = time.time()
            results = self._perform_search(search_request)
            search_time = time.time() - start_time

            return ExecutionResult(
                success=True,
                data={
                    "results": [self._result_to_dict(r) for r in results],
                    "total_found": len(results),
                    "search_time": search_time,
                },
            )

        except Exception as e:
            logger.exception("Web search failed")
            return ExecutionResult(success=False, error=f"Web search failed: {e}")

    def _perform_search(self, request: WebSearchRequest) -> list[SearchResult]:
        """Perform the actual web search."""
        # Mock implementation - in real implementation, this would use
        # Google Search API, Bing API, or other search engines

        # For now, return mock results based on the query
        mock_results = [
            SearchResult(
                title=f"Result 1 for '{request.query}'",
                url=f"https://example1.com/search?q={request.query}",
                snippet=f"This is a mock search result for the query '{request.query}'. It contains relevant information about the topic.",
                score=0.95,
            ),
            SearchResult(
                title=f"Result 2 for '{request.query}'",
                url=f"https://example2.com/search?q={request.query}",
                snippet=f"Another mock result for '{request.query}'. This provides additional context and details.",
                score=0.87,
            ),
            SearchResult(
                title=f"Result 3 for '{request.query}'",
                url=f"https://example3.com/search?q={request.query}",
                snippet=f"Third mock result for '{request.query}'. Contains supplementary information.",
                score=0.82,
            ),
        ]

        # Limit results
        return mock_results[: request.max_results]

    def _result_to_dict(self, result: SearchResult) -> dict[str, Any]:
        """Convert SearchResult to dictionary."""
        return {
            "title": result.title,
            "url": result.url,
            "snippet": result.snippet,
            "score": result.score,
        }


class URLVisitTool(ToolRunner):
    """Tool for visiting URLs and extracting content."""

    def __init__(self):
        super().__init__(
            ToolSpec(
                name="url_visit",
                description="Visit URLs and extract their content for analysis",
                inputs={
                    "urls": "JSON",
                    "max_content_length": "INTEGER",
                    "timeout": "INTEGER",
                },
                outputs={
                    "visited_urls": "JSON",
                    "successful_visits": "INTEGER",
                    "failed_visits": "INTEGER",
                },
            )
        )

    def run(self, params: dict[str, Any]) -> ExecutionResult:
        """Execute URL visits."""
        ok, err = self.validate(params)
        if not ok:
            return ExecutionResult(success=False, error=err)

        try:
            # Extract parameters
            urls_data = params.get("urls", [])
            max_content_length = int(params.get("max_content_length", 5000))
            timeout = int(params.get("timeout", 30))

            if not urls_data:
                return ExecutionResult(success=False, error="No URLs provided")

            # Parse URLs
            urls = json.loads(urls_data) if isinstance(urls_data, str) else urls_data

            if not isinstance(urls, list):
                return ExecutionResult(success=False, error="URLs must be a list")

            # Limit URLs per step
            urls = urls[:MAX_URLS_PER_STEP]

            # Visit URLs
            results = []
            successful_visits = 0
            failed_visits = 0

            for url in urls:
                result = self._visit_url(url, max_content_length, timeout)
                results.append(self._result_to_dict(result))

                if result.success:
                    successful_visits += 1
                else:
                    failed_visits += 1

            return ExecutionResult(
                success=True,
                data={
                    "visited_urls": results,
                    "successful_visits": successful_visits,
                    "failed_visits": failed_visits,
                },
            )

        except Exception as e:
            logger.exception("URL visit failed")
            return ExecutionResult(success=False, error=f"URL visit failed: {e!s}")

    def _visit_url(
        self, url: str, max_content_length: int, timeout: int
    ) -> URLVisitResult:
        """Visit a single URL and extract content."""
        start_time = time.time()

        try:
            # Validate URL
            parsed_url = urlparse(url)
            if not parsed_url.scheme or not parsed_url.netloc:
                return URLVisitResult(
                    url=url,
                    title="",
                    content="",
                    success=False,
                    error="Invalid URL format",
                    processing_time=time.time() - start_time,
                )

            # Make request
            response = requests.get(
                url,
                timeout=timeout,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                },
            )
            response.raise_for_status()

            # Parse content
            soup = BeautifulSoup(response.content, "html.parser")

            # Extract title
            title = ""
            title_tag = soup.find("title")
            if title_tag:
                title = title_tag.get_text().strip()

            # Extract main content
            content = ""

            # Try to find main content areas
            main_content = (
                soup.find("main")
                or soup.find("article")
                or soup.find("div", class_="content")
            )
            if main_content:
                content = main_content.get_text()
            else:
                # Fallback to body content
                body = soup.find("body")
                if body:
                    content = body.get_text()

            # Clean and limit content
            content = self._clean_text(content)
            if len(content) > max_content_length:
                content = content[:max_content_length] + "..."

            return URLVisitResult(
                url=url,
                title=title,
                content=content,
                success=True,
                processing_time=time.time() - start_time,
            )

        except Exception as e:
            return URLVisitResult(
                url=url,
                title="",
                content="",
                success=False,
                error=str(e),
                processing_time=time.time() - start_time,
            )

    def _clean_text(self, text: str) -> str:
        """Clean extracted text."""
        # Remove extra whitespace and normalize
        lines = [line.strip() for line in text.split("\n")]
        lines = [line for line in lines if line]  # Remove empty lines
        return "\n".join(lines)

    def _result_to_dict(self, result: URLVisitResult) -> dict[str, Any]:
        """Convert URLVisitResult to dictionary."""
        return {
            "url": result.url,
            "title": result.title,
            "content": result.content,
            "success": result.success,
            "error": result.error,
            "processing_time": result.processing_time,
        }


class ReflectionTool(ToolRunner):
    """Tool for generating reflection questions."""

    def __init__(self):
        super().__init__(
            ToolSpec(
                name="reflection",
                description="Generate reflection questions to guide deeper research",
                inputs={
                    "original_question": "TEXT",
                    "current_knowledge": "TEXT",
                    "search_results": "JSON",
                },
                outputs={"reflection_questions": "JSON", "knowledge_gaps": "JSON"},
            )
        )

    def run(self, params: dict[str, Any]) -> ExecutionResult:
        """Generate reflection questions."""
        ok, err = self.validate(params)
        if not ok:
            return ExecutionResult(success=False, error=err)

        try:
            # Extract parameters
            original_question = str(params.get("original_question", "")).strip()
            current_knowledge = str(params.get("current_knowledge", "")).strip()
            search_results_data = params.get("search_results", [])

            if not original_question:
                return ExecutionResult(
                    success=False, error="No original question provided"
                )

            # Parse search results
            if isinstance(search_results_data, str):
                search_results = json.loads(search_results_data)
            else:
                search_results = search_results_data

            # Generate reflection questions
            reflection_questions = self._generate_reflection_questions(
                original_question, current_knowledge, search_results
            )

            # Identify knowledge gaps
            knowledge_gaps = self._identify_knowledge_gaps(
                original_question, current_knowledge, search_results
            )

            return ExecutionResult(
                success=True,
                data={
                    "reflection_questions": [
                        self._question_to_dict(q) for q in reflection_questions
                    ],
                    "knowledge_gaps": knowledge_gaps,
                },
            )

        except Exception as e:
            logger.exception("Reflection generation failed")
            return ExecutionResult(
                success=False, error=f"Reflection generation failed: {e!s}"
            )

    def _generate_reflection_questions(
        self,
        original_question: str,
        current_knowledge: str,
        search_results: list[dict[str, Any]],
    ) -> list[ReflectionQuestion]:
        """Generate reflection questions based on current state."""
        questions = []

        # Analyze the original question for gaps
        question_lower = original_question.lower()

        # Check for different types of information needs
        if "how" in question_lower and not any(
            word in current_knowledge.lower() for word in ["process", "method", "steps"]
        ):
            questions.append(
                ReflectionQuestion(
                    question=f"What is the specific process or methodology for {original_question}?",
                    priority=1,
                    context="process_methodology",
                )
            )

        if "why" in question_lower and not any(
            word in current_knowledge.lower() for word in ["reason", "cause", "because"]
        ):
            questions.append(
                ReflectionQuestion(
                    question=f"What are the underlying reasons or causes for {original_question}?",
                    priority=1,
                    context="causation",
                )
            )

        if "what" in question_lower and not any(
            word in current_knowledge.lower()
            for word in ["definition", "meaning", "is"]
        ):
            questions.append(
                ReflectionQuestion(
                    question=f"What is the precise definition or meaning of the key concepts in {original_question}?",
                    priority=1,
                    context="definition",
                )
            )

        # Check for missing context
        if not any(
            word in current_knowledge.lower()
            for word in ["recent", "latest", "current", "2024", "2023"]
        ):
            questions.append(
                ReflectionQuestion(
                    question=f"What are the most recent developments or current status regarding {original_question}?",
                    priority=2,
                    context="recency",
                )
            )

        # Check for missing examples
        if not any(
            word in current_knowledge.lower()
            for word in ["example", "instance", "case"]
        ):
            questions.append(
                ReflectionQuestion(
                    question=f"What are concrete examples or case studies that illustrate {original_question}?",
                    priority=2,
                    context="examples",
                )
            )

        # Limit to max reflection questions
        return sorted(questions, key=lambda q: q.priority)[:MAX_REFLECT_PER_STEP]

    def _identify_knowledge_gaps(
        self,
        original_question: str,
        current_knowledge: str,
        search_results: list[dict[str, Any]],
    ) -> list[str]:
        """Identify specific knowledge gaps."""
        gaps = []

        # Check for missing quantitative data
        if not any(char.isdigit() for char in current_knowledge):
            gaps.append("Quantitative data and statistics")

        # Check for missing authoritative sources
        if not any(
            word in current_knowledge.lower()
            for word in ["study", "research", "paper", "journal"]
        ):
            gaps.append("Academic or research sources")

        # Check for missing practical applications
        if not any(
            word in current_knowledge.lower()
            for word in ["application", "use", "practice", "implementation"]
        ):
            gaps.append("Practical applications and use cases")

        return gaps

    def _question_to_dict(self, question: ReflectionQuestion) -> dict[str, Any]:
        """Convert ReflectionQuestion to dictionary."""
        return {
            "question": question.question,
            "priority": question.priority,
            "context": question.context,
        }


class AnswerGeneratorTool(ToolRunner):
    """Tool for generating comprehensive answers."""

    def __init__(self):
        super().__init__(
            ToolSpec(
                name="answer_generator",
                description="Generate comprehensive answers based on collected knowledge",
                inputs={
                    "original_question": "TEXT",
                    "collected_knowledge": "JSON",
                    "search_results": "JSON",
                    "visited_urls": "JSON",
                },
                outputs={"answer": "TEXT", "confidence": "FLOAT", "sources": "JSON"},
            )
        )

    def run(self, params: dict[str, Any]) -> ExecutionResult:
        """Generate comprehensive answer."""
        ok, err = self.validate(params)
        if not ok:
            return ExecutionResult(success=False, error=err)

        try:
            # Extract parameters
            original_question = str(params.get("original_question", "")).strip()
            collected_knowledge_data = params.get("collected_knowledge", {})
            search_results_data = params.get("search_results", [])
            visited_urls_data = params.get("visited_urls", [])

            if not original_question:
                return ExecutionResult(
                    success=False, error="No original question provided"
                )

            # Parse data
            if isinstance(collected_knowledge_data, str):
                collected_knowledge = json.loads(collected_knowledge_data)
            else:
                collected_knowledge = collected_knowledge_data

            if isinstance(search_results_data, str):
                search_results = json.loads(search_results_data)
            else:
                search_results = search_results_data

            if isinstance(visited_urls_data, str):
                visited_urls = json.loads(visited_urls_data)
            else:
                visited_urls = visited_urls_data

            # Generate answer
            answer, confidence, sources = self._generate_answer(
                original_question, collected_knowledge, search_results, visited_urls
            )

            return ExecutionResult(
                success=True,
                data={"answer": answer, "confidence": confidence, "sources": sources},
            )

        except Exception as e:
            logger.exception("Answer generation failed")
            return ExecutionResult(
                success=False, error=f"Answer generation failed: {e!s}"
            )

    def _generate_answer(
        self,
        original_question: str,
        collected_knowledge: dict[str, Any],
        search_results: list[dict[str, Any]],
        visited_urls: list[dict[str, Any]],
    ) -> tuple[str, float, list[dict[str, Any]]]:
        """Generate comprehensive answer from collected information."""

        # Build answer components
        answer_parts = []
        sources = []
        confidence_factors = []

        # Add question
        answer_parts.append(f"Question: {original_question}")
        answer_parts.append("")

        # Add main answer based on collected knowledge
        if collected_knowledge:
            main_answer = self._extract_main_answer(
                collected_knowledge, original_question
            )
            answer_parts.append(f"Answer: {main_answer}")
            confidence_factors.append(0.8)  # High confidence for collected knowledge
        else:
            answer_parts.append(
                "Answer: Based on the available information, I can provide the following insights:"
            )
            confidence_factors.append(
                0.5
            )  # Lower confidence without collected knowledge

        answer_parts.append("")

        # Add detailed information from search results
        if search_results:
            answer_parts.append("Detailed Information:")
            for i, result in enumerate(search_results[:3], 1):  # Limit to top 3
                answer_parts.append(f"{i}. {result.get('snippet', '')}")
                sources.append(
                    {
                        "title": result.get("title", ""),
                        "url": result.get("url", ""),
                        "type": "search_result",
                    }
                )
                confidence_factors.append(0.7)

        # Add information from visited URLs
        if visited_urls:
            answer_parts.append("")
            answer_parts.append("Additional Sources:")
            for i, url_result in enumerate(visited_urls[:2], 1):  # Limit to top 2
                if url_result.get("success", False):
                    content = url_result.get("content", "")
                    if content:
                        # Extract key points from content
                        key_points = self._extract_key_points(
                            content, original_question
                        )
                        if key_points:
                            answer_parts.append(f"{i}. {key_points}")
                            sources.append(
                                {
                                    "title": url_result.get("title", ""),
                                    "url": url_result.get("url", ""),
                                    "type": "visited_url",
                                }
                            )
                            confidence_factors.append(0.6)

        # Calculate overall confidence
        overall_confidence = (
            sum(confidence_factors) / len(confidence_factors)
            if confidence_factors
            else 0.5
        )

        # Add confidence note
        answer_parts.append("")
        answer_parts.append(f"Confidence Level: {overall_confidence:.1%}")

        final_answer = "\n".join(answer_parts)

        return final_answer, overall_confidence, sources

    def _extract_main_answer(
        self, collected_knowledge: dict[str, Any], question: str
    ) -> str:
        """Extract main answer from collected knowledge."""
        # This would use AI to synthesize the collected knowledge
        # For now, return a mock synthesis
        return f"Based on the comprehensive research conducted, here's what I found regarding '{question}': The available information suggests multiple perspectives and approaches to this topic, with various factors influencing the outcome."

    def _extract_key_points(self, content: str, question: str) -> str:
        """Extract key points from content relevant to the question."""
        # Simple extraction - in real implementation, this would use NLP
        sentences = content.split(".")
        relevant_sentences = []

        question_words = set(question.lower().split())

        for sentence in sentences[:5]:  # Check first 5 sentences
            sentence_words = set(sentence.lower().split())
            if question_words.intersection(sentence_words):
                relevant_sentences.append(sentence.strip())

        return ". ".join(relevant_sentences[:2]) + "." if relevant_sentences else ""


class QueryRewriterTool(ToolRunner):
    """Tool for rewriting queries for better search results."""

    def __init__(self):
        super().__init__(
            ToolSpec(
                name="query_rewriter",
                description="Rewrite search queries for optimal results",
                inputs={
                    "original_query": "TEXT",
                    "search_context": "TEXT",
                    "target_language": "TEXT",
                },
                outputs={"rewritten_queries": "JSON", "search_strategies": "JSON"},
            )
        )

    def run(self, params: dict[str, Any]) -> ExecutionResult:
        """Rewrite search queries."""
        ok, err = self.validate(params)
        if not ok:
            return ExecutionResult(success=False, error=err)

        try:
            # Extract parameters
            original_query = str(params.get("original_query", "")).strip()
            search_context = str(params.get("search_context", "")).strip()
            target_language = params.get("target_language")

            if not original_query:
                return ExecutionResult(
                    success=False, error="No original query provided"
                )

            # Rewrite queries
            rewritten_queries = self._rewrite_queries(
                original_query, search_context, target_language
            )
            search_strategies = self._generate_search_strategies(original_query)

            return ExecutionResult(
                success=True,
                data={
                    "rewritten_queries": rewritten_queries,
                    "search_strategies": search_strategies,
                },
            )

        except Exception as e:
            logger.exception("Query rewriting failed")
            return ExecutionResult(
                success=False, error=f"Query rewriting failed: {e!s}"
            )

    def _rewrite_queries(
        self, original_query: str, search_context: str, target_language: str | None
    ) -> list[dict[str, Any]]:
        """Rewrite queries for better search results."""
        queries = []

        # Basic query
        queries.append({"q": original_query, "tbs": None, "location": None})

        # More specific query
        if len(original_query.split()) > 2:
            specific_query = self._make_specific(original_query)
            queries.append(
                {
                    "q": specific_query,
                    "tbs": getattr(SearchTimeFilter.PAST_YEAR, "value", None),
                    "location": None,
                }
            )

        # Broader query
        broader_query = self._make_broader(original_query)
        queries.append({"q": broader_query, "tbs": None, "location": None})

        # Recent query
        queries.append(
            {
                "q": f"{original_query} 2024",
                "tbs": getattr(SearchTimeFilter.PAST_YEAR, "value", None),
                "location": None,
            }
        )

        # Limit to max queries
        return queries[:MAX_QUERIES_PER_STEP]

    def _make_specific(self, query: str) -> str:
        """Make query more specific."""
        # Add specificity indicators
        specific_terms = ["specific", "exact", "precise", "detailed"]
        return f"{query} {specific_terms[0]}"

    def _make_broader(self, query: str) -> str:
        """Make query broader."""
        # Remove specific terms and add broader context
        words = query.split()
        if len(words) > 3:
            return " ".join(words[:3])
        return query

    def _generate_search_strategies(self, original_query: str) -> list[str]:
        """Generate search strategies for the query."""
        return [
            "Direct keyword search",
            "Synonym and related term search",
            "Recent developments search",
            "Academic and research sources search",
        ]


# Register all deep search tools
@dataclass
class DeepSearchTool(ToolRunner):
    """Main deep search tool that orchestrates the entire search process."""

    def __init__(self):
        super().__init__(
            ToolSpec(
                name="deep_search",
                description="Perform comprehensive deep search with multiple steps",
                inputs={"query": "TEXT", "max_steps": "NUMBER", "config": "TEXT"},
                outputs={"results": "TEXT", "search_history": "TEXT"},
            )
        )

    def run(self, params: dict[str, str]) -> ExecutionResult:
        query = params.get("query", "")
        max_steps = int(params.get("max_steps", "10"))

        if not query:
            return ExecutionResult(success=False, error="No query provided")

        # Simulate deep search execution
        search_results = {
            "query": query,
            "steps_completed": min(max_steps, 5),  # Simulate some steps
            "results_found": 15,
            "final_answer": f"Deep search completed for query: {query}",
        }

        return ExecutionResult(
            success=True,
            data={
                "results": search_results,
                "search_history": f"Search history for: {query}",
            },
            metrics={"steps": max_steps, "results": 15},
        )


registry.register("web_search", WebSearchTool)
registry.register("url_visit", URLVisitTool)
registry.register("reflection", ReflectionTool)
registry.register("answer_generator", AnswerGeneratorTool)
registry.register("query_rewriter", QueryRewriterTool)
registry.register("deep_search", DeepSearchTool)
