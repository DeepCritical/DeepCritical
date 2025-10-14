"""
Base classes and protocols for code execution in DeepCritical.

Adapted from AG2 coding framework for use in DeepCritical's code execution system.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal, Protocol, TypedDict, runtime_checkable

from pydantic import BaseModel, Field

from DeepResearch.src.datatypes.ag_types import (
    UserMessageImageContentPart,
    UserMessageTextContentPart,
)


class CodeBlock(BaseModel):
    """A class that represents a code block for execution."""

    code: str = Field(description="The code to execute.")
    language: str = Field(description="The language of the code.")


class CodeResult(BaseModel):
    """A class that represents the result of a code execution."""

    exit_code: int = Field(description="The exit code of the code execution.")
    output: str = Field(description="The output of the code execution.")


class IPythonCodeResult(CodeResult):
    """A code result class for IPython code executor."""

    output_files: list[str] = Field(
        default_factory=list,
        description="The list of files that the executed code blocks generated.",
    )


class CommandLineCodeResult(CodeResult):
    """A code result class for command line code executor."""

    code_file: str | None = Field(
        default=None,
        description="The file that the executed code block was saved to.",
    )
    command: str = Field(description="The command that was executed.")
    image: str | None = Field(None, description="The Docker image used for execution.")


class CodeExtractor(Protocol):
    """A code extractor class that extracts code blocks from a message."""

    def extract_code_blocks(
        self,
        message: str
        | list[UserMessageTextContentPart | UserMessageImageContentPart]
        | None,
    ) -> list[CodeBlock]:
        """Extract code blocks from a message.

        Args:
            message (str): The message to extract code blocks from.

        Returns:
            List[CodeBlock]: The extracted code blocks.
        """
        ...  # pragma: no cover


@runtime_checkable
class CodeExecutor(Protocol):
    """A code executor class that executes code blocks and returns the result."""

    @property
    def code_extractor(self) -> CodeExtractor:
        """The code extractor used by this code executor."""
        ...  # pragma: no cover

    def execute_code_blocks(self, code_blocks: list[CodeBlock]) -> CodeResult:
        """Execute code blocks and return the result.

        This method should be implemented by the code executor.

        Args:
            code_blocks (List[CodeBlock]): The code blocks to execute.

        Returns:
            CodeResult: The result of the code execution.
        """
        ...  # pragma: no cover

    def restart(self) -> None:
        """Restart the code executor.

        This method should be implemented by the code executor.

        This method is called when the agent is reset.
        """
        ...  # pragma: no cover


CodeExecutionConfig = TypedDict(
    "CodeExecutionConfig",
    {
        "executor": Literal[
            "ipython-embedded", "commandline-local", "yepcode", "docker"
        ]
        | CodeExecutor,
        "last_n_messages": int | Literal["auto"],
        "timeout": int,
        "use_docker": bool | str | list[str],
        "work_dir": str,
        "ipython-embedded": Mapping[str, Any],
        "commandline-local": Mapping[str, Any],
        "commandline-docker": Mapping[str, Any],
        "yepcode": Mapping[str, Any],
    },
    total=False,
)
