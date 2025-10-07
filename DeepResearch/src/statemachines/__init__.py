"""
State machine modules for DeepCritical workflows.

This package contains Pydantic Graph-based workflow implementations
for various DeepCritical operations including bioinformatics, RAG,
and search workflows.
"""

from .bioinformatics_workflow import (
    AssessDataQuality,
    BioinformaticsState,
    CreateReasoningTask,
    FuseDataSources,
    ParseBioinformaticsQuery,
    PerformReasoning,
)
from .bioinformatics_workflow import (
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

__all__ = [
    "AssessDataQuality",
    "BioSynthesizeResults",
    # Bioinformatics workflow
    "BioinformaticsState",
    "CheckSearchProgress",
    "CompleteDeepSearch",
    "CreateReasoningTask",
    "DeepSearchError",
    # Deep search workflow
    "DeepSearchState",
    "DeepSearchSynthesizeResults",
    "EvaluateResults",
    "ExecuteSearchStep",
    "FuseDataSources",
    "GenerateFinalResponse",
    "GenerateResponse",
    "InitializeDeepSearch",
    "InitializeRAG",
    "InitializeSearch",
    "LoadDocuments",
    "ParseBioinformaticsQuery",
    "PerformReasoning",
    "PerformWebSearch",
    "PlanSearchStrategy",
    "ProcessDocuments",
    "ProcessResults",
    "QueryRAG",
    "RAGError",
    # RAG workflow
    "RAGState",
    "SearchWorkflowError",
    # Search workflow
    "SearchWorkflowState",
    "StoreDocuments",
]
