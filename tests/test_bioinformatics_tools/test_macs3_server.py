"""
MACS3 server component tests.
"""

from unittest.mock import patch

import pytest

from tests.test_bioinformatics_tools.base.test_base_tool import (
    BaseBioinformaticsToolTest,
)


class TestMACS3Server(BaseBioinformaticsToolTest):
    """Test MACS3 server functionality."""

    @property
    def tool_name(self) -> str:
        return "macs3-server"

    @property
    def tool_class(self):
        # Import the actual MACS3Server class
        from DeepResearch.src.tools.bioinformatics.macs3_server import MACS3Server

        return MACS3Server

    @property
    def required_parameters(self) -> dict:
        return {
            "treatment": ["path/to/treatment.bam"],
            "name": "test_peaks",
        }

    @pytest.fixture
    def sample_bam_files(self, tmp_path):
        """Create sample BAM files for testing."""
        treatment_bam = tmp_path / "treatment.bam"
        control_bam = tmp_path / "control.bam"

        # Create mock BAM files (just need to exist for validation)
        treatment_bam.write_text("mock BAM content")
        control_bam.write_text("mock BAM content")

        return {
            "treatment_bam": treatment_bam,
            "control_bam": control_bam,
        }

    @pytest.fixture
    def sample_bedgraph_files(self, tmp_path):
        """Create sample bedGraph files for testing."""
        treatment_bg = tmp_path / "treatment.bdg"
        control_bg = tmp_path / "control.bdg"

        # Create mock bedGraph files
        treatment_bg.write_text("chr1\t100\t200\t1.5\n")
        control_bg.write_text("chr1\t100\t200\t0.8\n")

        return {
            "treatment_bdg": treatment_bg,
            "control_bdg": control_bg,
        }

    @pytest.fixture
    def sample_bampe_files(self, tmp_path):
        """Create sample BAMPE files for testing."""
        bampe_file = tmp_path / "atac.bam"

        # Create mock BAMPE file
        bampe_file.write_text("mock BAMPE content")

        return {"bampe_file": bampe_file}

    @pytest.mark.optional
    def test_server_initialization(self, tool_instance):
        """Test MACS3 server initializes correctly."""
        assert tool_instance is not None
        assert tool_instance.name == "macs3-server"
        assert tool_instance.server_type.value == "macs3"

        # Check capabilities
        capabilities = tool_instance.config.capabilities
        assert "chip_seq" in capabilities
        assert "atac_seq" in capabilities
        assert "hmmratac" in capabilities

    @pytest.mark.optional
    def test_server_info(self, tool_instance):
        """Test server info functionality."""
        info = tool_instance.get_server_info()

        assert isinstance(info, dict)
        assert info["name"] == "macs3-server"
        assert info["type"] == "macs3"
        assert "tools" in info
        assert isinstance(info["tools"], list)
        assert len(info["tools"]) == 4  # callpeak, hmmratac, bdgcmp, filterdup

    @pytest.mark.optional
    def test_list_tools(self, tool_instance):
        """Test tool listing functionality."""
        tools = tool_instance.list_tools()

        assert isinstance(tools, list)
        assert len(tools) == 4
        assert "macs3_callpeak" in tools
        assert "macs3_hmmratac" in tools
        assert "macs3_bdgcmp" in tools
        assert "macs3_filterdup" in tools

    @pytest.mark.optional
    def test_macs3_callpeak_basic(
        self, tool_instance, sample_bam_files, sample_output_dir
    ):
        """Test MACS3 callpeak basic functionality."""
        params = {
            "operation": "callpeak",
            "treatment": [sample_bam_files["treatment_bam"]],
            "control": [sample_bam_files["control_bam"]],
            "name": "test_peaks",
            "outdir": sample_output_dir,
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "output_files" in result
        assert "command_executed" in result
        assert isinstance(result["output_files"], list)

        # Check expected output files are mentioned
        output_files = result["output_files"]
        assert any("test_peaks_peaks.xls" in f for f in output_files)
        assert any("test_peaks_peaks.narrowPeak" in f for f in output_files)
        assert any("test_peaks_summits.bed" in f for f in output_files)

    @pytest.mark.optional
    def test_macs3_callpeak_comprehensive(
        self, tool_instance, sample_bam_files, sample_output_dir
    ):
        """Test MACS3 callpeak with comprehensive parameters."""
        params = {
            "operation": "callpeak",
            "treatment": [sample_bam_files["treatment_bam"]],
            "control": [sample_bam_files["control_bam"]],
            "name": "comprehensive_peaks",
            "outdir": sample_output_dir,
            "format": "BAM",
            "gsize": "hs",
            "qvalue": 0.01,
            "pvalue": 0.0,
            "broad": True,
            "broad_cutoff": 0.05,
            "call_summits": True,
            "bdg": True,
            "trackline": True,
            "cutoff_analysis": True,
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "output_files" in result

        # Check for broad peak and bedGraph outputs
        output_files = result["output_files"]
        assert any("comprehensive_peaks_peaks.broadPeak" in f for f in output_files)
        assert any("comprehensive_peaks_treat_pileup.bdg" in f for f in output_files)

    @pytest.mark.optional
    def test_macs3_hmmratac_basic(
        self, tool_instance, sample_bampe_files, sample_output_dir
    ):
        """Test MACS3 HMMRATAC basic functionality."""
        params = {
            "operation": "hmmratac",
            "input_files": [sample_bampe_files["bampe_file"]],
            "name": "test_atac",
            "outdir": sample_output_dir,
            "format": "BAMPE",
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "output_files" in result
        assert "command_executed" in result

        # Check for expected HMMRATAC output
        output_files = result["output_files"]
        assert any("test_atac_peaks.narrowPeak" in f for f in output_files)

    @pytest.mark.optional
    def test_macs3_hmmratac_comprehensive(
        self, tool_instance, sample_bampe_files, sample_output_dir
    ):
        """Test MACS3 HMMRATAC with comprehensive parameters."""
        # Create training regions file
        training_file = sample_output_dir / "training_regions.bed"
        training_file.write_text("chr1\t1000\t2000\nchr2\t5000\t6000\n")

        params = {
            "operation": "hmmratac",
            "input_files": [sample_bampe_files["bampe_file"]],
            "name": "comprehensive_atac",
            "outdir": sample_output_dir,
            "format": "BAMPE",
            "min_frag_p": 0.001,
            "upper": 15,
            "lower": 8,
            "prescan_cutoff": 1.5,
            "hmm_type": "gaussian",
            "training": str(training_file),
            "cutoff_analysis_only": False,
            "cutoff_analysis_max": 50,
            "cutoff_analysis_steps": 50,
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "output_files" in result

    @pytest.mark.optional
    def test_macs3_bdgcmp(
        self, tool_instance, sample_bedgraph_files, sample_output_dir
    ):
        """Test MACS3 bdgcmp functionality."""
        params = {
            "operation": "bdgcmp",
            "treatment_bdg": str(sample_bedgraph_files["treatment_bdg"]),
            "control_bdg": str(sample_bedgraph_files["control_bdg"]),
            "name": "test_fold_enrichment",
            "output_dir": str(sample_output_dir),
            "method": "ppois",
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "output_files" in result

        # Check for expected bdgcmp output files
        output_files = result["output_files"]
        assert any("test_fold_enrichment_ppois.bdg" in f for f in output_files)
        assert any("test_fold_enrichment_logLR.bdg" in f for f in output_files)

    @pytest.mark.optional
    def test_macs3_filterdup(self, tool_instance, sample_bam_files, sample_output_dir):
        """Test MACS3 filterdup functionality."""
        output_bam = sample_output_dir / "filtered.bam"

        params = {
            "operation": "filterdup",
            "input_bam": str(sample_bam_files["treatment_bam"]),
            "output_bam": str(output_bam),
            "gsize": "hs",
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "output_files" in result
        assert str(output_bam) in result["output_files"]

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
    def test_callpeak_validation_empty_treatment(self, tool_instance):
        """Test callpeak validation with empty treatment files."""
        with pytest.raises(
            ValueError, match="At least one treatment file must be specified"
        ):
            tool_instance.macs3_callpeak(treatment=[], name="test")

    @pytest.mark.optional
    def test_callpeak_validation_missing_file(self, tool_instance, tmp_path):
        """Test callpeak validation with missing treatment file."""
        missing_file = tmp_path / "missing.bam"

        with pytest.raises(FileNotFoundError, match="Treatment file not found"):
            tool_instance.macs3_callpeak(treatment=[missing_file], name="test")

    @pytest.mark.optional
    def test_callpeak_validation_invalid_format(self, tool_instance, sample_bam_files):
        """Test callpeak validation with invalid format."""
        with pytest.raises(ValueError, match="Invalid format 'INVALID'"):
            tool_instance.macs3_callpeak(
                treatment=[sample_bam_files["treatment_bam"]],
                name="test",
                format="INVALID",
            )

    @pytest.mark.optional
    def test_callpeak_validation_invalid_qvalue(self, tool_instance, sample_bam_files):
        """Test callpeak validation with invalid qvalue."""
        with pytest.raises(ValueError, match="qvalue must be > 0 and <= 1"):
            tool_instance.macs3_callpeak(
                treatment=[sample_bam_files["treatment_bam"]], name="test", qvalue=2.0
            )

    @pytest.mark.optional
    def test_callpeak_validation_bam_pe_shift(self, tool_instance, sample_bam_files):
        """Test callpeak validation with invalid shift for BAMPE format."""
        with pytest.raises(ValueError, match="shift must be 0 when format is BAMPE"):
            tool_instance.macs3_callpeak(
                treatment=[sample_bam_files["treatment_bam"]],
                name="test",
                format="BAMPE",
                shift=10,
            )

    @pytest.mark.optional
    def test_callpeak_validation_broad_cutoff_without_broad(
        self, tool_instance, sample_bam_files
    ):
        """Test callpeak validation with broad_cutoff when broad is False."""
        with pytest.raises(
            ValueError, match="broad_cutoff option is only valid when broad is enabled"
        ):
            tool_instance.macs3_callpeak(
                treatment=[sample_bam_files["treatment_bam"]],
                name="test",
                broad=False,
                broad_cutoff=0.05,
            )

    @pytest.mark.optional
    def test_hmmratac_validation_empty_input(self, tool_instance):
        """Test HMMRATAC validation with empty input files."""
        with pytest.raises(
            ValueError, match="At least one input file must be provided"
        ):
            tool_instance.macs3_hmmratac(input_files=[], name="test")

    @pytest.mark.optional
    def test_hmmratac_validation_missing_file(self, tool_instance, tmp_path):
        """Test HMMRATAC validation with missing input file."""
        missing_file = tmp_path / "missing.bam"

        with pytest.raises(FileNotFoundError, match="Input file does not exist"):
            tool_instance.macs3_hmmratac(input_files=[missing_file], name="test")

    @pytest.mark.optional
    def test_hmmratac_validation_invalid_format(
        self, tool_instance, sample_bampe_files
    ):
        """Test HMMRATAC validation with invalid format."""
        with pytest.raises(ValueError, match="Invalid format 'INVALID'"):
            tool_instance.macs3_hmmratac(
                input_files=[sample_bampe_files["bampe_file"]],
                name="test",
                format="INVALID",
            )

    @pytest.mark.optional
    def test_hmmratac_validation_invalid_min_frag_p(
        self, tool_instance, sample_bampe_files
    ):
        """Test HMMRATAC validation with invalid min_frag_p."""
        with pytest.raises(ValueError, match="min_frag_p must be between 0 and 1"):
            tool_instance.macs3_hmmratac(
                input_files=[sample_bampe_files["bampe_file"]],
                name="test",
                min_frag_p=2.0,
            )

    @pytest.mark.optional
    def test_hmmratac_validation_invalid_prescan_cutoff(
        self, tool_instance, sample_bampe_files
    ):
        """Test HMMRATAC validation with invalid prescan_cutoff."""
        with pytest.raises(ValueError, match="prescan_cutoff must be > 1"):
            tool_instance.macs3_hmmratac(
                input_files=[sample_bampe_files["bampe_file"]],
                name="test",
                prescan_cutoff=0.5,
            )

    @pytest.mark.optional
    def test_bdgcmp_validation_missing_files(self, tool_instance, tmp_path):
        """Test bdgcmp validation with missing input files."""
        missing_file = tmp_path / "missing.bdg"

        # Test the method directly since validation happens there
        result = tool_instance.macs3_bdgcmp(
            treatment_bdg=str(missing_file), control_bdg=str(missing_file), name="test"
        )

        assert result["success"] is False
        assert "error" in result
        assert "Treatment file not found" in result["error"]

    @pytest.mark.optional
    def test_filterdup_validation_missing_file(
        self, tool_instance, tmp_path, sample_output_dir
    ):
        """Test filterdup validation with missing input file."""
        missing_file = tmp_path / "missing.bam"
        output_file = sample_output_dir / "output.bam"

        # Test the method directly since validation happens there
        result = tool_instance.macs3_filterdup(
            input_bam=str(missing_file), output_bam=str(output_file)
        )

        assert result["success"] is False
        assert "error" in result
        assert "Input file not found" in result["error"]

    @pytest.mark.optional
    @patch("shutil.which")
    def test_mock_functionality_callpeak(
        self, mock_which, tool_instance, sample_bam_files, sample_output_dir
    ):
        """Test mock functionality when MACS3 is not available."""
        mock_which.return_value = None

        params = {
            "operation": "callpeak",
            "treatment": [sample_bam_files["treatment_bam"]],
            "name": "mock_peaks",
            "outdir": sample_output_dir,
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert result["mock"] is True
        assert "output_files" in result
        assert (
            len(result["output_files"]) == 4
        )  # peaks.xls, peaks.narrowPeak, summits.bed, model.r

    @pytest.mark.optional
    @patch("shutil.which")
    def test_mock_functionality_hmmratac(
        self, mock_which, tool_instance, sample_bampe_files, sample_output_dir
    ):
        """Test mock functionality for HMMRATAC when MACS3 is not available."""
        mock_which.return_value = None

        params = {
            "operation": "hmmratac",
            "input_files": [sample_bampe_files["bampe_file"]],
            "name": "mock_atac",
            "outdir": sample_output_dir,
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert result["mock"] is True
        assert "output_files" in result
        assert len(result["output_files"]) == 1  # peaks.narrowPeak

    @pytest.mark.optional
    @patch("shutil.which")
    def test_mock_functionality_bdgcmp(
        self, mock_which, tool_instance, sample_bedgraph_files, sample_output_dir
    ):
        """Test mock functionality for bdgcmp when MACS3 is not available."""
        mock_which.return_value = None

        params = {
            "operation": "bdgcmp",
            "treatment_bdg": str(sample_bedgraph_files["treatment_bdg"]),
            "control_bdg": str(sample_bedgraph_files["control_bdg"]),
            "name": "mock_fold",
            "output_dir": str(sample_output_dir),
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert result["mock"] is True
        assert "output_files" in result
        assert len(result["output_files"]) == 3  # ppois.bdg, logLR.bdg, FE.bdg

    @pytest.mark.optional
    @patch("shutil.which")
    def test_mock_functionality_filterdup(
        self, mock_which, tool_instance, sample_bam_files, sample_output_dir
    ):
        """Test mock functionality for filterdup when MACS3 is not available."""
        mock_which.return_value = None

        output_bam = sample_output_dir / "filtered.bam"
        params = {
            "operation": "filterdup",
            "input_bam": str(sample_bam_files["treatment_bam"]),
            "output_bam": str(output_bam),
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert result["mock"] is True
        assert "output_files" in result
        assert str(output_bam) in result["output_files"]
