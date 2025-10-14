"""
Mock data generators for testing.
"""

from pathlib import Path


def create_mock_fastq(file_path: Path, num_reads: int = 100) -> Path:
    """Create a mock FASTQ file for testing."""
    reads = []

    for i in range(num_reads):
        # Generate mock read data
        read_id = f"@READ_{i:06d}"
        sequence = "ATCG" * 10  # 40bp read
        quality_header = "+"
        quality_scores = "I" * 40  # Mock quality scores

        reads.extend([read_id, sequence, quality_header, quality_scores])

    file_path.write_text("\n".join(reads))
    return file_path


def create_mock_fasta(file_path: Path, num_sequences: int = 10) -> Path:
    """Create a mock FASTA file for testing."""
    sequences = []

    for i in range(num_sequences):
        header = f">SEQUENCE_{i:03d}"
        sequence = "ATCG" * 25  # 100bp sequence

        sequences.extend([header, sequence])

    file_path.write_text("\n".join(sequences))
    return file_path


def create_mock_fastq_paired(
    read1_path: Path, read2_path: Path, num_reads: int = 100
) -> tuple[Path, Path]:
    """Create mock paired-end FASTQ files."""
    # Create read 1
    create_mock_fastq(read1_path, num_reads)

    # Create read 2 (reverse complement pattern)
    reads = []
    for i in range(num_reads):
        read_id = f"@READ_{i:06d}"
        sequence = "TAGC" * 10  # Different pattern for read 2
        quality_header = "+"
        quality_scores = "I" * 40

        reads.extend([read_id, sequence, quality_header, quality_scores])

    read2_path.write_text("\n".join(reads))
    return read1_path, read2_path


def create_mock_sam(file_path: Path, num_alignments: int = 50) -> Path:
    """Create a mock SAM file for testing."""
    header_lines = [
        "@HD	VN:1.0	SO:coordinate",
        "@SQ	SN:chr1	LN:1000",
        "@SQ	SN:chr2	LN:2000",
        "@PG	ID:bwa	PN:bwa	VN:0.7.17-r1188	CL:bwa mem -t 1 ref.fa read.fq",
    ]

    alignment_lines = []
    for i in range(num_alignments):
        # Generate mock SAM alignment
        qname = f"READ_{i:06d}"
        flag = "0"
        rname = "chr1" if i % 2 == 0 else "chr2"
        pos = str((i % 100) * 10 + 1)
        mapq = "60"
        cigar = "40M"
        rnext = "*"
        pnext = "0"
        tlen = "0"
        seq = "ATCG" * 10
        qual = "IIIIIIIIIIII"

        alignment_lines.append(
            f"{qname}\t{flag}\t{rname}\t{pos}\t{mapq}\t{cigar}\t{rnext}\t{pnext}\t{tlen}\t{seq}\t{qual}"
        )

    all_lines = header_lines + alignment_lines
    file_path.write_text("\n".join(all_lines))
    return file_path


def create_mock_vcf(file_path: Path, num_variants: int = 20) -> Path:
    """Create a mock VCF file for testing."""
    header_lines = [
        "##fileformat=VCFv4.2",
        "##contig=<ID=chr1,length=1000>",
        "##contig=<ID=chr2,length=2000>",
        "#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO",
    ]

    variant_lines = []
    for i in range(num_variants):
        chrom = "chr1" if i % 2 == 0 else "chr2"
        pos = str((i % 50) * 20 + 1)
        id_val = f"var_{i:03d}"
        ref = "A" if i % 3 == 0 else "C"
        alt = "T" if i % 3 == 0 else "G"
        qual = "100"
        filter_val = "PASS"
        info = "."

        variant_lines.append(
            f"{chrom}\t{pos}\t{id_val}\t{ref}\t{alt}\t{qual}\t{filter_val}\t{info}"
        )

    all_lines = header_lines + variant_lines
    file_path.write_text("\n".join(all_lines))
    return file_path


def create_mock_gtf(file_path: Path, num_features: int = 10) -> Path:
    """Create a mock GTF file for testing."""
    header_lines = ["#!genome-build test", "#!genome-version 1.0"]

    feature_lines = []
    for i in range(num_features):
        chrom = "chr1" if i % 2 == 0 else "chr2"
        source = "test"
        feature = "gene" if i % 3 == 0 else "transcript"
        start = str((i % 20) * 50 + 1)
        end = str(int(start) + 100)
        score = "."
        strand = "+" if i % 2 == 0 else "-"
        frame = "."
        attributes = f'gene_id "GENE_{i:03d}"; transcript_id "TRANSCRIPT_{i:03d}";'

        feature_lines.append(
            f"{chrom}\t{source}\t{feature}\t{start}\t{end}\t{score}\t{strand}\t{frame}\t{attributes}"
        )

    all_lines = header_lines + feature_lines
    file_path.write_text("\n".join(all_lines))
    return file_path


def create_test_directory_structure(base_path: Path) -> dict[str, Path]:
    """Create a complete test directory structure with sample files."""
    structure = {}

    # Create main directories
    data_dir = base_path / "data"
    results_dir = base_path / "results"
    logs_dir = base_path / "logs"

    data_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Create sample files
    structure["reference"] = create_mock_fasta(data_dir / "reference.fa")
    structure["reads1"], structure["reads2"] = create_mock_fastq_paired(
        data_dir / "reads_1.fq", data_dir / "reads_2.fq"
    )
    structure["alignment"] = create_mock_sam(results_dir / "alignment.sam")
    structure["variants"] = create_mock_vcf(results_dir / "variants.vcf")
    structure["annotation"] = create_mock_gtf(results_dir / "annotation.gtf")

    return structure


def create_mock_bed(file_path: Path, num_regions: int = 10) -> Path:
    """Create a mock BED file for testing."""
    regions = []

    for i in range(num_regions):
        chrom = f"chr{i % 3 + 1}"
        start = i * 1000
        end = start + 500
        name = f"region_{i}"
        score = 100
        strand = "+" if i % 2 == 0 else "-"

        regions.append(f"{chrom}\t{start}\t{end}\t{name}\t{score}\t{strand}")

    file_path.write_text("\n".join(regions))
    return file_path


def create_mock_bam(file_path: Path, num_reads: int = 100) -> Path:
    """Create a mock BAM file for testing."""
    # For testing purposes, we just create a placeholder file
    # In a real scenario, you'd use samtools or similar to create a proper BAM
    file_path.write_text("BAM\x01")  # Minimal BAM header
    return file_path


def create_mock_bigwig(file_path: Path, num_entries: int = 100) -> Path:
    """Create a mock BigWig file for testing."""
    # For testing purposes, we just create a placeholder file
    # In a real scenario, you'd use appropriate tools to create a proper BigWig
    file_path.write_text("bigWig\x01")  # Minimal BigWig header
    return file_path
