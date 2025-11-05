"""Stub tools module for pydantic_ai."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Tool:
    """Placeholder tool structure."""

    name: str
    description: str | None = None
    metadata: dict[str, Any] | None = None
