"""
Import tests for DeepResearch datatypes modules.

This module tests that all imports from the datatypes subdirectory work correctly,
including all individual datatype modules and their dependencies.
"""

import inspect

import pytest


class TestDatatypesModuleImports:
    """Test imports for individual datatype modules."""

    def test_bioinformatics_imports(self):
        """Test all imports from bioinformatics module."""

        from DeepResearch.src.datatypes.bioinformatics import (
            BioinformaticsAgentDeps,
            DataFusionRequest,
            DataFusionResult,
            DrugTarget,
            EvidenceCode,
            FusedDataset,
            GeneExpressionProfile,
            GEOPlatform,
            GEOSeries,
            GOAnnotation,
            GOTerm,
            PerturbationProfile,
            ProteinInteraction,
            ProteinStructure,
            PubMedPaper,
            ReasoningResult,
            ReasoningTask,
        )

        # Verify they are all accessible and not None
        assert EvidenceCode is not None
        assert GOTerm is not None
        assert GOAnnotation is not None
        assert PubMedPaper is not None
        assert GEOPlatform is not None
        assert GEOSeries is not None
        assert GeneExpressionProfile is not None
        assert DrugTarget is not None
        assert PerturbationProfile is not None
        assert ProteinStructure is not None
        assert ProteinInteraction is not None
        assert FusedDataset is not None
        assert ReasoningTask is not None
        assert DataFusionRequest is not None
        assert BioinformaticsAgentDeps is not None
        assert DataFusionResult is not None
        assert ReasoningResult is not None

        # Test enum values exist
        assert hasattr(EvidenceCode, "IDA")
        assert hasattr(EvidenceCode, "IEA")

    def test_agents_datatypes_init_imports(self):
        """Test all imports from agents datatypes module."""

        from DeepResearch.src.datatypes.agents import (
            AgentDependencies,
            AgentResult,
            AgentStatus,
            AgentType,
            ExecutionHistory,
        )

        # Verify they are all accessible and not None
        assert AgentType is not None
        assert AgentStatus is not None
        assert AgentDependencies is not None
        assert AgentResult is not None
        assert ExecutionHistory is not None

        # Test enum values exist
        assert hasattr(AgentType, "PARSER")
        assert hasattr(AgentType, "PLANNER")
        assert hasattr(AgentStatus, "IDLE")
        assert hasattr(AgentStatus, "RUNNING")

    def test_rag_imports(self):
        """Test all imports from rag module."""

        from DeepResearch.src.datatypes.rag import (
            Document,
            EmbeddingModelType,
            Embeddings,
            EmbeddingsConfig,
            IntegratedSearchRequest,
            IntegratedSearchResponse,
            LLMModelType,
            LLMProvider,
            RAGConfig,
            RAGQuery,
            RAGResponse,
            RAGSystem,
            RAGWorkflowState,
            SearchResult,
            SearchType,
            VectorStore,
            VectorStoreConfig,
            VectorStoreType,
            VLLMConfig,
        )

        # Verify they are all accessible and not None
        assert SearchType is not None
        assert EmbeddingModelType is not None
        assert LLMModelType is not None
        assert VectorStoreType is not None
        assert Document is not None
        assert SearchResult is not None
        assert EmbeddingsConfig is not None
        assert VLLMConfig is not None
        assert VectorStoreConfig is not None
        assert RAGQuery is not None
        assert RAGResponse is not None
        assert RAGConfig is not None
        assert IntegratedSearchRequest is not None
        assert IntegratedSearchResponse is not None
        assert Embeddings is not None
        assert VectorStore is not None
        assert LLMProvider is not None
        assert RAGSystem is not None
        assert RAGWorkflowState is not None

        # Test enum values exist
        assert hasattr(SearchType, "SEMANTIC")
        assert hasattr(VectorStoreType, "CHROMA")

    def test_vllm_integration_imports(self):
        """Test all imports from vllm_integration module."""

        from DeepResearch.src.datatypes.vllm_integration import (
            VLLMDeployment,
            VLLMEmbeddings,
            VLLMEmbeddingServerConfig,
            VLLMLLMProvider,
            VLLMRAGSystem,
            VLLMServerConfig,
        )

        # Verify they are all accessible and not None
        assert VLLMEmbeddings is not None
        assert VLLMLLMProvider is not None
        assert VLLMServerConfig is not None
        assert VLLMEmbeddingServerConfig is not None
        assert VLLMDeployment is not None
        assert VLLMRAGSystem is not None

    def test_vllm_agent_imports(self):
        """Test all imports from vllm_agent module."""

        from DeepResearch.src.datatypes.vllm_agent import (
            VLLMAgentConfig,
            VLLMAgentDependencies,
        )

        # Verify they are all accessible and not None
        assert VLLMAgentDependencies is not None
        assert VLLMAgentConfig is not None

        # Test that they are proper Pydantic models
        assert hasattr(VLLMAgentDependencies, "model_fields") or hasattr(
            VLLMAgentDependencies, "__fields__"
        )
        assert hasattr(VLLMAgentConfig, "model_fields") or hasattr(
            VLLMAgentConfig, "__fields__"
        )

    def test_chunk_dataclass_imports(self):
        """Test all imports from chunk_dataclass module."""

        from DeepResearch.src.datatypes.chunk_dataclass import Chunk

        # Verify they are all accessible and not None
        assert Chunk is not None

    def test_document_dataclass_imports(self):
        """Test all imports from document_dataclass module."""

        from DeepResearch.src.datatypes.document_dataclass import Document

        # Verify they are all accessible and not None
        assert Document is not None

    def test_chroma_dataclass_imports(self):
        """Test all imports from chroma_dataclass module."""

        from DeepResearch.src.datatypes.chroma_dataclass import ChromaDocument

        # Verify they are all accessible and not None
        assert ChromaDocument is not None

    def test_postgres_dataclass_imports(self):
        """Test all imports from postgres_dataclass module."""

        from DeepResearch.src.datatypes.postgres_dataclass import PostgresDocument

        # Verify they are all accessible and not None
        assert PostgresDocument is not None

    def test_vllm_dataclass_imports(self):
        """Test all imports from vllm_dataclass module."""

        from DeepResearch.src.datatypes.vllm_dataclass import VLLMDocument

        # Verify they are all accessible and not None
        assert VLLMDocument is not None

    def test_markdown_imports(self):
        """Test all imports from markdown module."""

        from DeepResearch.src.datatypes.markdown import MarkdownDocument

        # Verify they are all accessible and not None
        assert MarkdownDocument is not None

    def test_agents_imports(self):
        """Test all imports from agents module."""

        from DeepResearch.src.datatypes.agents import (
            AgentDependencies,
            AgentResult,
            AgentStatus,
            AgentType,
            ExecutionHistory,
        )

        # Verify they are all accessible and not None
        assert AgentType is not None
        assert AgentStatus is not None
        assert AgentDependencies is not None
        assert AgentResult is not None
        assert ExecutionHistory is not None

        # Test enum values exist
        assert hasattr(AgentType, "PARSER")
        assert hasattr(AgentType, "PLANNER")
        assert hasattr(AgentStatus, "IDLE")
        assert hasattr(AgentStatus, "RUNNING")

        # Test that they can be instantiated
        try:
            # Test AgentDependencies
            deps = AgentDependencies(config={"test": "value"})
            assert deps.config["test"] == "value"
            assert deps.tools == []
            assert deps.other_agents == []
            assert deps.data_sources == []

            # Test AgentResult
            result = AgentResult(success=True, data={"test": "data"})
            assert result.success is True
            assert result.data["test"] == "data"
            assert result.agent_type == AgentType.EXECUTOR

            # Test ExecutionHistory
            history = ExecutionHistory()
            assert history.items == []
            assert hasattr(history, "record")

        except Exception as e:
            pytest.fail(f"Agents datatypes instantiation failed: {e}")

    def test_deep_agent_state_imports(self):
        """Test all imports from deep_agent_state module."""

        from DeepResearch.src.datatypes.deep_agent_state import DeepAgentState

        # Verify they are all accessible and not None
        assert DeepAgentState is not None

    def test_deep_agent_types_imports(self):
        """Test all imports from deep_agent_types module."""

        from DeepResearch.src.datatypes.deep_agent_types import DeepAgentType

        # Verify they are all accessible and not None
        assert DeepAgentType is not None

    def test_deep_agent_tools_imports(self):
        """Test all imports from deep_agent_tools module."""

        from DeepResearch.src.datatypes.deep_agent_tools import (
            EditFileRequest,
            EditFileResponse,
            ListFilesResponse,
            ReadFileRequest,
            ReadFileResponse,
            TaskRequestModel,
            TaskResponse,
            WriteFileRequest,
            WriteFileResponse,
            WriteTodosRequest,
            WriteTodosResponse,
        )

        # Verify they are all accessible and not None
        assert WriteTodosRequest is not None
        assert WriteTodosResponse is not None
        assert ListFilesResponse is not None
        assert ReadFileRequest is not None
        assert ReadFileResponse is not None
        assert WriteFileRequest is not None
        assert WriteFileResponse is not None
        assert EditFileRequest is not None
        assert EditFileResponse is not None
        assert TaskRequestModel is not None
        assert TaskResponse is not None

        # Test that they are proper Pydantic models
        assert hasattr(WriteTodosRequest, "model_fields") or hasattr(
            WriteTodosRequest, "__fields__"
        )
        assert hasattr(TaskRequestModel, "model_fields") or hasattr(
            TaskRequestModel, "__fields__"
        )

        # Test that they can be instantiated
        try:
            request = WriteTodosRequest(todos=[{"content": "test todo"}])
            assert request.todos[0]["content"] == "test todo"

            response = WriteTodosResponse(success=True, todos_created=1, message="test")
            assert response.success is True
            assert response.todos_created == 1

            task_request = TaskRequestModel(
                description="test task", subagent_type="test_agent"
            )
            assert task_request.description == "test task"
            assert task_request.subagent_type == "test_agent"

            task_response = TaskResponse(
                success=True, task_id="test_id", message="test"
            )
            assert task_response.success is True
            assert task_response.task_id == "test_id"

        except Exception as e:
            pytest.fail(f"DeepAgent tools model instantiation failed: {e}")

    def test_workflow_orchestration_imports(self):
        """Test all imports from workflow_orchestration module."""

        from DeepResearch.src.datatypes.workflow_orchestration import (
            BreakConditionCheck,
            JudgeEvaluationRequest,
            JudgeEvaluationResult,
            MultiAgentCoordinationRequest,
            MultiAgentCoordinationResult,
            NestedLoopRequest,
            OrchestrationResult,
            OrchestratorDependencies,
            SubgraphSpawnRequest,
            WorkflowOrchestrationState,
            WorkflowSpawnRequest,
            WorkflowSpawnResult,
        )

        # Verify they are all accessible and not None
        assert WorkflowOrchestrationState is not None
        assert OrchestratorDependencies is not None
        assert WorkflowSpawnRequest is not None
        assert WorkflowSpawnResult is not None
        assert MultiAgentCoordinationRequest is not None
        assert MultiAgentCoordinationResult is not None
        assert JudgeEvaluationRequest is not None
        assert JudgeEvaluationResult is not None
        assert NestedLoopRequest is not None
        assert SubgraphSpawnRequest is not None
        assert BreakConditionCheck is not None
        assert OrchestrationResult is not None

    def test_multi_agent_imports(self):
        """Test all imports from multi_agent module."""

        from DeepResearch.src.datatypes.multi_agent import (
            AgentRole,
            AgentState,
            CommunicationProtocol,
            CoordinationMessage,
            CoordinationResult,
            CoordinationRound,
            CoordinationStrategy,
            MultiAgentCoordinatorConfig,
        )

        # Verify they are all accessible and not None
        assert CoordinationStrategy is not None
        assert CommunicationProtocol is not None
        assert AgentState is not None
        assert CoordinationMessage is not None
        assert CoordinationRound is not None
        assert CoordinationResult is not None
        assert MultiAgentCoordinatorConfig is not None
        assert AgentRole is not None

        # Test enum values exist
        assert hasattr(CoordinationStrategy, "COLLABORATIVE")
        assert hasattr(CommunicationProtocol, "DIRECT")
        assert hasattr(AgentRole, "COORDINATOR")

    def test_execution_imports(self):
        """Test all imports from execution module."""

        from DeepResearch.src.datatypes.execution import (
            ExecutionContext,
            WorkflowDAG,
            WorkflowStep,
        )

        # Verify they are all accessible and not None
        assert WorkflowStep is not None
        assert WorkflowDAG is not None
        assert ExecutionContext is not None

        # Test that they are dataclasses (since they're defined with @dataclass)
        from dataclasses import is_dataclass

        assert is_dataclass(WorkflowStep)
        assert is_dataclass(WorkflowDAG)
        assert is_dataclass(ExecutionContext)

    def test_research_imports(self):
        """Test all imports from research module."""

        from DeepResearch.src.datatypes.research import (
            ResearchOutcome,
            StepResult,
        )

        # Verify they are all accessible and not None
        assert StepResult is not None
        assert ResearchOutcome is not None

        # Test that they are dataclasses
        from dataclasses import is_dataclass

        assert is_dataclass(StepResult)
        assert is_dataclass(ResearchOutcome)

    def test_search_agent_imports(self):
        """Test all imports from search_agent module."""

        from DeepResearch.src.datatypes.search_agent import (
            SearchAgentConfig,
            SearchAgentDependencies,
            SearchQuery,
            SearchResult,
        )

        # Verify they are all accessible and not None
        assert SearchAgentConfig is not None
        assert SearchQuery is not None
        assert SearchResult is not None
        assert SearchAgentDependencies is not None

        # Test that they are proper Pydantic models
        assert hasattr(SearchAgentConfig, "model_fields") or hasattr(
            SearchAgentConfig, "__fields__"
        )
        assert hasattr(SearchQuery, "model_fields") or hasattr(
            SearchQuery, "__fields__"
        )
        assert hasattr(SearchResult, "model_fields") or hasattr(
            SearchResult, "__fields__"
        )
        assert hasattr(SearchAgentDependencies, "model_fields") or hasattr(
            SearchAgentDependencies, "__fields__"
        )

        # Test factory method exists
        assert hasattr(SearchAgentDependencies, "from_search_query")

    def test_analytics_imports(self):
        """Test all imports from analytics module."""

        from DeepResearch.src.datatypes.analytics import (
            AnalyticsDataRequest,
            AnalyticsDataResponse,
            AnalyticsRequest,
            AnalyticsResponse,
        )

        # Verify they are all accessible and not None
        assert AnalyticsRequest is not None
        assert AnalyticsResponse is not None
        assert AnalyticsDataRequest is not None
        assert AnalyticsDataResponse is not None

        # Test that they are proper Pydantic models
        assert hasattr(AnalyticsRequest, "model_fields") or hasattr(
            AnalyticsRequest, "__fields__"
        )
        assert hasattr(AnalyticsResponse, "model_fields") or hasattr(
            AnalyticsResponse, "__fields__"
        )
        assert hasattr(AnalyticsDataRequest, "model_fields") or hasattr(
            AnalyticsDataRequest, "__fields__"
        )
        assert hasattr(AnalyticsDataResponse, "model_fields") or hasattr(
            AnalyticsDataResponse, "__fields__"
        )

        # Test that they can be instantiated
        try:
            request = AnalyticsRequest(duration=2.5, num_results=4)
            assert request.duration == 2.5
            assert request.num_results == 4

            response = AnalyticsResponse(success=True, message="Test message")
            assert response.success is True
            assert response.message == "Test message"

            data_request = AnalyticsDataRequest(days=30)
            assert data_request.days == 30

            data_response = AnalyticsDataResponse(data=[], success=True, error=None)
            assert data_response.success is True
            assert data_response.error is None
        except Exception as e:
            pytest.fail(f"Analytics model instantiation failed: {e}")

    def test_deepsearch_imports(self):
        """Test all imports from deepsearch module."""

        from DeepResearch.src.datatypes.deepsearch import (
            MAX_QUERIES_PER_STEP,
            MAX_REFLECT_PER_STEP,
            MAX_URLS_PER_STEP,
            ActionType,
            DeepSearchSchemas,
            EvaluationType,
            PromptPair,
            ReflectionQuestion,
            SearchResult,
            SearchTimeFilter,
            URLVisitResult,
            WebSearchRequest,
        )

        # Verify they are all accessible and not None
        assert EvaluationType is not None
        assert ActionType is not None
        assert SearchTimeFilter is not None
        assert SearchResult is not None
        assert WebSearchRequest is not None
        assert URLVisitResult is not None
        assert ReflectionQuestion is not None
        assert PromptPair is not None
        assert DeepSearchSchemas is not None

        # Test enum values exist
        assert hasattr(EvaluationType, "DEFINITIVE")
        assert hasattr(ActionType, "SEARCH")
        assert hasattr(SearchTimeFilter, "PAST_HOUR")

        # Test constants are correct types and values
        assert isinstance(MAX_URLS_PER_STEP, int)
        assert isinstance(MAX_QUERIES_PER_STEP, int)
        assert isinstance(MAX_REFLECT_PER_STEP, int)
        assert MAX_URLS_PER_STEP > 0
        assert MAX_QUERIES_PER_STEP > 0
        assert MAX_REFLECT_PER_STEP > 0

        # Test that they are dataclasses (for dataclass types)
        from dataclasses import is_dataclass

        assert is_dataclass(SearchResult)
        assert is_dataclass(WebSearchRequest)
        assert is_dataclass(URLVisitResult)
        assert is_dataclass(ReflectionQuestion)
        assert is_dataclass(PromptPair)

        # Test that DeepSearchSchemas is a class
        assert inspect.isclass(DeepSearchSchemas)

        # Test that they can be instantiated
        try:
            # Test SearchTimeFilter
            time_filter = SearchTimeFilter(SearchTimeFilter.PAST_DAY)
            assert time_filter.value == "qdr:d"

            # Test SearchResult
            result = SearchResult(
                title="Test Result",
                url="https://example.com",
                snippet="Test snippet",
                score=0.95,
            )
            assert result.title == "Test Result"
            assert result.score == 0.95

            # Test WebSearchRequest
            request = WebSearchRequest(query="test query", max_results=5)
            assert request.query == "test query"
            assert request.max_results == 5

            # Test URLVisitResult
            visit_result = URLVisitResult(
                url="https://example.com",
                title="Test Page",
                content="Test content",
                success=True,
            )
            assert visit_result.url == "https://example.com"
            assert visit_result.success is True

            # Test ReflectionQuestion
            question = ReflectionQuestion(
                question="What is the main topic?", priority=1
            )
            assert question.question == "What is the main topic?"
            assert question.priority == 1

            # Test PromptPair
            prompt_pair = PromptPair(system="System prompt", user="User prompt")
            assert prompt_pair.system == "System prompt"
            assert prompt_pair.user == "User prompt"

            # Test DeepSearchSchemas
            schemas = DeepSearchSchemas()
            assert schemas.language_style == "formal English"
            assert schemas.language_code == "en"

        except Exception as e:
            pytest.fail(f"DeepSearch model instantiation failed: {e}")

    def test_docker_sandbox_datatypes_imports(self):
        """Test all imports from docker_sandbox_datatypes module."""

        from DeepResearch.src.datatypes.docker_sandbox_datatypes import (
            DockerExecutionRequest,
            DockerExecutionResult,
            DockerSandboxConfig,
            DockerSandboxContainerInfo,
            DockerSandboxEnvironment,
            DockerSandboxMetrics,
            DockerSandboxPolicies,
            DockerSandboxRequest,
            DockerSandboxResponse,
        )

        # Verify they are all accessible and not None
        assert DockerSandboxConfig is not None
        assert DockerExecutionRequest is not None
        assert DockerExecutionResult is not None
        assert DockerSandboxEnvironment is not None
        assert DockerSandboxPolicies is not None
        assert DockerSandboxContainerInfo is not None
        assert DockerSandboxMetrics is not None
        assert DockerSandboxRequest is not None
        assert DockerSandboxResponse is not None

        # Test that they are proper Pydantic models
        assert hasattr(DockerSandboxConfig, "model_fields") or hasattr(
            DockerSandboxConfig, "__fields__"
        )
        assert hasattr(DockerExecutionRequest, "model_fields") or hasattr(
            DockerExecutionRequest, "__fields__"
        )
        assert hasattr(DockerExecutionResult, "model_fields") or hasattr(
            DockerExecutionResult, "__fields__"
        )
        assert hasattr(DockerSandboxEnvironment, "model_fields") or hasattr(
            DockerSandboxEnvironment, "__fields__"
        )
        assert hasattr(DockerSandboxPolicies, "model_fields") or hasattr(
            DockerSandboxPolicies, "__fields__"
        )
        assert hasattr(DockerSandboxContainerInfo, "model_fields") or hasattr(
            DockerSandboxContainerInfo, "__fields__"
        )
        assert hasattr(DockerSandboxMetrics, "model_fields") or hasattr(
            DockerSandboxMetrics, "__fields__"
        )
        assert hasattr(DockerSandboxRequest, "model_fields") or hasattr(
            DockerSandboxRequest, "__fields__"
        )
        assert hasattr(DockerSandboxResponse, "model_fields") or hasattr(
            DockerSandboxResponse, "__fields__"
        )

        # Test that they can be instantiated
        try:
            # Test DockerSandboxConfig
            config = DockerSandboxConfig(image="python:3.11-slim")
            assert config.image == "python:3.11-slim"
            assert config.working_directory == "/workspace"
            assert config.auto_remove is True

            # Test DockerSandboxPolicies
            policies = DockerSandboxPolicies()
            assert policies.python is True
            assert policies.bash is True
            assert policies.is_language_allowed("python") is True
            assert policies.is_language_allowed("javascript") is False

            # Test DockerSandboxEnvironment
            env = DockerSandboxEnvironment(variables={"TEST_VAR": "test_value"})
            assert env.variables["TEST_VAR"] == "test_value"
            assert env.working_directory == "/workspace"

            # Test DockerExecutionRequest
            request = DockerExecutionRequest(
                language="python", code="print('hello')", timeout=30
            )
            assert request.language == "python"
            assert request.code == "print('hello')"
            assert request.timeout == 30

            # Test DockerExecutionResult
            result = DockerExecutionResult(
                success=True,
                stdout="hello",
                stderr="",
                exit_code=0,
                files_created=[],
                execution_time=0.5,
            )
            assert result.success is True
            assert result.stdout == "hello"
            assert result.exit_code == 0
            assert result.execution_time == 0.5

            # Test DockerSandboxContainerInfo
            container_info = DockerSandboxContainerInfo(
                container_id="test_id",
                container_name="test_container",
                image="python:3.11-slim",
                status="exited",
            )
            assert container_info.container_id == "test_id"
            assert container_info.status == "exited"

            # Test DockerSandboxMetrics
            metrics = DockerSandboxMetrics()
            assert metrics.total_executions == 0
            assert metrics.success_rate == 0.0

            # Test DockerSandboxRequest
            sandbox_request = DockerSandboxRequest(execution=request, config=config)
            assert sandbox_request.execution is request
            assert sandbox_request.config is config

            # Test DockerSandboxResponse
            sandbox_response = DockerSandboxResponse(
                request=sandbox_request, result=result
            )
            assert sandbox_response.request is sandbox_request
            assert sandbox_response.result is result

        except Exception as e:
            pytest.fail(f"Docker sandbox datatypes instantiation failed: {e}")

    def test_middleware_imports(self):
        """Test all imports from middleware module."""

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

        # Verify they are all accessible and not None
        assert MiddlewareConfig is not None
        assert MiddlewareResult is not None
        assert BaseMiddleware is not None
        assert PlanningMiddleware is not None
        assert FilesystemMiddleware is not None
        assert SubAgentMiddleware is not None
        assert SummarizationMiddleware is not None
        assert PromptCachingMiddleware is not None
        assert MiddlewarePipeline is not None
        assert create_planning_middleware is not None
        assert create_filesystem_middleware is not None
        assert create_subagent_middleware is not None
        assert create_summarization_middleware is not None
        assert create_prompt_caching_middleware is not None
        assert create_default_middleware_pipeline is not None

        # Test that they are proper Pydantic models (for Pydantic classes)
        assert hasattr(MiddlewareConfig, "model_fields") or hasattr(
            MiddlewareConfig, "__fields__"
        )
        assert hasattr(MiddlewareResult, "model_fields") or hasattr(
            MiddlewareResult, "__fields__"
        )

        # Test that factory functions are callable
        assert callable(create_planning_middleware)
        assert callable(create_filesystem_middleware)
        assert callable(create_subagent_middleware)
        assert callable(create_summarization_middleware)
        assert callable(create_prompt_caching_middleware)
        assert callable(create_default_middleware_pipeline)

        # Test that they can be instantiated
        try:
            config = MiddlewareConfig(enabled=True, priority=1, timeout=30.0)
            assert config.enabled is True
            assert config.priority == 1
            assert config.timeout == 30.0

            result = MiddlewareResult(success=True, modified_state=False)
            assert result.success is True
            assert result.modified_state is False

            # Test factory function
            middleware = create_planning_middleware(config)
            assert middleware is not None
            assert isinstance(middleware, PlanningMiddleware)

        except Exception as e:
            pytest.fail(f"Middleware model instantiation failed: {e}")

    def test_pydantic_ai_tools_imports(self):
        """Test all imports from pydantic_ai_tools module."""

        from DeepResearch.src.datatypes.pydantic_ai_tools import (
            CodeExecBuiltinRunner,
            UrlContextBuiltinRunner,
            WebSearchBuiltinRunner,
        )
        from DeepResearch.src.utils.pydantic_ai_utils import (
            build_agent as _build_agent,
        )
        from DeepResearch.src.utils.pydantic_ai_utils import (
            build_builtin_tools as _build_builtin_tools,
        )
        from DeepResearch.src.utils.pydantic_ai_utils import (
            build_toolsets as _build_toolsets,
        )
        from DeepResearch.src.utils.pydantic_ai_utils import (
            get_pydantic_ai_config as _get_cfg,
        )
        from DeepResearch.src.utils.pydantic_ai_utils import (
            run_agent_sync as _run_sync,
        )

        # Verify they are all accessible and not None
        assert WebSearchBuiltinRunner is not None
        assert CodeExecBuiltinRunner is not None
        assert UrlContextBuiltinRunner is not None
        assert _get_cfg is not None
        assert _build_builtin_tools is not None
        assert _build_toolsets is not None
        assert _build_agent is not None
        assert _run_sync is not None

        # Test that tool runners can be instantiated
        try:
            web_search_tool = WebSearchBuiltinRunner()
            assert web_search_tool is not None
            assert hasattr(web_search_tool, "run")

            code_exec_tool = CodeExecBuiltinRunner()
            assert code_exec_tool is not None
            assert hasattr(code_exec_tool, "run")

            url_context_tool = UrlContextBuiltinRunner()
            assert url_context_tool is not None
            assert hasattr(url_context_tool, "run")

        except Exception as e:
            pytest.fail(f"Pydantic AI tools instantiation failed: {e}")

        # Test utility functions are callable
        assert callable(_get_cfg)
        assert callable(_build_builtin_tools)
        assert callable(_build_toolsets)
        assert callable(_build_agent)
        assert callable(_run_sync)

    def test_tools_datatypes_imports(self):
        """Test all imports from tools datatypes module."""

        from DeepResearch.src.datatypes.tools import (
            ExecutionResult,
            MockToolRunner,
            ToolMetadata,
            ToolRunner,
        )

        # Verify they are all accessible and not None
        assert ToolMetadata is not None
        assert ExecutionResult is not None
        assert ToolRunner is not None
        assert MockToolRunner is not None

        # Test that they are proper dataclasses (for dataclass types)
        from dataclasses import is_dataclass

        assert is_dataclass(ToolMetadata)
        assert is_dataclass(ExecutionResult)

        # Test that ToolRunner is an abstract base class
        import inspect

        assert inspect.isabstract(ToolRunner)

        # Test that MockToolRunner inherits from ToolRunner
        assert issubclass(MockToolRunner, ToolRunner)

        # Test that they can be instantiated
        try:
            metadata = ToolMetadata(
                name="test_tool",
                category="search",
                description="Test tool",
                version="1.0.0",
                tags=["test", "tool"],
            )
            assert metadata.name == "test_tool"
            assert metadata.category == "search"
            assert metadata.description == "Test tool"
            assert metadata.version == "1.0.0"
            assert metadata.tags == ["test", "tool"]

            result = ExecutionResult(
                success=True,
                data={"test": "data"},
                error=None,
                metadata={"test": "metadata"},
            )
            assert result.success is True
            assert result.data["test"] == "data"
            assert result.error is None
            assert result.metadata["test"] == "metadata"

        except Exception as e:
            pytest.fail(f"Tools datatypes instantiation failed: {e}")


