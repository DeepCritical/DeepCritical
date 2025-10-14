"""
Seqtk MCP server component tests.

Tests for the comprehensive Seqtk bioinformatics server that integrates with Pydantic AI.
These tests validate all MCP tool functions for FASTA/Q processing operations.
"""

from pathlib import Path
from typing import Any

import pytest

from tests.test_bioinformatics_tools.base.test_base_tool import (
    BaseBioinformaticsToolTest,
)

# Import the MCP module to test MCP functionality
try:
    from DeepResearch.src.tools.bioinformatics.seqtk_server import SeqtkServer

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    SeqtkServer = None  # type: ignore[assignment]


class TestSeqtkServer(BaseBioinformaticsToolTest):
    """Test Seqtk server functionality."""

    @property
    def tool_name(self) -> str:
        return "seqtk-server"

    @property
    def tool_class(self):
        if not MCP_AVAILABLE:
            pytest.skip("Seqtk MCP server not available")
        return SeqtkServer

    @property
    def required_parameters(self) -> dict[str, Any]:
        return {
            "operation": "sample",
            "input_file": "path/to/sequences.fa",
            "fraction": 0.1,
            "output_file": "path/to/sampled.fa",
        }

    @pytest.fixture
    def sample_fasta_file(self, tmp_path: Path) -> Path:
        """Create sample FASTA file for testing."""
        fasta_file = tmp_path / "sequences.fa"

        # Create mock FASTA file with multiple sequences
        fasta_file.write_text(
            ">seq1 description\n"
            "ATCGATCGATCGATCGATCGATCGATCGATCGATCG\n"
            ">seq2 description\n"
            "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTA\n"
            ">seq3 description\n"
            "TTTTAAAAAGGGGCCCCTTATAGCGCGATATATAT\n"
        )

        return fasta_file

    @pytest.fixture
    def sample_fastq_file(self, tmp_path: Path) -> Path:
        """Create sample FASTQ file for testing."""
        fastq_file = tmp_path / "reads.fq"

        # Create mock FASTQ file with quality scores
        fastq_file.write_text(
            "@read1\n"
            "ATCGATCGATCGATCGATCGATCGATCGATCGATCG\n"
            "+\n"
            "IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII\n"
            "@read2\n"
            "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTA\n"
            "+\n"
            "IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII\n"
        )

        return fastq_file

    @pytest.fixture
    def sample_region_file(self, tmp_path: Path) -> Path:
        """Create sample region file for subseq testing."""
        region_file = tmp_path / "regions.txt"

        # Create region file with sequence names and ranges
        region_file.write_text("seq1\nseq2:5-15\n")

        return region_file

    @pytest.fixture
    def sample_gapped_fasta_file(self, tmp_path: Path) -> Path:
        """Create sample FASTA file with gaps for cutN testing."""
        gapped_file = tmp_path / "gapped.fa"
        gapped_file.write_text(">seq_with_gaps\nATCGATCGNNNNNNNNNNGCTAGCTAGCTAGCTA\n")
        return gapped_file

    @pytest.fixture
    def sample_interleaved_fastq_file(self, tmp_path: Path) -> Path:
        """Create sample interleaved FASTQ file for dropse testing."""
        interleaved_file = tmp_path / "interleaved.fq"
        interleaved_file.write_text(
            "@read1\n"
            "ATCGATCGATCGATCGATCGATCGATCGATCGATCG\n"
            "+\n"
            "IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII\n"
            "@read1\n"
            "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTA\n"
            "+\n"
            "IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII\n"
        )
        return interleaved_file

    @pytest.fixture
    def sample_input_files(
        self, sample_fasta_file: Path, sample_fastq_file: Path, sample_region_file: Path
    ) -> dict[str, Path]:
        """Create sample input files for testing."""
        return {
            "fasta_file": sample_fasta_file,
            "fastq_file": sample_fastq_file,
            "region_file": sample_region_file,
        }

    @pytest.mark.optional
    def test_seqtk_seq_conversion(
        self, tool_instance, sample_fasta_file: Path, sample_output_dir: Path
    ) -> None:
        """Test Seqtk seq format conversion functionality."""
        params = {
            "operation": "seq",
            "input_file": str(sample_fasta_file),
            "output_file": str(sample_output_dir / "converted.fq"),
            "convert_to_fastq": True,
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "command_executed" in result
        assert "output_files" in result

        # Skip file checks for mock results
        if result.get("mock"):
            assert "mock" in result
            return

        # Verify output file was created
        assert Path(result["output_files"][0]).exists()

    @pytest.mark.optional
    def test_seqtk_seq_trimming(
        self, tool_instance, sample_fasta_file: Path, sample_output_dir: Path
    ) -> None:
        """Test Seqtk seq trimming functionality."""
        params = {
            "operation": "seq",
            "input_file": str(sample_fasta_file),
            "output_file": str(sample_output_dir / "trimmed.fa"),
            "trim_left": 5,
            "trim_right": 3,
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "command_executed" in result

        # Skip file checks for mock results
        if result.get("mock"):
            return

    @pytest.mark.optional
    def test_seqtk_fqchk_quality_stats(
        self, tool_instance, sample_fastq_file: Path, sample_output_dir: Path
    ) -> None:
        """Test Seqtk fqchk quality statistics functionality."""
        params = {
            "operation": "fqchk",
            "input_file": str(sample_fastq_file),
            "output_file": str(sample_output_dir / "quality_stats.txt"),
            "quality_encoding": "sanger",
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "command_executed" in result

        # Skip file checks for mock results
        if result.get("mock"):
            return

    @pytest.mark.optional
    def test_seqtk_sample(
        self, tool_instance, sample_fasta_file: Path, sample_output_dir: Path
    ) -> None:
        """Test Seqtk sample functionality."""
        params = {
            "operation": "sample",
            "input_file": str(sample_fasta_file),
            "fraction": 0.5,
            "output_file": str(sample_output_dir / "sampled.fa"),
            "seed": 42,
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "output_files" in result

        # Skip file checks for mock results
        if result.get("mock"):
            return

    @pytest.mark.optional
    def test_seqtk_subseq_extraction(
        self,
        tool_instance,
        sample_fasta_file: Path,
        sample_region_file: Path,
        sample_output_dir: Path,
    ) -> None:
        """Test Seqtk subseq extraction functionality."""
        params = {
            "operation": "subseq",
            "input_file": str(sample_fasta_file),
            "region_file": str(sample_region_file),
            "output_file": str(sample_output_dir / "extracted.fa"),
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "output_files" in result

        # Skip file checks for mock results
        if result.get("mock"):
            return

    @pytest.mark.optional
    def test_seqtk_mergepe_paired_end(
        self, tool_instance, sample_fastq_file: Path, sample_output_dir: Path
    ) -> None:
        """Test Seqtk mergepe paired-end merging functionality."""
        # Create a second read file for paired-end testing
        read2_file = sample_output_dir / "read2.fq"
        read2_file.write_text(
            "@read1\n"
            "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTA\n"
            "+\n"
            "IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII\n"
        )

        params = {
            "operation": "mergepe",
            "read1_file": str(sample_fastq_file),
            "read2_file": str(read2_file),
            "output_file": str(sample_output_dir / "interleaved.fq"),
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "output_files" in result

        # Skip file checks for mock results
        if result.get("mock"):
            return

    @pytest.mark.optional
    def test_seqtk_comp_composition(
        self, tool_instance, sample_fasta_file: Path, sample_output_dir: Path
    ) -> None:
        """Test Seqtk comp base composition functionality."""
        params = {
            "operation": "comp",
            "input_file": str(sample_fasta_file),
            "output_file": str(sample_output_dir / "composition.txt"),
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "command_executed" in result

        # Skip file checks for mock results
        if result.get("mock"):
            return

    @pytest.mark.optional
    def test_seqtk_trimfq_quality_trimming(
        self, tool_instance, sample_fastq_file: Path, sample_output_dir: Path
    ) -> None:
        """Test Seqtk trimfq quality trimming functionality."""
        params = {
            "operation": "trimfq",
            "input_file": str(sample_fastq_file),
            "output_file": str(sample_output_dir / "trimmed.fq"),
            "quality_threshold": 20,
            "window_size": 4,
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "output_files" in result

        # Skip file checks for mock results
        if result.get("mock"):
            return

    @pytest.mark.optional
    def test_seqtk_hety_heterozygosity(
        self, tool_instance, sample_fasta_file: Path, sample_output_dir: Path
    ) -> None:
        """Test Seqtk hety heterozygosity analysis functionality."""
        params = {
            "operation": "hety",
            "input_file": str(sample_fasta_file),
            "output_file": str(sample_output_dir / "heterozygosity.txt"),
            "window_size": 100,
            "step_size": 50,
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "command_executed" in result

        # Skip file checks for mock results
        if result.get("mock"):
            return

    @pytest.mark.optional
    def test_seqtk_mutfa_mutation(
        self, tool_instance, sample_fasta_file: Path, sample_output_dir: Path
    ) -> None:
        """Test Seqtk mutfa point mutation functionality."""
        params = {
            "operation": "mutfa",
            "input_file": str(sample_fasta_file),
            "output_file": str(sample_output_dir / "mutated.fa"),
            "mutation_rate": 0.01,
            "seed": 123,
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "output_files" in result

        # Skip file checks for mock results
        if result.get("mock"):
            return

    @pytest.mark.optional
    def test_seqtk_mergefa_file_merging(
        self, tool_instance, sample_fasta_file: Path, sample_output_dir: Path
    ) -> None:
        """Test Seqtk mergefa file merging functionality."""
        # Create a second FASTA file to merge
        fasta2_file = sample_output_dir / "sequences2.fa"
        fasta2_file.write_text(
            ">seq4 description\nCCCCGGGGAAAATTTTGGGGAAAATTTTCCCCGGGG\n"
        )

        params = {
            "operation": "mergefa",
            "input_files": [str(sample_fasta_file), str(fasta2_file)],
            "output_file": str(sample_output_dir / "merged.fa"),
            "force": False,
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "output_files" in result

        # Skip file checks for mock results
        if result.get("mock"):
            return

    @pytest.mark.optional
    def test_seqtk_dropse_paired_filtering(
        self,
        tool_instance,
        sample_interleaved_fastq_file: Path,
        sample_output_dir: Path,
    ) -> None:
        """Test Seqtk dropse unpaired read filtering functionality."""
        params = {
            "operation": "dropse",
            "input_file": str(sample_interleaved_fastq_file),
            "output_file": str(sample_output_dir / "filtered.fq"),
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "output_files" in result

        # Skip file checks for mock results
        if result.get("mock"):
            return

    @pytest.mark.optional
    def test_seqtk_rename_header_renaming(
        self, tool_instance, sample_fasta_file: Path, sample_output_dir: Path
    ) -> None:
        """Test Seqtk rename header renaming functionality."""
        params = {
            "operation": "rename",
            "input_file": str(sample_fasta_file),
            "output_file": str(sample_output_dir / "renamed.fa"),
            "prefix": "sample_",
            "start_number": 1,
            "keep_original": True,
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "output_files" in result

        # Skip file checks for mock results
        if result.get("mock"):
            return

    @pytest.mark.optional
    def test_seqtk_cutN_gap_splitting(
        self, tool_instance, sample_gapped_fasta_file: Path, sample_output_dir: Path
    ) -> None:
        """Test Seqtk cutN gap splitting functionality."""
        params = {
            "operation": "cutN",
            "input_file": str(sample_gapped_fasta_file),
            "output_file": str(sample_output_dir / "cut.fa"),
            "min_n_length": 5,
            "gap_fraction": 0.5,
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "output_files" in result

        # Skip file checks for mock results
        if result.get("mock"):
            return

    @pytest.mark.optional
    def test_invalid_operation(self, tool_instance) -> None:
        """Test handling of invalid operations."""
        params = {
            "operation": "invalid_operation",
        }

        result = tool_instance.run(params)

        assert result["success"] is False
        assert "error" in result
        assert "Unsupported operation" in result["error"]

    @pytest.mark.optional
    def test_missing_operation_parameter(self, tool_instance) -> None:
        """Test handling of missing operation parameter."""
        params = {
            "input_file": "test.fa",
        }

        result = tool_instance.run(params)

        assert result["success"] is False
        assert "error" in result
        assert "Missing 'operation' parameter" in result["error"]

    @pytest.mark.optional
    def test_file_not_found_error(self, tool_instance, sample_output_dir: Path) -> None:
        """Test handling of file not found errors."""
        params = {
            "operation": "seq",
            "input_file": "/nonexistent/file.fa",
            "output_file": str(sample_output_dir / "output.fa"),
        }

        result = tool_instance.run(params)

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.optional
    def test_parameter_validation_errors(
        self, tool_instance, sample_fasta_file: Path, sample_output_dir: Path
    ) -> None:
        """Test parameter validation for various operations."""
        # Test invalid fraction for sampling
        params = {
            "operation": "sample",
            "input_file": str(sample_fasta_file),
            "fraction": -0.1,
            "output_file": str(sample_output_dir / "output.fa"),
        }

        result = tool_instance.run(params)

        assert result["success"] is False
        assert "error" in result

        # Test invalid quality encoding for fqchk
        params = {
            "operation": "fqchk",
            "input_file": str(sample_fasta_file),
            "quality_encoding": "invalid",
            "output_file": str(sample_output_dir / "output.txt"),
        }

        result = tool_instance.run(params)

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.optional
    def test_server_info_and_tools(self, tool_instance) -> None:
        """Test server information and available tools."""
        if not MCP_AVAILABLE:
            pytest.skip("MCP server not available")

        # Test server info
        server_info = tool_instance.get_server_info()
        assert isinstance(server_info, dict)
        assert "name" in server_info
        assert "tools" in server_info
        assert server_info["name"] == "seqtk-server"

        # Test available tools
        tools = tool_instance.list_tools()
        assert isinstance(tools, list)
        assert len(tools) > 0

        # Check that all expected operations are available
        expected_tools = [
            "seqtk_seq",
            "seqtk_fqchk",
            "seqtk_subseq",
            "seqtk_sample",
            "seqtk_mergepe",
            "seqtk_comp",
            "seqtk_trimfq",
            "seqtk_hety",
            "seqtk_mutfa",
            "seqtk_mergefa",
            "seqtk_dropse",
            "seqtk_rename",
            "seqtk_cutN",
        ]

        for tool_name in expected_tools:
            assert tool_name in tools

    @pytest.mark.optional
    def test_seqtk_seq_reverse_complement(
        self, tool_instance, sample_fasta_file: Path, sample_output_dir: Path
    ) -> None:
        """Test Seqtk seq reverse complement functionality."""
        params = {
            "operation": "seq",
            "input_file": str(sample_fasta_file),
            "output_file": str(sample_output_dir / "revcomp.fa"),
            "reverse_complement": True,
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "command_executed" in result

        # Skip file checks for mock results
        if result.get("mock"):
            return

    @pytest.mark.optional
    def test_seqtk_seq_length_filtering(
        self, tool_instance, sample_fasta_file: Path, sample_output_dir: Path
    ) -> None:
        """Test Seqtk seq length filtering functionality."""
        params = {
            "operation": "seq",
            "input_file": str(sample_fasta_file),
            "output_file": str(sample_output_dir / "filtered.fa"),
            "min_length": 20,
            "max_length": 50,
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "command_executed" in result

        # Skip file checks for mock results
        if result.get("mock"):
            return

    @pytest.mark.optional
    def test_seqtk_sample_two_pass(
        self, tool_instance, sample_fasta_file: Path, sample_output_dir: Path
    ) -> None:
        """Test Seqtk sample with two-pass algorithm."""
        params = {
            "operation": "sample",
            "input_file": str(sample_fasta_file),
            "fraction": 0.8,
            "output_file": str(sample_output_dir / "two_pass_sampled.fa"),
            "seed": 12345,
            "two_pass": True,
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "output_files" in result

        # Skip file checks for mock results
        if result.get("mock"):
            return

    @pytest.mark.optional
    def test_seqtk_subseq_with_options(
        self,
        tool_instance,
        sample_fasta_file: Path,
        sample_region_file: Path,
        sample_output_dir: Path,
    ) -> None:
        """Test Seqtk subseq with additional options."""
        params = {
            "operation": "subseq",
            "input_file": str(sample_fasta_file),
            "region_file": str(sample_region_file),
            "output_file": str(sample_output_dir / "extracted_options.fa"),
            "uppercase": True,
            "reverse_complement": True,
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "output_files" in result

        # Skip file checks for mock results
        if result.get("mock"):
            return

    @pytest.mark.optional
    def test_seqtk_mergefa_force_merge(
        self, tool_instance, sample_fasta_file: Path, sample_output_dir: Path
    ) -> None:
        """Test Seqtk mergefa with force merge option."""
        # Create a second FASTA file with conflicting sequence names
        fasta2_file = sample_output_dir / "conflicting.fa"
        fasta2_file.write_text(
            ">seq1 duplicate\n"  # Same name as in sample_fasta_file
            "AAAAAAAAGGGGCCCCTTATAGCGCGATATATAT\n"
        )

        params = {
            "operation": "mergefa",
            "input_files": [str(sample_fasta_file), str(fasta2_file)],
            "output_file": str(sample_output_dir / "force_merged.fa"),
            "force": True,
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "output_files" in result

        # Skip file checks for mock results
        if result.get("mock"):
            return

    @pytest.mark.optional
    def test_seqtk_mutfa_transitions_only(
        self, tool_instance, sample_fasta_file: Path, sample_output_dir: Path
    ) -> None:
        """Test Seqtk mutfa with transitions only option."""
        params = {
            "operation": "mutfa",
            "input_file": str(sample_fasta_file),
            "output_file": str(sample_output_dir / "transitions.fa"),
            "mutation_rate": 0.05,
            "seed": 98765,
            "transitions_only": True,
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "output_files" in result

        # Skip file checks for mock results
        if result.get("mock"):
            return

    @pytest.mark.optional
    def test_seqtk_rename_without_prefix(
        self, tool_instance, sample_fasta_file: Path, sample_output_dir: Path
    ) -> None:
        """Test Seqtk rename without prefix."""
        params = {
            "operation": "rename",
            "input_file": str(sample_fasta_file),
            "output_file": str(sample_output_dir / "numbered.fa"),
            "start_number": 100,
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "output_files" in result

        # Skip file checks for mock results
        if result.get("mock"):
            return

    @pytest.mark.optional
    def test_seqtk_comp_stdout_output(
        self, tool_instance, sample_fasta_file: Path
    ) -> None:
        """Test Seqtk comp with stdout output (no output file)."""
        params = {
            "operation": "comp",
            "input_file": str(sample_fasta_file),
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "command_executed" in result
        assert "stdout" in result

        # Skip file checks for mock results
        if result.get("mock"):
            return
