"""
Tests for genomics agent tool registration.

These tests verify that agent tools are properly registered and call
MCP server methods (not CLI directly).

Reference: burner_docs/haplotype_agent/02_implementation_plan.md Phase 4
"""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest


class TestAgentToolsRegistered:
    """Test that all tools are registered to the agent."""

    def test_agent_has_tools_registered(self):
        """Test that genomics_agent has tools registered."""
        from examples.simple_genomics_discovery.genomics_agent import genomics_agent

        # Agent should have tools registered
        assert len(genomics_agent._function_toolset.tools) > 0

    def test_run_fastqc_tool_registered(self):
        """Test that run_fastqc tool is registered."""
        from examples.simple_genomics_discovery.genomics_agent import genomics_agent

        # Check tool is in registered functions
        tool_names = [
            tool.name for tool in genomics_agent._function_toolset.tools.values()
        ]
        assert "run_fastqc" in tool_names

    def test_run_samtools_flagstat_tool_registered(self):
        """Test that run_samtools_flagstat tool is registered."""
        from examples.simple_genomics_discovery.genomics_agent import genomics_agent

        tool_names = [
            tool.name for tool in genomics_agent._function_toolset.tools.values()
        ]
        assert "run_samtools_flagstat" in tool_names

    def test_run_haplotypecaller_tool_registered(self):
        """Test that run_haplotypecaller tool is registered."""
        from examples.simple_genomics_discovery.genomics_agent import genomics_agent

        tool_names = [
            tool.name for tool in genomics_agent._function_toolset.tools.values()
        ]
        assert "run_haplotypecaller" in tool_names


class TestRunFastQCTool:
    """Test run_fastqc tool functionality."""

    @pytest.mark.asyncio
    async def test_run_fastqc_calls_mcp_server(self, tmp_path):
        """Test that run_fastqc calls FastQCServer.run_fastqc method."""
        from unittest.mock import AsyncMock

        from examples.simple_genomics_discovery.genomics_agent import (
            fastqc_server,
            genomics_agent,
        )
        from examples.simple_genomics_discovery.genomics_deps import GenomicsAgentDeps

        # Create test deps
        deps = GenomicsAgentDeps(
            data_dir=tmp_path / "data",
            output_dir=tmp_path / "output",
            reference_genome=tmp_path / "ref.fasta",
        )

        # Create dummy BAM file
        deps.data_dir.mkdir()
        (deps.data_dir / "test.bam").touch()

        # Mock the MCP server method
        with patch.object(fastqc_server, "run_fastqc", return_value={"success": True}):
            # Get the tool function
            tools = {
                tool.name: tool
                for tool in genomics_agent._function_toolset.tools.values()
            }
            run_fastqc_tool = tools["run_fastqc"]

            # Create mock context
            mock_ctx = MagicMock()
            mock_ctx.deps = deps

            # Call the tool function
            result = await run_fastqc_tool.function(mock_ctx, "test.bam")

            # Verify MCP server was called
            fastqc_server.run_fastqc.assert_called_once()
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_run_fastqc_tracks_tool_usage(self, tmp_path):
        """Test that run_fastqc appends to tools_called list."""
        from examples.simple_genomics_discovery.genomics_agent import (
            fastqc_server,
            genomics_agent,
        )
        from examples.simple_genomics_discovery.genomics_deps import GenomicsAgentDeps

        deps = GenomicsAgentDeps(
            data_dir=tmp_path / "data",
            output_dir=tmp_path / "output",
            reference_genome=tmp_path / "ref.fasta",
        )

        deps.data_dir.mkdir()
        (deps.data_dir / "test.bam").touch()

        # Initial state
        assert len(deps.tools_called) == 0

        with patch.object(fastqc_server, "run_fastqc", return_value={"success": True}):
            tools = {
                tool.name: tool
                for tool in genomics_agent._function_toolset.tools.values()
            }
            run_fastqc_tool = tools["run_fastqc"]

            mock_ctx = MagicMock()
            mock_ctx.deps = deps

            await run_fastqc_tool.function(mock_ctx, "test.bam")

            # Should have tracked the tool call
            assert "fastqc" in deps.tools_called

    @pytest.mark.asyncio
    async def test_run_fastqc_handles_missing_file(self, tmp_path):
        """Test that run_fastqc handles file not found gracefully."""
        from examples.simple_genomics_discovery.genomics_agent import genomics_agent
        from examples.simple_genomics_discovery.genomics_deps import GenomicsAgentDeps

        deps = GenomicsAgentDeps(
            data_dir=tmp_path / "data",
            output_dir=tmp_path / "output",
            reference_genome=tmp_path / "ref.fasta",
        )

        deps.data_dir.mkdir()
        # DON'T create the BAM file - it's missing

        tools = {
            tool.name: tool for tool in genomics_agent._function_toolset.tools.values()
        }
        run_fastqc_tool = tools["run_fastqc"]

        mock_ctx = MagicMock()
        mock_ctx.deps = deps

        result = await run_fastqc_tool.function(mock_ctx, "missing.bam")

        # Should return error dict
        assert result["success"] is False
        assert "error" in result
        assert "not found" in result["error"].lower()


