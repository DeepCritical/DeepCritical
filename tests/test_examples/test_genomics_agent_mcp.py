"""
MCP Server Integration Tests for Genomics Agent.

Tests that verify the genomics agent correctly imports and integrates
with existing MCP servers (FastQCServer, SamtoolsServer, HaplotypeCallerServer).

Reference: burner_docs/haplotype_agent/04_testing_strategy.md
"""

import pytest


class TestMCPServerIntegration:
    """Test suite for MCP server integration in genomics agent."""

    def test_can_import_genomics_agent_module(self):
        """Test that genomics_agent module can be imported."""
        # This will fail until we create genomics_agent.py
        from examples.simple_genomics_discovery import genomics_agent

        assert genomics_agent is not None

    def test_fastqc_server_exists(self):
        """Verify FastQCServer is instantiated in genomics_agent."""
        from examples.simple_genomics_discovery.genomics_agent import fastqc_server

        assert fastqc_server is not None

    def test_fastqc_server_has_run_fastqc_method(self):
        """Verify FastQCServer has run_fastqc method."""
        from examples.simple_genomics_discovery.genomics_agent import fastqc_server

        assert hasattr(fastqc_server, "run_fastqc")
        assert callable(fastqc_server.run_fastqc)

    def test_samtools_server_exists(self):
        """Verify SamtoolsServer is instantiated in genomics_agent."""
        from examples.simple_genomics_discovery.genomics_agent import samtools_server

        assert samtools_server is not None

    def test_samtools_server_has_samtools_flagstat_method(self):
        """Verify SamtoolsServer has samtools_flagstat method."""
        from examples.simple_genomics_discovery.genomics_agent import samtools_server

        assert hasattr(samtools_server, "samtools_flagstat")
        assert callable(samtools_server.samtools_flagstat)

    def test_haplotypecaller_server_exists(self):
        """Verify HaplotypeCallerServer is instantiated in genomics_agent."""
        from examples.simple_genomics_discovery.genomics_agent import (
            haplotypecaller_server,
        )

        assert haplotypecaller_server is not None

    def test_haplotypecaller_server_has_call_variants_method(self):
        """Verify HaplotypeCallerServer has call_variants method."""
        from examples.simple_genomics_discovery.genomics_agent import (
            haplotypecaller_server,
        )

        assert hasattr(haplotypecaller_server, "call_variants")
        assert callable(haplotypecaller_server.call_variants)

    def test_all_mcp_servers_imported_from_deepresearch(self):
        """Verify MCP servers are imported from DeepResearch package."""
        # Import the module to trigger server instantiation
        # Verify server types match expected MCP server classes
        from DeepResearch.src.tools.bioinformatics.fastqc_server import FastQCServer
        from DeepResearch.src.tools.bioinformatics.haplotypecaller_server import (
            HaplotypeCallerServer,
        )
        from DeepResearch.src.tools.bioinformatics.samtools_server import SamtoolsServer
        from examples.simple_genomics_discovery import genomics_agent

        assert isinstance(genomics_agent.fastqc_server, FastQCServer)
        assert isinstance(genomics_agent.samtools_server, SamtoolsServer)
        assert isinstance(genomics_agent.haplotypecaller_server, HaplotypeCallerServer)
