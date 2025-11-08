#!/usr/bin/env python3
"""GATK HaplotypeCaller End-to-End Demo

Demonstrates variant calling on real genomic data:

Pipeline:
1. FastQC: Quality control on BAM file
2. SAMtools: Verify BAM integrity and get stats
3. HaplotypeCaller: Call genetic variants
4. Output: VCF file with variants

Note: This demo starts with a pre-aligned BAM file. In production workflows,
you would first align FASTQ reads to the reference using tools like BWA or STAR.
"""

import sys
from pathlib import Path


def check_tools():
    """Verify required tools are installed."""
    import shutil

    required = ["gatk", "samtools", "fastqc"]
    missing = [tool for tool in required if not shutil.which(tool)]

    if missing:
        print("❌ Missing required tools:", ", ".join(missing))
        print()
        print("Please run: ./install_tools.sh")
        print("Then activate: conda activate genomics-demo")
        sys.exit(1)


def main():
    """Run the variant calling pipeline end-to-end."""
    print("🧬 GATK HaplotypeCaller End-to-End Demo")
    print("=" * 60)
    print()

    # Check tools
    print("🔍 Checking tools...")
    check_tools()
    print("✅ All tools found")
    print()

    # Setup paths
    data_dir = Path("data")
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    bam_file = data_dir / "sample.bam"
    reference = data_dir / "human_g1k_v37.20.21.fasta"
    output_vcf = output_dir / "variants.vcf"
    fastqc_out = output_dir

    # Validate inputs
    if not bam_file.exists():
        print(f"❌ BAM file not found: {bam_file}")
        print("Please run: ./download_data.sh")
        sys.exit(1)

    if not reference.exists():
        print(f"❌ Reference not found: {reference}")
        print("Please run: ./download_data.sh")
        sys.exit(1)

    print(f"Input BAM: {bam_file}")
    print(f"Reference: {reference}")
    print(f"Output VCF: {output_vcf}")
    print()

    # Step 1: Quality Control with FastQC
    print("=" * 60)
    print("📊 Step 1: Quality Control with FastQC")
    print("=" * 60)
    import subprocess

    try:
        subprocess.run(
            ["fastqc", str(bam_file), "-o", str(fastqc_out)],
            check=True,
            capture_output=True,
            text=True,
        )
        print("✅ FastQC complete")
        print(f"   Report: {fastqc_out}/sample_fastqc.html")
    except subprocess.CalledProcessError as e:
        print(f"❌ FastQC failed: {e.stderr}")
        sys.exit(1)

    print()

    # Step 2: Verify BAM with SAMtools
    print("=" * 60)
    print("🔍 Step 2: Verify BAM with SAMtools")
    print("=" * 60)

    try:
        result = subprocess.run(
            ["samtools", "flagstat", str(bam_file)],
            check=True,
            capture_output=True,
            text=True,
        )
        print("✅ BAM verification complete")
        print()
        print("Statistics:")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"❌ SAMtools failed: {e.stderr}")
        sys.exit(1)

    print()

    # Step 3: Call variants with GATK HaplotypeCaller
    print("=" * 60)
    print("🧬 Step 3: Call Variants with GATK HaplotypeCaller")
    print("=" * 60)
    print()
    print("This step may take 2-5 minutes...")
    print()

    try:
        subprocess.run(
            [
                "gatk",
                "HaplotypeCaller",
                "-I",
                str(bam_file),
                "-R",
                str(reference),
                "-O",
                str(output_vcf),
                "-L",
                "20",  # Only analyze chromosome 20
            ],
            check=True,
            capture_output=False,  # Show GATK output
        )
        print()
        print("✅ Variant calling complete!")
        print(f"   Output: {output_vcf}")
    except subprocess.CalledProcessError:
        print("❌ HaplotypeCaller failed")
        sys.exit(1)

    print()

    # Show results
    if output_vcf.exists():
        print("=" * 60)
        print("📄 Variants Found")
        print("=" * 60)

        with open(output_vcf) as f:
            lines = f.readlines()
            [line for line in lines if line.startswith("#")]
            variant_lines = [line for line in lines if not line.startswith("#")]

        print(f"Total variants: {len(variant_lines)}")
        print()
        print("First 20 variants:")
        print("-" * 60)

        for line in variant_lines[:20]:
            cols = line.strip().split("\t")
            if len(cols) >= 5:
                chrom = cols[0]
                pos = cols[1]
                ref = cols[3]
                alt = cols[4]
                qual = cols[5]
                print(f"  chr{chrom}:{pos:>9}  {ref:>5} → {alt:<5}  QUAL={qual}")

        print()
        print("=" * 60)
        print("🎉 Pipeline Complete!")
        print("=" * 60)
        print()
        print("Output files:")
        print(f"  - {fastqc_out}/sample_fastqc.html  (quality report)")
        print(f"  - {output_vcf}  ({len(variant_lines)} variants)")
        print()
        print("Next steps:")
        print("  - Annotate variants with VEP or SnpEff")
        print("  - Query ClinVar for clinical significance")
        print("  - Filter variants by quality thresholds")
        print("  - Integrate with DeepResearch agent workflows")


if __name__ == "__main__":
    main()
