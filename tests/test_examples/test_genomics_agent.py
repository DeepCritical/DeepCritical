"""
Tests for genomics agent with MCP server integration.

Following TDD approach with Red → Green → Refactor cycles.
"""

from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel


class TestGenomicsAgentDeps:
    """Test suite for GenomicsAgentDeps dataclass."""

    def test_can_import_genomics_deps(self):
        """Test that GenomicsAgentDeps can be imported."""
        # This will fail until we create genomics_deps.py
        from examples.simple_genomics_discovery.genomics_deps import GenomicsAgentDeps

        assert GenomicsAgentDeps is not None

    def test_create_deps_with_required_fields(self):
        """Test creating GenomicsAgentDeps with all required fields."""
        from examples.simple_genomics_discovery.genomics_deps import GenomicsAgentDeps

        deps = GenomicsAgentDeps(
            data_dir=Path("/data"),
            output_dir=Path("/output"),
            reference_genome=Path("/ref.fasta"),
        )

        assert deps.data_dir == Path("/data")
        assert deps.output_dir == Path("/output")
        assert deps.reference_genome == Path("/ref.fasta")

    def test_deps_optional_fields_have_defaults(self):
        """Test that optional fields have correct default values."""
        from examples.simple_genomics_discovery.genomics_deps import GenomicsAgentDeps

        deps = GenomicsAgentDeps(
            data_dir=Path("/data"),
            output_dir=Path("/output"),
            reference_genome=Path("/ref.fasta"),
        )

        # Default values from 02_implementation_plan.md
        assert isinstance(deps.config, dict)
        assert deps.config == {}
        assert isinstance(deps.tools_called, list)
        assert deps.tools_called == []

    def test_deps_config_field_type(self):
        """Test config field accepts dict[str, Any]."""
        from examples.simple_genomics_discovery.genomics_deps import GenomicsAgentDeps

        config = {"model": "claude-sonnet-4-0", "timeout": 300}
        deps = GenomicsAgentDeps(
            data_dir=Path("/data"),
            output_dir=Path("/output"),
            reference_genome=Path("/ref.fasta"),
            config=config,
        )

        assert deps.config == config
        assert deps.config["model"] == "claude-sonnet-4-0"

    def test_deps_tools_called_tracking(self):
        """Test tools_called list can be appended to."""
        from examples.simple_genomics_discovery.genomics_deps import GenomicsAgentDeps

        deps = GenomicsAgentDeps(
            data_dir=Path("/data"),
            output_dir=Path("/output"),
            reference_genome=Path("/ref.fasta"),
        )

        # Simulate tool tracking
        deps.tools_called.append("fastqc")
        deps.tools_called.append("samtools")

        assert len(deps.tools_called) == 2
        assert "fastqc" in deps.tools_called
        assert "samtools" in deps.tools_called

    def test_deps_paths_are_path_objects(self):
        """Test that all directory fields are Path objects."""
        from examples.simple_genomics_discovery.genomics_deps import GenomicsAgentDeps

        deps = GenomicsAgentDeps(
            data_dir=Path("/data"),
            output_dir=Path("/output"),
            reference_genome=Path("/ref.fasta"),
        )

        assert isinstance(deps.data_dir, Path)
        assert isinstance(deps.output_dir, Path)
        assert isinstance(deps.reference_genome, Path)

    def test_deps_is_dataclass(self):
        """Test that GenomicsAgentDeps is a dataclass."""
        from dataclasses import is_dataclass

        from examples.simple_genomics_discovery.genomics_deps import GenomicsAgentDeps

        assert is_dataclass(GenomicsAgentDeps)


