"""
Code Execution Orchestrator for DeepCritical.

This orchestrator coordinates the complete code generation and execution pipeline,
providing a high-level interface for natural language to executable code workflows.
"""

from __future__ import annotations

import time
from typing import Any

from pydantic import BaseModel, Field

from DeepResearch.src.agents.code_generation_agent import (
    CodeExecutionAgent,
    CodeExecutionAgentSystem,
    CodeGenerationAgent,
)
from DeepResearch.src.datatypes.agent_framework_types import AgentRunResponse
from DeepResearch.src.datatypes.agents import AgentDependencies, AgentResult, AgentType
from DeepResearch.src.statemachines.code_execution_workflow import CodeExecutionWorkflow


class CodeExecutionConfig(BaseModel):
    """Configuration for code execution orchestrator."""

    # Agent configuration
    generation_model: str = Field(
        "anthropic:claude-sonnet-4-0", description="Model for code generation"
    )

    # Execution configuration
    use_docker: bool = Field(True, description="Use Docker for execution")
    use_jupyter: bool = Field(False, description="Use Jupyter for execution")
    jupyter_config: dict[str, Any] = Field(
        default_factory=dict, description="Jupyter connection configuration"
    )

    # Retry and timeout configuration
    max_retries: int = Field(3, description="Maximum execution retries")
    generation_timeout: float = Field(60.0, description="Code generation timeout")
    execution_timeout: float = Field(60.0, description="Code execution timeout")
    max_improvement_attempts: int = Field(
        3, description="Maximum code improvement attempts"
    )
    enable_improvement: bool = Field(
        True, description="Enable automatic code improvement on errors"
    )

    # Workflow configuration
    use_workflow: bool = Field(True, description="Use state machine workflow")
    enable_adaptive_retry: bool = Field(True, description="Enable adaptive retry logic")

    # Environment configuration
    supported_environments: list[str] = Field(
        default_factory=lambda: ["python", "bash"],
        description="Supported execution environments",
    )
    default_environment: str = Field(
        "python", description="Default execution environment"
    )


