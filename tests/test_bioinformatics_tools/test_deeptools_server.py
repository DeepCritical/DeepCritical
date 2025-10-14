"""
Deeptools MCP server component tests.

Tests for the FastMCP-based Deeptools bioinformatics server that integrates with Pydantic AI.
These tests validate the MCP tool functions that can be used with Pydantic AI agents,
including GC bias computation and correction, coverage analysis, and heatmap generation.
"""

import asyncio
from pathlib import Path

import pytest

from tests.test_bioinformatics_tools.base.test_base_tool import (
    BaseBioinformaticsToolTest,
)

# Import the MCP module to test MCP functionality
try:
    import DeepResearch.src.tools.bioinformatics.deeptools_server as deeptools_server_module

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    deeptools_server_module = None  # type: ignore


# Mock functions for testing parameter validation before MCP decoration
def mock_compute_gc_bias(
    bamfile: str,
    effective_genome_size: int,
    genome: str,
    fragment_length: int = 200,
    gc_bias_frequencies_file: str = "",
    number_of_processors: int = 1,
    verbose: bool = False,
):
    """Mock computeGCBias function for testing."""
    bam_path = Path(bamfile)
    genome_path = Path(genome)

    if not bam_path.exists():
        raise FileNotFoundError(f"BAM file not found: {bamfile}")
    if not genome_path.exists():
        raise FileNotFoundError(f"Genome file not found: {genome}")

    if effective_genome_size <= 0:
        raise ValueError("effective_genome_size must be positive")
    if fragment_length <= 0:
        raise ValueError("fragment_length must be positive")

    output_files = []
    if gc_bias_frequencies_file:
        output_files.append(gc_bias_frequencies_file)

    return {
        "command_executed": f"computeGCBias -b {bamfile} --effectiveGenomeSize {effective_genome_size} -g {genome}",
        "stdout": "GC bias computation completed successfully",
        "stderr": "",
        "output_files": output_files,
        "success": True,
    }


def mock_correct_gc_bias(
    bamfile: str,
    effective_genome_size: int,
    genome: str,
    gc_bias_frequencies_file: str,
    corrected_file: str,
    bin_size: int = 50,
    region: str | None = None,
    number_of_processors: int = 1,
    verbose: bool = False,
):
    """Mock correctGCBias function for testing."""
    bam_path = Path(bamfile)
    genome_path = Path(genome)
    freq_path = Path(gc_bias_frequencies_file)
    corrected_path = Path(corrected_file)

    if not bam_path.exists():
        raise FileNotFoundError(f"BAM file not found: {bamfile}")
    if not genome_path.exists():
        raise FileNotFoundError(f"Genome file not found: {genome}")
    if not freq_path.exists():
        raise FileNotFoundError(
            f"GC bias frequencies file not found: {gc_bias_frequencies_file}"
        )

    if corrected_path.suffix not in [".bam", ".bw", ".bg"]:
        raise ValueError("corrected_file must end with .bam, .bw, or .bg")

    if effective_genome_size <= 0:
        raise ValueError("effective_genome_size must be positive")
    if bin_size <= 0:
        raise ValueError("bin_size must be positive")

    return {
        "command_executed": f"correctGCBias -b {bamfile} --effectiveGenomeSize {effective_genome_size} -g {genome} --GCbiasFrequenciesFile {gc_bias_frequencies_file} -o {corrected_file}",
        "stdout": "GC bias correction completed successfully",
        "stderr": "",
        "output_files": [corrected_file],
        "success": True,
    }


