"""
Workflow orchestrator prompts for DeepCritical's workflow-of-workflows architecture.

This module defines system prompts and instructions for the primary workflow orchestrator
that coordinates multiple specialized workflows using Pydantic AI patterns.
"""

# System prompt for the primary workflow orchestrator
WORKFLOW_ORCHESTRATOR_SYSTEM_PROMPT = """You are the primary orchestrator for a sophisticated workflow-of-workflows system.
Your role is to:
1. Analyze user input and determine which workflows to spawn
2. Coordinate multiple specialized workflows (RAG, bioinformatics, search, multi-agent systems)
3. Manage data flow between workflows
4. Ensure quality through judge evaluation
5. Synthesize results from multiple workflows
6. Generate comprehensive outputs including hypotheses, testing environments, and reasoning results

You have access to various tools for spawning workflows, coordinating agents, and evaluating outputs.
Always consider the user's intent and select the most appropriate combination of workflows."""


# Instructions for the primary workflow orchestrator
WORKFLOW_ORCHESTRATOR_INSTRUCTIONS = [
    "Analyze the user input to understand the research question or task",
    "Determine which workflows are needed based on the input",
    "Spawn appropriate workflows with correct parameters",
    "Coordinate data flow between workflows",
    "Use judges to evaluate intermediate and final results",
    "Synthesize results from multiple workflows into comprehensive outputs",
    "Generate datasets, testing environments, and reasoning results as needed",
    "Ensure quality and consistency across all outputs",
]


# Prompt templates for workflow orchestrator operations
WORKFLOW_ORCHESTRATOR_PROMPTS: dict[str, str] = {
    "system": WORKFLOW_ORCHESTRATOR_SYSTEM_PROMPT,
    "instructions": "\n".join(WORKFLOW_ORCHESTRATOR_INSTRUCTIONS),
    "spawn_workflow": "Spawn a new workflow with the following parameters: {workflow_type}, {workflow_name}, {input_data}",
    "coordinate_agents": "Coordinate multiple agents for the task: {task_description}",
    "evaluate_content": "Evaluate content using judge: {judge_id} with criteria: {evaluation_criteria}",
    "compose_workflows": "Compose workflows for user input: {user_input} using workflows: {selected_workflows}",
    "generate_hypothesis_dataset": "Generate hypothesis dataset: {name} with description: {description}",
    "create_testing_environment": "Create testing environment: {name} for hypothesis: {hypothesis}",
}


class WorkflowOrchestratorPrompts:
    """Prompt templates for workflow orchestrator operations."""

    SYSTEM_PROMPT = WORKFLOW_ORCHESTRATOR_SYSTEM_PROMPT
    INSTRUCTIONS = WORKFLOW_ORCHESTRATOR_INSTRUCTIONS
    PROMPTS = WORKFLOW_ORCHESTRATOR_PROMPTS

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

    @classmethod
    def get_prompt(cls, prompt_type: str, **kwargs) -> str:
        """Get a formatted prompt."""
        template = cls.PROMPTS.get(prompt_type, "")
        if not template:
            return ""

        try:
            return template.format(**kwargs)
        except KeyError as e:
            return f"Missing required parameter: {e}"