class CodeExecutionOrchestrator:
    """Orchestrator for code generation and execution workflows."""

    def __init__(self, config: CodeExecutionConfig | None = None):
        """Initialize the code execution orchestrator.

        Args:
            config: Configuration for the orchestrator
        """
        self.config = config or CodeExecutionConfig()

        # Initialize agents
        self.generation_agent = CodeGenerationAgent(
            model_name=self.config.generation_model,
            max_retries=self.config.max_retries,
            timeout=self.config.generation_timeout,
        )

        self.execution_agent = CodeExecutionAgent(
            model_name=self.config.generation_model,
            use_docker=self.config.use_docker,
            use_jupyter=self.config.use_jupyter,
            jupyter_config=self.config.jupyter_config,
            max_retries=self.config.max_retries,
            timeout=self.config.execution_timeout,
        )

        # Initialize improvement agent
        from DeepResearch.src.agents.code_improvement_agent import CodeImprovementAgent

        self.improvement_agent = CodeImprovementAgent(
            model_name=self.config.generation_model,
            max_improvement_attempts=self.config.max_improvement_attempts,
        )

        self.agent_system = CodeExecutionAgentSystem(
            generation_model=self.config.generation_model,
            execution_config={
                "use_docker": self.config.use_docker,
                "use_jupyter": self.config.use_jupyter,
                "jupyter_config": self.config.jupyter_config,
                "max_retries": self.config.max_retries,
                "timeout": self.config.execution_timeout,
            },
        )

        # Initialize workflow
        self.workflow = CodeExecutionWorkflow() if self.config.use_workflow else None

    async def process_request(
        self,
        user_message: str,
        code_type: str | None = None,
        use_workflow: bool | None = None,
        **kwargs,
    ) -> AgentResult:
        """Process a user request for code generation and execution.

        Args:
            user_message: Natural language description of desired operation
            code_type: Optional code type specification ("bash", "python", or None for auto)
            use_workflow: Whether to use the state machine workflow (overrides config)
            **kwargs: Additional execution parameters

        Returns:
            AgentResult with execution outcome
        """
        start_time = time.time()

        try:
            # Determine whether to use workflow
            use_workflow_mode = (
                use_workflow if use_workflow is not None else self.config.use_workflow
            )

            if use_workflow_mode and self.workflow:
                # Use state machine workflow
                result = await self._execute_workflow(user_message, code_type, **kwargs)
            else:
                # Use direct agent system
                result = await self._execute_direct(user_message, code_type, **kwargs)

            execution_time = time.time() - start_time

            return AgentResult(
                success=result is not None,
                data={
                    "response": result,
                    "execution_time": execution_time,
                    "code_type": code_type,
                    "workflow_used": use_workflow_mode,
                }
                if result
                else {},
                metadata={
                    "orchestrator": "code_execution",
                    "generation_model": self.config.generation_model,
                    "execution_config": self.config.dict(),
                },
                error=None,
                execution_time=execution_time,
                agent_type=AgentType.EXECUTOR,
            )

        except Exception as e:
            execution_time = time.time() - start_time
            return AgentResult(
                success=False,
                data={},
                error=f"Orchestration failed: {e!s}",
                execution_time=execution_time,
                agent_type=AgentType.EXECUTOR,
            )

    async def _execute_workflow(
        self, user_message: str, code_type: str | None = None, **kwargs
    ) -> AgentRunResponse | None:
        """Execute using the state machine workflow."""
        workflow_config = {
            "use_docker": kwargs.get("use_docker", self.config.use_docker),
            "use_jupyter": kwargs.get("use_jupyter", self.config.use_jupyter),
            "jupyter_config": kwargs.get("jupyter_config", self.config.jupyter_config),
            "max_retries": kwargs.get("max_retries", self.config.max_retries),
            "timeout": kwargs.get("timeout", self.config.execution_timeout),
            "enable_improvement": kwargs.get(
                "enable_improvement", self.config.enable_improvement
            ),
            "max_improvement_attempts": kwargs.get(
                "max_improvement_attempts", self.config.max_improvement_attempts
            ),
        }

        state = await self.workflow.execute(
            user_query=user_message, code_type=code_type, **workflow_config
        )

        return state.final_response

    async def _execute_direct(
        self, user_message: str, code_type: str | None = None, **kwargs
    ) -> AgentRunResponse | None:
        """Execute using direct agent system calls."""
        return await self.agent_system.process_request(user_message, code_type)

    async def generate_code_only(
        self, user_message: str, code_type: str | None = None
    ) -> tuple[str, str]:
        """Generate code without executing it.

        Args:
            user_message: Natural language description
            code_type: Optional code type specification

        Returns:
            Tuple of (detected_code_type, generated_code)
        """
        return await self.generation_agent.generate_code(user_message, code_type)

    async def execute_code_only(
        self, code: str, language: str, **kwargs
    ) -> dict[str, Any]:
        """Execute code without generating it.

        Args:
            code: Code to execute
            language: Language of the code
            **kwargs: Execution parameters

        Returns:
            Execution results dictionary
        """
        return await self.execution_agent.execute_code(code, language)

    async def analyze_and_improve_code(
        self,
        code: str,
        error_message: str,
        language: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Analyze an error and improve the code.

        Args:
            code: The code that failed
            error_message: The error message from execution
            language: Language of the code
            context: Additional context

        Returns:
            Improvement results with analysis and improved code
        """
        # Analyze the error
        analysis = await self.improvement_agent.analyze_error(
            code=code, error_message=error_message, language=language, context=context
        )

        # Improve the code
        improvement = await self.improvement_agent.improve_code(
            original_code=code,
            error_message=error_message,
            language=language,
            context=context,
            improvement_focus="fix_errors",
        )

        return {
            "analysis": analysis,
            "improvement": improvement,
            "original_code": code,
            "improved_code": improvement["improved_code"],
            "language": language,
        }

    async def iterative_improve_and_execute(
        self,
        user_message: str,
        code_type: str | None = None,
        max_iterations: int = 3,
        **kwargs,
    ) -> AgentResult:
        """Iteratively improve and execute code until it works.

        Args:
            user_message: Natural language description
            code_type: Optional code type specification
            max_iterations: Maximum improvement iterations
            **kwargs: Additional execution parameters

        Returns:
            AgentResult with final successful execution or last attempt
        """
        # Generate initial code
        detected_type, generated_code = await self.generation_agent.generate_code(
            user_message, code_type
        )

        # Create test function that executes code and returns error or None
        async def test_execution(code: str, language: str) -> str | None:
            result = await self.execution_agent.execute_code(code, language)
            return result.get("error") if not result.get("success") else None

        # Iteratively improve the code
        improvement_result = await self.improvement_agent.iterative_improve(
            code=generated_code,
            language=detected_type,
            test_function=test_execution,
            max_iterations=max_iterations,
            context={
                "user_request": user_message,
                "code_type": detected_type,
            },
        )

        # Execute the final code one more time to get the result
        final_result = await test_execution(
            improvement_result["final_code"], detected_type
        )

        # Format the response
        messages = []
        from DeepResearch.src.datatypes.agent_framework_content import TextContent
        from DeepResearch.src.datatypes.agent_framework_types import ChatMessage, Role

        # Code message
        code_content = f"**Final {detected_type.upper()} Code:**\n\n```python\n{improvement_result['final_code']}\n```"
        messages.append(
            ChatMessage(role=Role.ASSISTANT, contents=[TextContent(text=code_content)])
        )

        # Result message
        if improvement_result["success"]:
            result_content = f"**✅ Success after {improvement_result['iterations_used']} iterations!**\n\n"
            result_content += f"**Execution Result:**\n```\n{final_result or 'Code executed successfully'}\n```"
        else:
            result_content = (
                f"**❌ Failed after {max_iterations} improvement attempts**\n\n"
            )
            result_content += (
                f"**Final Error:**\n```\n{final_result or 'Unknown error'}\n```"
            )

        # Add improvement summary
        if improvement_result["improvement_history"]:
            result_content += f"\n\n**Improvement Summary:** {len(improvement_result['improvement_history'])} fixes applied"

        messages.append(
            ChatMessage(
                role=Role.ASSISTANT, contents=[TextContent(text=result_content)]
            )
        )

        # Add detailed improvement history
        if improvement_result["improvement_history"]:
            history_content = "**Improvement History:**\n\n"
            for i, hist in enumerate(improvement_result["improvement_history"], 1):
                history_content += f"**Attempt {i}:**\n"
                history_content += f"- **Error:** {hist['error_message'][:100]}{'...' if len(hist['error_message']) > 100 else ''}\n"
                history_content += f"- **Fix:** {hist['improvement']['explanation'][:150]}{'...' if len(hist['improvement']['explanation']) > 150 else ''}\n\n"

            messages.append(
                ChatMessage(
                    role=Role.ASSISTANT, contents=[TextContent(text=history_content)]
                )
            )

        from DeepResearch.src.datatypes.agent_framework_types import AgentRunResponse

        return AgentResult(
            success=improvement_result["success"],
            data={
                "response": AgentRunResponse(messages=messages),
                "improvement_history": improvement_result["improvement_history"],
                "iterations_used": improvement_result["iterations_used"],
                "final_code": improvement_result["final_code"],
                "code_type": detected_type,
            },
            metadata={
                "orchestrator": "code_execution_improvement",
                "improvement_iterations": improvement_result["iterations_used"],
                "success": improvement_result["success"],
            },
            error=None if improvement_result["success"] else final_result,
            execution_time=0.0,  # Would need to track actual timing
            agent_type=AgentType.EXECUTOR,
        )

    def get_supported_environments(self) -> list[str]:
        """Get list of supported execution environments."""
        return self.config.supported_environments.copy()

    def update_config(self, **kwargs) -> None:
        """Update orchestrator configuration."""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)

        # Reinitialize agents if necessary
        if any(
            key in kwargs
            for key in ["generation_model", "max_retries", "generation_timeout"]
        ):
            self.generation_agent = CodeGenerationAgent(
                model_name=self.config.generation_model,
                max_retries=self.config.max_retries,
                timeout=self.config.generation_timeout,
            )

        if any(
            key in kwargs
            for key in [
                "use_docker",
                "use_jupyter",
                "jupyter_config",
                "max_retries",
                "execution_timeout",
            ]
        ):
            self.execution_agent = CodeExecutionAgent(
                model_name=self.config.generation_model,
                use_docker=self.config.use_docker,
                use_jupyter=self.config.use_jupyter,
                jupyter_config=self.config.jupyter_config,
                max_retries=self.config.max_retries,
                timeout=self.config.execution_timeout,
            )

    def get_config(self) -> dict[str, Any]:
        """Get current configuration."""
        return self.config.dict()


# Convenience functions for common use cases
async def execute_bash_command(description: str, **kwargs) -> AgentResult:
    """Execute a bash command described in natural language."""
    orchestrator = CodeExecutionOrchestrator()
    return await orchestrator.process_request(description, code_type="bash", **kwargs)


async def execute_python_script(description: str, **kwargs) -> AgentResult:
    """Execute a Python script described in natural language."""
    orchestrator = CodeExecutionOrchestrator()
    return await orchestrator.process_request(description, code_type="python", **kwargs)


async def execute_auto_code(description: str, **kwargs) -> AgentResult:
    """Automatically determine and execute appropriate code type."""
    orchestrator = CodeExecutionOrchestrator()
    return await orchestrator.process_request(description, code_type=None, **kwargs)


# Factory function for creating configured orchestrators
def create_code_execution_orchestrator(
    generation_model: str = "anthropic:claude-sonnet-4-0",
    use_docker: bool = True,
    use_jupyter: bool = False,
    max_retries: int = 3,
    **kwargs,
) -> CodeExecutionOrchestrator:
    """Create a configured code execution orchestrator.

    Args:
        generation_model: Model for code generation
        use_docker: Whether to use Docker execution
        use_jupyter: Whether to use Jupyter execution
        max_retries: Maximum retry attempts
        **kwargs: Additional configuration options

    Returns:
        Configured CodeExecutionOrchestrator instance
    """
    config = CodeExecutionConfig(
        generation_model=generation_model,
        use_docker=use_docker,
        use_jupyter=use_jupyter,
        max_retries=max_retries,
        **kwargs,
    )

    return CodeExecutionOrchestrator(config)


# Command-line interface functions
async def process_message_to_command_log(message: str) -> str:
    """Process a natural language message and return the command execution log.

    This is the main entry point for the agent system that takes messages
    and returns command logs as specified in the requirements.

    Args:
        message: Natural language description of desired operation

    Returns:
        Formatted command execution log
    """
    orchestrator = create_code_execution_orchestrator()

    result = await orchestrator.process_request(message)

    if result.success and result.data.get("response"):
        response = result.data["response"]
        # Extract text content from the response
        log_lines = []
        for msg in response.messages:
            if hasattr(msg, "text") and msg.text:
                log_lines.append(msg.text)

        return "\n\n".join(log_lines)
    return f"Command execution failed: {result.error}"


async def run_code_execution_agent(message: str) -> dict[str, Any]:
    """Run the code execution agent system and return structured results.

    Args:
        message: Natural language description of desired operation

    Returns:
        Dictionary with complete execution results
    """
    from DeepResearch.src.statemachines.code_execution_workflow import (
        generate_and_execute_code,
    )

    return await generate_and_execute_code(message)
