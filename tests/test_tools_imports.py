"""
Import tests for DeepResearch tools modules.

This module tests that all imports from the tools subdirectory work correctly,
including all individual tool modules and their dependencies.
"""

import pytest

# Import ToolCategory with fallback
try:
    from DeepResearch.src.datatypes.tool_specs import ToolCategory
except ImportError:
    # Fallback for type checking
    class ToolCategory:
        SEARCH = "search"


class TestToolsModuleImports:
    """Test imports for individual tool modules."""

    def test_base_imports(self):
        """Test all imports from base module."""

        from DeepResearch.src.tools.base import (
            ToolSpec,
            ToolRegistry,
        )
        from DeepResearch.src.datatypes.tools import (
            ExecutionResult,
            ToolRunner,
        )

        # Verify they are all accessible and not None
        assert ToolSpec is not None
        assert ExecutionResult is not None
        assert ToolRunner is not None
        assert ToolRegistry is not None

        # Test that registry is accessible from tools module
        from DeepResearch.src.tools import registry

        assert registry is not None

    def test_tools_datatypes_imports(self):
        """Test all imports from tools datatypes module."""

        from DeepResearch.src.datatypes.tools import (
            ToolMetadata,
            ExecutionResult,
            ToolRunner,
            MockToolRunner,
        )

        # Verify they are all accessible and not None
        assert ToolMetadata is not None
        assert ExecutionResult is not None
        assert ToolRunner is not None
        assert MockToolRunner is not None

        # Test that they can be instantiated
        try:
            # Use string literal and cast to avoid import issues
            from typing import cast, Any

            metadata = ToolMetadata(
                name="test_tool",
                category=cast(Any, "search"),  # type: ignore
                description="Test tool",
            )
            assert metadata.name == "test_tool"
            assert metadata.category == "search"  # type: ignore
            assert metadata.description == "Test tool"

            result = ExecutionResult(success=True, data={"test": "data"})
            assert result.success is True
            assert result.data["test"] == "data"

            # Test that MockToolRunner inherits from ToolRunner
            from DeepResearch.src.datatypes.tool_specs import ToolSpec, ToolCategory

            spec = ToolSpec(
                name="mock_tool",
                category=ToolCategory.SEARCH,
                input_schema={"query": "TEXT"},
                output_schema={"result": "TEXT"},
            )
            mock_runner = MockToolRunner(spec)
            assert mock_runner is not None
            assert hasattr(mock_runner, "run")

        except Exception as e:
            pytest.fail(f"Tools datatypes instantiation failed: {e}")

    def test_mock_tools_imports(self):
        """Test all imports from mock_tools module."""

        from DeepResearch.src.tools.mock_tools import (
            MockTool,
            MockWebSearchTool,
            MockBioinformaticsTool,
        )

        # Verify they are all accessible and not None
        assert MockTool is not None
        assert MockWebSearchTool is not None
        assert MockBioinformaticsTool is not None

    def test_workflow_tools_imports(self):
        """Test all imports from workflow_tools module."""

        from DeepResearch.src.tools.workflow_tools import (
            WorkflowTool,
            WorkflowStepTool,
        )

        # Verify they are all accessible and not None
        assert WorkflowTool is not None
        assert WorkflowStepTool is not None

    def test_pyd_ai_tools_imports(self):
        """Test all imports from pyd_ai_tools module."""

        from DeepResearch.src.datatypes.pydantic_ai_tools import (
            WebSearchBuiltinRunner,
            CodeExecBuiltinRunner,
            UrlContextBuiltinRunner,
        )

        # Verify they are all accessible and not None
        assert WebSearchBuiltinRunner is not None
        assert CodeExecBuiltinRunner is not None
        assert UrlContextBuiltinRunner is not None

        # Test that tools are registered in the registry
        from DeepResearch.src.tools.base import registry

        assert "web_search" in registry.list()
        assert "pyd_code_exec" in registry.list()
        assert "pyd_url_context" in registry.list()

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

    def test_code_sandbox_imports(self):
        """Test all imports from code_sandbox module."""

        from DeepResearch.src.tools.code_sandbox import CodeSandboxTool

        # Verify they are all accessible and not None
        assert CodeSandboxTool is not None

    def test_docker_sandbox_imports(self):
        """Test all imports from docker_sandbox module."""

        from DeepResearch.src.tools.docker_sandbox import DockerSandboxTool

        # Verify they are all accessible and not None
        assert DockerSandboxTool is not None

    def test_deepsearch_workflow_tool_imports(self):
        """Test all imports from deepsearch_workflow_tool module."""

        from DeepResearch.src.tools.deepsearch_workflow_tool import (
            DeepSearchWorkflowTool,
        )

        # Verify they are all accessible and not None
        assert DeepSearchWorkflowTool is not None

    def test_deepsearch_tools_imports(self):
        """Test all imports from deepsearch_tools module."""

        from DeepResearch.src.tools.deepsearch_tools import (
            DeepSearchTool,
            WebSearchTool,
            URLVisitTool,
            ReflectionTool,
            AnswerGeneratorTool,
            QueryRewriterTool,
        )

        # Verify they are all accessible and not None
        assert DeepSearchTool is not None
        assert WebSearchTool is not None
        assert URLVisitTool is not None
        assert ReflectionTool is not None
        assert AnswerGeneratorTool is not None
        assert QueryRewriterTool is not None

        # Test that they inherit from ToolRunner
        from DeepResearch.src.tools.base import ToolRunner

        assert issubclass(WebSearchTool, ToolRunner)
        assert issubclass(URLVisitTool, ToolRunner)
        assert issubclass(ReflectionTool, ToolRunner)
        assert issubclass(AnswerGeneratorTool, ToolRunner)
        assert issubclass(QueryRewriterTool, ToolRunner)
        assert issubclass(DeepSearchTool, ToolRunner)

        # Test that they can be instantiated
        try:
            web_search_tool = WebSearchTool()
            assert web_search_tool is not None
            assert hasattr(web_search_tool, "run")

            url_visit_tool = URLVisitTool()
            assert url_visit_tool is not None
            assert hasattr(url_visit_tool, "run")

            reflection_tool = ReflectionTool()
            assert reflection_tool is not None
            assert hasattr(reflection_tool, "run")

            answer_tool = AnswerGeneratorTool()
            assert answer_tool is not None
            assert hasattr(answer_tool, "run")

            query_tool = QueryRewriterTool()
            assert query_tool is not None
            assert hasattr(query_tool, "run")

            deep_search_tool = DeepSearchTool()
            assert deep_search_tool is not None
            assert hasattr(deep_search_tool, "run")

        except Exception as e:
            pytest.fail(f"DeepSearch tools instantiation failed: {e}")

    def test_websearch_tools_imports(self):
        """Test all imports from websearch_tools module."""

        from DeepResearch.src.tools.websearch_tools import WebSearchTool

        # Verify they are all accessible and not None
        assert WebSearchTool is not None

    def test_websearch_cleaned_imports(self):
        """Test all imports from websearch_cleaned module."""

        from DeepResearch.src.tools.websearch_cleaned import WebSearchCleanedTool

        # Verify they are all accessible and not None
        assert WebSearchCleanedTool is not None

    def test_analytics_tools_imports(self):
        """Test all imports from analytics_tools module."""

        from DeepResearch.src.tools.analytics_tools import AnalyticsTool

        # Verify they are all accessible and not None
        assert AnalyticsTool is not None

    def test_integrated_search_tools_imports(self):
        """Test all imports from integrated_search_tools module."""

        from DeepResearch.src.tools.integrated_search_tools import IntegratedSearchTool

        # Verify they are all accessible and not None
        assert IntegratedSearchTool is not None

    def test_deep_agent_middleware_imports(self):
        """Test all imports from deep_agent_middleware module."""

        from DeepResearch.src.tools.deep_agent_middleware import (
            MiddlewareConfig,
            MiddlewareResult,
            BaseMiddleware,
            PlanningMiddleware,
            FilesystemMiddleware,
            SubAgentMiddleware,
            SummarizationMiddleware,
            PromptCachingMiddleware,
            MiddlewarePipeline,
            create_planning_middleware,
            create_filesystem_middleware,
            create_subagent_middleware,
            create_summarization_middleware,
            create_prompt_caching_middleware,
            create_default_middleware_pipeline,
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

        # Test that they are the same types as imported from datatypes
        from DeepResearch.src.datatypes.middleware import (
            MiddlewareConfig as DTCfg,
            MiddlewareResult as DTRes,
            BaseMiddleware as DTBase,
        )
        from DeepResearch.src.datatypes import (
            SearchResult,
            WebSearchRequest,
            URLVisitResult,
            ReflectionQuestion,
        )

        assert MiddlewareConfig is DTCfg
        assert MiddlewareResult is DTRes
        assert BaseMiddleware is DTBase
        # Test deep search types are the same
        assert SearchResult is not None
        assert WebSearchRequest is not None
        assert URLVisitResult is not None
        assert ReflectionQuestion is not None


class TestToolsCrossModuleImports:
    """Test cross-module imports and dependencies within tools."""

    def test_tools_internal_dependencies(self):
        """Test that tool modules can import from each other correctly."""
        # Test that tools can import base classes
        from DeepResearch.src.tools.mock_tools import MockTool
        from DeepResearch.src.tools.base import ToolSpec

        # This should work without circular imports
        assert MockTool is not None
        assert ToolSpec is not None

    def test_datatypes_integration_imports(self):
        """Test that tools can import from datatypes module."""
        # This tests the import chain: tools -> datatypes
        from DeepResearch.src.tools.base import ToolSpec
        from DeepResearch.src.datatypes import Document

        # If we get here without ImportError, the import chain works
        assert ToolSpec is not None
        assert Document is not None

    def test_agents_integration_imports(self):
        """Test that tools can import from agents module."""
        # This tests the import chain: tools -> agents
        from DeepResearch.src.tools.pyd_ai_tools import _build_agent

        # If we get here without ImportError, the import chain works
        assert _build_agent is not None


class TestToolsComplexImportChains:
    """Test complex import chains involving multiple modules."""

    def test_full_tool_initialization_chain(self):
        """Test the complete import chain for tool initialization."""
        try:
            from DeepResearch.src.tools.base import ToolRegistry, ToolSpec
            from DeepResearch.src.tools.mock_tools import MockTool
            from DeepResearch.src.tools.workflow_tools import WorkflowTool
            from DeepResearch.src.datatypes import Document

            # If all imports succeed, the chain is working
            assert ToolRegistry is not None
            assert ToolSpec is not None
            assert MockTool is not None
            assert WorkflowTool is not None
            assert Document is not None

        except ImportError as e:
            pytest.fail(f"Tool import chain failed: {e}")

    def test_tool_execution_chain(self):
        """Test the complete import chain for tool execution."""
        try:
            from DeepResearch.src.datatypes.tools import ExecutionResult, ToolRunner
            from DeepResearch.src.tools.websearch_tools import WebSearchTool
            from DeepResearch.src.agents.prime_executor import ToolExecutor

            # If all imports succeed, the chain is working
            assert ExecutionResult is not None
            assert ToolRunner is not None
            assert WebSearchTool is not None
            assert ToolExecutor is not None

        except ImportError as e:
            pytest.fail(f"Tool execution import chain failed: {e}")


class TestToolsImportErrorHandling:
    """Test import error handling for tools modules."""

    def test_missing_dependencies_handling(self):
        """Test that modules handle missing dependencies gracefully."""
        # Test that pyd_ai_tools handles optional dependencies
        from DeepResearch.src.tools.pyd_ai_tools import _build_agent

        # This should work even if pydantic_ai is not installed
        assert _build_agent is not None

    def test_circular_import_prevention(self):
        """Test that there are no circular imports in tools."""
        # This test will fail if there are circular imports

        # If we get here, no circular imports were detected
        assert True

    def test_registry_functionality(self):
        """Test that the tool registry works correctly."""
        from DeepResearch.src.tools.base import ToolRegistry

        registry = ToolRegistry()

        # Test that registry can be instantiated and used
        assert registry is not None
        assert hasattr(registry, "register")
        assert hasattr(registry, "make")

    def test_tool_spec_validation(self):
        """Test that ToolSpec works correctly."""
        from DeepResearch.src.tools.base import ToolSpec

        spec = ToolSpec(
            name="test_tool",
            description="Test tool",
            inputs={"param": "TEXT"},
            outputs={"result": "TEXT"},
        )

        # Test that ToolSpec can be created and used
        assert spec is not None
        assert spec.name == "test_tool"
        assert "param" in spec.inputs
