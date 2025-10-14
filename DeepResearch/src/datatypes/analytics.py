"""
Analytics data types for DeepCritical research workflows.

This module defines Pydantic models for analytics operations including
request tracking, data retrieval, and metrics collection.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AnalyticsRequest(BaseModel):
    """Request model for analytics operations."""

    duration: float | None = Field(None, description="Request duration in seconds")
    num_results: int | None = Field(None, description="Number of results processed")

    model_config = ConfigDict(
        json_schema_extra={"example": {"duration": 2.5, "num_results": 4}}
    )


class AnalyticsResponse(BaseModel):
    """Response model for analytics operations."""

    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Operation result message")
    error: str | None = Field(None, description="Error message if operation failed")

    model_config = ConfigDict(json_schema_extra={})


class AnalyticsDataRequest(BaseModel):
    """Request model for analytics data retrieval."""

    days: int = Field(30, description="Number of days to retrieve data for")

    model_config = ConfigDict(json_schema_extra={"example": {"days": 30}})


class AnalyticsDataResponse(BaseModel):
    """Response model for analytics data retrieval."""

    data: list[dict[str, Any]] = Field(..., description="Analytics data")
    success: bool = Field(..., description="Whether the operation was successful")
    error: str | None = Field(None, description="Error message if operation failed")

    model_config = ConfigDict(json_schema_extra={})
