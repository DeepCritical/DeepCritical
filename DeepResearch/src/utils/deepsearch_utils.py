"""
Deep Search utility classes for DeepCritical research workflows.

This module provides utility classes for managing deep search operations,
including context tracking, knowledge management, and search orchestration.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any, cast

from DeepResearch.src.datatypes.deepsearch import (
    ActionType,
    DeepSearchSchemas,
    EvaluationType,
)

from .execution_history import ExecutionHistory, ExecutionItem
from .execution_status import ExecutionStatus

# Configure logging
logger = logging.getLogger(__name__)


class SearchContext:
    """Context for deep search operations."""

    def __init__(self, original_question: str, config: dict[str, Any] | None = None):
        self.original_question = original_question
        self.config = config or {}
        self.start_time = datetime.now()
        self.current_step = 0
        self.max_steps = self.config.get("max_steps", 20)
        self.token_budget = self.config.get("token_budget", 10000)
        self.used_tokens = 0

        # Knowledge tracking
        self.collected_knowledge: dict[str, Any] = {}
        self.search_results: list[dict[str, Any]] = []
        self.visited_urls: list[dict[str, Any]] = []
        self.reflection_questions: list[str] = []

        # State tracking
        self.available_actions: set[ActionType] = set(ActionType)
        self.disabled_actions: set[ActionType] = set()
        self.current_gaps: list[str] = []

        # Performance tracking
        self.execution_history = ExecutionHistory()
        self.search_count = 0
        self.visit_count = 0
        self.reflect_count = 0

        # Initialize schemas
        self.schemas = DeepSearchSchemas()

    def can_continue(self) -> bool:
        """Check if search can continue based on constraints."""
        if self.current_step >= self.max_steps:
            logger.info("Maximum steps reached")
            return False

        if self.used_tokens >= self.token_budget:
            logger.info("Token budget exceeded")
            return False

        return True

    def get_available_actions(self) -> set[ActionType]:
        """Get currently available actions."""
        return self.available_actions - self.disabled_actions

    def disable_action(self, action: ActionType) -> None:
        """Disable an action for the next step."""
        self.disabled_actions.add(action)

    def enable_action(self, action: ActionType) -> None:
        """Enable an action."""
        self.disabled_actions.discard(action)

    def add_knowledge(self, key: str, value: Any) -> None:
        """Add knowledge to the context."""
        self.collected_knowledge[key] = value

    def add_search_results(self, results: list[dict[str, Any]]) -> None:
        """Add search results to the context."""
        self.search_results.extend(results)
        self.search_count += 1

    def add_visited_urls(self, urls: list[dict[str, Any]]) -> None:
        """Add visited URLs to the context."""
        self.visited_urls.extend(urls)
        self.visit_count += 1

    def add_reflection_questions(self, questions: list[str]) -> None:
        """Add reflection questions to the context."""
        self.reflection_questions.extend(questions)
        self.reflect_count += 1

    def consume_tokens(self, tokens: int) -> None:
        """Consume tokens from the budget."""
        self.used_tokens += tokens

    def next_step(self) -> None:
        """Move to the next step."""
        self.current_step += 1
        # Re-enable actions for next step
        self.disabled_actions.clear()

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of the current context."""
        return {
            "original_question": self.original_question,
            "current_step": self.current_step,
            "max_steps": self.max_steps,
            "used_tokens": self.used_tokens,
            "token_budget": self.token_budget,
            "search_count": self.search_count,
            "visit_count": self.visit_count,
            "reflect_count": self.reflect_count,
            "available_actions": list(self.get_available_actions()),
            "knowledge_keys": list(self.collected_knowledge.keys()),
            "total_search_results": len(self.search_results),
            "total_visited_urls": len(self.visited_urls),
            "total_reflection_questions": len(self.reflection_questions),
        }