def mock_bam_coverage(
    bam_file: str,
    output_file: str,
    bin_size: int = 50,
    number_of_processors: int = 1,
    normalize_using: str = "RPGC",
    effective_genome_size: int = 2150570000,
    extend_reads: int = 200,
    ignore_duplicates: bool = False,
    min_mapping_quality: int = 10,
    smooth_length: int = 60,
    scale_factors: str | None = None,
    center_reads: bool = False,
    sam_flag_include: int | None = None,
    sam_flag_exclude: int | None = None,
    min_fragment_length: int = 0,
    max_fragment_length: int = 0,
    use_basal_level: bool = False,
    offset: int = 0,
):
    """Mock bamCoverage function for testing."""
    bam_path = Path(bam_file)

    if not bam_path.exists():
        raise FileNotFoundError(f"Input BAM file not found: {bam_file}")

    if normalize_using == "RPGC" and effective_genome_size <= 0:
        raise ValueError(
            "effective_genome_size must be positive for RPGC normalization"
        )

    if extend_reads < 0:
        raise ValueError("extend_reads cannot be negative")

    if min_mapping_quality < 0:
        raise ValueError("min_mapping_quality cannot be negative")

    if smooth_length < 0:
        raise ValueError("smooth_length cannot be negative")

    return {
        "command_executed": f"bamCoverage --bam {bam_file} --outFileName {output_file} --binSize {bin_size} --normalizeUsing {normalize_using}",
        "stdout": "Coverage track generated successfully",
        "stderr": "",
        "output_files": [output_file],
        "exit_code": 0,
        "success": True,
    }


class TestDeeptoolsServer(BaseBioinformaticsToolTest):
    """Test Deeptools server functionality using base test class."""

    @property
    def tool_name(self) -> str:
        return "deeptools-server"

    @property
    def tool_class(self):
        from DeepResearch.src.tools.bioinformatics.deeptools_server import (
            DeeptoolsServer,
        )

        return DeeptoolsServer

    @property
    def required_parameters(self) -> dict:
        return {
            "bam_file": "path/to/sample.bam",
            "output_file": "path/to/coverage.bw",
        }

    @pytest.fixture
    def sample_input_files(self, tmp_path):
        """Create sample BAM and genome files for testing."""
        bam_file = tmp_path / "sample.bam"
        genome_file = tmp_path / "genome.2bit"
        bed_file = tmp_path / "regions.bed"
        bigwig_file = tmp_path / "sample.bw"

        # Create mock files
        bam_file.write_text("mock BAM content")
        genome_file.write_text("mock genome content")
        bed_file.write_text("chr1\t1000\t2000\tregion1\n")
        bigwig_file.write_text("mock bigWig content")

        return {
            "bam_file": bam_file,
            "genome_file": genome_file,
            "bed_file": bed_file,
            "bigwig_file": bigwig_file,
        }