class TestGenomicsAnalysisResult:
    """Test suite for GenomicsAnalysisResult Pydantic model."""

    def test_can_import_analysis_result(self):
        """Test that GenomicsAnalysisResult can be imported."""
        from examples.simple_genomics_discovery.genomics_agent import (
            GenomicsAnalysisResult,
        )

        assert GenomicsAnalysisResult is not None

    def test_analysis_result_is_pydantic_model(self):
        """Test that GenomicsAnalysisResult is a Pydantic BaseModel."""
        from examples.simple_genomics_discovery.genomics_agent import (
            GenomicsAnalysisResult,
        )

        assert issubclass(GenomicsAnalysisResult, BaseModel)

    def test_analysis_result_required_fields(self):
        """Test GenomicsAnalysisResult has all required fields."""
        from examples.simple_genomics_discovery.genomics_agent import (
            GenomicsAnalysisResult,
        )

        # Create with all required fields
        result = GenomicsAnalysisResult(
            analysis_type="qc_only",
            success=True,
            tools_used=["fastqc"],
            output_files={"qc_report": "/path/to/report.html"},
            summary="Quality control completed successfully",
        )

        assert result.analysis_type == "qc_only"
        assert result.success is True
        assert result.tools_used == ["fastqc"]
        assert result.output_files == {"qc_report": "/path/to/report.html"}
        assert result.summary == "Quality control completed successfully"

    def test_analysis_result_optional_fields(self):
        """Test GenomicsAnalysisResult optional fields have None defaults."""
        from examples.simple_genomics_discovery.genomics_agent import (
            GenomicsAnalysisResult,
        )

        result = GenomicsAnalysisResult(
            analysis_type="qc_only",
            success=True,
            tools_used=["fastqc"],
            output_files={},
            summary="Test",
        )

        assert result.error is None
        assert result.variants_found is None

    def test_analysis_result_with_error(self):
        """Test GenomicsAnalysisResult with error field."""
        from examples.simple_genomics_discovery.genomics_agent import (
            GenomicsAnalysisResult,
        )

        result = GenomicsAnalysisResult(
            analysis_type="variant_calling",
            success=False,
            tools_used=[],
            output_files={},
            summary="Failed",
            error="File not found: sample.bam",
        )

        assert result.error == "File not found: sample.bam"
        assert result.success is False

    def test_analysis_result_with_variants(self):
        """Test GenomicsAnalysisResult with variants_found field."""
        from examples.simple_genomics_discovery.genomics_agent import (
            GenomicsAnalysisResult,
        )

        result = GenomicsAnalysisResult(
            analysis_type="variant_calling",
            success=True,
            tools_used=["fastqc", "samtools", "haplotypecaller"],
            output_files={"vcf": "/output/variants.vcf"},
            summary="Found 41 variants",
            variants_found=41,
        )

        assert result.variants_found == 41


class TestGenomicsAgentCreation:
    """Test suite for genomics_agent instantiation."""

    def test_can_import_genomics_agent(self):
        """Test that genomics_agent can be imported."""
        from examples.simple_genomics_discovery.genomics_agent import genomics_agent

        assert genomics_agent is not None

    def test_agent_is_pydantic_ai_agent(self):
        """Test that genomics_agent is a Pydantic AI Agent."""
        from pydantic_ai import Agent

        from examples.simple_genomics_discovery.genomics_agent import genomics_agent

        # Check it's an Agent instance
        assert isinstance(genomics_agent, Agent)

    def test_agent_model_is_claude_sonnet(self):
        """Test that agent uses claude-sonnet-4-0 model (or TestModel in CI)."""
        import os

        from examples.simple_genomics_discovery.genomics_agent import genomics_agent

        # Access agent's model configuration
        model_name = str(genomics_agent.model)
        # In CI (no API key): uses TestModel
        # With API key: uses AnthropicModel
        if os.getenv("ANTHROPIC_API_KEY"):
            assert "Anthropic" in model_name
        else:
            assert "TestModel" in model_name or "Anthropic" in model_name

    def test_agent_has_system_prompt(self):
        """Test that agent has a system prompt."""
        from examples.simple_genomics_discovery.genomics_agent import genomics_agent

        # Agent should have system prompts configured (it's a list)
        assert genomics_agent._system_prompts is not None
        assert len(genomics_agent._system_prompts) > 0

        # Get first system prompt
        system_prompt = str(genomics_agent._system_prompts[0]).lower()

        # System prompt should mention the tools
        assert "fastqc" in system_prompt or "quality control" in system_prompt

    def test_agent_system_prompt_mentions_mcp_servers(self):
        """Test that system prompt references MCP servers."""
        from examples.simple_genomics_discovery.genomics_agent import genomics_agent

        system_prompt = str(genomics_agent._system_prompts[0]).lower()

        # Should mention the MCP server backing
        assert any(
            keyword in system_prompt
            for keyword in ["fastqc", "samtools", "haplotypecaller", "gatk"]
        )


