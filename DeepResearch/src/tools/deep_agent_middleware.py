"""
DeepAgent Middleware - Pydantic AI middleware for DeepAgent operations.

This module implements middleware components for planning, filesystem operations,
and subagent orchestration using Pydantic AI patterns that align with
DeepCritical's architecture.
"""

from __future__ import annotations

# Import existing DeepCritical types
# Import middleware types from datatypes module
from DeepResearch.src.datatypes.middleware import (
    BaseMiddleware,
    FilesystemMiddleware,
    MiddlewareConfig,
    MiddlewarePipeline,
    MiddlewareResult,
    PlanningMiddleware,
    PromptCachingMiddleware,
    SubAgentMiddleware,
    SummarizationMiddleware,
    create_default_middleware_pipeline,
    create_filesystem_middleware,
    create_planning_middleware,
    create_prompt_caching_middleware,
    create_subagent_middleware,
    create_summarization_middleware,
)

# Export all middleware components
__all__ = [
    # Base classes
    "BaseMiddleware",
    "FilesystemMiddleware",
    # Configuration and results
    "MiddlewareConfig",
    "MiddlewarePipeline",
    "MiddlewareResult",
    # Middleware implementations
    "PlanningMiddleware",
    "PromptCachingMiddleware",
    "SubAgentMiddleware",
    "SummarizationMiddleware",
    "create_default_middleware_pipeline",
    "create_filesystem_middleware",
    # Factory functions
    "create_planning_middleware",
    "create_prompt_caching_middleware",
    "create_subagent_middleware",
    "create_summarization_middleware",
]
