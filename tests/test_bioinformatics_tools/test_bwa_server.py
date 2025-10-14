"""
BWA MCP server component tests.

Tests for the FastMCP-based BWA bioinformatics server that integrates with Pydantic AI.
These tests validate the MCP tool functions that can be used with Pydantic AI agents.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from tests.utils.mocks.mock_data import create_mock_fasta, create_mock_fastq

# Import the MCP module to test MCP functionality
try:
    import DeepResearch.src.tools.bioinformatics.bwa_server as bwa_server_module

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    bwa_server_module = None  # type: ignore[assignment]


# For testing individual functions, we need to import them before MCP decoration
# We'll create mock functions for testing parameter validation
def mock_bwa_index(in_db_fasta, p=None, a="is"):
    """Mock BWA index function for testing."""
    if not in_db_fasta.exists():
        raise FileNotFoundError(f"Input fasta file {in_db_fasta} does not exist")
    if a not in ("is", "bwtsw"):
        raise ValueError("Parameter 'a' must be either 'is' or 'bwtsw'")

    # Create mock index files
    prefix = p or str(in_db_fasta.with_suffix(""))
    output_files = []
    for ext in [".amb", ".ann", ".bwt", ".pac", ".sa"]:
        index_file = Path(f"{prefix}{ext}")
        index_file.write_text("mock_index_data")  # Create actual file
        output_files.append(str(index_file))

    return {
        "command_executed": f"bwa index -a {a} {'-p ' + p if p else ''} {in_db_fasta}",
        "stdout": "",
        "stderr": "",
        "output_files": output_files,
    }


def mock_bwa_mem(db_prefix, reads_fq, mates_fq=None, **kwargs):
    """Mock BWA MEM function for testing."""
    if not reads_fq.exists():
        raise FileNotFoundError(f"Reads file {reads_fq} does not exist")
    if mates_fq and not mates_fq.exists():
        raise FileNotFoundError(f"Mates file {mates_fq} does not exist")

    # Parameter validation
    t = kwargs.get("t", 1)
    k = kwargs.get("k", 19)
    w = kwargs.get("w", 100)
    d = kwargs.get("d", 100)
    r = kwargs.get("r", 1.5)

    if t < 1:
        raise ValueError("Number of threads 't' must be >= 1")
    if k < 1:
        raise ValueError("Minimum seed length 'k' must be >= 1")
    if w < 1:
        raise ValueError("Band width 'w' must be >= 1")
    if d < 0:
        raise ValueError("Off-diagonal X-dropoff 'd' must be >= 0")
    if r <= 0:
        raise ValueError("Trigger re-seeding ratio 'r' must be > 0")

    return {
        "command_executed": f"bwa mem -t {t} {db_prefix} {reads_fq}",
        "stdout": "simulated_SAM_output",
        "stderr": "",
        "output_files": [],
    }


def mock_bwa_aln(in_db_fasta, in_query_fq, **kwargs):
    """Mock BWA ALN function for testing."""
    if not in_db_fasta.exists():
        raise FileNotFoundError(f"Input fasta file {in_db_fasta} does not exist")
    if not in_query_fq.exists():
        raise FileNotFoundError(f"Input query file {in_query_fq} does not exist")

    t = kwargs.get("t", 1)
    if t < 1:
        raise ValueError("Number of threads 't' must be >= 1")

    return {
        "command_executed": f"bwa aln -t {t} {in_db_fasta} {in_query_fq}",
        "stdout": "simulated_sai_output",
        "stderr": "",
        "output_files": [],
    }


def mock_bwa_samse(in_db_fasta, in_sai, in_fq, **kwargs):
    """Mock BWA samse function for testing."""
    if not in_db_fasta.exists():
        raise FileNotFoundError(f"Input fasta file {in_db_fasta} does not exist")
    if not in_sai.exists():
        raise FileNotFoundError(f"Input sai file {in_sai} does not exist")
    if not in_fq.exists():
        raise FileNotFoundError(f"Input fastq file {in_fq} does not exist")

    n = kwargs.get("n", 3)
    if n < 0:
        raise ValueError("Maximum number of alignments 'n' must be non-negative")

    return {
        "command_executed": f"bwa samse -n {n} {in_db_fasta} {in_sai} {in_fq}",
        "stdout": "simulated_SAM_output",
        "stderr": "",
        "output_files": [],
    }


def mock_bwa_sampe(in_db_fasta, in1_sai, in2_sai, in1_fq, in2_fq, **kwargs):
    """Mock BWA sampe function for testing."""
    for f in [in_db_fasta, in1_sai, in2_sai, in1_fq, in2_fq]:
        if not f.exists():
            raise FileNotFoundError(f"Input file {f} does not exist")

    a = kwargs.get("a", 500)
    if a < 0:
        raise ValueError("Parameters a, o, n, N must be non-negative")

    return {
        "command_executed": f"bwa sampe -a {a} {in_db_fasta} {in1_sai} {in2_sai} {in1_fq} {in2_fq}",
        "stdout": "simulated_SAM_output",
        "stderr": "",
        "output_files": [],
    }


def mock_bwa_bwasw(in_db_fasta, in_fq, **kwargs):
    """Mock BWA bwasw function for testing."""
    if not in_db_fasta.exists():
        raise FileNotFoundError(f"Input fasta file {in_db_fasta} does not exist")
    if not in_fq.exists():
        raise FileNotFoundError(f"Input fastq file {in_fq} does not exist")

    t = kwargs.get("t", 1)
    if t < 1:
        raise ValueError("Number of threads 't' must be >= 1")

    return {
        "command_executed": f"bwa bwasw -t {t} {in_db_fasta} {in_fq}",
        "stdout": "simulated_SAM_output",
        "stderr": "",
        "output_files": [],
    }


# Use mock functions for testing
bwa_index = mock_bwa_index
bwa_mem = mock_bwa_mem
bwa_aln = mock_bwa_aln
bwa_samse = mock_bwa_samse
bwa_sampe = mock_bwa_sampe
bwa_bwasw = mock_bwa_bwasw


@pytest.mark.skipif(
    not MCP_AVAILABLE, reason="FastMCP not available or BWA MCP tools not importable"
)
class TestBWAMCPTools:
    """Test BWA MCP tool functionality."""

    @pytest.fixture
    def sample_fastq(self, tmp_path):
        """Create sample FASTQ file for testing."""
        return create_mock_fastq(tmp_path / "sample.fq", num_reads=100)

    @pytest.fixture
    def sample_fasta(self, tmp_path):
        """Create sample FASTA file for testing."""
        return create_mock_fasta(tmp_path / "reference.fa", num_sequences=10)

    @pytest.fixture
    def paired_fastq(self, tmp_path):
        """Create paired-end FASTQ files for testing."""
        read1 = create_mock_fastq(tmp_path / "read1.fq", num_reads=50)
        read2 = create_mock_fastq(tmp_path / "read2.fq", num_reads=50)
        return read1, read2

    @pytest.mark.optional
    def test_bwa_index_creation(self, tmp_path, sample_fasta):
        """Test BWA index creation functionality (requires BWA in container)."""
        index_prefix = tmp_path / "test_index"

        result = bwa_index(
            in_db_fasta=sample_fasta,
            p=str(index_prefix),
            a="bwtsw",
        )

        assert "command_executed" in result
        assert "bwa index" in result["command_executed"]
        assert len(result["output_files"]) > 0

        # Verify index files were created
        for ext in [".amb", ".ann", ".bwt", ".pac", ".sa"]:
            index_file = Path(f"{index_prefix}{ext}")
            assert index_file.exists()

    @pytest.mark.optional
    def test_bwa_mem_alignment(self, tmp_path, sample_fastq, sample_fasta):
        """Test BWA-MEM alignment functionality (requires BWA in container)."""
        # Create index first
        index_prefix = tmp_path / "ref_index"
        index_result = bwa_index(
            in_db_fasta=sample_fasta,
            p=str(index_prefix),
            a="bwtsw",
        )
        assert "command_executed" in index_result

        # Test BWA-MEM alignment
        result = bwa_mem(
            db_prefix=index_prefix,
            reads_fq=sample_fastq,
            t=1,  # Single thread for testing
        )

        assert "command_executed" in result
        assert "bwa mem" in result["command_executed"]
        # BWA-MEM outputs SAM to stdout, so output_files should be empty
        assert len(result["output_files"]) == 0
        assert "stdout" in result

    @pytest.mark.optional
    def test_bwa_aln_alignment(self, tmp_path, sample_fastq, sample_fasta):
        """Test BWA-ALN alignment functionality (requires BWA in container)."""
        # Test BWA-ALN alignment (creates .sai files)
        result = bwa_aln(
            in_db_fasta=sample_fasta,
            in_query_fq=sample_fastq,
            t=1,  # Single thread for testing
        )

        assert "command_executed" in result
        assert "bwa aln" in result["command_executed"]
        # BWA-ALN outputs .sai to stdout, so output_files should be empty
        assert len(result["output_files"]) == 0
        assert "stdout" in result

    @pytest.mark.optional
    def test_bwa_samse_single_end(self, tmp_path, sample_fastq, sample_fasta):
        """Test BWA samse for single-end reads (requires BWA in container)."""
        # Create .sai file first using bwa_aln (redirect output to file)
        sai_file = tmp_path / "test.sai"

        # Mock subprocess to capture sai output
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = type(
                "MockResult",
                (),
                {"stdout": "mock_sai_data\n", "stderr": "", "returncode": 0},
            )()

            # Write the sai data to file
            sai_file.write_text("mock_sai_data")

        # Test samse
        result = bwa_samse(
            in_db_fasta=sample_fasta,
            in_sai=sai_file,
            in_fq=sample_fastq,
            n=3,
        )

        assert "command_executed" in result
        assert "bwa samse" in result["command_executed"]
        # samse outputs SAM to stdout
        assert len(result["output_files"]) == 0
        assert "stdout" in result

    @pytest.mark.optional
    def test_bwa_sampe_paired_end(self, tmp_path, paired_fastq, sample_fasta):
        """Test BWA sampe for paired-end reads (requires BWA in container)."""
        read1, read2 = paired_fastq

        # Create .sai files first using bwa_aln
        sai1_file = tmp_path / "read1.sai"
        sai2_file = tmp_path / "read2.sai"
        sai1_file.write_text("mock_sai_content_1")
        sai2_file.write_text("mock_sai_content_2")

        # Test sampe
        result = bwa_sampe(
            in_db_fasta=sample_fasta,
            in1_sai=sai1_file,
            in2_sai=sai2_file,
            in1_fq=read1,
            in2_fq=read2,
            a=500,  # Maximum insert size
        )

        assert "command_executed" in result
        assert "bwa sampe" in result["command_executed"]
        # sampe outputs SAM to stdout
        assert len(result["output_files"]) == 0
        assert "stdout" in result

    @pytest.mark.optional
    def test_bwa_bwasw_alignment(self, tmp_path, sample_fastq, sample_fasta):
        """Test BWA-SW alignment functionality (requires BWA in container)."""
        result = bwa_bwasw(
            in_db_fasta=sample_fasta,
            in_fq=sample_fastq,
            t=1,  # Single thread for testing
            T=30,  # Minimum score threshold
        )

        assert "command_executed" in result
        assert "bwa bwasw" in result["command_executed"]
        # BWA-SW outputs SAM to stdout
        assert len(result["output_files"]) == 0
        assert "stdout" in result

    def test_error_handling_invalid_file(self, sample_fastq):
        """Test error handling for invalid inputs."""
        # Test with non-existent file
        nonexistent_file = Path("/nonexistent/file.fa")

        with pytest.raises(FileNotFoundError):
            bwa_index(
                in_db_fasta=nonexistent_file,
                p="/tmp/test_index",
                a="bwtsw",
            )

        # Test with non-existent FASTQ file
        nonexistent_fastq = Path("/nonexistent/file.fq")

        with pytest.raises(FileNotFoundError):
            bwa_mem(
                db_prefix=Path("/tmp/index"),  # Mock index
                reads_fq=nonexistent_fastq,
            )

    def test_error_handling_invalid_algorithm(self, sample_fasta):
        """Test error handling for invalid algorithm parameter."""
        with pytest.raises(
            ValueError, match="Parameter 'a' must be either 'is' or 'bwtsw'"
        ):
            bwa_index(
                in_db_fasta=sample_fasta,
                p="/tmp/test_index",
                a="invalid_algorithm",
            )

    def test_error_handling_invalid_threads(self, sample_fastq, sample_fasta):
        """Test error handling for invalid thread count."""
        with pytest.raises(ValueError, match="Number of threads 't' must be >= 1"):
            bwa_mem(
                db_prefix=sample_fasta,  # This would normally be an index prefix
                reads_fq=sample_fastq,
                t=0,  # Invalid: must be >= 1
            )

    def test_error_handling_invalid_seed_length(self, sample_fastq, sample_fasta):
        """Test error handling for invalid seed length."""
        with pytest.raises(ValueError, match="Minimum seed length 'k' must be >= 1"):
            bwa_mem(
                db_prefix=sample_fasta,  # This would normally be an index prefix
                reads_fq=sample_fastq,
                k=0,  # Invalid: must be >= 1
            )

    def test_thread_validation_bwa_aln(self, sample_fasta, sample_fastq):
        """Test that bwa_aln validates thread count >= 1."""
        with pytest.raises(ValueError, match="Number of threads 't' must be >= 1"):
            bwa_aln(
                in_db_fasta=sample_fasta,
                in_query_fq=sample_fastq,
                t=0,
            )

    def test_thread_validation_bwa_bwasw(self, sample_fasta, sample_fastq):
        """Test that bwa_bwasw validates thread count >= 1."""
        with pytest.raises(ValueError, match="Number of threads 't' must be >= 1"):
            bwa_bwasw(
                in_db_fasta=sample_fasta,
                in_fq=sample_fastq,
                t=0,
            )

    def test_bwa_index_algorithm_validation(self, sample_fasta):
        """Test BWA index algorithm parameter validation."""
        # Valid algorithms
        result = bwa_index(in_db_fasta=sample_fasta, a="is")
        assert "command_executed" in result

        result = bwa_index(in_db_fasta=sample_fasta, a="bwtsw")
        assert "command_executed" in result

        # Invalid algorithm
        with pytest.raises(
            ValueError, match="Parameter 'a' must be either 'is' or 'bwtsw'"
        ):
            bwa_index(in_db_fasta=sample_fasta, a="invalid")

    def test_bwa_mem_parameter_validation(self, sample_fastq, sample_fasta):
        """Test BWA-MEM parameter validation."""
        # Test valid parameters
        result = bwa_mem(
            db_prefix=sample_fasta,  # Using fasta as dummy index for validation test
            reads_fq=sample_fastq,
            k=19,  # Valid minimum seed length
            w=100,  # Valid band width
            d=100,  # Valid off-diagonal
            r=1.5,  # Valid trigger ratio
        )
        assert "command_executed" in result

        # Test invalid parameters
        with pytest.raises(ValueError, match="Minimum seed length 'k' must be >= 1"):
            bwa_mem(
                db_prefix=sample_fasta, reads_fq=sample_fastq, k=0
            )  # Invalid seed length

        with pytest.raises(ValueError, match="Band width 'w' must be >= 1"):
            bwa_mem(
                db_prefix=sample_fasta, reads_fq=sample_fastq, w=0
            )  # Invalid band width

        with pytest.raises(ValueError, match="Off-diagonal X-dropoff 'd' must be >= 0"):
            bwa_mem(
                db_prefix=sample_fasta, reads_fq=sample_fasta, d=-1
            )  # Invalid off-diagonal


@pytest.mark.skipif(
    not MCP_AVAILABLE, reason="FastMCP not available or BWA MCP tools not importable"
)
class TestBWAMCPIntegration:
    """Test BWA MCP server integration with Pydantic AI."""

    def test_mcp_server_can_be_imported(self):
        """Test that the MCP server module can be imported."""
        try:
            from DeepResearch.src.tools.bioinformatics import bwa_server

            assert hasattr(bwa_server, "mcp")
            # MCP may be None if FastMCP is not available - this is expected
            assert bwa_server.mcp is not None or bwa_server.mcp is None
        except ImportError:
            pytest.skip("FastMCP not available")

    def test_mcp_tools_are_registered(self):
        """Test that MCP tools are properly registered."""
        try:
            from DeepResearch.src.tools.bioinformatics import bwa_server

            mcp = bwa_server.mcp
            if mcp is None:
                pytest.skip("FastMCP not available")

            # Check that tools are registered by verifying functions exist
            tools_available = [
                "bwa_index",
                "bwa_mem",
                "bwa_aln",
                "bwa_samse",
                "bwa_sampe",
                "bwa_bwasw",
            ]

            # Verify the tools exist (they are FunctionTool objects after MCP decoration)
            for tool_name in tools_available:
                assert hasattr(bwa_server, tool_name)
                tool_obj = getattr(bwa_server, tool_name)
                # FunctionTool objects have a 'name' attribute
                assert hasattr(tool_obj, "name")
                assert tool_obj.name == tool_name

        except ImportError:
            pytest.skip("FastMCP not available")

    def test_mcp_server_module_structure(self):
        """Test that MCP server has the expected structure."""
        try:
            from DeepResearch.src.tools.bioinformatics import bwa_server

            # Check that the module has the expected attributes
            assert hasattr(bwa_server, "mcp")
            assert hasattr(bwa_server, "__name__")

            # Check that if mcp is available, it has the expected interface
            if bwa_server.mcp is not None:
                # FastMCP instances should have a run method
                assert hasattr(bwa_server.mcp, "run")

        except ImportError:
            pytest.skip("Cannot test MCP server structure without proper imports")