class TestRunGenomicsAnalysis:
    """Test suite for run_genomics_analysis main entry point."""

    def test_can_import_run_genomics_analysis(self):
        """Test that run_genomics_analysis function can be imported."""
        from examples.simple_genomics_discovery.genomics_agent import (
            run_genomics_analysis,
        )

        assert run_genomics_analysis is not None
        assert callable(run_genomics_analysis)

    @pytest.mark.asyncio
    async def test_run_genomics_analysis_signature(self, tmp_path):
        """Test run_genomics_analysis has correct signature."""
        import inspect

        from examples.simple_genomics_discovery.genomics_agent import (
            run_genomics_analysis,
        )

        sig = inspect.signature(run_genomics_analysis)
        params = list(sig.parameters.keys())

        # Should have: prompt, data_dir, output_dir, reference_genome
        assert "prompt" in params
        assert "data_dir" in params
        assert "output_dir" in params
        assert "reference_genome" in params

    @pytest.mark.asyncio
    async def test_run_genomics_analysis_returns_result_model(self, tmp_path):
        """Test that run_genomics_analysis returns GenomicsAnalysisResult."""
        from pathlib import Path
        from unittest.mock import AsyncMock, patch

        from examples.simple_genomics_discovery.genomics_agent import (
            GenomicsAnalysisResult,
            run_genomics_analysis,
        )

        # Setup test paths
        data_dir = tmp_path / "data"
        output_dir = tmp_path / "output"
        ref_genome = tmp_path / "ref.fasta"

        data_dir.mkdir()
        output_dir.mkdir()
        ref_genome.touch()

        # Mock the agent.run to avoid actual API call
        mock_result = AsyncMock()
        mock_result.output = GenomicsAnalysisResult(
            analysis_type="test",
            success=True,
            tools_used=[],
            output_files={},
            summary="Test",
        )

        from examples.simple_genomics_discovery.genomics_agent import genomics_agent

        with patch.object(genomics_agent, "run", return_value=mock_result):
            result = await run_genomics_analysis(
                prompt="Test prompt",
                data_dir=data_dir,
                output_dir=output_dir,
                reference_genome=ref_genome,
            )

            # Should return GenomicsAnalysisResult (using result.output not result.data)
            assert isinstance(result, GenomicsAnalysisResult)

    @pytest.mark.asyncio
    async def test_run_genomics_analysis_creates_deps(self, tmp_path):
        """Test that run_genomics_analysis creates GenomicsAgentDeps correctly."""
        from unittest.mock import AsyncMock, patch

        from examples.simple_genomics_discovery.genomics_agent import (
            GenomicsAnalysisResult,
            genomics_agent,
            run_genomics_analysis,
        )

        data_dir = tmp_path / "data"
        output_dir = tmp_path / "output"
        ref_genome = tmp_path / "ref.fasta"

        data_dir.mkdir()
        output_dir.mkdir()
        ref_genome.touch()

        mock_result = AsyncMock()
        mock_result.output = GenomicsAnalysisResult(
            analysis_type="test",
            success=True,
            tools_used=[],
            output_files={},
            summary="Test",
        )

        with patch.object(genomics_agent, "run", return_value=mock_result) as mock_run:
            await run_genomics_analysis(
                prompt="Test",
                data_dir=data_dir,
                output_dir=output_dir,
                reference_genome=ref_genome,
            )

            # Verify agent.run was called
            mock_run.assert_called_once()

            # Verify deps were created with correct paths
            call_args = mock_run.call_args
            assert call_args[0][0] == "Test"  # prompt
            deps = call_args[1]["deps"]
            assert deps.data_dir == data_dir
            assert deps.output_dir == output_dir
            assert deps.reference_genome == ref_genome