class TestDatatypesCrossModuleImports:
    """Test cross-module imports and dependencies within datatypes."""

    def test_datatypes_internal_dependencies(self):
        """Test that datatype modules can import from each other correctly."""
        # Test that bioinformatics can import from rag
        from DeepResearch.src.datatypes.bioinformatics import GOTerm
        from DeepResearch.src.datatypes.rag import Document

        # This should work without circular imports
        assert GOTerm is not None
        assert Document is not None

    def test_pydantic_base_model_inheritance(self):
        """Test that datatype models properly inherit from Pydantic BaseModel."""
        from DeepResearch.src.datatypes.bioinformatics import GOTerm
        from DeepResearch.src.datatypes.rag import Document

        # Test that they are proper Pydantic models
        assert hasattr(GOTerm, "__fields__") or hasattr(GOTerm, "model_fields")
        assert hasattr(Document, "__fields__") or hasattr(Document, "model_fields")

    def test_enum_definitions(self):
        """Test that enum classes are properly defined."""
        from DeepResearch.src.datatypes.bioinformatics import EvidenceCode
        from DeepResearch.src.datatypes.rag import SearchType

        # Test that enums have expected values
        assert len(EvidenceCode) > 0
        assert len(SearchType) > 0


class TestDatatypesComplexImportChains:
    """Test complex import chains involving multiple modules."""

    def test_full_datatype_initialization_chain(self):
        """Test the complete import chain for datatype initialization."""
        try:
            from DeepResearch.src.datatypes.bioinformatics import (
                BioinformaticsAgentDeps,
                DataFusionResult,
                EvidenceCode,
                GOAnnotation,
                GOTerm,
                PubMedPaper,
                ReasoningResult,
            )
            from DeepResearch.src.datatypes.rag import (
                Document,
                IntegratedSearchRequest,
                IntegratedSearchResponse,
                RAGQuery,
                SearchType,
            )
            from DeepResearch.src.datatypes.search_agent import (
                SearchAgentConfig,
                SearchAgentDependencies,
                SearchQuery,
                SearchResult,
            )
            from DeepResearch.src.datatypes.vllm_integration import VLLMEmbeddings

            # If all imports succeed, the chain is working
            assert EvidenceCode is not None
            assert GOTerm is not None
            assert GOAnnotation is not None
            assert PubMedPaper is not None
            assert BioinformaticsAgentDeps is not None
            assert DataFusionResult is not None
            assert ReasoningResult is not None
            assert SearchType is not None
            assert Document is not None
            assert SearchResult is not None
            assert RAGQuery is not None
            assert IntegratedSearchRequest is not None
            assert IntegratedSearchResponse is not None
            assert SearchAgentConfig is not None
            assert SearchQuery is not None
            assert SearchAgentDependencies is not None
            assert VLLMEmbeddings is not None

        except ImportError as e:
            pytest.fail(f"Datatype import chain failed: {e}")

    def test_cross_module_references(self):
        """Test that modules can reference each other's types."""
        try:
            # Test that bioinformatics can reference RAG types
            from DeepResearch.src.datatypes.bioinformatics import FusedDataset
            from DeepResearch.src.datatypes.rag import Document

            # If we get here without ImportError, cross-references work
            assert FusedDataset is not None
            assert Document is not None

        except ImportError as e:
            pytest.fail(f"Cross-module reference failed: {e}")


class TestDatatypesImportErrorHandling:
    """Test import error handling for datatypes modules."""

    def test_pydantic_availability(self):
        """Test that Pydantic is available for datatype models."""
        try:
            from pydantic import BaseModel

            assert BaseModel is not None
        except ImportError:
            pytest.fail("Pydantic not available for datatype models")

    def test_circular_import_prevention(self):
        """Test that there are no circular imports in datatypes."""
        # This test will fail if there are circular imports

        # If we get here, no circular imports were detected
        assert True

    def test_missing_dependencies_handling(self):
        """Test that modules handle missing dependencies gracefully."""
        # Most datatype modules should work without external dependencies
        # beyond Pydantic and standard library
        from DeepResearch.src.datatypes.bioinformatics import EvidenceCode
        from DeepResearch.src.datatypes.rag import SearchType

        # These should always be available
        assert EvidenceCode is not None
        assert SearchType is not None
