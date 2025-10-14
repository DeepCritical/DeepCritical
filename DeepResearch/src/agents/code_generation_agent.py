"""
Code Generation Agent for DeepCritical.

This agent generates bash commands or Python scripts from natural language descriptions,
using the vendored AG2 code execution framework for execution.
"""

from __future__ import annotations

from typing import Any

from pydantic_ai import Agent

from DeepResearch.src.datatypes.agent_framework_content import TextContent
from DeepResearch.src.datatypes.agent_framework_types import (
    AgentRunResponse,
    ChatMessage,
    Role,
)
from DeepResearch.src.datatypes.agents import AgentDependencies, AgentResult, AgentType
from DeepResearch.src.datatypes.coding_base import CodeBlock
from DeepResearch.src.prompts.code_exec import CodeExecPrompts
from DeepResearch.src.prompts.code_sandbox import CodeSandboxPrompts


class CodeGenerationAgent:
    """Agent that generates code (bash commands or Python scripts) from natural language."""

    def __init__(
        self,
        model_name: str = "anthropic:claude-sonnet-4-0",
        max_retries: int = 3,
        timeout: float = 60.0,
    ):
        """Initialize the code generation agent.

        Args:
            model_name: The model to use for code generation
            max_retries: Maximum number of generation retries
            timeout: Timeout for generation
        """
        self.model_name = model_name
        self.max_retries = max_retries
        self.timeout = timeout

        # Initialize Pydantic AI agents for different code types
        self.bash_agent = self._create_bash_agent()
        self.python_agent = self._create_python_agent()
        self.universal_agent = self._create_universal_agent()

    def _create_bash_agent(self) -> Agent:
        """Create agent specialized for bash command generation."""
        system_prompt = """
        You are an expert bash/shell scripting agent. Your task is to generate safe, efficient bash commands
        that accomplish the user's request.

        Guidelines:
        1. Generate bash commands that are safe to execute
        2. Use appropriate flags and options for robustness
        3. Include error handling where appropriate
        4. Prefer modern bash features but maintain compatibility
        5. Return ONLY the bash command(s) as plain text, no markdown formatting

        Examples:
        - User: "list all files in current directory"
          Response: ls -la

        - User: "find all Python files modified in last 7 days"
          Response: find . -name "*.py" -mtime -7 -type f

        - User: "create a backup of my config file"
          Response: cp config.json config.json.backup && echo "Backup created: config.json.backup"
        """

        return Agent(
            model=self.model_name,
            system_prompt=system_prompt,
        )

    def _create_python_agent(self) -> Agent:
        """Create agent specialized for Python code generation."""
        system_prompt = """
        You are an expert Python programmer. Your task is to generate Python code that accomplishes
        the user's request.

        Guidelines:
        1. Generate clean, readable, and efficient Python code
        2. Include appropriate imports
        3. Add docstrings and comments for clarity
        4. Handle edge cases and errors appropriately
        5. Use modern Python features (type hints, f-strings, etc.)
        6. Return ONLY the Python code as plain text, no markdown formatting

        Examples:
        - User: "calculate the factorial of a number"
          Response:
          def factorial(n: int) -> int:
              \"\"\"Calculate the factorial of a number.\"\"\"
              if n < 0:
                  raise ValueError("Factorial is not defined for negative numbers")
              if n == 0 or n == 1:
                  return 1
              return n * factorial(n - 1)

        - User: "read a CSV file and calculate column averages"
          Response:
          import csv
          from typing import Dict, List

          def calculate_column_averages(filename: str) -> Dict[str, float]:
              \"\"\"Calculate average values for each numeric column in a CSV file.\"\"\"
              with open(filename, 'r') as f:
                  reader = csv.DictReader(f)
                  data = list(reader)

              if not data:
                  return {}

              # Get numeric columns
              numeric_columns = []
              for key, value in data[0].items():
                  try:
                      float(value)
                      numeric_columns.append(key)
                  except (ValueError, TypeError):
                      continue

              averages = {}
              for col in numeric_columns:
                  values = []
                  for row in data:
                      try:
                          values.append(float(row[col]))
                      except (ValueError, TypeError):
                          continue
                  averages[col] = sum(values) / len(values) if values else 0.0

              return averages
        """

        return Agent(
            model=self.model_name,
            system_prompt=system_prompt,
        )

    def _create_universal_agent(self) -> Agent:
        """Create universal agent that determines code type and generates appropriately."""
        system_prompt = """
        You are an expert code generation agent. Analyze the user's request and determine whether
        they need a bash/shell command or Python code, then generate the appropriate solution.

        First, classify the request:
        - Use BASH for: file operations, system administration, data processing with command-line tools
        - Use PYTHON for: complex logic, data analysis, calculations, custom algorithms, API interactions

        Then generate the appropriate code following these guidelines:

        For BASH commands:
        - Generate safe, efficient bash commands
        - Use appropriate flags and options
        - Include error handling
        - Return ONLY the bash command(s) as plain text

        For PYTHON code:
        - Generate clean, readable Python code
        - Include imports and type hints
        - Add error handling
        - Return ONLY the Python code as plain text

        Response format:
        TYPE: [BASH|PYTHON]
        CODE: [your generated code here]
        """

        return Agent(
            model=self.model_name,
            system_prompt=system_prompt,
        )

    async def generate_bash_command(self, description: str) -> str:
        """Generate a bash command from natural language description.

        Args:
            description: Natural language description of the desired operation

        Returns:
            Generated bash command as string
        """
        result = await self.bash_agent.run(
            f"Generate a bash command for: {description}"
        )
        return str(result.data).strip()

    async def generate_python_code(self, description: str) -> str:
        """Generate Python code from natural language description.

        Args:
            description: Natural language description of the desired operation

        Returns:
            Generated Python code as string
        """
        result = await self.python_agent.run(f"Generate Python code for: {description}")
        return str(result.data).strip()

    async def generate_code(
        self, description: str, code_type: str | None = None
    ) -> tuple[str, str]:
        """Generate code from natural language description.

        Args:
            description: Natural language description of the desired operation
            code_type: Type of code to generate ("bash", "python", or None for auto-detection)

        Returns:
            Tuple of (code_type, generated_code)
        """
        if code_type == "bash":
            code = await self.generate_bash_command(description)
            return "bash", code
        if code_type == "python":
            code = await self.generate_python_code(description)
            return "python", code
        # Use universal agent to determine type and generate
        result = await self.universal_agent.run(
            f"Analyze and generate code for: {description}"
        )
        response = str(result.data).strip()

        # Parse response format: TYPE: [BASH|PYTHON]\nCODE: [code]
        lines = response.split("\n", 2)
        if len(lines) >= 2:
            type_line = lines[0]
            code_line = lines[1] if len(lines) > 1 else ""

            if type_line.startswith("TYPE:"):
                detected_type = type_line.split("TYPE:", 1)[1].strip().lower()
                if code_line.startswith("CODE:"):
                    code = code_line.split("CODE:", 1)[1].strip()
                    return detected_type, code

        # Fallback: try to infer from content
        if any(
            keyword in description.lower()
            for keyword in [
                "file",
                "directory",
                "list",
                "find",
                "copy",
                "move",
                "delete",
                "system",
            ]
        ):
            code = await self.generate_bash_command(description)
            return "bash", code
        code = await self.generate_python_code(description)
        return "python", code

    def create_code_block(self, code: str, language: str) -> CodeBlock:
        """Create a CodeBlock from generated code.

        Args:
            code: The generated code
            language: The language of the code

        Returns:
            CodeBlock instance
        """
        return CodeBlock(code=code, language=language)

    async def generate_and_create_block(
        self, description: str, code_type: str | None = None
    ) -> tuple[str, CodeBlock]:
        """Generate code and create a CodeBlock.

        Args:
            description: Natural language description
            code_type: Optional code type specification

        Returns:
            Tuple of (code_type, CodeBlock)
        """
        language, code = await self.generate_code(description, code_type)
        block = self.create_code_block(code, language)
        return language, block


