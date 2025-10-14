"""
STAR server component tests.
"""

import pytest

from tests.test_bioinformatics_tools.base.test_base_tool import (
    BaseBioinformaticsToolTest,
)


class TestSTARServer(BaseBioinformaticsToolTest):
    """Test STAR server functionality."""

    @property
    def tool_name(self) -> str:
        return "star-server"

    @property
    def tool_class(self):
        # Import the actual StarServer server class
        from DeepResearch.src.tools.bioinformatics.star_server import STARServer

        return STARServer

    @property
    def required_parameters(self) -> dict:
        return {
            "genome_dir": "path/to/genome/index",
            "read_files_in": "path/to/reads_1.fq path/to/reads_2.fq",
            "out_file_name_prefix": "output_prefix",
        }

    @pytest.fixture
    def sample_input_files(self, tmp_path):
        """Create sample FASTQ files for testing."""
        reads1 = tmp_path / "reads_1.fq"
        reads2 = tmp_path / "reads_2.fq"

        # Create mock paired-end reads
        reads1.write_text(
            "@READ_001\nATCGATCGATCG\n+\nIIIIIIIIIIII\n@READ_002\nGCTAGCTAGCTA\n+\nIIIIIIIIIIII\n"
        )
        reads2.write_text(
            "@READ_001\nTAGCTAGCTAGC\n+\nIIIIIIIIIIII\n@READ_002\nATCGATCGATCG\n+\nIIIIIIIIIIII\n"
        )

        return {"reads_1": reads1, "reads_2": reads2}

    @pytest.mark.optional
    def test_star_alignment(self, tool_instance, sample_input_files, sample_output_dir):
        """Test STAR alignment functionality."""
        params = {
            "operation": "alignment",
            "genome_dir": "/path/to/genome/index",  # Mock genome directory
            "read_files_in": f"{sample_input_files['reads_1']} {sample_input_files['reads_2']}",
            "out_file_name_prefix": str(sample_output_dir / "star_output"),
            "threads": 2,
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "output_files" in result

        # Skip file checks for mock results
        if result.get("mock"):
            return
        # Verify output files were created
        bam_file = sample_output_dir / "star_outputAligned.out.bam"
        assert bam_file.exists()

    @pytest.mark.optional
    def test_star_indexing(self, tool_instance, tmp_path):
        """Test STAR genome indexing functionality."""
        genome_dir = tmp_path / "genome_index"
        fasta_file = tmp_path / "genome.fa"
        gtf_file = tmp_path / "genes.gtf"

        # Create mock genome files
        fasta_file.write_text(">chr1\nATCGATCGATCGATCGATCGATCGATCGATCGATCG\n")
        gtf_file.write_text(
            'chr1\tHAVANA\tgene\t1\t20\t.\t+\t.\tgene_id "GENE1"; gene_name "Gene1";\n'
        )

        params = {
            "operation": "generate_genome",
            "genome_fasta_files": str(fasta_file),
            "sjdb_gtf_file": str(gtf_file),
            "genome_dir": str(genome_dir),
            "threads": 1,
        }

        result = tool_instance.run(params)

        assert result["success"] is True

        # Skip file checks for mock results
        if result.get("mock"):
            return

        # Verify output files were created
        assert genome_dir.exists()
        assert (genome_dir / "SAindex").exists()  # STAR index files
