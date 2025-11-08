"""Dependencies for genomics agent."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class GenomicsAgentDeps:
    """Dependencies for genomics agent execution."""

    data_dir: Path
    output_dir: Path
    reference_genome: Path
    config: dict[str, Any] = field(default_factory=dict)
    tools_called: list[str] = field(default_factory=list)