class CodeExecutionAgent:
    """Agent that executes generated code using the AG2 execution framework."""

    def __init__(
        self,
        model_name: str = "anthropic:claude-sonnet-4-0",
        use_docker: bool = True,
        use_jupyter: bool = False,
        jupyter_config: dict[str, Any] | None = None,
        max_retries: int = 3,
        timeout: float = 60.0,
    ):
        """Initialize the code execution agent.

        Args:
            model_name: Model for execution analysis
            use_docker: Whether to use Docker for execution
            use_jupyter: Whether to use Jupyter for execution
            jupyter_config: Jupyter connection configuration
            max_retries: Maximum execution retries
            timeout: Execution timeout
        """
        self.model_name = model_name
        self.use_docker = use_docker
        self.use_jupyter = use_jupyter
        self.jupyter_config = jupyter_config or {}
        self.max_retries = max_retries
        self.timeout = timeout

        # Import execution utilities
        from DeepResearch.src.utils.coding import (
            DockerCommandLineCodeExecutor,
            LocalCommandLineCodeExecutor,
        )
        from DeepResearch.src.utils.jupyter import JupyterCodeExecutor
        from DeepResearch.src.utils.python_code_execution import PythonCodeExecutionTool

        # Initialize executors
        self.docker_executor = (
            DockerCommandLineCodeExecutor(timeout=int(timeout)) if use_docker else None
        )

        self.local_executor = LocalCommandLineCodeExecutor(timeout=int(timeout))

        self.jupyter_executor = None
        if use_jupyter:
            from DeepResearch.src.utils.jupyter.base import JupyterConnectionInfo

            conn_info = JupyterConnectionInfo(**self.jupyter_config)
            self.jupyter_executor = JupyterCodeExecutor(conn_info)

        self.python_tool = PythonCodeExecutionTool(
            timeout=int(timeout), use_docker=use_docker
        )

    def _get_executor(self, language: str):
        """Get the appropriate executor for the language."""
        if language == "python" and self.python_tool:
            return self.python_tool
        if self.use_jupyter and self.jupyter_executor:
            return self.jupyter_executor
        if self.use_docker and self.docker_executor:
            return self.docker_executor
        return self.local_executor

    async def execute_code_block(self, code_block: CodeBlock) -> dict[str, Any]:
        """Execute a code block and return results.

        Args:
            code_block: CodeBlock to execute

        Returns:
            Dictionary with execution results
        """
        executor = self._get_executor(code_block.language)

        try:
            if hasattr(executor, "run"):  # PythonCodeExecutionTool
                result = executor.run(
                    {
                        "code": code_block.code,
                        "max_retries": self.max_retries,
                        "timeout": self.timeout,
                    }
                )
                return {
                    "success": result.success,
                    "output": result.data.get("output", "") if result.success else "",
                    "error": result.data.get("error", "") if not result.success else "",
                    "exit_code": 0 if result.success else 1,
                    "language": code_block.language,
                    "executor": "python_tool"
                    if code_block.language == "python"
                    else "local",
                }
            # CodeExecutor interface
            result = executor.execute_code_blocks([code_block])
            return {
                "success": result.exit_code == 0,
                "output": result.output,
                "error": "" if result.exit_code == 0 else result.output,
                "exit_code": result.exit_code,
                "language": code_block.language,
                "executor": "jupyter"
                if self.use_jupyter
                else ("docker" if self.use_docker else "local"),
            }

        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": f"Execution failed: {e!s}",
                "exit_code": 1,
                "language": code_block.language,
                "executor": "unknown",
            }

    async def execute_code(self, code: str, language: str) -> dict[str, Any]:
        """Execute code string directly.

        Args:
            code: Code to execute
            language: Language of the code

        Returns:
            Dictionary with execution results
        """
        code_block = CodeBlock(code=code, language=language)
        return await self.execute_code_block(code_block)