class TestDeeptoolsParameterValidation:
    """Test parameter validation for Deeptools functions."""

    def test_compute_gc_bias_parameter_validation(self, tmp_path):
        """Test computeGCBias parameter validation."""
        bam_file = tmp_path / "sample.bam"
        genome_file = tmp_path / "genome.2bit"
        bam_file.write_text("mock")
        genome_file.write_text("mock")

        # Test valid parameters
        result = mock_compute_gc_bias(
            bamfile=str(bam_file),
            effective_genome_size=3000000000,
            genome=str(genome_file),
            fragment_length=200,
            gc_bias_frequencies_file=str(tmp_path / "gc_bias.txt"),
        )
        assert "command_executed" in result
        assert result["success"] is True

        # Test invalid effective_genome_size
        with pytest.raises(ValueError, match="effective_genome_size must be positive"):
            mock_compute_gc_bias(
                bamfile=str(bam_file),
                effective_genome_size=0,
                genome=str(genome_file),
            )

        # Test invalid fragment_length
        with pytest.raises(ValueError, match="fragment_length must be positive"):
            mock_compute_gc_bias(
                bamfile=str(bam_file),
                effective_genome_size=3000000000,
                genome=str(genome_file),
                fragment_length=0,
            )

        # Test missing BAM file
        with pytest.raises(FileNotFoundError, match="BAM file not found"):
            mock_compute_gc_bias(
                bamfile="nonexistent.bam",
                effective_genome_size=3000000000,
                genome=str(genome_file),
            )

        # Test missing genome file
        with pytest.raises(FileNotFoundError, match="Genome file not found"):
            mock_compute_gc_bias(
                bamfile=str(bam_file),
                effective_genome_size=3000000000,
                genome="nonexistent.2bit",
            )

    def test_correct_gc_bias_parameter_validation(self, tmp_path):
        """Test correctGCBias parameter validation."""
        bam_file = tmp_path / "sample.bam"
        genome_file = tmp_path / "genome.2bit"
        freq_file = tmp_path / "gc_bias.txt"
        bam_file.write_text("mock")
        genome_file.write_text("mock")
        freq_file.write_text("mock")

        # Test valid parameters
        result = mock_correct_gc_bias(
            bamfile=str(bam_file),
            effective_genome_size=3000000000,
            genome=str(genome_file),
            gc_bias_frequencies_file=str(freq_file),
            corrected_file=str(tmp_path / "corrected.bam"),
        )
        assert "command_executed" in result
        assert result["success"] is True

        # Test invalid file extension
        with pytest.raises(ValueError, match="corrected_file must end with"):
            mock_correct_gc_bias(
                bamfile=str(bam_file),
                effective_genome_size=3000000000,
                genome=str(genome_file),
                gc_bias_frequencies_file=str(freq_file),
                corrected_file=str(tmp_path / "corrected.txt"),
            )

        # Test invalid effective_genome_size
        with pytest.raises(ValueError, match="effective_genome_size must be positive"):
            mock_correct_gc_bias(
                bamfile=str(bam_file),
                effective_genome_size=0,
                genome=str(genome_file),
                gc_bias_frequencies_file=str(freq_file),
                corrected_file=str(tmp_path / "corrected.bam"),
            )

        # Test invalid bin_size
        with pytest.raises(ValueError, match="bin_size must be positive"):
            mock_correct_gc_bias(
                bamfile=str(bam_file),
                effective_genome_size=3000000000,
                genome=str(genome_file),
                gc_bias_frequencies_file=str(freq_file),
                corrected_file=str(tmp_path / "corrected.bam"),
                bin_size=0,
            )

    def test_bam_coverage_parameter_validation(self, tmp_path):
        """Test bamCoverage parameter validation."""
        bam_file = tmp_path / "sample.bam"
        output_file = tmp_path / "coverage.bw"
        bam_file.write_text("mock")

        # Test valid parameters
        result = mock_bam_coverage(
            bam_file=str(bam_file),
            output_file=str(output_file),
            bin_size=50,
            normalize_using="RPGC",
            effective_genome_size=3000000000,
        )
        assert "command_executed" in result
        assert result["success"] is True

        # Test invalid normalize_using with RPGC
        with pytest.raises(ValueError, match="effective_genome_size must be positive"):
            mock_bam_coverage(
                bam_file=str(bam_file),
                output_file=str(output_file),
                normalize_using="RPGC",
                effective_genome_size=0,
            )

        # Test invalid extend_reads
        with pytest.raises(ValueError, match="extend_reads cannot be negative"):
            mock_bam_coverage(
                bam_file=str(bam_file),
                output_file=str(output_file),
                extend_reads=-1,
            )

        # Test invalid min_mapping_quality
        with pytest.raises(ValueError, match="min_mapping_quality cannot be negative"):
            mock_bam_coverage(
                bam_file=str(bam_file),
                output_file=str(output_file),
                min_mapping_quality=-1,
            )

        # Test invalid smooth_length
        with pytest.raises(ValueError, match="smooth_length cannot be negative"):
            mock_bam_coverage(
                bam_file=str(bam_file),
                output_file=str(output_file),
                smooth_length=-1,
            )


