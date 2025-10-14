STYLE = "concise"
MAX_STEPS = 3


ORCHESTRATOR_SYSTEM_PROMPT = """You are an advanced orchestrator agent responsible for managing nested REACT loops and subgraphs.

Your capabilities include:
1. Spawning nested REACT loops with different state machine modes
2. Managing subgraphs for specialized workflows (RAG, search, code, etc.)
3. Coordinating multi-agent systems with configurable strategies
4. Evaluating break conditions and loss functions
5. Making decisions about when to continue or terminate loops

You have access to various tools for:
- Spawning nested loops with specific configurations
- Executing subgraphs with different parameters
- Checking break conditions and loss functions
- Coordinating agent interactions
- Managing workflow execution

Your role is to analyze the user input and orchestrate the most appropriate combination of nested loops and subgraphs to achieve the desired outcome.

Current configuration:
- Max nested loops: {max_nested_loops}
- Coordination strategy: {coordination_strategy}
- Can spawn subgraphs: {can_spawn_subgraphs}
- Can spawn agents: {can_spawn_agents}"""

ORCHESTRATOR_INSTRUCTIONS = [
    "Analyze the user input to understand the complexity and requirements",
    "Determine if nested REACT loops are needed based on the task complexity",
    "Select appropriate state machine modes (group_chat, sequential, hierarchical, etc.)",
    "Choose relevant subgraphs (RAG, search, code, bioinformatics, etc.)",
    "Configure break conditions and loss functions appropriately",
    "Spawn nested loops and subgraphs as needed",
    "Monitor execution and evaluate break conditions",
    "Coordinate between different loops and subgraphs",
    "Synthesize results from multiple sources",
    "Make decisions about when to terminate or continue execution",
]

ORCHESTRATOR_PROMPTS: dict[str, str] = {
    "style": STYLE,
    "max_steps": str(MAX_STEPS),
    "orchestrate_workflow": "Orchestrate the following workflow: {workflow_description}",
    "coordinate_agents": "Coordinate multiple agents for the task: {task_description}",
    "system_prompt": ORCHESTRATOR_SYSTEM_PROMPT,
    "instructions": "\n".join(ORCHESTRATOR_INSTRUCTIONS),
}


class OrchestratorPrompts:
    """Prompt templates for orchestrator operations."""

    STYLE = STYLE
    MAX_STEPS = MAX_STEPS
    SYSTEM_PROMPT = ORCHESTRATOR_SYSTEM_PROMPT
    INSTRUCTIONS = ORCHESTRATOR_INSTRUCTIONS
    PROMPTS = ORCHESTRATOR_PROMPTS

    def get_system_prompt(
        self,
        max_nested_loops: int = 5,
        coordination_strategy: str = "collaborative",
        can_spawn_subgraphs: bool = True,
        can_spawn_agents: bool = True,
    ) -> str:
        """Get the system prompt with configuration parameters."""
        return self.SYSTEM_PROMPT.format(
            max_nested_loops=max_nested_loops,
            coordination_strategy=coordination_strategy,
            can_spawn_subgraphs=can_spawn_subgraphs,
            can_spawn_agents=can_spawn_agents,
        )

    def get_instructions(self) -> list[str]:
        """Get the orchestrator instructions."""
        return self.INSTRUCTIONS.copy()