class KnowledgeManager:
    """Manages knowledge collection and synthesis."""

    def __init__(self):
        self.knowledge_base: dict[str, Any] = {}
        self.knowledge_sources: dict[str, list[str]] = {}
        self.knowledge_confidence: dict[str, float] = {}
        self.knowledge_timestamps: dict[str, datetime] = {}

    def add_knowledge(
        self, key: str, value: Any, source: str, confidence: float = 0.8
    ) -> None:
        """Add knowledge with source tracking."""
        self.knowledge_base[key] = value
        self.knowledge_sources[key] = [*self.knowledge_sources.get(key, []), source]
        self.knowledge_confidence[key] = max(
            self.knowledge_confidence.get(key, 0.0), confidence
        )
        self.knowledge_timestamps[key] = datetime.now()

    def get_knowledge(self, key: str) -> Any | None:
        """Get knowledge by key."""
        return self.knowledge_base.get(key)

    def get_knowledge_with_metadata(self, key: str) -> dict[str, Any] | None:
        """Get knowledge with metadata."""
        if key not in self.knowledge_base:
            return None

        return {
            "value": self.knowledge_base[key],
            "sources": self.knowledge_sources.get(key, []),
            "confidence": self.knowledge_confidence.get(key, 0.0),
            "timestamp": self.knowledge_timestamps.get(key),
        }

    def search_knowledge(self, query: str) -> list[dict[str, Any]]:
        """Search knowledge base for relevant information."""
        results = []
        query_lower = query.lower()

        for key, value in self.knowledge_base.items():
            if query_lower in key.lower() or query_lower in str(value).lower():
                results.append(
                    {
                        "key": key,
                        "value": value,
                        "sources": self.knowledge_sources.get(key, []),
                        "confidence": self.knowledge_confidence.get(key, 0.0),
                    }
                )

        # Sort by confidence
        results.sort(key=lambda x: x["confidence"], reverse=True)
        return results

    def synthesize_knowledge(self, topic: str) -> str:
        """Synthesize knowledge for a specific topic."""
        relevant_knowledge = self.search_knowledge(topic)

        if not relevant_knowledge:
            return f"No knowledge found for topic: {topic}"

        synthesis_parts = [f"Knowledge synthesis for '{topic}':"]

        for item in relevant_knowledge[:5]:  # Limit to top 5
            synthesis_parts.append(f"- {item['key']}: {item['value']}")
            synthesis_parts.append(f"  Sources: {', '.join(item['sources'])}")
            synthesis_parts.append(f"  Confidence: {item['confidence']:.2f}")

        return "\n".join(synthesis_parts)

    def get_knowledge_summary(self) -> dict[str, Any]:
        """Get a summary of the knowledge base."""
        return {
            "total_knowledge_items": len(self.knowledge_base),
            "knowledge_keys": list(self.knowledge_base.keys()),
            "average_confidence": (
                sum(self.knowledge_confidence.values()) / len(self.knowledge_confidence)
                if self.knowledge_confidence
                else 0.0
            ),
            "most_confident": (
                max(self.knowledge_confidence.items(), key=lambda x: x[1])
                if self.knowledge_confidence
                else None
            ),
            "oldest_knowledge": (
                min(self.knowledge_timestamps.values())
                if self.knowledge_timestamps
                else None
            ),
            "newest_knowledge": (
                max(self.knowledge_timestamps.values())
                if self.knowledge_timestamps
                else None
            ),
        }


