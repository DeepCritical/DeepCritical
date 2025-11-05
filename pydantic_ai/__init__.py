"""Minimal stub of the pydantic_ai package required for tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass
class RunContext(Generic[T]):
    """Lightweight stand-in for pydantic_ai.RunContext."""

    deps: T | None = None


@dataclass
class Agent(Generic[T]):
    """Minimal placeholder agent used in type hints."""

    name: str | None = None
    context: RunContext[T] | None = None


__all__ = ["RunContext", "Agent"]