class CodeExecutionAgentSystem:
    """Complete agent system for code generation and execution."""

    def __init__(
        self,
        generation_model: str = "anthropic:claude-sonnet-4-0",
        execution_config: dict[str, Any] | None = None,
    ):
        """Initialize the complete code execution agent system.

        Args:
            generation_model: Model for code generation
            execution_config: Configuration for code execution
        """
        self.generation_model = generation_model
        self.execution_config = execution_config or {
            "use_docker": True,
            "use_jupyter": False,
            "max_retries": 3,
            "timeout": 60.0,
        }

        # Initialize agents
        self.generation_agent = CodeGenerationAgent(
            model_name=generation_model,
            max_retries=self.execution_config.get("max_retries", 3),
            timeout=self.execution_config.get("timeout", 60.0),
        )

        self.execution_agent = CodeExecutionAgent(
            model_name=generation_model, **self.execution_config
        )

    async def process_request(
        self, user_message: str, code_type: str | None = None
    ) -> AgentRunResponse:
        """Process a user request for code generation and execution.

        Args:
            user_message: Natural language description of desired operation
            code_type: Optional code type specification ("bash" or "python")

        Returns:
            AgentRunResponse with execution results
        """
        try:
            # Generate code
            detected_type, generated_code = await self.generation_agent.generate_code(
                user_message, code_type
            )

            # Execute code
            execution_result = await self.execution_agent.execute_code(
                generated_code, detected_type
            )

            # Format response
            messages = []

            # Add generation message
            generation_content = f"**Generated {detected_type.upper()} Code:**\n\n```python\n{generated_code}\n```"
            messages.append(
                ChatMessage(
                    role=Role.ASSISTANT, contents=[TextContent(text=generation_content)]
                )
            )

            # Add execution message
            if execution_result["success"]:
                execution_content = f"**Execution Successful**\n\n**Output:**\n```\n{execution_result['output']}\n```"
                if execution_result.get("executor"):
                    execution_content += (
                        f"\n\n**Executed using:** {execution_result['executor']}"
                    )
            else:
                execution_content = f"**Execution Failed**\n\n**Error:**\n```\n{execution_result['error']}\n```"

            messages.append(
                ChatMessage(
                    role=Role.ASSISTANT, contents=[TextContent(text=execution_content)]
                )
            )

            return AgentRunResponse(messages=messages)

        except Exception as e:
            # Error response
            error_content = f"**Error processing request:** {e!s}"
            messages = [
                ChatMessage(
                    role=Role.ASSISTANT, contents=[TextContent(text=error_content)]
                )
            ]
            return AgentRunResponse(messages=messages)
