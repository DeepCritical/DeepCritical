"""
Vendored usage types from agent_framework._types.

This module provides usage tracking types for AI agent interactions.
"""

from typing import Optional

from pydantic import BaseModel
from typing_extensions import Self


class UsageDetails(BaseModel):
    """Provides usage details about a request/response."""

    input_token_count: int | None = None
    output_token_count: int | None = None
    total_token_count: int | None = None
    additional_counts: dict[str, int] | None = None

    def __hash__(self) -> int:
        """Generate hash for the usage details."""
        return hash(
            (
                self.input_token_count,
                self.output_token_count,
                self.total_token_count,
                (
                    tuple(sorted(self.additional_counts.items()))
                    if self.additional_counts
                    else None
                ),
            )
        )

    def __init__(self, **kwargs):
        # Extract additional counts from kwargs
        additional_counts = {}
        for key, value in kwargs.items():
            if key not in [
                "input_token_count",
                "output_token_count",
                "total_token_count",
            ]:
                if not isinstance(value, int):
                    msg = f"Additional counts must be integers, got {type(value).__name__}"
                    raise ValueError(msg)
                additional_counts[key] = value

        super().__init__(
            input_token_count=kwargs.get("input_token_count"),
            output_token_count=kwargs.get("output_token_count"),
            total_token_count=kwargs.get("total_token_count"),
            additional_counts=additional_counts if additional_counts else None,
        )

    def __add__(self, other: Optional["UsageDetails"]) -> "UsageDetails":
        """Combines two UsageDetails instances."""
        if not other:
            return self
        if not isinstance(other, UsageDetails):
            msg = "Can only add two usage details objects together."
            raise ValueError(msg)

        additional_counts = {}
        if self.additional_counts:
            additional_counts.update(self.additional_counts)
        if other.additional_counts:
            for key, value in other.additional_counts.items():
                additional_counts[key] = additional_counts.get(key, 0) + (value or 0)

        return UsageDetails(
            input_token_count=(self.input_token_count or 0)
            + (other.input_token_count or 0),
            output_token_count=(self.output_token_count or 0)
            + (other.output_token_count or 0),
            total_token_count=(self.total_token_count or 0)
            + (other.total_token_count or 0),
            **additional_counts,
        )

    def __iadd__(self, other: Optional["UsageDetails"]) -> Self:
        """In-place addition of UsageDetails."""
        if not other:
            return self
        if not isinstance(other, UsageDetails):
            msg = "Can only add usage details objects together."
            raise ValueError(msg)

        self.input_token_count = (self.input_token_count or 0) + (
            other.input_token_count or 0
        )
        self.output_token_count = (self.output_token_count or 0) + (
            other.output_token_count or 0
        )
        self.total_token_count = (self.total_token_count or 0) + (
            other.total_token_count or 0
        )

        if other.additional_counts:
            if self.additional_counts is None:
                self.additional_counts = {}
            for key, value in other.additional_counts.items():
                self.additional_counts[key] = self.additional_counts.get(key, 0) + (
                    value or 0
                )

        return self

    def __eq__(self, other: object) -> bool:
        """Check if two UsageDetails instances are equal."""
        if not isinstance(other, UsageDetails):
            return False

        return (
            self.input_token_count == other.input_token_count
            and self.output_token_count == other.output_token_count
            and self.total_token_count == other.total_token_count
            and self.additional_counts == other.additional_counts
        )
