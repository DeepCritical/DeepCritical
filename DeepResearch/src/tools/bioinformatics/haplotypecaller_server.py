"""
GATK HaplotypeCaller MCP Server.

Wraps GATK HaplotypeCaller CLI for variant calling.
Container: quay.io/biocontainers/gatk4:4.6.1.0--hdfd78af_0
"""

from __future__ import annotations

import asyncio
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from DeepResearch.src.datatypes.bioinformatics_mcp import MCPServerBase
from DeepResearch.src.datatypes.mcp import (
    MCPServerConfig,
    MCPServerDeployment,
    MCPServerStatus,
)


class HaplotypeCallerServer(MCPServerBase):
    """GATK HaplotypeCaller MCP Server.

    Wraps GATK HaplotypeCaller CLI for variant calling.
    Container: quay.io/biocontainers/gatk4:4.6.1.0--hdfd78af_0
    """

    def __init__(self, config: MCPServerConfig | None = None):
        """Initialize with GATK config."""
        default_config = MCPServerConfig(
            server_name="haplotypecaller",
            container_image="quay.io/biocontainers/gatk4:4.6.1.0--hdfd78af_0",
            environment_variables={},
        )
        super().__init__(config or default_config)

    def call_variants(
        self,
        input_bam: str,
        reference_fasta: str,
        output_vcf: str,
        dbsnp: str | None = None,
        intervals: str | None = None,
        ploidy: int = 2,
        threads: int = 1,
    ) -> dict[str, Any]:
        """Call variants in VCF mode.

        Args:
            input_bam: Path to indexed BAM/CRAM file
            reference_fasta: Path to reference genome (.fa + .fai + .dict required)
            output_vcf: Path for output VCF file
            dbsnp: Optional dbSNP database for variant annotation
            intervals: Optional genomic intervals (chr:start-end)
            ploidy: Sample ploidy (default: 2)
            threads: Native HMM threads (default: 1)

        Returns:
            dict with keys: success, command, stdout, stderr, exit_code, output_file
        """
        # Validation
        self._validate_reference_files(reference_fasta)
        self._validate_alignment_file(input_bam)
        self._validate_ploidy(ploidy)

        # Command building (pure function)
        command = self._build_command(
            operation="call_variants",
            input_bam=input_bam,
            reference_fasta=reference_fasta,
            output_vcf=output_vcf,
            dbsnp=dbsnp,
            intervals=intervals,
            ploidy=ploidy,
            threads=threads,
        )

        # Execution
        return self._run_command(command, output_file=output_vcf)

    def call_gvcf(
        self,
        input_bam: str,
        reference_fasta: str,
        output_gvcf: str,
        dbsnp: str | None = None,
        intervals: str | None = None,
        threads: int = 1,
    ) -> dict[str, Any]:
        """Call variants in GVCF mode (for joint calling).

        Args:
            input_bam: Path to indexed BAM/CRAM file
            reference_fasta: Path to reference genome (.fa + .fai + .dict required)
            output_gvcf: Path for output GVCF file
            dbsnp: Optional dbSNP database
            intervals: Optional genomic intervals
            threads: Native HMM threads (default: 1)

        Returns:
            dict with keys: success, command, stdout, stderr, exit_code, output_file
        """
        self._validate_reference_files(reference_fasta)
        self._validate_alignment_file(input_bam)

        command = self._build_command(
            operation="call_gvcf",
            input_bam=input_bam,
            reference_fasta=reference_fasta,
            output_gvcf=output_gvcf,
            dbsnp=dbsnp,
            intervals=intervals,
            threads=threads,
        )

        return self._run_command(command, output_file=output_gvcf)

    def get_version(self) -> dict[str, Any]:
        """Get GATK version."""
        return self._run_command(["gatk", "--version"])

    def _build_command(self, operation: str, **kwargs) -> list[str]:
        """Build GATK command (PURE FUNCTION - easily testable).

        Args:
            operation: "call_variants" or "call_gvcf"
            **kwargs: Operation parameters

        Returns:
            List of command arguments
        """
        command = ["gatk", "HaplotypeCaller"]

        # Required flags (short form)
        command.extend(["-I", kwargs["input_bam"]])
        command.extend(["-R", kwargs["reference_fasta"]])

        # Output - operation specific
        if operation == "call_variants":
            command.extend(["-O", kwargs["output_vcf"]])
        elif operation == "call_gvcf":
            command.extend(["-O", kwargs["output_gvcf"]])
            command.extend(["-ERC", "GVCF"])  # Emit reference confidence

        # Optional parameters
        if kwargs.get("dbsnp"):
            command.extend(["--dbsnp", kwargs["dbsnp"]])
        if kwargs.get("intervals"):
            command.extend(["-L", kwargs["intervals"]])

        # Always set ploidy and threads
        command.extend(["--sample-ploidy", str(kwargs.get("ploidy", 2))])
        command.extend(["--native-pair-hmm-threads", str(kwargs.get("threads", 1))])

        return command

    def _run_command(
        self, command: list[str], output_file: str | None = None
    ) -> dict[str, Any]:
        """Execute GATK command via subprocess.

        Args:
            command: Command to execute
            output_file: Optional expected output file

        Returns:
            Structured result dict
        """
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
                timeout=3600,  # 1 hour max
            )

            return {
                "success": True,
                "command": command,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode,
                "output_file": output_file,
            }

        except FileNotFoundError as e:
            return {
                "success": False,
                "command": command,
                "error": f"GATK not found: {e}. Install GATK or run in container.",
                "exit_code": -1,
                "output_file": output_file,
            }
        except subprocess.CalledProcessError as e:
            return {
                "success": False,
                "command": command,
                "stdout": e.stdout,
                "stderr": e.stderr,
                "exit_code": e.returncode,
                "error": str(e),
                "output_file": output_file,
            }
        except subprocess.TimeoutExpired as e:
            return {
                "success": False,
                "command": command,
                "error": f"Command timeout after 1 hour: {e}",
                "exit_code": -1,
            }

    def _validate_reference_files(self, reference_fasta: str) -> None:
        """Validate reference genome has ALL required files.

        GATK requires:
        - ref.fa (FASTA file)
        - ref.fa.fai (FASTA index)
        - ref.dict (sequence dictionary)

        Raises:
            ValueError: If any required file is missing
        """
        if not reference_fasta:
            raise ValueError("reference_fasta is required")

        ref_path = Path(reference_fasta)
        fai_path = Path(f"{reference_fasta}.fai")
        dict_path = ref_path.with_suffix(".dict")

        if not ref_path.exists():
            raise ValueError(f"Reference FASTA not found: {reference_fasta}")

        if not fai_path.exists():
            raise ValueError(
                f"Reference FASTA index not found: {fai_path}\n"
                f"Create with: samtools faidx {reference_fasta}"
            )

        if not dict_path.exists():
            raise ValueError(
                f"Reference sequence dictionary not found: {dict_path}\n"
                f"Create with: gatk CreateSequenceDictionary -R {reference_fasta}"
            )

    def _validate_alignment_file(self, input_bam: str) -> None:
        """Validate BAM/CRAM file is indexed.

        Raises:
            ValueError: If file missing or not indexed
        """
        if not input_bam:
            raise ValueError("input_bam is required")

        bam_path = Path(input_bam)

        if not bam_path.exists():
            raise ValueError(f"Alignment file not found: {input_bam}")

        # Check for index
        if input_bam.endswith(".bam"):
            index_path = Path(f"{input_bam}.bai")
            if not index_path.exists():
                raise ValueError(
                    f"BAM index not found: {index_path}\n"
                    f"Create with: samtools index {input_bam}"
                )
        elif input_bam.endswith(".cram"):
            index_path = Path(f"{input_bam}.crai")
            if not index_path.exists():
                raise ValueError(
                    f"CRAM index not found: {index_path}\n"
                    f"Create with: samtools index {input_bam}"
                )
        else:
            raise ValueError("input_bam must be .bam or .cram file")

    def _validate_ploidy(self, ploidy: int) -> None:
        """Validate ploidy value.

        Raises:
            ValueError: If ploidy invalid
        """
        if ploidy < 1:
            raise ValueError("ploidy must be >= 1")
        if ploidy > 100:
            raise ValueError("ploidy seems unreasonably high (> 100)")

    def list_tools(self) -> list[str]:
        """List available operations."""
        return ["call_variants", "call_gvcf", "get_version"]

    def run_tool(self, tool_name: str, **kwargs) -> Any:
        """Run operation by name (for MCP protocol)."""
        if tool_name == "call_variants":
            return self.call_variants(**kwargs)
        if tool_name == "call_gvcf":
            return self.call_gvcf(**kwargs)
        if tool_name == "get_version":
            return self.get_version()
        available = ", ".join(self.list_tools())
        raise ValueError(f"Unknown tool: {tool_name}. Available: {available}")

    async def deploy_with_testcontainers(self) -> MCPServerDeployment:
        """Deploy GATK HaplotypeCaller server using testcontainers."""
        try:
            from testcontainers.core.container import DockerContainer

            # Create container with GATK image
            container = DockerContainer(self.config.container_image)
            container.with_name(f"mcp-haplotypecaller-server-{id(self)}")

            # Start container
            container.start()

            # Wait for container to be ready
            container.reload()
            while container.status != "running":
                await asyncio.sleep(0.1)
                container.reload()

            # Store container info
            self.container_id = container.get_wrapped_container().id
            self.container_name = container.get_wrapped_container().name

            return MCPServerDeployment(
                server_name=self.name,
                server_type=self.server_type,
                container_id=self.container_id,
                container_name=self.container_name,
                status=MCPServerStatus.RUNNING,
                created_at=datetime.now(),
                started_at=datetime.now(),
                tools_available=self.list_tools(),
                configuration=self.config,
            )

        except Exception as e:
            return MCPServerDeployment(
                server_name=self.name,
                server_type=self.server_type,
                status=MCPServerStatus.FAILED,
                error_message=str(e),
                configuration=self.config,
            )

    async def stop_with_testcontainers(self) -> bool:
        """Stop GATK HaplotypeCaller server deployed with testcontainers."""
        try:
            if self.container_id:
                from testcontainers.core.container import DockerContainer

                container = DockerContainer(self.container_id)
                container.stop()

                self.container_id = None
                self.container_name = None

                return True
            return False
        except Exception:
            return False
