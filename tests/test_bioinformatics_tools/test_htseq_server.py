"""
HTSeq server component tests.
"""

import pytest

from tests.test_bioinformatics_tools.base.test_base_tool import (
    BaseBioinformaticsToolTest,
)


class TestHTSeqServer(BaseBioinformaticsToolTest):
    """Test HTSeq server functionality."""

    @property
    def tool_name(self) -> str:
        return "featurecounts-server"

    @property
    def tool_class(self):
        # Use FeatureCountsServer as HTSeq equivalent
        from DeepResearch.src.tools.bioinformatics.featurecounts_server import (
            FeatureCountsServer,
        )

        return FeatureCountsServer

    @property
    def required_parameters(self) -> dict:
        return {
            "sam_file": "path/to/aligned.sam",
            "gtf_file": "path/to/genes.gtf",
            "output_file": "path/to/counts.txt",
        }

    @pytest.fixture
    def sample_input_files(self, tmp_path):
        """Create sample SAM and GTF files for testing."""
        sam_file = tmp_path / "sample.sam"
        gtf_file = tmp_path / "genes.gtf"

        # Create mock SAM file
        sam_file.write_text(
            "read1\t0\tchr1\t100\t60\t8M\t*\t0\t0\tATCGATCG\tIIIIIIII\n"
            "read2\t0\tchr1\t200\t60\t8M\t*\t0\t0\tGCTAGCTA\tIIIIIIII\n"
        )

        # Create mock GTF file
        gtf_file.write_text(
            'chr1\tgene\tgene\t1\t1000\t.\t+\t.\tgene_id "gene1"\n'
            'chr1\tgene\texon\t100\t200\t.\t+\t.\tgene_id "gene1"\n'
        )

        return {"sam_file": sam_file, "gtf_file": gtf_file}

    @pytest.mark.optional
    def test_htseq_count(self, tool_instance, sample_input_files, sample_output_dir):
        """Test HTSeq count functionality using FeatureCounts."""
        params = {
            "operation": "count",
            "annotation_file": str(sample_input_files["gtf_file"]),
            "input_files": [str(sample_input_files["sam_file"])],
            "output_file": str(sample_output_dir / "counts.txt"),
            "feature_type": "exon",
            "attribute_type": "gene_id",
            "stranded": "0",  # unstranded
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "output_files" in result

        # Skip file checks for mock results
        if result.get("mock"):
            return
