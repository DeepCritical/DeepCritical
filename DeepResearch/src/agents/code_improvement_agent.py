"""
Code Improvement Agent for DeepCritical.

This agent analyzes execution errors and improves code/scripts based on error messages,
providing intelligent code fixes and optimizations.
"""

from __future__ import annotations

import re
from typing import Any

from pydantic_ai import Agent

from DeepResearch.src.datatypes.agents import AgentResult, AgentType
from DeepResearch.src.datatypes.coding_base import CodeBlock
from DeepResearch.src.prompts.code_exec import CodeExecPrompts
from DeepResearch.src.utils.code_utils import infer_lang


class CodeImprovementAgent:
    """Agent that analyzes errors and improves code/scripts."""

    def __init__(
        self,
        model_name: str = "anthropic:claude-sonnet-4-0",
        max_improvement_attempts: int = 3,
        timeout: float = 60.0,
    ):
        """Initialize the code improvement agent.

        Args:
            model_name: The model to use for code improvement
            max_improvement_attempts: Maximum number of improvement attempts
            timeout: Timeout for improvement operations
        """
        self.model_name = model_name
        self.max_improvement_attempts = max_improvement_attempts
        self.timeout = timeout

        # Initialize Pydantic AI agents
        self.improvement_agent = self._create_improvement_agent()
        self.analysis_agent = self._create_analysis_agent()
        self.optimization_agent = self._create_optimization_agent()

    def _create_improvement_agent(self) -> Agent:
        """Create agent specialized for fixing code errors."""
        system_prompt = """
        You are an expert code improvement agent. Your task is to analyze code execution errors
        and provide corrected, improved versions of the code.

        Guidelines:
        1. Analyze the error message carefully to understand the root cause
        2. Look at the original code and identify specific issues
        3. Provide corrected code that fixes the identified problems
        4. Include explanations of what was wrong and how it was fixed
        5. Suggest best practices and improvements beyond just fixing the error
        6. For bash commands, ensure proper error handling and safety
        7. For Python code, follow PEP 8 and include proper error handling
        8. Return ONLY the improved code as plain text, no markdown formatting

        Common error patterns to handle:
        - Syntax errors: missing imports, incorrect syntax, indentation issues
        - Runtime errors: undefined variables, type errors, index errors
        - Command errors: missing commands, permission issues, path problems
        - Logic errors: incorrect algorithms, edge cases not handled

        Response format:
        ANALYSIS: [brief analysis of the error]
        IMPROVED_CODE: [the corrected/improved code]
        EXPLANATION: [what was fixed and why]
        """

        return Agent(
            model=self.model_name,
            system_prompt=system_prompt,
        )

    def _create_analysis_agent(self) -> Agent:
        """Create agent specialized for error analysis."""
        system_prompt = """
        You are an expert error analysis agent. Your task is to analyze execution errors
        and provide detailed insights about what went wrong.

        Guidelines:
        1. Carefully analyze error messages and stack traces
        2. Identify the root cause of the error
        3. Consider the context of what the code was trying to accomplish
        4. Suggest specific fixes and improvements
        5. Provide actionable recommendations

        Focus on:
        - Error type classification (syntax, runtime, logical, environment)
        - Specific line/file where error occurred
        - Missing dependencies or imports
        - Incorrect assumptions about data or environment
        - Best practices violations

        Response format:
        ERROR_TYPE: [syntax/runtime/logical/environment]
        ROOT_CAUSE: [specific cause of the error]
        IMPACT: [what the error prevents]
        RECOMMENDATIONS: [specific steps to fix]
        PREVENTION: [how to avoid similar errors in future]
        """

        return Agent(
            model=self.model_name,
            system_prompt=system_prompt,
        )

    def _create_optimization_agent(self) -> Agent:
        """Create agent specialized for code optimization."""
        system_prompt = """
        You are an expert code optimization agent. Your task is to improve code
        for better performance, readability, and maintainability.

        Guidelines:
        1. Improve code efficiency and performance
        2. Enhance readability and maintainability
        3. Add proper error handling and validation
        4. Follow language-specific best practices
        5. Optimize resource usage (memory, CPU, I/O)
        6. Add comprehensive documentation

        Focus areas:
        - Algorithm optimization
        - Memory efficiency
        - Error handling improvements
        - Code structure and organization
        - Documentation and comments
        - Input validation and sanitization

        Response format:
        OPTIMIZATIONS: [list of improvements made]
        PERFORMANCE_IMPACT: [expected performance improvements]
        READABILITY_IMPROVEMENTS: [code clarity enhancements]
        ROBUSTNESS_IMPROVEMENTS: [error handling and validation additions]
        """

        return Agent(
            model=self.model_name,
            system_prompt=system_prompt,
        )

    async def analyze_error(
        self,
        code: str,
        error_message: str,
        language: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Analyze an execution error and provide insights.

        Args:
            code: The code that failed
            error_message: The error message from execution
            language: The language of the code
            context: Additional context about the execution

        Returns:
            Dictionary with error analysis
        """
        context_info = context or {}
        execution_context = f"""
Execution Context:
- Language: {language}
- Working Directory: {context_info.get("working_directory", "unknown")}
- Environment: {context_info.get("environment", "unknown")}
- Timeout: {context_info.get("timeout", "unknown")}
"""

        analysis_prompt = f"""
Please analyze this code execution error:

ORIGINAL CODE:
```python
{code}
```

ERROR MESSAGE:
```
{error_message}
```

{execution_context}

Provide a detailed analysis of what went wrong and how to fix it.
"""

        result = await self.analysis_agent.run(analysis_prompt)
        analysis_response = str(result.data).strip()

        # Parse the structured response
        analysis = self._parse_analysis_response(analysis_response)

        return {
            "error_type": analysis.get("error_type", "unknown"),
            "root_cause": analysis.get("root_cause", "Unable to determine"),
            "impact": analysis.get("impact", "Prevents code execution"),
            "recommendations": analysis.get("recommendations", []),
            "prevention": analysis.get("prevention", "Add proper error handling"),
            "raw_analysis": analysis_response,
        }

    async def improve_code(
        self,
        original_code: str,
        error_message: str,
        language: str,
        context: dict[str, Any] | None = None,
        improvement_focus: str = "fix_errors",
    ) -> dict[str, Any]:
        """Improve code based on error analysis.

        Args:
            original_code: The original code that failed
            error_message: The error message from execution
            language: The language of the code
            context: Additional execution context
            improvement_focus: Focus of improvement ("fix_errors", "optimize", "robustness")

        Returns:
            Dictionary with improved code and analysis
        """
        context_info = context or {}

        if improvement_focus == "fix_errors":
            improvement_prompt = self._create_error_fix_prompt(
                original_code, error_message, language, context_info
            )
            agent = self.improvement_agent
        elif improvement_focus == "optimize":
            improvement_prompt = self._create_optimization_prompt(
                original_code, language, context_info
            )
            agent = self.optimization_agent
        else:  # robustness
            improvement_prompt = self._create_robustness_prompt(
                original_code, language, context_info
            )
            agent = self.improvement_agent

        result = await agent.run(improvement_prompt)
        improvement_response = str(result.data).strip()

        # Parse the improvement response
        improved_code = self._extract_improved_code(improvement_response)
        explanation = self._extract_explanation(improvement_response)

        return {
            "original_code": original_code,
            "improved_code": improved_code,
            "language": language,
            "improvement_focus": improvement_focus,
            "explanation": explanation,
            "raw_response": improvement_response,
        }

    async def iterative_improve(
        self,
        code: str,
        language: str,
        test_function: Any,
        max_iterations: int = 3,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Iteratively improve code until it works or max iterations reached.

        Args:
            code: Initial code to improve
            language: Language of the code
            test_function: Function to test code execution (should return error message or None)
            max_iterations: Maximum improvement iterations
            context: Additional context

        Returns:
            Dictionary with final result and improvement history
        """
        improvement_history = []
        current_code = code

        for iteration in range(max_iterations):
            # Test current code
            error_message = await test_function(current_code, language)

            if error_message is None:
                # Code works successfully
                return {
                    "success": True,
                    "final_code": current_code,
                    "iterations_used": iteration,
                    "improvement_history": improvement_history,
                    "error_message": None,
                }

            # Analyze the error
            analysis = await self.analyze_error(
                current_code, error_message, language, context
            )

            # Improve the code
            improvement = await self.improve_code(
                current_code, error_message, language, context, "fix_errors"
            )

            # Update for next iteration
            current_code = improvement["improved_code"]

            improvement_history.append(
                {
                    "iteration": iteration + 1,
                    "original_code": improvement["original_code"],
                    "error_message": error_message,
                    "analysis": analysis,
                    "improvement": improvement,
                }
            )

        # Max iterations reached, return best attempt
        final_error = await test_function(current_code, language)

        return {
            "success": final_error is None,
            "final_code": current_code,
            "iterations_used": max_iterations,
            "improvement_history": improvement_history,
            "error_message": final_error,
        }

    def _create_error_fix_prompt(
        self, code: str, error: str, language: str, context: dict[str, Any]
    ) -> str:
        """Create a prompt for fixing code errors."""
        return f"""
Please fix this {language} code that is producing an error:

ORIGINAL CODE:
```python
{code}
```

ERROR MESSAGE:
```
{error}
```

EXECUTION CONTEXT:
- Language: {language}
- Working Directory: {context.get("working_directory", "unknown")}
- Environment: {context.get("environment", "unknown")}
- Timeout: {context.get("timeout", "unknown")}

Please provide the corrected code that fixes the error. Focus on:
1. Fixing the immediate error
2. Adding proper error handling
3. Improving code robustness
4. Following language best practices

Return only the corrected code without any markdown formatting or explanations.
"""

    def _create_optimization_prompt(
        self, code: str, language: str, context: dict[str, Any]
    ) -> str:
        """Create a prompt for optimizing code."""
        return f"""
Please optimize this {language} code for better performance and efficiency:

ORIGINAL CODE:
```python
{code}
```

EXECUTION CONTEXT:
- Language: {language}
- Working Directory: {context.get("working_directory", "unknown")}
- Environment: {context.get("environment", "unknown")}

Please provide an optimized version that:
1. Improves performance and efficiency
2. Reduces resource usage
3. Maintains the same functionality
4. Adds proper error handling

Return only the optimized code without any markdown formatting.
"""

    def _create_robustness_prompt(
        self, code: str, language: str, context: dict[str, Any]
    ) -> str:
        """Create a prompt for improving code robustness."""
        return f"""
Please improve the robustness of this {language} code:

ORIGINAL CODE:
```python
{code}
```

EXECUTION CONTEXT:
- Language: {language}
- Working Directory: {context.get("working_directory", "unknown")}
- Environment: {context.get("environment", "unknown")}

Please provide a more robust version that:
1. Adds comprehensive error handling
2. Includes input validation
3. Handles edge cases gracefully
4. Provides meaningful error messages
5. Follows defensive programming practices

Return only the improved code without any markdown formatting.
"""

    def _parse_analysis_response(self, response: str) -> dict[str, Any]:
        """Parse the structured analysis response."""
        analysis = {}

        # Extract sections using regex
        patterns = {
            "error_type": r"ERROR_TYPE:\s*(.+?)(?=\n[A-Z_]+:|$)",
            "root_cause": r"ROOT_CAUSE:\s*(.+?)(?=\n[A-Z_]+:|$)",
            "impact": r"IMPACT:\s*(.+?)(?=\n[A-Z_]+:|$)",
            "recommendations": r"RECOMMENDATIONS:\s*(.+?)(?=\n[A-Z_]+:|$)",
            "prevention": r"PREVENTION:\s*(.+?)(?=\n[A-Z_]+:|$)",
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                if key == "recommendations":
                    # Split recommendations into list
                    analysis[key] = [r.strip() for r in value.split("\n") if r.strip()]
                else:
                    analysis[key] = value

        return analysis

    def _extract_improved_code(self, response: str) -> str:
        """Extract the improved code from the response."""
        # Look for code blocks or plain code
        code_patterns = [
            r"```[\w]*\n(.*?)\n```",  # Markdown code blocks
            r"IMPROVED_CODE:\s*(.+?)(?=\nEXPLANATION:|$)",  # Structured format
        ]

        for pattern in code_patterns:
            match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1).strip()

        # If no structured format found, return the whole response as code
        return response.strip()

    def _extract_explanation(self, response: str) -> str:
        """Extract the explanation from the response."""
        match = re.search(r"EXPLANATION:\s*(.+)", response, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return "Code improved based on error analysis and best practices."

    def create_improved_code_block(
        self, improvement_result: dict[str, Any]
    ) -> CodeBlock:
        """Create a CodeBlock from improvement results.

        Args:
            improvement_result: Result from improve_code method

        Returns:
            CodeBlock instance
        """
        return CodeBlock(
            code=improvement_result["improved_code"],
            language=improvement_result["language"],
        )
