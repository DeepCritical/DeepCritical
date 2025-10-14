"""
Salmon server component tests.
"""

from unittest.mock import Mock, patch

import pytest

from DeepResearch.src.datatypes.mcp import MCPServerConfig, MCPServerType


class TestSalmonServer:
    """Test Salmon server functionality."""

    @pytest.fixture
    def salmon_server(self):
        """Create a SalmonServer instance for testing."""
        from DeepResearch.src.tools.bioinformatics.salmon_server import SalmonServer

        config = MCPServerConfig(
            server_name="test-salmon-server",
            server_type=MCPServerType.CUSTOM,
            container_image="condaforge/miniforge3:latest",
            environment_variables={"SALMON_VERSION": "1.10.1"},
            capabilities=["rna_seq", "quantification", "transcript_expression"],
        )
        return SalmonServer(config)

    @pytest.fixture
    def sample_fasta_file(self, tmp_path):
        """Create a sample FASTA file for testing."""
        fasta_file = tmp_path / "transcripts.fa"
        fasta_file.write_text(
            ">transcript1\nATCGATCGATCGATCGATCG\n>transcript2\nGCTAGCTAGCTAGCTAGCTA\n"
        )
        return fasta_file

    @pytest.fixture
    def sample_fastq_files(self, tmp_path):
        """Create sample FASTQ files for testing."""
        reads1_file = tmp_path / "reads_1.fq"
        reads2_file = tmp_path / "reads_2.fq"

        # Create mock FASTQ files
        fastq_content = "@read1\nATCGATCGATCG\n+\nIIIIIIIIIIII\n@read2\nGCTAGCTAGCTA\n+\nJJJJJJJJJJJJ\n"
        reads1_file.write_text(fastq_content)
        reads2_file.write_text(fastq_content)

        return {"mates1": [reads1_file], "mates2": [reads2_file]}

    @pytest.fixture
    def sample_quant_files(self, tmp_path):
        """Create sample quant.sf files for testing."""
        quant1_file = tmp_path / "sample1" / "quant.sf"
        quant2_file = tmp_path / "sample2" / "quant.sf"

        # Create directories
        quant1_file.parent.mkdir(parents=True, exist_ok=True)
        quant2_file.parent.mkdir(parents=True, exist_ok=True)

        # Create mock quant.sf files
        quant_content = "Name\tLength\tEffectiveLength\tTPM\tNumReads\ntranscript1\t20\t15.5\t50.0\t10\ntranscript2\t20\t15.5\t50.0\t10\n"
        quant1_file.write_text(quant_content)
        quant2_file.write_text(quant_content)

        return [quant1_file, quant2_file]

    @pytest.fixture
    def sample_gtf_file(self, tmp_path):
        """Create a sample GTF file for testing."""
        gtf_file = tmp_path / "annotation.gtf"
        gtf_content = 'chr1\tsource\tgene\t100\t200\t.\t+\t.\tgene_id "gene1"; gene_name "GENE1";\n'
        gtf_file.write_text(gtf_content)
        return gtf_file

    @pytest.fixture
    def sample_tgmap_file(self, tmp_path):
        """Create a sample transcript-to-gene mapping file."""
        tgmap_file = tmp_path / "txp2gene.tsv"
        tgmap_content = "transcript1\tgene1\ntranscript2\tgene2\n"
        tgmap_file.write_text(tgmap_content)
        return tgmap_file

    def test_server_initialization(self, salmon_server):
        """Test that the SalmonServer initializes correctly."""
        assert salmon_server.name == "test-salmon-server"
        assert salmon_server.server_type == MCPServerType.CUSTOM
        assert "rna_seq" in salmon_server.config.capabilities

    def test_list_tools(self, salmon_server):
        """Test that all tools are properly registered."""
        tools = salmon_server.list_tools()
        expected_tools = [
            "salmon_index",
            "salmon_quant",
            "salmon_alevin",
            "salmon_quantmerge",
            "salmon_swim",
            "salmon_validate",
        ]
        assert all(tool in tools for tool in expected_tools)

    def test_get_server_info(self, salmon_server):
        """Test server info retrieval."""
        info = salmon_server.get_server_info()
        assert info["name"] == "test-salmon-server"
        assert info["type"] == "salmon"
        assert "tools" in info
        assert len(info["tools"]) >= 6  # Should have at least 6 tools

    @patch("subprocess.run")
    def test_salmon_index_mock(
        self, mock_subprocess, salmon_server, sample_fasta_file, tmp_path
    ):
        """Test Salmon index functionality with mock execution."""
        # Mock subprocess to simulate tool not being available
        mock_subprocess.side_effect = FileNotFoundError("Salmon not found in PATH")

        params = {
            "operation": "index",
            "transcripts_fasta": str(sample_fasta_file),
            "index_dir": str(tmp_path / "index"),
            "kmer_size": 31,
        }

        result = salmon_server.run(params)

        # Should return mock success result
        assert result["success"] is True
        assert result["mock"] is True
        assert "salmon index [mock" in result["command_executed"]

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_salmon_index_real(
        self, mock_subprocess, mock_which, salmon_server, sample_fasta_file, tmp_path
    ):
        """Test Salmon index functionality with simulated real execution."""
        # Mock shutil.which to return a path (simulating salmon is installed)
        mock_which.return_value = "/usr/bin/salmon"

        # Mock successful subprocess execution
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Index created successfully"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result

        index_dir = tmp_path / "index"
        index_dir.mkdir()

        params = {
            "operation": "index",
            "transcripts_fasta": str(sample_fasta_file),
            "index_dir": str(index_dir),
            "kmer_size": 31,
        }

        result = salmon_server.run(params)

        assert result["success"] is True
        assert result.get("mock") is not True
        assert "salmon index" in result["command_executed"]
        assert str(index_dir) in result["output_files"]
        mock_subprocess.assert_called_once()

    @patch("subprocess.run")
    def test_salmon_quant_mock(
        self, mock_subprocess, salmon_server, sample_fastq_files, tmp_path
    ):
        """Test Salmon quant functionality with mock execution."""
        mock_subprocess.side_effect = FileNotFoundError("Salmon not found in PATH")

        params = {
            "operation": "quant",
            "index_or_transcripts": str(tmp_path / "index"),
            "lib_type": "A",
            "output_dir": str(tmp_path / "quant"),
            "reads_1": [str(f) for f in sample_fastq_files["mates1"]],
            "threads": 2,
        }

        result = salmon_server.run(params)

        assert result["success"] is True
        assert result["mock"] is True
        assert "salmon quant [mock" in result["command_executed"]

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_salmon_quant_real(
        self, mock_subprocess, mock_which, salmon_server, sample_fastq_files, tmp_path
    ):
        """Test Salmon quant functionality with simulated real execution."""
        # Mock shutil.which to return a path (simulating salmon is installed)
        mock_which.return_value = "/usr/bin/salmon"

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Quantification completed"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result

        output_dir = tmp_path / "quant"
        output_dir.mkdir()

        # Create a dummy index directory (Salmon expects this to exist)
        index_dir = tmp_path / "index"
        index_dir.mkdir()
        (index_dir / "dummy_index_file").write_text("dummy index content")

        params = {
            "operation": "quant",
            "index_or_transcripts": str(index_dir),
            "lib_type": "A",
            "output_dir": str(output_dir),
            "reads_1": [str(f) for f in sample_fastq_files["mates1"]],
            "reads_2": [str(f) for f in sample_fastq_files["mates2"]],
            "threads": 2,
        }

        result = salmon_server.run(params)

        assert result["success"] is True
        assert result.get("mock") is not True
        assert "salmon quant" in result["command_executed"]
        mock_subprocess.assert_called_once()

    @patch("subprocess.run")
    def test_salmon_alevin_mock(
        self,
        mock_subprocess,
        salmon_server,
        sample_fastq_files,
        sample_tgmap_file,
        tmp_path,
    ):
        """Test Salmon alevin functionality with mock execution."""
        mock_subprocess.side_effect = FileNotFoundError("Salmon not found in PATH")

        params = {
            "operation": "alevin",
            "index": str(tmp_path / "index"),
            "lib_type": "ISR",
            "mates1": [str(f) for f in sample_fastq_files["mates1"]],
            "mates2": [str(f) for f in sample_fastq_files["mates2"]],
            "output": str(tmp_path / "alevin"),
            "tgmap": str(sample_tgmap_file),
            "threads": 2,
        }

        result = salmon_server.run(params)

        assert result["success"] is True
        assert result["mock"] is True
        assert "salmon alevin [mock" in result["command_executed"]

    @patch("subprocess.run")
    def test_salmon_swim_mock(
        self, mock_subprocess, salmon_server, sample_fastq_files, tmp_path
    ):
        """Test Salmon swim functionality with mock execution."""
        mock_subprocess.side_effect = FileNotFoundError("Salmon not found in PATH")

        params = {
            "operation": "swim",
            "index": str(tmp_path / "index"),
            "reads_1": [str(f) for f in sample_fastq_files["mates1"]],
            "output": str(tmp_path / "swim"),
            "validate_mappings": True,
        }

        result = salmon_server.run(params)

        assert result["success"] is True
        assert result["mock"] is True
        assert "salmon swim [mock" in result["command_executed"]

    @patch("subprocess.run")
    def test_salmon_quantmerge_mock(
        self, mock_subprocess, salmon_server, sample_quant_files, tmp_path
    ):
        """Test Salmon quantmerge functionality with mock execution."""
        mock_subprocess.side_effect = FileNotFoundError("Salmon not found in PATH")

        params = {
            "operation": "quantmerge",
            "quants": [str(f) for f in sample_quant_files],
            "output": str(tmp_path / "merged_quant.sf"),
            "names": ["sample1", "sample2"],
            "column": "TPM",
        }

        result = salmon_server.run(params)

        assert result["success"] is True
        assert result["mock"] is True
        assert "salmon quantmerge [mock" in result["command_executed"]

    @patch("subprocess.run")
    def test_salmon_validate_mock(
        self, mock_subprocess, salmon_server, sample_quant_files, sample_gtf_file
    ):
        """Test Salmon validate functionality with mock execution."""
        mock_subprocess.side_effect = FileNotFoundError("Salmon not found in PATH")

        params = {
            "operation": "validate",
            "quant_file": str(sample_quant_files[0]),
            "gtf_file": str(sample_gtf_file),
            "output": "validation_report.txt",
        }

        result = salmon_server.run(params)

        assert result["success"] is True
        assert result["mock"] is True
        assert "salmon validate [mock" in result["command_executed"]

    def test_invalid_operation(self, salmon_server):
        """Test handling of invalid operations."""
        params = {"operation": "invalid_operation"}

        result = salmon_server.run(params)

        assert result["success"] is False
        assert "Unsupported operation" in result["error"]

    def test_missing_operation(self, salmon_server):
        """Test handling of missing operation parameter."""
        params = {}

        result = salmon_server.run(params)

        assert result["success"] is False
        assert "Missing 'operation' parameter" in result["error"]

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_salmon_index_with_decoys(
        self, mock_subprocess, mock_which, salmon_server, sample_fasta_file, tmp_path
    ):
        """Test Salmon index with decoys file."""
        # Mock shutil.which to return a path (simulating salmon is installed)
        mock_which.return_value = "/usr/bin/salmon"

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Index with decoys created"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result

        decoys_file = tmp_path / "decoys.txt"
        decoys_file.write_text("decoys_sequence\n")

        index_dir = tmp_path / "index"
        index_dir.mkdir()

        params = {
            "operation": "index",
            "transcripts_fasta": str(sample_fasta_file),
            "index_dir": str(index_dir),
            "decoys_file": str(decoys_file),
            "kmer_size": 31,
        }

        result = salmon_server.run(params)

        assert result["success"] is True
        assert "--decoys" in result["command_executed"]

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_salmon_quant_advanced_params(
        self, mock_subprocess, mock_which, salmon_server, sample_fastq_files, tmp_path
    ):
        """Test Salmon quant with advanced parameters."""
        # Mock shutil.which to return a path (simulating salmon is installed)
        mock_which.return_value = "/usr/bin/salmon"

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Advanced quantification completed"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result

        output_dir = tmp_path / "quant"
        output_dir.mkdir()

        # Create a dummy index directory (Salmon expects this to exist)
        index_dir = tmp_path / "index"
        index_dir.mkdir()
        (index_dir / "dummy_index_file").write_text("dummy index content")

        params = {
            "operation": "quant",
            "index_or_transcripts": str(index_dir),
            "lib_type": "ISR",
            "output_dir": str(output_dir),
            "reads_1": [str(f) for f in sample_fastq_files["mates1"]],
            "reads_2": [str(f) for f in sample_fastq_files["mates2"]],
            "validate_mappings": True,
            "seq_bias": True,
            "gc_bias": True,
            "num_bootstraps": 30,
            "threads": 4,
        }

        result = salmon_server.run(params)

        assert result["success"] is True
        assert "--validateMappings" in result["command_executed"]
        assert "--seqBias" in result["command_executed"]
        assert "--gcBias" in result["command_executed"]
        assert "--numBootstraps 30" in result["command_executed"]

    def test_tool_spec_validation(self, salmon_server):
        """Test that tool specs are properly defined."""
        for tool_name in salmon_server.list_tools():
            tool_spec = salmon_server.get_tool_spec(tool_name)
            assert tool_spec is not None
            assert tool_spec.name == tool_name
            assert tool_spec.description
            assert tool_spec.inputs
            assert tool_spec.outputs

    def test_execute_tool_directly(self, salmon_server, tmp_path):
        """Test executing tools directly via the server."""
        # Test with invalid tool
        with pytest.raises(ValueError, match="Tool 'invalid_tool' not found"):
            salmon_server.execute_tool("invalid_tool")

        # Test with valid tool but non-existent file (should raise FileNotFoundError)
        with pytest.raises(FileNotFoundError, match="Transcripts FASTA file not found"):
            salmon_server.execute_tool(
                "salmon_index",
                transcripts_fasta="/nonexistent/test.fa",
                index_dir=str(tmp_path / "index"),
            )

        # Test that the method exists and can be called (even if it fails due to missing files)
        # We can't easily test successful execution without mocking the file system and subprocess
        assert hasattr(salmon_server, "execute_tool")
