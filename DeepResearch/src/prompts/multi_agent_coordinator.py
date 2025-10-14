"""
Multi-agent coordination prompts for DeepCritical's workflow orchestration.

This module defines system prompts and instructions for multi-agent coordination
patterns including collaborative, sequential, hierarchical, and peer-to-peer
coordination strategies.
"""

# Default system prompts for different agent roles
DEFAULT_SYSTEM_PROMPTS = {
    "coordinator": "You are a coordinator agent responsible for managing and coordinating other agents.",
    "executor": "You are an executor agent responsible for executing specific tasks.",
    "evaluator": "You are an evaluator agent responsible for evaluating and assessing outputs.",
    "judge": "You are a judge agent responsible for making final decisions and evaluations.",
    "reviewer": "You are a reviewer agent responsible for reviewing and providing feedback.",
    "linter": "You are a linter agent responsible for checking code quality and standards.",
    "code_executor": "You are a code executor agent responsible for executing code and analyzing results.",
    "hypothesis_generator": "You are a hypothesis generator agent responsible for creating scientific hypotheses.",
    "hypothesis_tester": "You are a hypothesis tester agent responsible for testing and validating hypotheses.",
    "reasoning_agent": "You are a reasoning agent responsible for logical reasoning and analysis.",
    "search_agent": "You are a search agent responsible for searching and retrieving information.",
    "rag_agent": "You are a RAG agent responsible for retrieval-augmented generation tasks.",
    "bioinformatics_agent": "You are a bioinformatics agent responsible for biological data analysis.",
    "default": "You are a specialized agent with specific capabilities.",
}


# Default instructions for different agent roles
DEFAULT_INSTRUCTIONS = {
    "coordinator": [
        "Coordinate with other agents to achieve common goals",
        "Manage task distribution and workflow",
        "Ensure effective communication between agents",
        "Monitor progress and resolve conflicts",
    ],
    "executor": [
        "Execute assigned tasks efficiently",
        "Provide clear status updates",
        "Handle errors gracefully",
        "Deliver high-quality outputs",
    ],
    "evaluator": [
        "Evaluate outputs objectively",
        "Provide constructive feedback",
        "Assess quality and accuracy",
        "Suggest improvements",
    ],
    "judge": [
        "Make fair and objective decisions",
        "Consider multiple perspectives",
        "Provide detailed reasoning",
        "Ensure consistency in evaluations",
    ],
    "default": [
        "Perform your role effectively",
        "Communicate clearly",
        "Maintain quality standards",
    ],
}


def get_system_prompt(role: str) -> str:
    """Get default system prompt for an agent role."""
    return DEFAULT_SYSTEM_PROMPTS.get(role, DEFAULT_SYSTEM_PROMPTS["default"])


def get_instructions(role: str) -> list[str]:
    """Get default instructions for an agent role."""
    return DEFAULT_INSTRUCTIONS.get(role, DEFAULT_INSTRUCTIONS["default"])


# Prompt templates for multi-agent coordination
MULTI_AGENT_COORDINATOR_PROMPTS: dict[str, str] = {
    "coordination_system": """You are an advanced multi-agent coordination system. Your role is to:

1. Coordinate multiple specialized agents to achieve complex objectives
2. Manage different coordination strategies (collaborative, sequential, hierarchical, peer-to-peer)
3. Ensure effective communication and information sharing between agents
4. Monitor progress and resolve conflicts
5. Synthesize results from multiple agent outputs

Current coordination strategy: {coordination_strategy}
Available agents: {agent_count}
Maximum rounds: {max_rounds}
Consensus threshold: {consensus_threshold}""",
    "agent_execution": """Execute your assigned task as {agent_role}.

Task: {task_description}
Round: {round_number}
Input data: {input_data}

Instructions:
{instructions}

Provide your output in the following format:
{{
    "result": "your_detailed_output_here",
    "confidence": 0.9,
    "needs_collaboration": false,
    "status": "completed"
}}""",
    "consensus_evaluation": """Evaluate consensus among agent outputs:

Agent outputs:
{agent_outputs}

Consensus threshold: {consensus_threshold}
Evaluation criteria:
- Agreement on key points
- Confidence levels
- Evidence quality
- Reasoning consistency

Provide consensus score (0.0-1.0) and reasoning.""",
    "task_distribution": """Distribute the following task among available agents:

Main task: {task_description}
Available agents: {available_agents}
Agent capabilities: {agent_capabilities}

Distribution strategy: {distribution_strategy}

Provide task assignments for each agent.""",
    "conflict_resolution": """Resolve conflicts between agent outputs:

Conflicting outputs:
{conflicting_outputs}

Resolution strategy: {resolution_strategy}
Available evidence: {available_evidence}

Provide resolved output and reasoning.""",
}


class MultiAgentCoordinatorPrompts:
    """Prompt templates for multi-agent coordinator operations."""

    PROMPTS = MULTI_AGENT_COORDINATOR_PROMPTS
    SYSTEM_PROMPTS = DEFAULT_SYSTEM_PROMPTS
    INSTRUCTIONS = DEFAULT_INSTRUCTIONS

    @classmethod
    def get_coordination_system_prompt(
        cls,
        coordination_strategy: str,
        agent_count: int,
        max_rounds: int,
        consensus_threshold: float,
    ) -> str:
        """Get coordination system prompt with parameters."""
        return cls.PROMPTS["coordination_system"].format(
            coordination_strategy=coordination_strategy,
            agent_count=agent_count,
            max_rounds=max_rounds,
            consensus_threshold=consensus_threshold,
        )

    @classmethod
    def get_agent_execution_prompt(
        cls,
        agent_role: str,
        task_description: str,
        round_number: int,
        input_data: dict,
        instructions: list[str],
    ) -> str:
        """Get agent execution prompt with parameters."""
        return cls.PROMPTS["agent_execution"].format(
            agent_role=agent_role,
            task_description=task_description,
            round_number=round_number,
            input_data=input_data,
            instructions="\n".join(f"- {instr}" for instr in instructions),
        )
