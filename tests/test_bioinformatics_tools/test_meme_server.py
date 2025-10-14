"""
MEME server component tests.
"""

from unittest.mock import patch

import pytest

from tests.test_bioinformatics_tools.base.test_base_tool import (
    BaseBioinformaticsToolTest,
)


class TestMEMEServer(BaseBioinformaticsToolTest):
    """Test MEME server functionality."""

    @property
    def tool_name(self) -> str:
        return "meme-server"

    @property
    def tool_class(self):
        # Import the actual MEMEServer class
        from DeepResearch.src.tools.bioinformatics.meme_server import MEMEServer

        return MEMEServer

    @property
    def required_parameters(self) -> dict:
        return {
            "sequences": "path/to/sequences.fa",
            "output_dir": "path/to/output",
        }

    @pytest.fixture
    def sample_fasta_files(self, tmp_path):
        """Create sample FASTA files for testing."""
        sequences_file = tmp_path / "sequences.fa"
        control_file = tmp_path / "control.fa"

        # Create mock FASTA files
        sequences_file.write_text(
            ">seq1\n"
            "ATCGATCGATCGATCGATCGATCGATCGATCGATCG\n"
            ">seq2\n"
            "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTA\n"
            ">seq3\n"
            "TTTTAAAAAGGGGCCCCTTTAAGGGCCCCTTTAAA\n"
        )

        control_file.write_text(
            ">ctrl1\n"
            "NNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNN\n"
            ">ctrl2\n"
            "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\n"
        )

        return {
            "sequences": sequences_file,
            "control": control_file,
        }

    @pytest.fixture
    def sample_motif_files(self, tmp_path):
        """Create sample motif files for testing."""
        meme_file = tmp_path / "motifs.meme"
        glam2_file = tmp_path / "motifs.glam2"

        # Create mock MEME format motif file
        meme_file.write_text(
            "MEME version 4\n\n"
            "ALPHABET= ACGT\n\n"
            "strands: + -\n\n"
            "Background letter frequencies\n"
            "A 0.25 C 0.25 G 0.25 T 0.25\n\n"
            "MOTIF MOTIF1\n"
            "letter-probability matrix: alength= 4 w= 8 nsites= 20 E= 0\n"
            " 0.3  0.1  0.4  0.2\n"
            " 0.2  0.3  0.1  0.4\n"
            " 0.4  0.2  0.3  0.1\n"
            " 0.1  0.4  0.2  0.3\n"
            " 0.3  0.1  0.4  0.2\n"
            " 0.2  0.3  0.1  0.4\n"
            " 0.4  0.2  0.3  0.1\n"
            " 0.1  0.4  0.2  0.3\n"
        )

        # Create mock GLAM2 file
        glam2_file.write_text("mock GLAM2 content\n")

        return {
            "meme": meme_file,
            "glam2": glam2_file,
        }

    @pytest.mark.optional
    def test_server_initialization(self, tool_instance):
        """Test MEME server initializes correctly."""
        assert tool_instance is not None
        assert tool_instance.name == "meme-server"
        assert tool_instance.server_type.value == "custom"

        # Check capabilities
        capabilities = tool_instance.config.capabilities
        assert "motif_discovery" in capabilities
        assert "motif_scanning" in capabilities
        assert "motif_alignment" in capabilities
        assert "motif_comparison" in capabilities
        assert "motif_centrality" in capabilities
        assert "motif_enrichment" in capabilities
        assert "glam2_scanning" in capabilities

    @pytest.mark.optional
    def test_server_info(self, tool_instance):
        """Test server info functionality."""
        info = tool_instance.get_server_info()

        assert isinstance(info, dict)
        assert info["name"] == "meme-server"
        assert info["type"] == "custom"
        assert "tools" in info
        assert isinstance(info["tools"], list)
        assert (
            len(info["tools"]) == 7
        )  # meme, fimo, mast, tomtom, centrimo, ame, glam2scan

    @pytest.mark.optional
    def test_meme_motif_discovery(
        self, tool_instance, sample_fasta_files, sample_output_dir
    ):
        """Test MEME motif discovery functionality."""
        params = {
            "operation": "motif_discovery",
            "sequences": str(sample_fasta_files["sequences"]),
            "output_dir": str(sample_output_dir),
            "nmotifs": 1,
            "minw": 6,
            "maxw": 12,
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "output_files" in result
        assert "command_executed" in result

        # Skip file checks for mock results
        if result.get("mock"):
            return

        # Check output files
        assert isinstance(result["output_files"], list)

    @pytest.mark.optional
    def test_meme_motif_discovery_comprehensive(
        self, tool_instance, sample_fasta_files, sample_output_dir
    ):
        """Test MEME motif discovery with comprehensive parameters."""
        params = {
            "operation": "motif_discovery",
            "sequences": str(sample_fasta_files["sequences"]),
            "output_dir": str(sample_output_dir),
            "nmotifs": 2,
            "minw": 8,
            "maxw": 15,
            "mod": "zoops",
            "objfun": "classic",
            "dna": True,
            "revcomp": True,
            "evt": 1.0,
            "maxiter": 25,
            "verbose": True,
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "command_executed" in result

    @pytest.mark.optional
    def test_fimo_motif_scanning(
        self, tool_instance, sample_fasta_files, sample_motif_files, sample_output_dir
    ):
        """Test FIMO motif scanning functionality."""
        params = {
            "operation": "motif_scanning",
            "sequences": str(sample_fasta_files["sequences"]),
            "motifs": str(sample_motif_files["meme"]),
            "output_dir": str(sample_output_dir),
            "thresh": 1e-3,
            "norc": True,
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "output_files" in result
        assert "command_executed" in result

        # Skip file checks for mock results
        if result.get("mock"):
            return

        # Check for FIMO-specific output files
        assert isinstance(result["output_files"], list)

    @pytest.mark.optional
    def test_mast_motif_alignment(
        self, tool_instance, sample_fasta_files, sample_motif_files, sample_output_dir
    ):
        """Test MAST motif alignment functionality."""
        params = {
            "operation": "mast",
            "motifs": str(sample_motif_files["meme"]),
            "sequences": str(sample_fasta_files["sequences"]),
            "output_dir": str(sample_output_dir),
            "mt": 0.001,
            "best": True,
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "output_files" in result
        assert "command_executed" in result

    @pytest.mark.optional
    def test_tomtom_motif_comparison(
        self, tool_instance, sample_motif_files, sample_output_dir
    ):
        """Test TomTom motif comparison functionality."""
        params = {
            "operation": "tomtom",
            "query_motifs": str(sample_motif_files["meme"]),
            "target_motifs": str(sample_motif_files["meme"]),
            "output_dir": str(sample_output_dir),
            "thresh": 0.5,
            "dist": "pearson",
            "norc": True,
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "output_files" in result
        assert "command_executed" in result

    @pytest.mark.optional
    def test_centrimo_motif_centrality(
        self, tool_instance, sample_fasta_files, sample_motif_files, sample_output_dir
    ):
        """Test CentriMo motif centrality analysis."""
        params = {
            "operation": "centrimo",
            "sequences": str(sample_fasta_files["sequences"]),
            "motifs": str(sample_motif_files["meme"]),
            "output_dir": str(sample_output_dir),
            "score": "totalhits",
            "flank": 100,
            "norc": True,
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "output_files" in result
        assert "command_executed" in result

    @pytest.mark.optional
    def test_ame_motif_enrichment(
        self, tool_instance, sample_fasta_files, sample_motif_files, sample_output_dir
    ):
        """Test AME motif enrichment analysis."""
        params = {
            "operation": "ame",
            "sequences": str(sample_fasta_files["sequences"]),
            "control_sequences": str(sample_fasta_files["control"]),
            "motifs": str(sample_motif_files["meme"]),
            "output_dir": str(sample_output_dir),
            "method": "fisher",
            "scoring": "avg",
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "output_files" in result
        assert "command_executed" in result

    @pytest.mark.optional
    def test_glam2scan_scanning(
        self, tool_instance, sample_fasta_files, sample_motif_files, sample_output_dir
    ):
        """Test GLAM2SCAN motif scanning functionality."""
        params = {
            "operation": "glam2scan",
            "glam2_file": str(sample_motif_files["glam2"]),
            "sequences": str(sample_fasta_files["sequences"]),
            "output_dir": str(sample_output_dir),
            "score": 0.5,
            "norc": True,
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "output_files" in result
        assert "command_executed" in result

    @pytest.mark.optional
    def test_parameter_validation_motif_discovery(self, tool_instance, tmp_path):
        """Test parameter validation for MEME motif discovery."""
        # Create dummy sequence file
        dummy_seq = tmp_path / "dummy.fa"
        dummy_seq.write_text(">seq1\nATCG\n")

        # Test invalid nmotifs
        with pytest.raises(ValueError, match="nmotifs must be >= 1"):
            tool_instance.meme_motif_discovery(
                sequences=str(dummy_seq),
                output_dir="dummy_out",
                nmotifs=0,
            )

        # Test invalid shuf_kmer
        with pytest.raises(ValueError, match="shuf_kmer must be between 1 and 6"):
            tool_instance.meme_motif_discovery(
                sequences=str(dummy_seq),
                output_dir="dummy_out",
                shuf_kmer=10,
            )

        # Test invalid evt
        with pytest.raises(ValueError, match="evt must be positive"):
            tool_instance.meme_motif_discovery(
                sequences=str(dummy_seq),
                output_dir="dummy_out",
                evt=0,
            )

    @pytest.mark.optional
    def test_parameter_validation_fimo(self, tool_instance, tmp_path):
        """Test parameter validation for FIMO motif scanning."""
        # Create dummy files
        dummy_seq = tmp_path / "dummy.fa"
        dummy_motif = tmp_path / "dummy.meme"
        dummy_seq.write_text(">seq1\nATCG\n")
        dummy_motif.write_text(
            "MEME version 4\n\nALPHABET= ACGT\n\nMOTIF M1\nletter-probability matrix: alength= 4 w= 4 nsites= 1\n 0.25  0.25  0.25  0.25\n 0.25  0.25  0.25  0.25\n 0.25  0.25  0.25  0.25\n 0.25  0.25  0.25  0.25\n"
        )

        # Test invalid thresh
        with pytest.raises(ValueError, match="thresh must be between 0 and 1"):
            tool_instance.fimo_motif_scanning(
                sequences=str(dummy_seq),
                motifs=str(dummy_motif),
                output_dir="dummy_out",
                thresh=2.0,
            )

        # Test invalid verbosity
        with pytest.raises(ValueError, match="verbosity must be between 0 and 3"):
            tool_instance.fimo_motif_scanning(
                sequences=str(dummy_seq),
                motifs=str(dummy_motif),
                output_dir="dummy_out",
                verbosity=5,
            )

    @pytest.mark.optional
    def test_file_validation(self, tool_instance, tmp_path):
        """Test file validation for missing input files."""
        # Create dummy motif file for FIMO test
        dummy_motif = tmp_path / "dummy.meme"
        dummy_motif.write_text(
            "MEME version 4\n\nALPHABET= ACGT\n\nMOTIF M1\nletter-probability matrix: alength= 4 w= 4 nsites= 1\n 0.25  0.25  0.25  0.25\n"
        )

        # Test missing sequences file for MEME
        with pytest.raises(FileNotFoundError, match="Primary sequence file not found"):
            tool_instance.meme_motif_discovery(
                sequences="nonexistent.fa",
                output_dir="dummy_out",
            )

        # Create dummy sequence file for FIMO test
        dummy_seq = tmp_path / "dummy.fa"
        dummy_seq.write_text(">seq1\nATCG\n")

        # Test missing motifs file for FIMO
        with pytest.raises(FileNotFoundError, match="Motif file not found"):
            tool_instance.fimo_motif_scanning(
                sequences=str(dummy_seq),
                motifs="nonexistent.meme",
                output_dir="dummy_out",
            )

    @pytest.mark.optional
    def test_operation_routing(
        self, tool_instance, sample_fasta_files, sample_motif_files, sample_output_dir
    ):
        """Test operation routing through the run method."""
        operations_to_test = [
            (
                "motif_discovery",
                {
                    "sequences": str(sample_fasta_files["sequences"]),
                    "output_dir": str(sample_output_dir),
                    "nmotifs": 1,
                },
            ),
            (
                "motif_scanning",
                {
                    "sequences": str(sample_fasta_files["sequences"]),
                    "motifs": str(sample_motif_files["meme"]),
                    "output_dir": str(sample_output_dir),
                },
            ),
        ]

        for operation, params in operations_to_test:
            test_params = {"operation": operation, **params}
            result = tool_instance.run(test_params)

            assert result["success"] is True
            assert "command_executed" in result

    @pytest.mark.optional
    def test_unsupported_operation(self, tool_instance):
        """Test handling of unsupported operations."""
        params = {
            "operation": "unsupported_tool",
            "dummy": "value",
        }

        result = tool_instance.run(params)

        assert result["success"] is False
        assert "Unsupported operation" in result["error"]

    @pytest.mark.optional
    def test_missing_operation(self, tool_instance):
        """Test handling of missing operation parameter."""
        params = {
            "sequences": "dummy.fa",
            "output_dir": "dummy_out",
        }

        result = tool_instance.run(params)

        assert result["success"] is False
        assert "Missing 'operation' parameter" in result["error"]

    @pytest.mark.optional
    def test_mock_responses(self, tool_instance, sample_fasta_files, sample_output_dir):
        """Test mock responses when tools are not available."""
        # Mock shutil.which to return None (tool not available)
        with patch("shutil.which", return_value=None):
            params = {
                "operation": "motif_discovery",
                "sequences": str(sample_fasta_files["sequences"]),
                "output_dir": str(sample_output_dir),
                "nmotifs": 1,
            }

            result = tool_instance.run(params)

            # Should return mock success
            assert result["success"] is True
            assert result["mock"] is True
            assert "mock" in result["command_executed"].lower()
