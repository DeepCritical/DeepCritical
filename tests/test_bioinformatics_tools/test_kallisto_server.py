"""
Kallisto server component tests.

Tests for the improved Kallisto server with FastMCP integration, Pydantic AI MCP support,
and comprehensive bioinformatics functionality. Includes RNA-seq quantification, index building,
single-cell BUS file generation, and utility functions.
"""

from pathlib import Path

import pytest

from tests.test_bioinformatics_tools.base.test_base_tool import (
    BaseBioinformaticsToolTest,
)
from tests.utils.mocks.mock_data import (
    create_mock_fasta,
    create_mock_fastq,
    create_mock_fastq_paired,
)

# Import the MCP module to test MCP functionality
try:
    import DeepResearch.src.tools.bioinformatics.kallisto_server as kallisto_server_module

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    kallisto_server_module = None  # type: ignore[assignment]

# Check if kallisto is available on the system
import shutil

KALLISTO_AVAILABLE = shutil.which("kallisto") is not None


class TestKallistoServer(BaseBioinformaticsToolTest):
    """Test Kallisto server functionality with FastMCP and Pydantic AI integration."""

    @property
    def tool_name(self) -> str:
        return "kallisto-server"

    @property
    def tool_class(self):
        if not KALLISTO_AVAILABLE:
            pytest.skip("Kallisto not available on system")
        # Import the actual Kallisto server class
        from DeepResearch.src.tools.bioinformatics.kallisto_server import KallistoServer

        return KallistoServer

    @property
    def required_parameters(self) -> dict:
        """Required parameters for backward compatibility testing."""
        return {
            "fasta_files": ["path/to/transcripts.fa"],  # Updated parameter name
            "index": "path/to/index",  # Updated parameter name
            "operation": "index",  # For legacy run() method
        }

    @pytest.fixture
    def test_config(self):
        """Test configuration fixture."""
        import os

        return {
            "docker_enabled": os.getenv("DOCKER_TESTS", "false").lower() == "true",
            "mcp_enabled": MCP_AVAILABLE,
            "kallisto_available": KALLISTO_AVAILABLE,
        }

    @pytest.fixture
    def sample_input_files(self, tmp_path):
        """Create sample FASTA and FASTQ files for testing."""
        # Create reference transcriptome FASTA
        transcripts_file = tmp_path / "transcripts.fa"
        create_mock_fasta(transcripts_file, num_sequences=10)

        # Create single-end reads FASTQ
        single_end_reads = tmp_path / "single_reads.fq"
        create_mock_fastq(single_end_reads, num_reads=1000)

        # Create paired-end reads
        paired_reads_1 = tmp_path / "paired_reads_1.fq"
        paired_reads_2 = tmp_path / "paired_reads_2.fq"
        create_mock_fastq_paired(paired_reads_1, paired_reads_2, num_reads=1000)

        # Create TCC matrix file (mock)
        tcc_matrix = tmp_path / "tcc_matrix.mtx"
        tcc_matrix.write_text(
            "%%MatrixMarket matrix coordinate real general\n3 2 4\n1 1 1.0\n1 2 2.0\n2 1 3.0\n3 1 4.0\n"
        )

        return {
            "transcripts_file": transcripts_file,
            "single_end_reads": single_end_reads,
            "paired_reads_1": paired_reads_1,
            "paired_reads_2": paired_reads_2,
            "tcc_matrix": tcc_matrix,
        }

    @pytest.mark.optional
    def test_kallisto_index_legacy(
        self, tool_instance, sample_input_files, sample_output_dir
    ):
        """Test Kallisto index functionality using legacy run() method."""
        params = {
            "operation": "index",
            "fasta_files": [str(sample_input_files["transcripts_file"])],
            "index": str(sample_output_dir / "kallisto_index"),
            "kmer_size": 31,
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "output_files" in result
        assert "command_executed" in result
        assert "kallisto index" in result["command_executed"]

        # Skip file checks for mock results
        if result.get("mock"):
            return

        # Check that index file was created
        index_file = sample_output_dir / "kallisto_index"
        assert index_file.exists()

    @pytest.mark.optional
    def test_kallisto_index_direct(
        self, tool_instance, sample_input_files, sample_output_dir
    ):
        """Test Kallisto index functionality using direct method call."""
        result = tool_instance.kallisto_index(
            fasta_files=[sample_input_files["transcripts_file"]],
            index=sample_output_dir / "kallisto_index_direct",
            kmer_size=31,
            make_unique=True,
        )

        assert "command_executed" in result
        assert "output_files" in result
        assert "kallisto index" in result["command_executed"]
        assert len(result["output_files"]) > 0

        # Skip file checks for mock results
        if result.get("mock"):
            return

    @pytest.mark.optional
    def test_kallisto_quant_legacy_paired_end(
        self, tool_instance, sample_input_files, sample_output_dir
    ):
        """Test Kallisto quant functionality for paired-end reads using legacy run() method."""
        # First create an index
        index_file = sample_output_dir / "kallisto_index"
        tool_instance.kallisto_index(
            fasta_files=[sample_input_files["transcripts_file"]],
            index=index_file,
            kmer_size=31,
        )

        params = {
            "operation": "quant",
            "fastq_files": [
                str(sample_input_files["paired_reads_1"]),
                str(sample_input_files["paired_reads_2"]),
            ],
            "index": str(index_file),
            "output_dir": str(sample_output_dir / "quant_pe"),
            "threads": 1,
            "bootstrap_samples": 0,
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "output_files" in result
        assert "command_executed" in result
        assert "kallisto quant" in result["command_executed"]

        # Skip file checks for mock results
        if result.get("mock"):
            return

    @pytest.mark.optional
    def test_kallisto_quant_legacy_single_end(
        self, tool_instance, sample_input_files, sample_output_dir
    ):
        """Test Kallisto quant functionality for single-end reads using legacy run() method."""
        # First create an index
        index_file = sample_output_dir / "kallisto_index_se"
        tool_instance.kallisto_index(
            fasta_files=[sample_input_files["transcripts_file"]],
            index=index_file,
            kmer_size=31,
        )

        params = {
            "operation": "quant",
            "fastq_files": [str(sample_input_files["single_end_reads"])],
            "index": str(index_file),
            "output_dir": str(sample_output_dir / "quant_se"),
            "single": True,
            "fragment_length": 200.0,
            "sd": 20.0,
            "threads": 1,
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "output_files" in result
        assert "command_executed" in result
        assert "kallisto quant" in result["command_executed"]
        assert "--single" in result["command_executed"]

        # Skip file checks for mock results
        if result.get("mock"):
            return

    @pytest.mark.optional
    def test_kallisto_quant_direct(
        self, tool_instance, sample_input_files, sample_output_dir
    ):
        """Test Kallisto quant functionality using direct method call."""
        # First create an index
        index_file = sample_output_dir / "kallisto_index_quant"
        tool_instance.kallisto_index(
            fasta_files=[sample_input_files["transcripts_file"]],
            index=index_file,
            kmer_size=31,
        )

        result = tool_instance.kallisto_quant(
            fastq_files=[
                sample_input_files["paired_reads_1"],
                sample_input_files["paired_reads_2"],
            ],
            index=index_file,
            output_dir=sample_output_dir / "quant_direct",
            bootstrap_samples=10,
            threads=1,
            plaintext=False,
        )

        assert "command_executed" in result
        assert "output_files" in result
        assert "kallisto quant" in result["command_executed"]
        assert (
            len(result["output_files"]) >= 2
        )  # abundance.tsv and run_info.json at minimum

        # Skip file checks for mock results
        if result.get("mock"):
            return

    @pytest.mark.optional
    def test_kallisto_quant_tcc(
        self, tool_instance, sample_input_files, sample_output_dir
    ):
        """Test Kallisto quant-tcc functionality."""
        result = tool_instance.kallisto_quant_tcc(
            tcc_matrix=sample_input_files["tcc_matrix"],
            output_dir=sample_output_dir / "quant_tcc",
            bootstrap_samples=10,
            threads=1,
        )

        assert "command_executed" in result
        assert "output_files" in result
        assert "kallisto quant-tcc" in result["command_executed"]

        # Skip file checks for mock results
        if result.get("mock"):
            return

    @pytest.mark.optional
    def test_kallisto_bus(self, tool_instance, sample_input_files, sample_output_dir):
        """Test Kallisto BUS functionality for single-cell data."""
        # First create an index
        index_file = sample_output_dir / "kallisto_index_bus"
        tool_instance.kallisto_index(
            fasta_files=[sample_input_files["transcripts_file"]],
            index=index_file,
            kmer_size=31,
        )

        result = tool_instance.kallisto_bus(
            fastq_files=[
                sample_input_files["paired_reads_1"],
                sample_input_files["paired_reads_2"],
            ],
            output_dir=sample_output_dir / "bus_output",
            index=index_file,
            threads=1,
            bootstrap_samples=0,
        )

        assert "command_executed" in result
        assert "output_files" in result
        assert "kallisto bus" in result["command_executed"]

        # Skip file checks for mock results
        if result.get("mock"):
            return

    @pytest.mark.optional
    def test_kallisto_h5dump(
        self, tool_instance, sample_input_files, sample_output_dir
    ):
        """Test Kallisto h5dump functionality."""
        # First create quantification results (mock HDF5 file)
        h5_file = sample_output_dir / "abundance.h5"
        h5_file.write_text("mock HDF5 content")  # Mock file for testing

        result = tool_instance.kallisto_h5dump(
            abundance_h5=h5_file,
            output_dir=sample_output_dir / "h5dump_output",
        )

        assert "command_executed" in result
        assert "output_files" in result
        assert "kallisto h5dump" in result["command_executed"]

        # Skip file checks for mock results
        if result.get("mock"):
            return

    @pytest.mark.optional
    def test_kallisto_inspect(
        self, tool_instance, sample_input_files, sample_output_dir
    ):
        """Test Kallisto inspect functionality."""
        # First create an index
        index_file = sample_output_dir / "kallisto_index_inspect"
        tool_instance.kallisto_index(
            fasta_files=[sample_input_files["transcripts_file"]],
            index=index_file,
            kmer_size=31,
        )

        result = tool_instance.kallisto_inspect(
            index_file=index_file,
            threads=1,
        )

        assert "command_executed" in result
        assert "stdout" in result
        assert "kallisto inspect" in result["command_executed"]

        # Skip content checks for mock results
        if result.get("mock"):
            return

    @pytest.mark.optional
    def test_kallisto_version(self, tool_instance):
        """Test Kallisto version functionality."""
        result = tool_instance.kallisto_version()

        assert "command_executed" in result
        assert "stdout" in result
        assert "kallisto version" in result["command_executed"]

        # Skip content checks for mock results
        if result.get("mock"):
            return

        # Version should be a string
        assert isinstance(result["stdout"], str)

    @pytest.mark.optional
    def test_kallisto_cite(self, tool_instance):
        """Test Kallisto cite functionality."""
        result = tool_instance.kallisto_cite()

        assert "command_executed" in result
        assert "stdout" in result
        assert "kallisto cite" in result["command_executed"]

        # Skip content checks for mock results
        if result.get("mock"):
            return

        # Citation should be a string
        assert isinstance(result["stdout"], str)

    @pytest.mark.optional
    def test_kallisto_server_info(self, tool_instance):
        """Test server information retrieval."""
        info = tool_instance.get_server_info()

        assert isinstance(info, dict)
        assert "name" in info
        assert "type" in info
        assert "version" in info
        assert "description" in info
        assert "tools" in info
        assert info["name"] == "kallisto-server"
        assert info["type"] == "kallisto"

        # Check that all expected tools are listed
        tools = info["tools"]
        expected_tools = [
            "kallisto_index",
            "kallisto_quant",
            "kallisto_quant_tcc",
            "kallisto_bus",
            "kallisto_h5dump",
            "kallisto_inspect",
            "kallisto_version",
            "kallisto_cite",
        ]
        for tool in expected_tools:
            assert tool in tools

    @pytest.mark.optional
    @pytest.mark.skipif(not MCP_AVAILABLE, reason="MCP functionality not available")
    def test_mcp_tool_registration(self, tool_instance):
        """Test that MCP tools are properly registered."""
        tools = tool_instance.list_tools()

        # Should have multiple tools registered
        assert len(tools) > 0

        # Check specific tool names
        assert "kallisto_index" in tools
        assert "kallisto_quant" in tools
        assert "kallisto_bus" in tools

    @pytest.mark.optional
    def test_parameter_validation_index(self, tool_instance):
        """Test parameter validation for kallisto_index."""
        # Test with missing required parameters
        with pytest.raises((ValueError, FileNotFoundError)):
            tool_instance.kallisto_index(
                fasta_files=[],  # Empty list should fail
                index=Path("/tmp/test_index"),
            )

        # Test with non-existent FASTA file
        with pytest.raises(FileNotFoundError):
            tool_instance.kallisto_index(
                fasta_files=[Path("/nonexistent/file.fa")],
                index=Path("/tmp/test_index"),
            )

    @pytest.mark.optional
    def test_parameter_validation_quant(self, tool_instance):
        """Test parameter validation for kallisto_quant."""
        # Test with non-existent index file
        with pytest.raises(FileNotFoundError):
            tool_instance.kallisto_quant(
                fastq_files=[Path("/tmp/test.fq")],
                index=Path("/nonexistent/index"),
                output_dir=Path("/tmp/output"),
            )

        # Test with single-end parameters missing fragment_length
        with pytest.raises(
            ValueError, match="fragment_length must be > 0 when using single-end mode"
        ):
            tool_instance.kallisto_quant(
                fastq_files=[Path("/tmp/test.fq")],
                index=Path("/tmp/index"),
                output_dir=Path("/tmp/output"),
                single=True,
                sd=20.0,
                # Missing fragment_length
            )
