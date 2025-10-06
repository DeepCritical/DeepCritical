"""
State machine modules for DeepCritical workflows.

This package contains Pydantic Graph-based workflow implementations
for various DeepCritical operations including bioinformatics, RAG,
and search workflows.
"""

from .bioinformatics_workflow import (
    BioinformaticsState,
    ParseBioinformaticsQuery,
    FuseDataSources,
    AssessDataQuality,
    CreateReasoningTask,
    PerformReasoning,
    SynthesizeResults as BioSynthesizeResults,
)

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

from .rag_workflow import (
    RAGState,
    InitializeRAG,
    LoadDocuments,
    ProcessDocuments,
    StoreDocuments,
    QueryRAG,
    GenerateResponse,
    RAGError,
)

from .search_workflow import (
    SearchWorkflowState,
    InitializeSearch,
    PerformWebSearch,
    ProcessResults,
    GenerateFinalResponse,
    SearchWorkflowError,
)

__all__ = [
    # Bioinformatics workflow
    "BioinformaticsState",
    "ParseBioinformaticsQuery",
    "FuseDataSources",
    "AssessDataQuality",
    "CreateReasoningTask",
    "PerformReasoning",
    "BioSynthesizeResults",
    # Deep search workflow
    "DeepSearchState",
    "InitializeDeepSearch",
    "PlanSearchStrategy",
    "ExecuteSearchStep",
    "CheckSearchProgress",
    "DeepSearchSynthesizeResults",
    "EvaluateResults",
    "CompleteDeepSearch",
    "DeepSearchError",
    # RAG workflow
    "RAGState",
    "InitializeRAG",
    "LoadDocuments",
    "ProcessDocuments",
    "StoreDocuments",
    "QueryRAG",
    "GenerateResponse",
    "RAGError",
    # Search workflow
    "SearchWorkflowState",
    "InitializeSearch",
    "PerformWebSearch",
    "ProcessResults",
    "GenerateFinalResponse",
    "SearchWorkflowError",
]
