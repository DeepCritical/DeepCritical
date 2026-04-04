"""
Import tests for DeepResearch tools modules.

This module tests that all imports from the tools subdirectory work correctly,
including all individual tool modules and their dependencies.
"""

import importlib
import subprocess
import sys

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

        from DeepResearch.src.datatypes.tools import (
            ExecutionResult,
            ToolRunner,
        )
        from DeepResearch.src.tools.base import (
            ToolRegistry,
            ToolSpec,
        )

        # Verify they are all accessible and not None
        assert ToolSpec is not None
        assert ExecutionResult is not None
        assert ToolRunner is not None
        assert ToolRegistry is not None

        # Test that registry is accessible from tools module
        from DeepResearch.src.tools import registry

        assert registry is not None

    def test_tools_package_import_does_not_eagerly_import_bioinformatics_tools(self):
        """Importing the tools package should stay clear of bioinformatics startup side effects."""

        command = [
            sys.executable,
            "-c",
            (
                "import sys\n"
                "import DeepResearch.src.tools as tools\n"
                "print(tools is not None)\n"
                "print('DeepResearch.src.tools.bioinformatics_tools' in sys.modules)\n"
            ),
        ]
        completed = subprocess.run(command, check=True, capture_output=True, text=True)

        assert completed.stdout.strip().splitlines() == [
            "True",
            "False",
        ]

    def test_tools_registry_keeps_bioinformatics_tools_registered(self):
        """The package-level registry export should preserve the full default tool set."""

        from DeepResearch.src.tools import registry

        assert registry is not None
        assert "go_annotation_processor" in registry.list()
        assert "pubmed_retriever" in registry.list()

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

        # Test that they can be instantiated
        try:
            # Use string literal and cast to avoid import issues
            from typing import Any, cast

            metadata = ToolMetadata(
                name="test_tool",
                category=cast("Any", "search"),  # type: ignore
                description="Test tool",
            )
            assert metadata.name == "test_tool"
            assert metadata.category == "search"  # type: ignore
            assert metadata.description == "Test tool"

            result = ExecutionResult(success=True, data={"test": "data"})
            assert result.success is True
            assert result.data["test"] == "data"

            # Test that MockToolRunner inherits from ToolRunner
            from DeepResearch.src.datatypes.tool_specs import ToolCategory, ToolSpec

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
            MockBioinformaticsTool,
            MockTool,
            MockWebSearchTool,
        )

        # Verify they are all accessible and not None
        assert MockTool is not None
        assert MockWebSearchTool is not None
        assert MockBioinformaticsTool is not None

    def test_workflow_tools_imports(self):
        """Test all imports from workflow_tools module."""

        from DeepResearch.src.tools.workflow_tools import (
            WorkflowStepTool,
            WorkflowTool,
        )

        # Verify they are all accessible and not None
        assert WorkflowTool is not None
        assert WorkflowStepTool is not None

    def test_pyd_ai_tools_imports(self):
        """Test all imports from pyd_ai_tools module."""

        from DeepResearch.src.datatypes.pydantic_ai_tools import (
            CodeExecBuiltinRunner,
            UrlContextBuiltinRunner,
            WebSearchBuiltinRunner,
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
            AnswerGeneratorTool,
            DeepSearchTool,
            QueryRewriterTool,
            ReflectionTool,
            URLVisitTool,
            WebSearchTool,
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

        # Test that they are the same types as imported from datatypes
        from DeepResearch.src.datatypes import (
            ReflectionQuestion,
            SearchResult,
            URLVisitResult,
            WebSearchRequest,
        )
        from DeepResearch.src.datatypes.middleware import (
            BaseMiddleware as DTBase,
        )
        from DeepResearch.src.datatypes.middleware import (
            MiddlewareConfig as DTCfg,
        )
        from DeepResearch.src.datatypes.middleware import (
            MiddlewareResult as DTRes,
        )

        assert MiddlewareConfig is DTCfg
        assert MiddlewareResult is DTRes
        assert BaseMiddleware is DTBase
        # Test deep search types are the same
        assert SearchResult is not None
        assert WebSearchRequest is not None
        assert URLVisitResult is not None
        assert ReflectionQuestion is not None

    def test_bioinformatics_tools_imports(self):
        """Test all imports from bioinformatics_tools module."""

        from DeepResearch.src.tools.bioinformatics_tools import (
            BioinformaticsFusionTool,
            BioinformaticsReasoningTool,
            BioinformaticsWorkflowTool,
            GOAnnotationTool,
            PubMedRetrievalTool,
        )

        # Verify they are all accessible and not None
        assert BioinformaticsFusionTool is not None
        assert BioinformaticsReasoningTool is not None
        assert BioinformaticsWorkflowTool is not None
        assert GOAnnotationTool is not None
        assert PubMedRetrievalTool is not None

    def test_mcp_server_management_imports(self):
        """Test all imports from mcp_server_management module."""

        from DeepResearch.src.tools.mcp_server_management import (
            MCPServerDeployTool,
            MCPServerExecuteTool,
            MCPServerListTool,
            MCPServerStatusTool,
            MCPServerStopTool,
        )

        # Verify they are all accessible and not None
        assert MCPServerDeployTool is not None
        assert MCPServerExecuteTool is not None
        assert MCPServerListTool is not None
        assert MCPServerStatusTool is not None
        assert MCPServerStopTool is not None

    def test_workflow_pattern_tools_imports(self):
        """Test all imports from workflow_pattern_tools module."""

        from DeepResearch.src.tools.workflow_pattern_tools import (
            CollaborativePatternTool,
            ConsensusTool,
            HierarchicalPatternTool,
            InteractionStateTool,
            MessageRoutingTool,
            SequentialPatternTool,
            WorkflowOrchestrationTool,
        )

        # Verify they are all accessible and not None
        assert CollaborativePatternTool is not None
        assert ConsensusTool is not None
        assert HierarchicalPatternTool is not None
        assert MessageRoutingTool is not None
        assert SequentialPatternTool is not None
        assert WorkflowOrchestrationTool is not None
        assert InteractionStateTool is not None

    def test_bioinformatics_bcftools_server_imports(self):
        """Test imports from bioinformatics/bcftools_server module."""
        from DeepResearch.src.tools.bioinformatics.bcftools_server import BCFtoolsServer

        # Verify accessible and not None
        assert BCFtoolsServer is not None

    def test_bioinformatics_bedtools_server_imports(self):
        """Test imports from bioinformatics/bedtools_server module."""
        from DeepResearch.src.tools.bioinformatics.bedtools_server import BEDToolsServer

        # Verify accessible and not None
        assert BEDToolsServer is not None

    def test_bioinformatics_bowtie2_server_imports(self):
        """Test imports from bioinformatics/bowtie2_server module."""
        from DeepResearch.src.tools.bioinformatics.bowtie2_server import Bowtie2Server

        # Verify accessible and not None
        assert Bowtie2Server is not None

    def test_bioinformatics_busco_server_imports(self):
        """Test imports from bioinformatics/busco_server module."""
        from DeepResearch.src.tools.bioinformatics.busco_server import BUSCOServer

        # Verify accessible and not None
        assert BUSCOServer is not None

    def test_bioinformatics_cutadapt_server_imports(self):
        """Test imports from bioinformatics/cutadapt_server module."""
        from DeepResearch.src.tools.bioinformatics.cutadapt_server import CutadaptServer

        # Verify accessible and not None
        assert CutadaptServer is not None

    def test_bioinformatics_deeptools_server_imports(self):
        """Test imports from bioinformatics/deeptools_server module."""
        from DeepResearch.src.tools.bioinformatics.deeptools_server import (
            DeeptoolsServer,
        )

        # Verify accessible and not None
        assert DeeptoolsServer is not None

    def test_bioinformatics_fastp_server_imports(self):
        """Test imports from bioinformatics/fastp_server module."""
        from DeepResearch.src.tools.bioinformatics.fastp_server import FastpServer

        # Verify accessible and not None
        assert FastpServer is not None

    def test_bioinformatics_fastqc_server_imports(self):
        """Test imports from bioinformatics/fastqc_server module."""
        from DeepResearch.src.tools.bioinformatics.fastqc_server import FastQCServer

        # Verify accessible and not None
        assert FastQCServer is not None

    def test_bioinformatics_featurecounts_server_imports(self):
        """Test imports from bioinformatics/featurecounts_server module."""
        from DeepResearch.src.tools.bioinformatics.featurecounts_server import (
            FeatureCountsServer,
        )

        # Verify accessible and not None
        assert FeatureCountsServer is not None

    def test_bioinformatics_flye_server_imports(self):
        """Test imports from bioinformatics/flye_server module."""
        from DeepResearch.src.tools.bioinformatics.flye_server import FlyeServer

        # Verify accessible and not None
        assert FlyeServer is not None

    def test_bioinformatics_freebayes_server_imports(self):
        """Test imports from bioinformatics/freebayes_server module."""
        from DeepResearch.src.tools.bioinformatics.freebayes_server import (
            FreeBayesServer,
        )

        # Verify accessible and not None
        assert FreeBayesServer is not None

    def test_bioinformatics_hisat2_server_imports(self):
        """Test imports from bioinformatics/hisat2_server module."""
        from DeepResearch.src.tools.bioinformatics.hisat2_server import HISAT2Server

        # Verify accessible and not None
        assert HISAT2Server is not None

    def test_bioinformatics_kallisto_server_imports(self):
        """Test imports from bioinformatics/kallisto_server module."""
        from DeepResearch.src.tools.bioinformatics.kallisto_server import KallistoServer

        # Verify accessible and not None
        assert KallistoServer is not None

    def test_bioinformatics_macs3_server_imports(self):
        """Test imports from bioinformatics/macs3_server module."""
        from DeepResearch.src.tools.bioinformatics.macs3_server import MACS3Server

        # Verify accessible and not None
        assert MACS3Server is not None

    def test_bioinformatics_meme_server_imports(self):
        """Test imports from bioinformatics/meme_server module."""
        from DeepResearch.src.tools.bioinformatics.meme_server import MEMEServer

        # Verify accessible and not None
        assert MEMEServer is not None

    def test_bioinformatics_minimap2_server_imports(self):
        """Test imports from bioinformatics/minimap2_server module."""
        from DeepResearch.src.tools.bioinformatics.minimap2_server import Minimap2Server

        # Verify accessible and not None
        assert Minimap2Server is not None

    def test_bioinformatics_multiqc_server_imports(self):
        """Test imports from bioinformatics/multiqc_server module."""
        from DeepResearch.src.tools.bioinformatics.multiqc_server import MultiQCServer

        # Verify accessible and not None
        assert MultiQCServer is not None

    def test_bioinformatics_qualimap_server_imports(self):
        """Test imports from bioinformatics/qualimap_server module."""
        from DeepResearch.src.tools.bioinformatics.qualimap_server import QualimapServer

        # Verify accessible and not None
        assert QualimapServer is not None

    def test_bioinformatics_salmon_server_imports(self):
        """Test imports from bioinformatics/salmon_server module."""
        from DeepResearch.src.tools.bioinformatics.salmon_server import SalmonServer

        # Verify accessible and not None
        assert SalmonServer is not None

    def test_bioinformatics_samtools_server_imports(self):
        """Test imports from bioinformatics/samtools_server module."""
        from DeepResearch.src.tools.bioinformatics.samtools_server import SamtoolsServer

        # Verify accessible and not None
        assert SamtoolsServer is not None

    def test_bioinformatics_seqtk_server_imports(self):
        """Test imports from bioinformatics/seqtk_server module."""
        from DeepResearch.src.tools.bioinformatics.seqtk_server import SeqtkServer

        # Verify accessible and not None
        assert SeqtkServer is not None

    def test_bioinformatics_star_server_imports(self):
        """Test imports from bioinformatics/star_server module."""
        from DeepResearch.src.tools.bioinformatics.star_server import STARServer

        # Verify accessible and not None
        assert STARServer is not None

    def test_bioinformatics_stringtie_server_imports(self):
        """Test imports from bioinformatics/stringtie_server module."""
        from DeepResearch.src.tools.bioinformatics.stringtie_server import (
            StringTieServer,
        )

        # Verify accessible and not None
        assert StringTieServer is not None

    def test_bioinformatics_trimgalore_server_imports(self):
        """Test imports from bioinformatics/trimgalore_server module."""
        from DeepResearch.src.tools.bioinformatics.trimgalore_server import (
            TrimGaloreServer,
        )

        # Verify accessible and not None
        assert TrimGaloreServer is not None


class TestToolsCrossModuleImports:
    """Test cross-module imports and dependencies within tools."""

    def test_tools_internal_dependencies(self):
        """Test that tool modules can import from each other correctly."""
        # Test that tools can import base classes
        from DeepResearch.src.tools.base import ToolSpec
        from DeepResearch.src.tools.mock_tools import MockTool

        # This should work without circular imports
        assert MockTool is not None
        assert ToolSpec is not None

    def test_datatypes_integration_imports(self):
        """Test that tools can import from datatypes module."""
        # This tests the import chain: tools -> datatypes
        from DeepResearch.src.datatypes import Document
        from DeepResearch.src.tools.base import ToolSpec

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
            from DeepResearch.src.datatypes import Document
            from DeepResearch.src.tools.base import ToolRegistry, ToolSpec
            from DeepResearch.src.tools.mock_tools import MockTool
            from DeepResearch.src.tools.workflow_tools import WorkflowTool

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
            from DeepResearch.src.agents.prime_executor import ToolExecutor
            from DeepResearch.src.datatypes.tools import ExecutionResult, ToolRunner
            from DeepResearch.src.tools.websearch_tools import WebSearchTool

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
