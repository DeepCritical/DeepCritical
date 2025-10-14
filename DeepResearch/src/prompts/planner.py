STYLE = "concise"
MAX_DEPTH = 3


PLANNER_PROMPTS: dict[str, str] = {
    "style": STYLE,
    "max_depth": str(MAX_DEPTH),
    "plan_workflow": "Plan the following workflow: {workflow_description}",
    "create_strategy": "Create a strategy for the task: {task_description}",
}


class PlannerPrompts:
    """Prompt templates for planner operations."""

    STYLE = STYLE
    MAX_DEPTH = MAX_DEPTH
    PROMPTS = PLANNER_PROMPTS
