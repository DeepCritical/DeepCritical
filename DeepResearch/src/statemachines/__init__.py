"""
State machine modules for DeepCritical workflows.

This package contains Pydantic Graph-based workflow implementations
for various DeepCritical operations including bioinformatics, RAG,
search, and code execution workflows.
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
    "AnalyzeError",
    "AssessDataQuality",
    "BioSynthesizeResults",
    "BioinformaticsState",
    "CheckSearchProgress",
    "CodeExecutionWorkflow",
    "CodeExecutionWorkflowState",
    "CompleteDeepSearch",
    "CreateReasoningTask",
    "DeepSearchError",
    "DeepSearchState",
    "DeepSearchSynthesizeResults",
    "EvaluateResults",
    "ExecuteCode",
    "ExecuteSearchStep",
    "FormatResponse",
    "FuseDataSources",
    "GenerateCode",
    "GenerateFinalResponse",
    "GenerateResponse",
    "ImproveCode",
    "InitializeCodeExecution",
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
    "RAGState",
    "SearchWorkflowError",
    "SearchWorkflowState",
    "StoreDocuments",
    "execute_code_workflow",
    "generate_and_execute_code",
]
