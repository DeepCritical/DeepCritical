"""
DeepAgent Tools - Pydantic models for DeepAgent tool operations.

This module defines Pydantic models for DeepAgent tool requests, responses,
and related data structures that align with DeepCritical's architecture.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class WriteTodosRequest(BaseModel):
    """Request for writing todos."""

    todos: list[dict[str, Any]] = Field(..., description="List of todos to write")

    @field_validator("todos")
    @classmethod
    def validate_todos(cls, v):
        if not v:
            msg = "Todos list cannot be empty"
            raise ValueError(msg)
        for todo in v:
            if not isinstance(todo, dict):
                msg = "Each todo must be a dictionary"
                raise ValueError(msg)
            if "content" not in todo:
                msg = "Each todo must have 'content' field"
                raise ValueError(msg)
        return v


class WriteTodosResponse(BaseModel):
    """Response from writing todos."""

    success: bool = Field(..., description="Whether operation succeeded")
    todos_created: int = Field(..., description="Number of todos created")
    message: str = Field(..., description="Response message")


class ListFilesResponse(BaseModel):
    """Response from listing files."""

    files: list[str] = Field(..., description="List of file paths")
    count: int = Field(..., description="Number of files")


class ReadFileRequest(BaseModel):
    """Request for reading a file."""

    file_path: str = Field(..., description="Path to the file to read")
    offset: int = Field(0, ge=0, description="Line offset to start reading from")
    limit: int = Field(2000, gt=0, description="Maximum number of lines to read")

    @field_validator("file_path")
    @classmethod
    def validate_file_path(cls, v):
        if not v or not v.strip():
            msg = "File path cannot be empty"
            raise ValueError(msg)
        return v.strip()


class ReadFileResponse(BaseModel):
    """Response from reading a file."""

    content: str = Field(..., description="File content")
    file_path: str = Field(..., description="File path")
    lines_read: int = Field(..., description="Number of lines read")
    total_lines: int = Field(..., description="Total lines in file")


class WriteFileRequest(BaseModel):
    """Request for writing a file."""

    file_path: str = Field(..., description="Path to the file to write")
    content: str = Field(..., description="Content to write to the file")

    @field_validator("file_path")
    @classmethod
    def validate_file_path(cls, v):
        if not v or not v.strip():
            msg = "File path cannot be empty"
            raise ValueError(msg)
        return v.strip()


class WriteFileResponse(BaseModel):
    """Response from writing a file."""

    success: bool = Field(..., description="Whether operation succeeded")
    file_path: str = Field(..., description="File path")
    bytes_written: int = Field(..., description="Number of bytes written")
    message: str = Field(..., description="Response message")


class EditFileRequest(BaseModel):
    """Request for editing a file."""

    file_path: str = Field(..., description="Path to the file to edit")
    old_string: str = Field(..., description="String to replace")
    new_string: str = Field(..., description="Replacement string")
    replace_all: bool = Field(False, description="Whether to replace all occurrences")

    @field_validator("file_path")
    @classmethod
    def validate_file_path(cls, v):
        if not v or not v.strip():
            msg = "File path cannot be empty"
            raise ValueError(msg)
        return v.strip()

    @field_validator("old_string")
    @classmethod
    def validate_old_string(cls, v):
        if not v:
            msg = "Old string cannot be empty"
            raise ValueError(msg)
        return v


class EditFileResponse(BaseModel):
    """Response from editing a file."""

    success: bool = Field(..., description="Whether operation succeeded")
    file_path: str = Field(..., description="File path")
    replacements_made: int = Field(..., description="Number of replacements made")
    message: str = Field(..., description="Response message")


class TaskRequestModel(BaseModel):
    """Request for task execution."""

    description: str = Field(..., description="Task description")
    subagent_type: str = Field(..., description="Type of subagent to use")
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Task parameters"
    )

    @field_validator("description")
    @classmethod
    def validate_description(cls, v):
        if not v or not v.strip():
            msg = "Task description cannot be empty"
            raise ValueError(msg)
        return v.strip()

    @field_validator("subagent_type")
    @classmethod
    def validate_subagent_type(cls, v):
        if not v or not v.strip():
            msg = "Subagent type cannot be empty"
            raise ValueError(msg)
        return v.strip()


class TaskResponse(BaseModel):
    """Response from task execution."""

    success: bool = Field(..., description="Whether task succeeded")
    task_id: str = Field(..., description="Task identifier")
    result: dict[str, Any] | None = Field(None, description="Task result")
    message: str = Field(..., description="Response message")