class SearchOrchestrator:
    """Orchestrates deep search operations."""

    def __init__(self, context: SearchContext):
        self.context = context
        self.knowledge_manager = KnowledgeManager()
        self.schemas = DeepSearchSchemas()

    async def execute_search_step(
        self, action: ActionType, parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute a single search step."""
        start_time = time.time()

        try:
            if action == ActionType.SEARCH:
                result = await self._execute_search(parameters)
            elif action == ActionType.VISIT:
                result = await self._execute_visit(parameters)
            elif action == ActionType.REFLECT:
                result = await self._execute_reflect(parameters)
            elif action == ActionType.ANSWER:
                result = await self._execute_answer(parameters)
            elif action == ActionType.CODING:
                result = await self._execute_coding(parameters)
            else:
                msg = f"Unknown action: {action}"
                raise ValueError(msg)

            # Update context
            self._update_context_after_action(action, result)

            # Record execution
            execution_item = ExecutionItem(
                step_name=f"step_{self.context.current_step}",
                tool=action.value,
                status=(
                    ExecutionStatus.SUCCESS
                    if result.get("success", False)
                    else ExecutionStatus.FAILED
                ),
                result=result,
                duration=time.time() - start_time,
                parameters=parameters,
            )
            self.context.execution_history.add_item(execution_item)

            return result

        except Exception as e:
            logger.exception("Search step execution failed")

            # Record failed execution
            execution_item = ExecutionItem(
                step_name=f"step_{self.context.current_step}",
                tool=action.value,
                status=ExecutionStatus.FAILED,
                error=str(e),
                duration=time.time() - start_time,
                parameters=parameters,
            )
            self.context.execution_history.add_item(execution_item)

            return {"success": False, "error": str(e)}

    async def _execute_search(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Execute search action."""
        # This would integrate with the actual search tools
        # For now, return mock result
        return {
            "success": True,
            "action": "search",
            "results": [
                {
                    "title": f"Search result for {parameters.get('query', '')}",
                    "url": "https://example.com",
                    "snippet": "Mock search result snippet",
                }
            ],
        }

    async def _execute_visit(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Execute visit action."""
        # This would integrate with the actual URL visit tools
        return {
            "success": True,
            "action": "visit",
            "visited_urls": [
                {
                    "url": "https://example.com",
                    "title": "Example Page",
                    "content": "Mock page content",
                }
            ],
        }

    async def _execute_reflect(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Execute reflect action."""
        # This would integrate with the actual reflection tools
        return {
            "success": True,
            "action": "reflect",
            "reflection_questions": [
                "What additional information is needed?",
                "Are there any gaps in the current understanding?",
            ],
        }

    async def _execute_answer(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Execute answer action."""
        # This would integrate with the actual answer generation tools
        return {
            "success": True,
            "action": "answer",
            "answer": "Mock comprehensive answer based on collected knowledge",
        }

    async def _execute_coding(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Execute coding action."""
        # This would integrate with the actual coding tools
        return {
            "success": True,
            "action": "coding",
            "code": "# Mock code solution",
            "output": "Mock execution output",
        }

    def _update_context_after_action(
        self, action: ActionType, result: dict[str, Any]
    ) -> None:
        """Update context after action execution."""
        if not result.get("success", False):
            return

        if action == ActionType.SEARCH:
            search_results = result.get("results", [])
            self.context.add_search_results(search_results)

            # Add to knowledge manager
            for result_item in search_results:
                self.knowledge_manager.add_knowledge(
                    key=f"search_result_{len(self.context.search_results)}",
                    value=result_item,
                    source="web_search",
                    confidence=0.7,
                )

        elif action == ActionType.VISIT:
            visited_urls = result.get("visited_urls", [])
            self.context.add_visited_urls(visited_urls)

            # Add to knowledge manager
            for url_item in visited_urls:
                self.knowledge_manager.add_knowledge(
                    key=f"url_content_{len(self.context.visited_urls)}",
                    value=url_item,
                    source="url_visit",
                    confidence=0.8,
                )

        elif action == ActionType.REFLECT:
            reflection_questions = result.get("reflection_questions", [])
            self.context.add_reflection_questions(reflection_questions)

        elif action == ActionType.ANSWER:
            answer = result.get("answer", "")
            self.context.add_knowledge("final_answer", answer)
            self.knowledge_manager.add_knowledge(
                key="final_answer",
                value=answer,
                source="answer_generation",
                confidence=0.9,
            )

    def should_continue_search(self) -> bool:
        """Determine if search should continue."""
        if not self.context.can_continue():
            return False

        # Check if we have enough information to answer
        if self.knowledge_manager.get_knowledge("final_answer"):
            return False

        # Check if we have sufficient search results
        return not len(self.context.search_results) >= 10

    def get_next_action(self) -> ActionType | None:
        """Determine the next action to take."""
        available_actions = self.context.get_available_actions()

        if not available_actions:
            return None

        # Priority order for actions
        action_priority = [
            ActionType.SEARCH,
            ActionType.VISIT,
            ActionType.REFLECT,
            ActionType.ANSWER,
            ActionType.CODING,
        ]

        for action in action_priority:
            if action in available_actions:
                return action

        return None

    def get_search_summary(self) -> dict[str, Any]:
        """Get a summary of the search process."""
        return {
            "context_summary": self.context.get_summary(),
            "knowledge_summary": self.knowledge_manager.get_knowledge_summary(),
            "execution_summary": self.context.execution_history.get_execution_summary(),
            "should_continue": self.should_continue_search(),
            "next_action": self.get_next_action(),
        }


class DeepSearchEvaluator:
    """Evaluates deep search results and quality."""

    def __init__(self, schemas: DeepSearchSchemas):
        self.schemas = schemas

    def evaluate_answer_quality(
        self, question: str, answer: str, evaluation_type: EvaluationType
    ) -> dict[str, Any]:
        """Evaluate the quality of an answer."""
        self.schemas.get_evaluator_schema(evaluation_type)

        # Mock evaluation - in real implementation, this would use AI
        if evaluation_type == EvaluationType.DEFINITIVE:
            is_definitive = not any(
                phrase in answer.lower()
                for phrase in [
                    "i don't know",
                    "not sure",
                    "unable",
                    "cannot",
                    "might",
                    "possibly",
                ]
            )
            return {
                "type": "definitive",
                "think": "Evaluating if answer is definitive and confident",
                "pass": is_definitive,
            }

        if evaluation_type == EvaluationType.FRESHNESS:
            # Check for recent information
            has_recent_info = any(year in answer for year in ["2024", "2023", "2022"])
            return {
                "type": "freshness",
                "think": "Evaluating if answer contains recent information",
                "freshness_analysis": {
                    "days_ago": 30 if has_recent_info else 365,
                    "max_age_days": 90,
                },
                "pass": has_recent_info,
            }

        if evaluation_type == EvaluationType.COMPLETENESS:
            # Check if answer covers multiple aspects
            word_count = len(answer.split())
            is_comprehensive = word_count > 100
            return {
                "type": "completeness",
                "think": "Evaluating if answer is comprehensive",
                "completeness_analysis": {
                    "aspects_expected": "comprehensive coverage",
                    "aspects_provided": (
                        "basic coverage"
                        if not is_comprehensive
                        else "comprehensive coverage"
                    ),
                },
                "pass": is_comprehensive,
            }

        return {
            "type": evaluation_type.value,
            "think": f"Evaluating {evaluation_type.value}",
            "pass": True,
        }

    def evaluate_search_progress(
        self, context: SearchContext, knowledge_manager: KnowledgeManager
    ) -> dict[str, Any]:
        """Evaluate the progress of the search process."""
        progress_score = 0.0
        max_score = 100.0

        # Knowledge completeness (30 points)
        knowledge_items = len(knowledge_manager.knowledge_base)
        knowledge_score = min(knowledge_items * 3, 30)
        progress_score += knowledge_score

        # Search diversity (25 points)
        search_diversity = min(len(context.search_results) * 2.5, 25)
        progress_score += search_diversity

        # URL coverage (20 points)
        url_coverage = min(len(context.visited_urls) * 4, 20)
        progress_score += url_coverage

        # Reflection depth (15 points)
        reflection_score = min(len(context.reflection_questions) * 3, 15)
        progress_score += reflection_score

        # Answer quality (10 points)
        has_answer = knowledge_manager.get_knowledge("final_answer") is not None
        answer_score = 10 if has_answer else 0
        progress_score += answer_score

        return {
            "progress_score": progress_score,
            "max_score": max_score,
            "progress_percentage": (progress_score / max_score) * 100,
            "knowledge_score": knowledge_score,
            "search_diversity": search_diversity,
            "url_coverage": url_coverage,
            "reflection_score": reflection_score,
            "answer_score": answer_score,
            "recommendations": self._get_recommendations(context, knowledge_manager),
        }

    def _get_recommendations(
        self, context: SearchContext, knowledge_manager: KnowledgeManager
    ) -> list[str]:
        """Get recommendations for improving search."""
        recommendations = []

        if len(context.search_results) < 5:
            recommendations.append(
                "Conduct more web searches to gather diverse information"
            )

        if len(context.visited_urls) < 3:
            recommendations.append("Visit more URLs to get detailed content")

        if len(context.reflection_questions) < 2:
            recommendations.append(
                "Generate more reflection questions to identify knowledge gaps"
            )

        if not knowledge_manager.get_knowledge("final_answer"):
            recommendations.append(
                "Generate a comprehensive answer based on collected knowledge"
            )

        if context.search_count > 10:
            recommendations.append(
                "Consider focusing on answer generation rather than more searches"
            )

        return recommendations


# Utility functions
def create_search_context(
    question: str, config: dict[str, Any] | None = None
) -> SearchContext:
    """Create a new search context."""
    return SearchContext(question, config)


def create_search_orchestrator(context: SearchContext) -> SearchOrchestrator:
    """Create a new search orchestrator."""
    return SearchOrchestrator(context)


def create_deep_search_evaluator() -> DeepSearchEvaluator:
    """Create a new deep search evaluator."""
    schemas = DeepSearchSchemas()
    return DeepSearchEvaluator(schemas)


class SearchResultProcessor:
    """Processor for search results and content extraction."""

    def __init__(self, schemas: DeepSearchSchemas):
        self.schemas = schemas

    def process_search_results(
        self, results: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Process and clean search results."""
        processed = []
        for result in results:
            processed_result = {
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "snippet": result.get("snippet", ""),
                "score": result.get("score", 0.0),
                "processed": True,
            }
            processed.append(processed_result)
        return processed

    def extract_relevant_content(
        self, results: list[dict[str, Any]], query: str
    ) -> str:
        """Extract relevant content from search results."""
        if not results:
            return "No relevant content found."

        content_parts = []
        for result in results[:3]:  # Top 3 results
            content_parts.append(f"Title: {result.get('title', '')}")
            content_parts.append(f"Content: {result.get('snippet', '')}")
            content_parts.append("")

        return "\n".join(content_parts)


class DeepSearchUtils:
    """Utility class for deep search operations."""

    @staticmethod
    def create_search_context(
        question: str, config: dict[str, Any] | None = None
    ) -> SearchContext:
        """Create a new search context."""
        return SearchContext(question, config)

    @staticmethod
    def create_search_orchestrator(schemas: DeepSearchSchemas) -> SearchOrchestrator:
        """Create a new search orchestrator."""
        if hasattr(schemas, "model_dump") and callable(schemas.model_dump):
            model_dump_method = schemas.model_dump
            config_result = model_dump_method()
            # Ensure config is a dict
            if isinstance(config_result, dict):
                config: dict[str, Any] = cast("dict[str, Any]", config_result)
            else:
                config: dict[str, Any] = {}
        else:
            config: dict[str, Any] = {}
        context = SearchContext("", config)
        return SearchOrchestrator(context)

    @staticmethod
    def create_search_evaluator(schemas: DeepSearchSchemas) -> DeepSearchEvaluator:
        """Create a new search evaluator."""
        return DeepSearchEvaluator(schemas)

    @staticmethod
    def create_result_processor(schemas: DeepSearchSchemas) -> SearchResultProcessor:
        """Create a new search result processor."""
        return SearchResultProcessor(schemas)

    @staticmethod
    def validate_search_config(config: dict[str, Any]) -> bool:
        """Validate search configuration."""
        required_keys = ["max_steps", "token_budget"]
        return all(key in config for key in required_keys)
