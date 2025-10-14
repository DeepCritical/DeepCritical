"""
SAMtools server component tests.
"""

import pytest

from tests.test_bioinformatics_tools.base.test_base_tool import (
    BaseBioinformaticsToolTest,
)
from tests.utils.mocks.mock_data import create_mock_sam


class TestSAMtoolsServer(BaseBioinformaticsToolTest):
    """Test SAMtools server functionality."""

    @property
    def tool_name(self) -> str:
        return "samtools-server"

    @property
    def tool_class(self):
        # Import the actual SamtoolsServer server class
        from DeepResearch.src.tools.bioinformatics.samtools_server import SamtoolsServer

        return SamtoolsServer

    @property
    def required_parameters(self) -> dict:
        return {"input_file": "path/to/input.sam"}

    @pytest.fixture
    def sample_input_files(self, tmp_path):
        """Create sample SAM file for testing."""
        sam_file = tmp_path / "sample.sam"
        create_mock_sam(sam_file, num_alignments=50)
        return {"input_file": sam_file}

    @pytest.fixture
    def sample_bam_file(self, tmp_path):
        """Create sample BAM file for testing."""
        bam_file = tmp_path / "sample.bam"
        # Create a minimal BAM file content (this is just for testing file existence)
        bam_file.write_bytes(b"BAM\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00")
        return bam_file

    @pytest.fixture
    def sample_fasta_file(self, tmp_path):
        """Create sample FASTA file for testing."""
        fasta_file = tmp_path / "sample.fasta"
        fasta_file.write_text(">chr1\nATCGATCGATCG\n>chr2\nGCTAGCTAGCTA\n")
        return fasta_file

    @pytest.mark.optional
    def test_samtools_view_sam_to_bam(
        self, tool_instance, sample_input_files, sample_output_dir
    ):
        """Test samtools view SAM to BAM conversion."""
        output_file = sample_output_dir / "output.bam"

        result = tool_instance.samtools_view(
            input_file=str(sample_input_files["input_file"]),
            output_file=str(output_file),
            format="sam",
            output_fmt="bam",
        )

        assert result["success"] is True
        assert "output_files" in result
        assert str(output_file) in result["output_files"]

        # Skip file checks for mock results
        if result.get("mock"):
            return

    @pytest.mark.optional
    def test_samtools_view_with_region(
        self, tool_instance, sample_input_files, sample_output_dir
    ):
        """Test samtools view with region filtering."""
        output_file = sample_output_dir / "region.sam"

        result = tool_instance.samtools_view(
            input_file=str(sample_input_files["input_file"]),
            output_file=str(output_file),
            region="chr1:1-100",
            output_fmt="sam",
        )

        assert result["success"] is True
        assert "output_files" in result

    @pytest.mark.optional
    def test_samtools_sort(self, tool_instance, sample_bam_file, sample_output_dir):
        """Test samtools sort functionality."""
        output_file = sample_output_dir / "sorted.bam"

        result = tool_instance.samtools_sort(
            input_file=str(sample_bam_file), output_file=str(output_file)
        )

        assert result["success"] is True
        assert "output_files" in result
        assert str(output_file) in result["output_files"]

    @pytest.mark.optional
    def test_samtools_index(self, tool_instance, sample_bam_file):
        """Test samtools index functionality."""
        result = tool_instance.samtools_index(input_file=str(sample_bam_file))

        assert result["success"] is True
        assert "output_files" in result

    @pytest.mark.optional
    def test_samtools_flagstat(self, tool_instance, sample_bam_file):
        """Test samtools flagstat functionality."""
        result = tool_instance.samtools_flagstat(input_file=str(sample_bam_file))

        assert result["success"] is True
        assert "flag_statistics" in result or result.get("mock")

    @pytest.mark.optional
    def test_samtools_stats(self, tool_instance, sample_bam_file, sample_output_dir):
        """Test samtools stats functionality."""
        output_file = sample_output_dir / "stats.txt"

        result = tool_instance.samtools_stats(
            input_file=str(sample_bam_file), output_file=str(output_file)
        )

        assert result["success"] is True
        assert "output_files" in result

    @pytest.mark.optional
    def test_samtools_merge(self, tool_instance, sample_bam_file, sample_output_dir):
        """Test samtools merge functionality."""
        output_file = sample_output_dir / "merged.bam"
        input_files = [
            str(sample_bam_file),
            str(sample_bam_file),
        ]  # Merge with itself for testing

        result = tool_instance.samtools_merge(
            output_file=str(output_file), input_files=input_files
        )

        assert result["success"] is True
        assert "output_files" in result
        assert str(output_file) in result["output_files"]

    @pytest.mark.optional
    def test_samtools_faidx(self, tool_instance, sample_fasta_file):
        """Test samtools faidx functionality."""
        result = tool_instance.samtools_faidx(fasta_file=str(sample_fasta_file))

        assert result["success"] is True
        assert "output_files" in result

    @pytest.mark.optional
    def test_samtools_faidx_with_regions(self, tool_instance, sample_fasta_file):
        """Test samtools faidx with region extraction."""
        regions = ["chr1:1-5", "chr2:1-3"]

        result = tool_instance.samtools_faidx(
            fasta_file=str(sample_fasta_file), regions=regions
        )

        assert result["success"] is True

    @pytest.mark.optional
    def test_samtools_fastq(self, tool_instance, sample_bam_file, sample_output_dir):
        """Test samtools fastq functionality."""
        output_file = sample_output_dir / "output.fastq"

        result = tool_instance.samtools_fastq(
            input_file=str(sample_bam_file), output_file=str(output_file)
        )

        assert result["success"] is True
        assert "output_files" in result

    @pytest.mark.optional
    def test_samtools_flag_convert(self, tool_instance):
        """Test samtools flag convert functionality."""
        flags = "147"  # Read paired, read mapped in proper pair, mate reverse strand

        result = tool_instance.samtools_flag_convert(flags=flags)

        assert result["success"] is True
        assert "stdout" in result

    @pytest.mark.optional
    def test_samtools_quickcheck(self, tool_instance, sample_bam_file):
        """Test samtools quickcheck functionality."""
        input_files = [str(sample_bam_file)]

        result = tool_instance.samtools_quickcheck(input_files=input_files)

        assert result["success"] is True

    @pytest.mark.optional
    def test_samtools_depth(self, tool_instance, sample_bam_file, sample_output_dir):
        """Test samtools depth functionality."""
        output_file = sample_output_dir / "depth.txt"

        result = tool_instance.samtools_depth(
            input_files=[str(sample_bam_file)], output_file=str(output_file)
        )

        assert result["success"] is True
        assert "output_files" in result
