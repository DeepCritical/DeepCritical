"""
MAFFT server component tests.
"""

from unittest.mock import patch

import pytest

from tests.test_bioinformatics_tools.base.test_base_tool import (
    BaseBioinformaticsToolTest,
)


class TestMAFFTServer(BaseBioinformaticsToolTest):
    """Test MAFFT server functionality."""

    @property
    def tool_name(self) -> str:
        return "mafft-server"

    @property
    def tool_class(self):
        from DeepResearch.src.tools.bioinformatics.mafft_server import MAFFTServer

        return MAFFTServer

    @property
    def required_parameters(self) -> dict:
        return {
            "input_fasta": "path/to/sequences.fasta",
        }

    @pytest.fixture
    def sample_fasta_file(self, tmp_path):
        """Create a sample multi-FASTA file for testing."""
        fasta_file = tmp_path / "sequences.fasta"
        fasta_file.write_text(
            ">seq1\nMKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG\n"
            ">seq2\nMKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG\n"
            ">seq3\nMKTVRQERLKSIVRILERSKEAVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG\n"
        )
        return fasta_file

    @pytest.fixture
    def sample_existing_alignment(self, tmp_path):
        """Create a sample aligned FASTA file for add tests."""
        aligned_file = tmp_path / "aligned.fasta"
        aligned_file.write_text(
            ">seq1\nMKTVRQERLKSIV-RILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG\n"
            ">seq2\nMKTVRQERLKSIVRRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG\n"
        )
        return aligned_file

    @pytest.fixture
    def sample_new_sequences(self, tmp_path):
        """Create a sample FASTA file with new sequences to add."""
        new_seqs = tmp_path / "new_seqs.fasta"
        new_seqs.write_text(
            ">seq_new\nMKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG\n"
        )
        return new_seqs

    @pytest.fixture
    def sample_merge_table(self, tmp_path):
        """Create a sample merge table file for merge tests."""
        merge_table = tmp_path / "merge_table.txt"
        merge_table.write_text("1 2\n3\n")
        return merge_table

    @pytest.mark.optional
    def test_server_initialization(self, tool_instance):
        """Test MAFFT server initializes correctly."""
        assert tool_instance is not None
        assert tool_instance.name == "mafft-server"

        capabilities = tool_instance.config.capabilities
        assert "multiple_sequence_alignment" in capabilities
        assert "protein_alignment" in capabilities
        assert "phylogenetic_analysis" in capabilities

    @pytest.mark.optional
    def test_server_info(self, tool_instance):
        """Test server info functionality."""
        info = tool_instance.get_server_info()

        assert isinstance(info, dict)
        assert info["name"] == "mafft-server"
        assert info["type"] == "mafft"
        assert "tools" in info
        assert isinstance(info["tools"], list)
        assert len(info["tools"]) == 3  # align, add, merge

    @pytest.mark.optional
    def test_list_tools(self, tool_instance):
        """Test tool listing functionality."""
        tools = tool_instance.list_tools()

        assert isinstance(tools, list)
        assert len(tools) == 3
        assert "mafft_align" in tools
        assert "mafft_add" in tools
        assert "mafft_merge" in tools

    @pytest.mark.optional
    def test_mafft_align_auto(
        self, tool_instance, sample_fasta_file, sample_output_dir
    ):
        """Test MAFFT align with auto algorithm selection."""
        output_file = sample_output_dir / "aligned.fasta"
        params = {
            "operation": "align",
            "input_fasta": str(sample_fasta_file),
            "output_file": str(output_file),
            "algorithm": "auto",
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "output_files" in result
        assert "command_executed" in result
        assert isinstance(result["output_files"], list)

    @pytest.mark.optional
    def test_mafft_align_linsi(
        self, tool_instance, sample_fasta_file, sample_output_dir
    ):
        """Test MAFFT align with L-INS-i algorithm."""
        output_file = sample_output_dir / "aligned_linsi.fasta"
        params = {
            "operation": "align",
            "input_fasta": str(sample_fasta_file),
            "output_file": str(output_file),
            "algorithm": "linsi",
            "maxiterate": 1000,
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "output_files" in result

    @pytest.mark.optional
    def test_mafft_align_ginsi(
        self, tool_instance, sample_fasta_file, sample_output_dir
    ):
        """Test MAFFT align with G-INS-i algorithm."""
        output_file = sample_output_dir / "aligned_ginsi.fasta"
        params = {
            "operation": "align",
            "input_fasta": str(sample_fasta_file),
            "output_file": str(output_file),
            "algorithm": "ginsi",
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "output_files" in result

    @pytest.mark.optional
    def test_mafft_align_einsi(
        self, tool_instance, sample_fasta_file, sample_output_dir
    ):
        """Test MAFFT align with E-INS-i algorithm."""
        output_file = sample_output_dir / "aligned_einsi.fasta"
        params = {
            "operation": "align",
            "input_fasta": str(sample_fasta_file),
            "output_file": str(output_file),
            "algorithm": "einsi",
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "output_files" in result

    @pytest.mark.optional
    def test_mafft_align_clustalout(
        self, tool_instance, sample_fasta_file, sample_output_dir
    ):
        """Test MAFFT align with ClustalW output format."""
        output_file = sample_output_dir / "aligned.aln"
        params = {
            "operation": "align",
            "input_fasta": str(sample_fasta_file),
            "output_file": str(output_file),
            "algorithm": "auto",
            "output_format": "clustal",
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "output_files" in result

    @pytest.mark.optional
    def test_mafft_add_basic(
        self,
        tool_instance,
        sample_new_sequences,
        sample_existing_alignment,
        sample_output_dir,
    ):
        """Test MAFFT add new sequences to existing alignment."""
        output_file = sample_output_dir / "updated_alignment.fasta"
        params = {
            "operation": "add",
            "new_sequences": str(sample_new_sequences),
            "existing_alignment": str(sample_existing_alignment),
            "output_file": str(output_file),
            "add_method": "add",
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "output_files" in result
        assert "command_executed" in result

    @pytest.mark.optional
    def test_mafft_add_fragments(
        self,
        tool_instance,
        sample_new_sequences,
        sample_existing_alignment,
        sample_output_dir,
    ):
        """Test MAFFT add fragments to existing alignment."""
        output_file = sample_output_dir / "updated_alignment_frags.fasta"
        params = {
            "operation": "add",
            "new_sequences": str(sample_new_sequences),
            "existing_alignment": str(sample_existing_alignment),
            "output_file": str(output_file),
            "add_method": "addfragments",
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "output_files" in result

    @pytest.mark.optional
    def test_mafft_merge_basic(
        self,
        tool_instance,
        sample_fasta_file,
        sample_merge_table,
        sample_output_dir,
    ):
        """Test MAFFT merge pre-aligned groups."""
        output_file = sample_output_dir / "merged_alignment.fasta"
        params = {
            "operation": "merge",
            "input_fasta": str(sample_fasta_file),
            "merge_table": str(sample_merge_table),
            "output_file": str(output_file),
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "output_files" in result
        assert "command_executed" in result

    @pytest.mark.optional
    def test_invalid_operation(self, tool_instance):
        """Test invalid operation handling."""
        params = {
            "operation": "invalid_operation",
        }

        result = tool_instance.run(params)

        assert result["success"] is False
        assert "error" in result
        assert "Unsupported operation" in result["error"]

    @pytest.mark.optional
    def test_missing_operation(self, tool_instance):
        """Test missing operation parameter."""
        params = {}

        result = tool_instance.run(params)

        assert result["success"] is False
        assert "error" in result
        assert "Missing 'operation' parameter" in result["error"]

    @pytest.mark.optional
    def test_align_validation_missing_file(self, tool_instance, tmp_path):
        """Test align validation with missing input file."""
        missing_file = tmp_path / "missing.fasta"

        with pytest.raises(FileNotFoundError, match="Input FASTA file not found"):
            tool_instance.mafft_align(input_fasta=str(missing_file))

    @pytest.mark.optional
    def test_align_validation_invalid_algorithm(self, tool_instance, sample_fasta_file):
        """Test align validation with invalid algorithm."""
        with pytest.raises(ValueError, match="Invalid algorithm"):
            tool_instance.mafft_align(
                input_fasta=str(sample_fasta_file), algorithm="INVALID"
            )

    @pytest.mark.optional
    def test_align_validation_invalid_output_format(
        self, tool_instance, sample_fasta_file
    ):
        """Test align validation with invalid output format."""
        with pytest.raises(ValueError, match="Invalid output_format"):
            tool_instance.mafft_align(
                input_fasta=str(sample_fasta_file), output_format="invalid_format"
            )

    @pytest.mark.optional
    def test_align_validation_negative_maxiterate(
        self, tool_instance, sample_fasta_file
    ):
        """Test align validation with negative maxiterate."""
        with pytest.raises(ValueError, match="maxiterate must be >= 0"):
            tool_instance.mafft_align(input_fasta=str(sample_fasta_file), maxiterate=-1)

    @pytest.mark.optional
    def test_align_validation_invalid_thread(self, tool_instance, sample_fasta_file):
        """Test align validation with invalid thread value."""
        with pytest.raises(ValueError, match="thread must be >= 1 or -1"):
            tool_instance.mafft_align(input_fasta=str(sample_fasta_file), thread=0)

    @pytest.mark.optional
    def test_align_validation_negative_gap_penalty(
        self, tool_instance, sample_fasta_file
    ):
        """Test align validation with negative gap opening penalty."""
        with pytest.raises(ValueError, match="Gap opening penalty"):
            tool_instance.mafft_align(input_fasta=str(sample_fasta_file), op=-1.0)

    @pytest.mark.optional
    def test_align_validation_invalid_blosum(self, tool_instance, sample_fasta_file):
        """Test align validation with invalid BLOSUM matrix."""
        with pytest.raises(ValueError, match="Invalid BLOSUM matrix"):
            tool_instance.mafft_align(input_fasta=str(sample_fasta_file), bl="99")

    @pytest.mark.optional
    def test_align_validation_conflicting_adjust(
        self, tool_instance, sample_fasta_file
    ):
        """Test align validation with conflicting adjustdirection options."""
        with pytest.raises(ValueError, match="Cannot use both"):
            tool_instance.mafft_align(
                input_fasta=str(sample_fasta_file),
                adjustdirection=True,
                adjustdirectionaccurately=True,
            )

    @pytest.mark.optional
    def test_add_validation_missing_new_sequences(self, tool_instance, tmp_path):
        """Test add validation with missing new sequences file."""
        missing_file = tmp_path / "missing.fasta"
        existing_file = tmp_path / "existing.fasta"
        existing_file.write_text(">seq1\nACGT\n")

        with pytest.raises(FileNotFoundError, match="New sequences file not found"):
            tool_instance.mafft_add(
                new_sequences=str(missing_file),
                existing_alignment=str(existing_file),
            )

    @pytest.mark.optional
    def test_add_validation_missing_existing_alignment(self, tool_instance, tmp_path):
        """Test add validation with missing existing alignment file."""
        new_file = tmp_path / "new.fasta"
        new_file.write_text(">seq1\nACGT\n")
        missing_file = tmp_path / "missing_alignment.fasta"

        with pytest.raises(
            FileNotFoundError, match="Existing alignment file not found"
        ):
            tool_instance.mafft_add(
                new_sequences=str(new_file),
                existing_alignment=str(missing_file),
            )

    @pytest.mark.optional
    def test_add_validation_invalid_add_method(
        self, tool_instance, sample_new_sequences, sample_existing_alignment
    ):
        """Test add validation with invalid add method."""
        with pytest.raises(ValueError, match="Invalid add_method"):
            tool_instance.mafft_add(
                new_sequences=str(sample_new_sequences),
                existing_alignment=str(sample_existing_alignment),
                add_method="INVALID",
            )

    @pytest.mark.optional
    def test_merge_validation_missing_input(self, tool_instance, tmp_path):
        """Test merge validation with missing input FASTA file."""
        missing_file = tmp_path / "missing.fasta"
        merge_table = tmp_path / "table.txt"
        merge_table.write_text("1 2\n")

        with pytest.raises(FileNotFoundError, match="Input FASTA file not found"):
            tool_instance.mafft_merge(
                input_fasta=str(missing_file),
                merge_table=str(merge_table),
            )

    @pytest.mark.optional
    def test_merge_validation_missing_table(self, tool_instance, sample_fasta_file):
        """Test merge validation with missing merge table file."""
        with pytest.raises(FileNotFoundError, match="Merge table file not found"):
            tool_instance.mafft_merge(
                input_fasta=str(sample_fasta_file),
                merge_table="/nonexistent/table.txt",
            )

    @pytest.mark.optional
    @patch("shutil.which")
    def test_mock_functionality_align(
        self, mock_which, tool_instance, sample_fasta_file, sample_output_dir
    ):
        """Test mock functionality when MAFFT is not available."""
        mock_which.return_value = None

        output_file = sample_output_dir / "aligned.fasta"
        params = {
            "operation": "align",
            "input_fasta": str(sample_fasta_file),
            "output_file": str(output_file),
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert result["mock"] is True
        assert "output_files" in result
        assert len(result["output_files"]) == 1

    @pytest.mark.optional
    @patch("shutil.which")
    def test_mock_functionality_add(
        self,
        mock_which,
        tool_instance,
        sample_new_sequences,
        sample_existing_alignment,
        sample_output_dir,
    ):
        """Test mock functionality for add when MAFFT is not available."""
        mock_which.return_value = None

        output_file = sample_output_dir / "updated.fasta"
        params = {
            "operation": "add",
            "new_sequences": str(sample_new_sequences),
            "existing_alignment": str(sample_existing_alignment),
            "output_file": str(output_file),
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert result["mock"] is True
        assert "output_files" in result

    @pytest.mark.optional
    @patch("shutil.which")
    def test_mock_functionality_merge(
        self,
        mock_which,
        tool_instance,
        sample_fasta_file,
        sample_merge_table,
        sample_output_dir,
    ):
        """Test mock functionality for merge when MAFFT is not available."""
        mock_which.return_value = None

        output_file = sample_output_dir / "merged.fasta"
        params = {
            "operation": "merge",
            "input_fasta": str(sample_fasta_file),
            "merge_table": str(sample_merge_table),
            "output_file": str(output_file),
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert result["mock"] is True
        assert "output_files" in result