class TestRunSamtoolsFlagstatTool:
    """Test run_samtools_flagstat tool functionality."""

    @pytest.mark.asyncio
    async def test_run_samtools_flagstat_calls_mcp_server(self, tmp_path):
        """Test that run_samtools_flagstat calls SamtoolsServer.samtools_flagstat method."""
        from examples.simple_genomics_discovery.genomics_agent import (
            genomics_agent,
            samtools_server,
        )
        from examples.simple_genomics_discovery.genomics_deps import GenomicsAgentDeps

        deps = GenomicsAgentDeps(
            data_dir=tmp_path / "data",
            output_dir=tmp_path / "output",
            reference_genome=tmp_path / "ref.fasta",
        )

        deps.data_dir.mkdir()
        (deps.data_dir / "test.bam").touch()

        with patch.object(
            samtools_server, "samtools_flagstat", return_value={"success": True}
        ):
            tools = {
                tool.name: tool
                for tool in genomics_agent._function_toolset.tools.values()
            }
            run_flagstat_tool = tools["run_samtools_flagstat"]

            mock_ctx = MagicMock()
            mock_ctx.deps = deps

            result = await run_flagstat_tool.function(mock_ctx, "test.bam")

            # Verify MCP server was called (not subprocess)
            samtools_server.samtools_flagstat.assert_called_once()
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_run_samtools_flagstat_tracks_usage(self, tmp_path):
        """Test that run_samtools_flagstat tracks tool usage."""
        from examples.simple_genomics_discovery.genomics_agent import (
            genomics_agent,
            samtools_server,
        )
        from examples.simple_genomics_discovery.genomics_deps import GenomicsAgentDeps

        deps = GenomicsAgentDeps(
            data_dir=tmp_path / "data",
            output_dir=tmp_path / "output",
            reference_genome=tmp_path / "ref.fasta",
        )

        deps.data_dir.mkdir()
        (deps.data_dir / "test.bam").touch()

        with patch.object(
            samtools_server, "samtools_flagstat", return_value={"success": True}
        ):
            tools = {
                tool.name: tool
                for tool in genomics_agent._function_toolset.tools.values()
            }
            run_flagstat_tool = tools["run_samtools_flagstat"]

            mock_ctx = MagicMock()
            mock_ctx.deps = deps

            await run_flagstat_tool.function(mock_ctx, "test.bam")

            assert "samtools_flagstat" in deps.tools_called


class TestRunHaplotypeCallerTool:
    """Test run_haplotypecaller tool functionality."""

    @pytest.mark.asyncio
    async def test_run_haplotypecaller_calls_mcp_server(self, tmp_path):
        """Test that run_haplotypecaller calls HaplotypeCallerServer.call_variants method."""
        from examples.simple_genomics_discovery.genomics_agent import (
            genomics_agent,
            haplotypecaller_server,
        )
        from examples.simple_genomics_discovery.genomics_deps import GenomicsAgentDeps

        deps = GenomicsAgentDeps(
            data_dir=tmp_path / "data",
            output_dir=tmp_path / "output",
            reference_genome=tmp_path / "ref.fasta",
        )

        deps.data_dir.mkdir()
        deps.output_dir.mkdir()
        (deps.data_dir / "test.bam").touch()
        deps.reference_genome.touch()

        with patch.object(
            haplotypecaller_server, "call_variants", return_value={"success": True}
        ) as mock_call_variants:
            tools = {
                tool.name: tool
                for tool in genomics_agent._function_toolset.tools.values()
            }
            run_hc_tool = tools["run_haplotypecaller"]

            mock_ctx = MagicMock()
            mock_ctx.deps = deps

            result = await run_hc_tool.function(mock_ctx, "test.bam")

            # Verify MCP server was called (not GATK CLI directly)
            mock_call_variants.assert_called_once()
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_run_haplotypecaller_tracks_usage(self, tmp_path):
        """Test that run_haplotypecaller tracks tool usage."""
        from examples.simple_genomics_discovery.genomics_agent import (
            genomics_agent,
            haplotypecaller_server,
        )
        from examples.simple_genomics_discovery.genomics_deps import GenomicsAgentDeps

        deps = GenomicsAgentDeps(
            data_dir=tmp_path / "data",
            output_dir=tmp_path / "output",
            reference_genome=tmp_path / "ref.fasta",
        )

        deps.data_dir.mkdir()
        deps.output_dir.mkdir()
        (deps.data_dir / "test.bam").touch()
        deps.reference_genome.touch()

        with patch.object(
            haplotypecaller_server, "call_variants", return_value={"success": True}
        ):
            tools = {
                tool.name: tool
                for tool in genomics_agent._function_toolset.tools.values()
            }
            run_hc_tool = tools["run_haplotypecaller"]

            mock_ctx = MagicMock()
            mock_ctx.deps = deps

            await run_hc_tool.function(mock_ctx, "test.bam")

            assert "haplotypecaller" in deps.tools_called

    @pytest.mark.asyncio
    async def test_run_haplotypecaller_handles_missing_reference(self, tmp_path):
        """Test that run_haplotypecaller handles missing reference genome."""
        from examples.simple_genomics_discovery.genomics_agent import genomics_agent
        from examples.simple_genomics_discovery.genomics_deps import GenomicsAgentDeps

        deps = GenomicsAgentDeps(
            data_dir=tmp_path / "data",
            output_dir=tmp_path / "output",
            reference_genome=tmp_path / "missing_ref.fasta",
        )

        deps.data_dir.mkdir()
        deps.output_dir.mkdir()
        (deps.data_dir / "test.bam").touch()
        # DON'T create reference genome

        tools = {
            tool.name: tool for tool in genomics_agent._function_toolset.tools.values()
        }
        run_hc_tool = tools["run_haplotypecaller"]

        mock_ctx = MagicMock()
        mock_ctx.deps = deps

        result = await run_hc_tool.function(mock_ctx, "test.bam")

        # Should return error
        assert result["success"] is False
        assert "error" in result
        assert "not found" in result["error"].lower()
