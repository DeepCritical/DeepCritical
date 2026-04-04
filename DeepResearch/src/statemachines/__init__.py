"""
State machine modules for DeepCritical workflows.

This package contains Pydantic Graph-based workflow implementations
for various DeepCritical operations including bioinformatics, RAG,
search, and code execution workflows.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

# from .deepsearch_workflow import (
#     DeepSearchState,
#     InitializeDeepSearch,
#     PlanSearchStrategy,
#     ExecuteSearchStep,
#     CheckSearchProgress,
#     SynthesizeResults as DeepSearchSynthesizeResults,
#     EvaluateResults,
#     CompleteDeepSearch,
#     DeepSearchError,
# )
from .code_execution_workflow import (
    AnalyzeError,
    CodeExecutionWorkflow,
    CodeExecutionWorkflowState,
    ExecuteCode,
    FormatResponse,
    GenerateCode,
    ImproveCode,
    InitializeCodeExecution,
    execute_code_workflow,
    generate_and_execute_code,
)
from .hypothesis_workflow import (
    CreateTestingPlans,
    HypothesisError,
    HypothesisWorkflowState,
    ParseHypothesisRequest,
    ScoreAndRankHypotheses,
    SynthesizeHypothesisReport,
    create_hypothesis_workflow,
    run_hypothesis_workflow,
)
from .hypothesis_workflow import (
    GatherEvidence as GatherHypothesisEvidence,
)
from .hypothesis_workflow import (
    GenerateHypotheses as GenerateHypothesesNode,
)
from .rag_workflow import (
    GenerateResponse,
    InitializeRAG,
    LoadDocuments,
    ProcessDocuments,
    QueryRAG,
    RAGError,
    RAGState,
    StoreDocuments,
)
from .search_workflow import (
    GenerateFinalResponse,
    InitializeSearch,
    PerformWebSearch,
    ProcessResults,
    SearchWorkflowError,
    SearchWorkflowState,
)

_BIOINFORMATICS_EXPORTS = {
    "AssessDataQuality": "AssessDataQuality",
    "BioinformaticsState": "BioinformaticsState",
    "BioSynthesizeResults": "SynthesizeResults",
    "CreateReasoningTask": "CreateReasoningTask",
    "FuseDataSources": "FuseDataSources",
    "ParseBioinformaticsQuery": "ParseBioinformaticsQuery",
    "PerformReasoning": "PerformReasoning",
    "bioinformatics_workflow": "bioinformatics_workflow",
}


def __getattr__(name: str) -> Any:
    if name in _BIOINFORMATICS_EXPORTS:
        module = import_module(f"{__name__}.bioinformatics_workflow")
        return getattr(module, _BIOINFORMATICS_EXPORTS[name])

    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)


__all__ = [
    "AnalyzeError",
    "AssessDataQuality",
    "BioSynthesizeResults",
    "BioinformaticsState",
    "CheckSearchProgress",
    "CodeExecutionWorkflow",
    "CodeExecutionWorkflowState",
    "CompleteDeepSearch",
    "CreateReasoningTask",
    "CreateTestingPlans",
    "DeepSearchError",
    "DeepSearchState",
    "DeepSearchSynthesizeResults",
    "EvaluateResults",
    "ExecuteCode",
    "ExecuteSearchStep",
    "FormatResponse",
    "FuseDataSources",
    "GatherHypothesisEvidence",
    "GenerateCode",
    "GenerateFinalResponse",
    "GenerateHypothesesNode",
    "GenerateResponse",
    "HypothesisError",
    "HypothesisWorkflowState",
    "ImproveCode",
    "InitializeCodeExecution",
    "InitializeDeepSearch",
    "InitializeRAG",
    "InitializeSearch",
    "LoadDocuments",
    "ParseBioinformaticsQuery",
    "ParseHypothesisRequest",
    "PerformReasoning",
    "PerformWebSearch",
    "PlanSearchStrategy",
    "ProcessDocuments",
    "ProcessResults",
    "QueryRAG",
    "RAGError",
    "RAGState",
    "ScoreAndRankHypotheses",
    "SearchWorkflowError",
    "SearchWorkflowState",
    "StoreDocuments",
    "SynthesizeHypothesisReport",
    "create_hypothesis_workflow",
    "execute_code_workflow",
    "generate_and_execute_code",
    "run_hypothesis_workflow",
]
