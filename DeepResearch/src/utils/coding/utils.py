"""
Utilities for code execution in DeepCritical.

Adapted from AG2 coding utilities for use in DeepCritical's code execution system.
"""

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _get_file_name_from_content(code: str, work_dir: Path) -> str | None:
    """Extract filename from code content comments, similar to AutoGen implementation."""
    lines = code.split("\n")
    for line in lines[:10]:  # Check first 10 lines
        line = line.strip()
        if line.startswith(("# filename:", "# file:")):
            filename = line.split(":", 1)[1].strip()
            # Basic validation - ensure it's a valid filename
            if filename and not filename.startswith("/") and ".." not in filename:
                return filename
    return None


def silence_pip(*args, **kwargs) -> dict[str, Any]:
    """Silence pip output when installing packages."""
    # This would implement pip silencing logic
    # For now, just return empty result
    return {"returncode": 0, "stdout": "", "stderr": ""}