@pytest.mark.skipif(
    not MCP_AVAILABLE,
    reason="FastMCP not available or Deeptools MCP tools not importable",
)
class TestDeeptoolsMCPIntegration:
    """Test Deeptools MCP server integration with Pydantic AI."""

    def test_mcp_server_can_be_imported(self):
        """Test that the MCP server module can be imported."""
        try:
            from DeepResearch.src.tools.bioinformatics import deeptools_server

            assert hasattr(deeptools_server, "deeptools_server")
            assert deeptools_server.deeptools_server is not None
        except ImportError:
            pytest.skip("FastMCP not available")

    def test_mcp_tools_are_registered(self):
        """Test that MCP tools are properly registered."""
        try:
            from DeepResearch.src.tools.bioinformatics import deeptools_server

            server = deeptools_server.deeptools_server
            assert server is not None

            # Check that tools are available via list_tools
            tools = server.list_tools()
            assert isinstance(tools, list)
            assert len(tools) > 0

            # Expected tools for Deeptools server
            expected_tools = [
                "compute_gc_bias",
                "correct_gc_bias",
                "deeptools_bam_coverage",
                "deeptools_compute_matrix",
                "deeptools_plot_heatmap",
                "deeptools_multi_bam_summary",
            ]

            # Verify expected tools are present
            for tool_name in expected_tools:
                assert tool_name in tools, f"Tool {tool_name} not found in tools list"

        except ImportError:
            pytest.skip("FastMCP not available")

    def test_mcp_server_module_structure(self):
        """Test that MCP server has the expected structure."""
        try:
            from DeepResearch.src.tools.bioinformatics import deeptools_server

            # Check that the module has the expected attributes
            assert hasattr(deeptools_server, "DeeptoolsServer")
            assert hasattr(deeptools_server, "deeptools_server")

            # Check server instance
            server = deeptools_server.deeptools_server
            assert server is not None

            # Check server has expected methods
            assert hasattr(server, "list_tools")
            assert hasattr(server, "get_server_info")
            assert hasattr(server, "run")

        except ImportError:
            pytest.skip("Cannot test MCP server structure without proper imports")

    def test_mcp_server_info(self):
        """Test MCP server information retrieval."""
        try:
            from DeepResearch.src.tools.bioinformatics import deeptools_server

            server = deeptools_server.deeptools_server
            info = server.get_server_info()

            assert isinstance(info, dict)
            assert "name" in info
            assert "type" in info
            assert "tools" in info
            assert "deeptools_version" in info
            assert "capabilities" in info

            assert info["name"] == "deeptools-server"
            assert info["type"] == "deeptools"
            assert isinstance(info["tools"], list)
            assert len(info["tools"]) > 0
            assert "gc_bias_correction" in info["capabilities"]

        except ImportError:
            pytest.skip("FastMCP not available")


@pytest.mark.containerized
class TestDeeptoolsContainerized:
    """Containerized tests for Deeptools server."""

    @pytest.mark.optional
    def test_deeptools_server_deployment(self, test_config):
        """Test Deeptools server can be deployed with testcontainers."""
        if not test_config["docker_enabled"]:
            pytest.skip("Docker tests disabled")

        try:
            from DeepResearch.src.tools.bioinformatics.deeptools_server import (
                DeeptoolsServer,
            )

            server = DeeptoolsServer()

            # Test deployment
            deployment = asyncio.run(server.deploy_with_testcontainers())

            assert deployment is not None
            assert deployment.server_name == "deeptools-server"
            assert deployment.status.value == "running"
            assert deployment.container_id is not None

            # Test health check
            is_healthy = asyncio.run(server.health_check())
            assert is_healthy is True

            # Cleanup
            stopped = asyncio.run(server.stop_with_testcontainers())
            assert stopped is True

        except ImportError:
            pytest.skip("testcontainers not available")

    @pytest.mark.optional
    def test_deeptools_server_docker_compose(self, test_config, tmp_path):
        """Test Deeptools server with docker-compose."""
        if not test_config["docker_enabled"]:
            pytest.skip("Docker tests disabled")

        # This test would verify that the docker-compose.yml works correctly
        # For now, just check that the compose file exists and is valid
        compose_file = Path("docker/bioinformatics/docker-compose-deeptools_server.yml")
        assert compose_file.exists()

        # Basic validation that compose file has expected structure
        import yaml

        with open(compose_file) as f:
            compose_data = yaml.safe_load(f)

        assert "services" in compose_data
        assert "mcp-deeptools" in compose_data["services"]

        service = compose_data["services"]["mcp-deeptools"]
        assert "image" in service or "build" in service
        assert "environment" in service
        assert "volumes" in service
