"""
Agent prompts for DeepCritical research workflows.

This module defines system prompts and instructions for agent types
in the DeepCritical system.
"""

from __future__ import annotations

# Base header template
HEADER = """DeepCritical Research Agent System
Current Date: ${current_date_utc}
System Version: 1.0.0

You are operating within the DeepCritical research framework, designed for advanced scientific research and analysis."""

# Actions wrapper template
ACTIONS_WRAPPER = """Available Actions:
${action_sections}

Please select and execute the most appropriate action for the current task."""

# Action visit template
ACTION_VISIT = """Action: Visit URL
URL: {url}
Purpose: {purpose}"""

# Action search template
ACTION_SEARCH = """Action: Search
Query: {query}
Purpose: {purpose}"""

# Action answer template
ACTION_ANSWER = """Action: Answer
Question: {question}
Answer: {answer}"""

# Action beast template
ACTION_BEAST = """Action: Beast Mode
Task: {task}
Approach: {approach}"""

# Action reflect template
ACTION_REFLECT = """Action: Reflect
Question: {question}
Reflection: {reflection}"""

# Footer template
FOOTER = """End of DeepCritical Research Agent Response
Generated on: ${current_date_utc}"""


class AgentPrompts:
    """Centralized agent prompt management."""

    def __init__(self):
        self._prompts = {
            "parser": {
                "system": """You are a research question parser. Your job is to analyze research questions and extract:
1. The main intent/purpose
2. Key entities and concepts
3. Required data sources
4. Expected output format
5. Complexity level

Provide structured analysis of the research question.""",
                "instructions": "Parse the research question systematically and provide structured output.",
            },
            "planner": {
                "system": """You are a research workflow planner. Your job is to create detailed execution plans by:
1. Breaking down complex research questions into steps
2. Identifying required tools and data sources
3. Determining execution order and dependencies
4. Estimating resource requirements

Create comprehensive, executable research plans.""",
                "instructions": "Plan the research workflow with clear steps and dependencies.",
            },
            "executor": {
                "system": """You are a research task executor. Your job is to execute research tasks by:
1. Following the provided execution plan
2. Using available tools effectively
3. Collecting and processing data
4. Recording results and metadata

Execute tasks efficiently and accurately.""",
                "instructions": "Execute the research tasks according to the plan.",
            },
        }

    def get_system_prompt(self, agent_type: str) -> str:
        """Get system prompt for a specific agent type."""
        return self._prompts.get(agent_type, {}).get(
            "system", "You are a research agent."
        )

    def get_instructions(self, agent_type: str) -> str:
        """Get instructions for a specific agent type."""
        return self._prompts.get(agent_type, {}).get(
            "instructions", "Execute your task effectively."
        )
