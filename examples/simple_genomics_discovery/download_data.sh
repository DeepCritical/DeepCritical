#!/usr/bin/env bash
set -euo pipefail

echo "🧬 Downloading GATK HaplotypeCaller demo data (b37 build)"
echo "==========================================================="
echo ""

# Create data directory
mkdir -p data
cd data

# Download chr20+21 reference (108 MB) - b37 build
echo "📥 Downloading chr20+21 reference genome (108 MB, b37 build)..."
echo "   Source: s3://gatk-test-data/mutect2/human_g1k_v37.20.21.fasta"
aws s3 cp \
  s3://gatk-test-data/mutect2/human_g1k_v37.20.21.fasta \
  human_g1k_v37.20.21.fasta \
  --no-sign-request

# Download FASTA index
echo "📥 Downloading reference index (.fai)..."
aws s3 cp \
  s3://gatk-test-data/mutect2/human_g1k_v37.20.21.fasta.fai \
  human_g1k_v37.20.21.fasta.fai \
  --no-sign-request

# Download sequence dictionary
echo "📥 Downloading sequence dictionary (.dict)..."
aws s3 cp \
  s3://gatk-test-data/mutect2/human_g1k_v37.20.21.dict \
  human_g1k_v37.20.21.dict \
  --no-sign-request

echo ""

# Download test BAM (8.8 MB) - b37 build
echo "📥 Downloading test BAM file (8.8 MB, b37 build)..."
echo "   Sample: NA12878 (1000 Genomes reference individual)"
aws s3 cp \
  s3://gatk-test-data/wgs_bam/NA12878_20k_b37/NA12878_20k.b37.bam \
  sample.bam \
  --no-sign-request

# Download BAM index
echo "📥 Downloading BAM index (.bai)..."
aws s3 cp \
  s3://gatk-test-data/wgs_bam/NA12878_20k_b37/NA12878_20k.b37.bai \
  sample.bam.bai \
  --no-sign-request

echo ""
echo "✅ Download complete!"
echo ""
echo "Downloaded files:"
echo "  - human_g1k_v37.20.21.fasta      (108 MB) - chr20+21 reference"
echo "  - human_g1k_v37.20.21.fasta.fai  (48 B)   - FASTA index"
echo "  - human_g1k_v37.20.21.dict       (317 B)  - sequence dictionary"
echo "  - sample.bam                      (8.8 MB) - NA12878 test data"
echo "  - sample.bam.bai                  (small)  - BAM index"
echo ""
echo "Total: ~117 MB"
