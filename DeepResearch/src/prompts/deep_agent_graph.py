"""
Deep Agent Graph prompts for DeepCritical research workflows.

This module defines prompts for deep agent graph operations and coordination.
"""

from __future__ import annotations

# Deep agent graph system prompt
DEEP_AGENT_GRAPH_SYSTEM_PROMPT = """You are a deep agent graph coordinator in the DeepCritical system. Your role is to:

1. Coordinate multiple specialized agents in complex workflows
2. Manage agent-to-agent communication and data flow
3. Handle subgraph spawning and nested execution
4. Monitor and optimize agent performance
5. Ensure proper error handling and recovery

You operate at the highest level of the agent hierarchy, orchestrating complex multi-agent research workflows."""

# Deep agent graph instructions
DEEP_AGENT_GRAPH_INSTRUCTIONS = """Execute deep agent graph coordination by:

1. Analyzing workflow requirements and agent capabilities
2. Creating optimal agent interaction patterns
3. Managing resource allocation and load balancing
4. Monitoring execution progress and performance
5. Handling failures and implementing recovery strategies
6. Ensuring data consistency across agent interactions

Maintain high-level oversight while allowing specialized agents to execute their tasks effectively."""


class DeepAgentGraphPrompts:
    """Prompts for deep agent graph operations."""

    def __init__(self):
        self.system_prompt = DEEP_AGENT_GRAPH_SYSTEM_PROMPT
        self.instructions = DEEP_AGENT_GRAPH_INSTRUCTIONS

    def get_coordination_prompt(self, workflow_type: str) -> str:
        """Get coordination prompt for specific workflow type."""
        return f"{self.system_prompt}\n\nWorkflow Type: {workflow_type}\n\n{self.instructions}"

    def get_subgraph_prompt(self, subgraph_config: dict) -> str:
        """Get prompt for subgraph coordination."""
        return f"{self.system_prompt}\n\nSubgraph Configuration: {subgraph_config}\n\n{self.instructions}"


# Export the module for import
deep_agent_graph = DeepAgentGraphPrompts()
DEEP_AGENT_GRAPH_PROMPTS = deep_agent_graph
