"""
DeepAgent Prompts - Pydantic AI prompts for DeepAgent operations.

This module defines prompts and system messages for DeepAgent operations
using Pydantic AI patterns that align with DeepCritical's architecture.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PromptType(str, Enum):
    """Types of prompts."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    TASK = "task"


class PromptTemplate(BaseModel):
    """Template for prompts with variable substitution."""

    name: str = Field(..., description="Prompt template name")
    template: str = Field(..., description="Prompt template string")
    variables: list[str] = Field(default_factory=list, description="Required variables")
    prompt_type: PromptType = Field(PromptType.SYSTEM, description="Type of prompt")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        if not v or not v.strip():
            msg = "Prompt template name cannot be empty"
            raise ValueError(msg)
        return v.strip()

    @field_validator("template")
    @classmethod
    def validate_template(cls, v):
        if not v or not v.strip():
            msg = "Prompt template cannot be empty"
            raise ValueError(msg)
        return v.strip()

    def format(self, **kwargs) -> str:
        """Format the template with provided variables."""
        try:
            return self.template.format(**kwargs)
        except KeyError as e:
            msg = f"Missing required variable: {e}"
            raise ValueError(msg)

    model_config = ConfigDict(json_schema_extra={})


# Tool descriptions
WRITE_TODOS_TOOL_DESCRIPTION = """Use this tool to create and manage a structured task list for your current work session. This helps you track progress, organize complex tasks, and demonstrate thoroughness to the user.
It also helps the user understand the progress of the task and overall progress of their requests.
Only use this tool if you think it will be helpful in staying organized. If the user's request is trivial and takes less than 3 steps, it is better to NOT use this tool and just do the taks directly.

## When to Use This Tool
Use this tool in these scenarios:

1. Complex multi-step tasks - When a task requires 3 or more distinct steps or actions
2. Non-trivial and complex tasks - Tasks that require careful planning or multiple operations
3. User explicitly requests todo list - When the user directly asks you to use the todo list
4. User provides multiple tasks - When users provide a list of things to be done (numbered or comma-separated)
5. The plan may need future revisions or updates based on results from the first few steps. Keeping track of this in a list is helpful.

## How to Use This Tool
1. When you start working on a task - Mark it as in_progress BEFORE beginning work.
2. After completing a task - Mark it as completed and add any new follow-up tasks discovered during implementation.
3. You can also update future tasks, such as deleting them if they are no longer necessary, or adding new tasks that are necessary. Don't change previously completed tasks.
4. You can make several updates to the todo list at once. For example, when you complete a task, you can mark the next task you need to start as in_progress.

## When NOT to Use This Tool
It is important to skip using this tool when:
1. There is only a single, straightforward task
2. The task is trivial and tracking it provides no benefit
3. The task can be completed in less than 3 trivial steps
4. The task is purely conversational or informational

## Task States and Management

1. **Task States**: Use these states to track progress:
   - pending: Task not yet started
   - in_progress: Currently working on (you can have multiple tasks in_progress at a time if they are not related to each other and can be run in parallel)
   - completed: Task finished successfully

2. **Task Management**:
   - Update task status in real-time as you work
   - Mark tasks complete IMMEDIATELY after finishing (don't batch completions)
   - Complete current tasks before starting new ones
   - Remove tasks that are no longer relevant from the list entirely
   - IMPORTANT: When you write this todo list, you should mark your first task (or tasks) as in_progress immediately!.
   - IMPORTANT: Unless all tasks are completed, you should always have at least one task in_progress to show the user that you are working on something.

3. **Task Completion Requirements**:
   - ONLY mark a task as completed when you have FULLY accomplished it
   - If you encounter errors, blockers, or cannot finish, keep the task as in_progress
   - When blocked, create a new task describing what needs to be resolved
   - Never mark a task as completed if:
     - There are unresolved issues or errors
     - Work is partial or incomplete
     - You encountered blockers that prevent completion
     - You couldn't find necessary resources or dependencies
     - Quality standards haven't been met

4. **Task Breakdown**:
   - Create specific, actionable items
   - Break complex tasks into smaller, manageable steps
   - Use clear, descriptive task names

Being proactive with task management demonstrates attentiveness and ensures you complete all requirements successfully
Remember: If you only need to make a few tool calls to complete a task, and it is clear what you need to do, it is better to just do the task directly and NOT call this tool at all."""

TASK_TOOL_DESCRIPTION = """Launch an ephemeral subagent to handle complex, multi-step independent tasks with isolated context windows.

Available agent types and the tools they have access to:
- general-purpose: General-purpose agent for researching complex questions, searching for files and content, and executing multi-step tasks. When you are searching for a keyword or file and are not confident that you will find the right match in the first few tries use this agent to perform the search for you. This agent has access to all tools as the main agent.
{other_agents}

When using the Task tool, you must specify a subagent_type parameter to select which agent type to use.

## Usage notes:
1. Launch multiple agents concurrently whenever possible, to maximize performance; to do that, use a single message with multiple tool uses
2. When the agent is done, it will return a single message back to you. The result returned by the agent is not visible to the user. To show the user the result, you should send a text message back to the user with a concise summary of the result.
3. Each agent invocation is stateless. You will not be able to send additional messages to the agent, nor will the agent be able to communicate with you outside of its final report. Therefore, your prompt should contain a highly detailed task description for the agent to perform autonomously and you should specify exactly what information the agent should return back to you in its final and only message to you.
4. The agent's outputs should generally be trusted
5. Clearly tell the agent whether you expect it to create content, perform analysis, or just do research (search, file reads, web fetches, etc.), since it is not aware of the user's intent
6. If the agent description mentions that it should be used proactively, then you should try your best to use it without the user having to ask for it first. Use your judgement.
7. When only the general-purpose agent is provided, you should use it for all tasks. It is great for isolating context and token usage, and completing specific, complex tasks, as it has all the same capabilities as the main agent.

### Example usage of the general-purpose agent:

<example_agent_descriptions>
"general-purpose": use this agent for general purpose tasks, it has access to all tools as the main agent.
</example_agent_descriptions>

<example>
User: "I want to conduct research on the accomplishments of Lebron James, Michael Jordan, and Kobe Bryant, and then compare them."
Assistant: *Uses the task tool in parallel to conduct isolated research on each of the three players*
Assistant: *Synthesizes the results of the three isolated research tasks and responds to the User*
<commentary>
Research is a complex, multi-step task in it of itself.
The research of each individual player is not dependent on the research of the other players.
The assistant uses the task tool to break down the complex objective into three isolated tasks.
Each research task only needs to worry about context and tokens about one player, then returns synthesized information about each player as the Tool Result.
This means each research task can dive deep and spend tokens and context deeply researching each player, but the final result is synthesized information, and saves us tokens in the long run when comparing the players to each other.
</commentary>
</example>

<example>
User: "Analyze a single large code repository for security vulnerabilities and generate a report."
Assistant: *Launches a single `task` subagent for the repository analysis*
Assistant: *Receives report and integrates results into final summary*
<commentary>
Subagent is used to isolate a large, context-heavy task, even though there is only one. This prevents the main thread from being overloaded with details.
If the user then asks followup questions, we have a concise report to reference instead of the entire history of analysis and tool calls, which is good and saves us time and money.
</commentary>
</example>

<example>
User: "Schedule two meetings for me and prepare agendas for each."
Assistant: *Calls the task tool in parallel to launch two `task` subagents (one per meeting) to prepare agendas*
Assistant: *Returns final schedules and agendas*
<commentary>
Tasks are simple individually, but subagents help silo agenda preparation.
Each subagent only needs to worry about the agenda for one meeting.
</commentary>
</example>

<example>
User: "I want to order a pizza from Dominos, order a burger from McDonald's, and order a salad from Subway."
Assistant: *Calls tools directly in parallel to order a pizza from Dominos, a burger from McDonald's, and a salad from Subway*
<commentary>
The assistant did not use the task tool because the objective is super simple and clear and only requires a few trivial tool calls.
It is better to just complete the task directly and NOT use the `task`tool.
</commentary>
</example>

### Example usage with custom agents:

<example_agent_descriptions>
"content-reviewer": use this agent after you are done creating significant content or documents
"greeting-responder": use this agent when to respond to user greetings with a friendly joke
"research-analyst": use this agent to conduct thorough research on complex topics
</example_agent_description>

<example>
user: "Please write a function that checks if a number is prime"
assistant: Sure let me write a function that checks if a number is prime
assistant: First let me use the Write tool to write a function that checks if a number is prime
assistant: I'm going to use the Write tool to write the following code:
<code>
function isPrime(n) {{
  if (n <= 1) return false
  for (let i = 2; i * i <= n; i++) {{
    if (n % i === 0) return false
  }}
  return true
}}
</code>
<commentary>
Since significant content was created and the task was completed, now use the content-reviewer agent to review the work
</commentary>
assistant: Now let me use the content-reviewer agent to review the code
assistant: Uses the Task tool to launch with the content-reviewer agent
</example>

<example>
user: "Can you help me research the environmental impact of different renewable energy sources and create a comprehensive report?"
<commentary>
This is a complex research task that would benefit from using the research-analyst agent to conduct thorough analysis
</commentary>
assistant: I'll help you research the environmental impact of renewable energy sources. Let me use the research-analyst agent to conduct comprehensive research on this topic.
assistant: Uses the Task tool to launch with the research-analyst agent, providing detailed instructions about what research to conduct and what format the report should take
</example>

<example>
user: "Hello"
<commentary>
Since the user is greeting, use the greeting-responder agent to respond with a friendly joke
</commentary>
assistant: "I'm going to use the Task tool to launch with the greeting-responder agent"
</example>"""

LIST_FILES_TOOL_DESCRIPTION = """Lists all files in the local filesystem.

Usage:
- The list_files tool will return a list of all files in the local filesystem.
- This is very useful for exploring the file system and finding the right file to read or edit.
- You should almost ALWAYS use this tool before using the Read or Edit tools."""

READ_FILE_TOOL_DESCRIPTION = """Reads a file from the local filesystem. You can access any file directly by using this tool.
Assume this tool is able to read all files on the machine. If the User provides a path to a file assume that path is valid. It is okay to read a file that does not exist; an error will be returned.

Usage:
- The file_path parameter must be an absolute path, not a relative path
- By default, it reads up to 2000 lines starting from the beginning of the file
- You can optionally specify a line offset and limit (especially handy for long files), but it's recommended to read the whole file by not providing these parameters
- Any lines longer than 2000 characters will be truncated
- Results are returned using cat -n format, with line numbers starting at 1
- You have the capability to call multiple tools in a single response. It is always better to speculatively read multiple files as a batch that are potentially useful.
- If you read a file that exists but has empty contents you will receive a system reminder warning in place of file contents.
- You should ALWAYS make sure a file has been read before editing it."""

EDIT_FILE_TOOL_DESCRIPTION = """Performs exact string replacements in files.

Usage:
- You must use your `Read` tool at least once in the conversation before editing. This tool will error if you attempt an edit without reading the file.
- When editing text from Read tool output, ensure you preserve the exact indentation (tabs/spaces) as it appears AFTER the line number prefix. The line number prefix format is: spaces + line number + tab. Everything after that tab is the actual file content to match. Never include any part of the line number prefix in the old_string or new_string.
- ALWAYS prefer editing existing files. NEVER write new files unless explicitly required.
- Only use emojis if the user explicitly requests it. Avoid adding emojis to files unless asked.
- The edit will FAIL if `old_string` is not unique in the file. Either provide a larger string with more surrounding context to make it unique or use `replace_all` to change every instance of `old_string`.
- Use `replace_all` for replacing and renaming strings across the file. This parameter is useful if you want to rename a variable for instance."""

WRITE_FILE_TOOL_DESCRIPTION = """Writes to a file in the local filesystem.

Usage:
- The file_path parameter must be an absolute path, not a relative path
- The content parameter must be a string
- The write_file tool will create the a new file.
- Prefer to edit existing files over creating new ones when possible."""

# System prompts
WRITE_TODOS_SYSTEM_PROMPT = """## `write_todos`

You have access to the `write_todos` tool to help you manage and plan complex objectives.
Use this tool for complex objectives to ensure that you are tracking each necessary step and giving the user visibility into your progress.
This tool is very helpful for planning complex objectives, and for breaking down these larger complex objectives into smaller steps.

It is critical that you mark todos as completed as soon as you are done with a step. Do not batch up multiple steps before marking them as completed.
For simple objectives that only require a few steps, it is better to just complete the objective directly and NOT use this tool.
Writing todos takes time and tokens, use it when it is helpful for managing complex many-step problems! But not for simple few-step requests.

## Important To-Do List Usage Notes to Remember
- The `write_todos` tool should never be called multiple times in parallel.
- Don't be afraid to revise the To-Do list as you go. New information may reveal new tasks that need to be done, or old tasks that are irrelevant."""

TASK_SYSTEM_PROMPT = """## `task` (subagent spawner)

You have access to a `task` tool to launch short-lived subagents that handle isolated tasks. These agents are ephemeral — they live only for the duration of the task and return a single result.

When to use the task tool:
- When a task is complex and multi-step, and can be fully delegated in isolation
- When a task is independent of other tasks and can run in parallel
- When a task requires focused reasoning or heavy token/context usage that would bloat the orchestrator thread
- When sandboxing improves reliability (e.g. code execution, structured searches, data formatting)
- When you only care about the output of the subagent, and not the intermediate steps (ex. performing a lot of research and then returned a synthesized report, performing a series of computations or lookups to achieve a concise, relevant answer.)

Subagent lifecycle:
1. **Spawn** → Provide clear role, instructions, and expected output
2. **Run** → The subagent completes the task autonomously
3. **Return** → The subagent provides a single structured result
4. **Reconcile** → Incorporate or synthesize the result into the main thread

When NOT to use the task tool:
- If you need to see the intermediate reasoning or steps after the subagent has completed (the task tool hides them)
- If the task is trivial (a few tool calls or simple lookup)
- If delegating does not reduce token usage, complexity, or context switching
- If splitting would add latency without benefit

## Important Task Tool Usage Notes to Remember
- Whenever possible, parallelize the work that you do. This is true for both tool_calls, and for tasks. Whenever you have independent steps to complete - make tool_calls, or kick off tasks (subagents) in parallel to accomplish them faster. This saves time for the user, which is incredibly important.
- Remember to use the `task` tool to silo independent tasks within a multi-part objective.
- You should use the `task` tool whenever you have a complex task that will take multiple steps, and is independent from other tasks that the agent needs to complete. These agents are highly competent and efficient."""

FILESYSTEM_SYSTEM_PROMPT = """## Filesystem Tools `ls`, `read_file`, `write_file`, `edit_file`

You have access to a local, private filesystem which you can interact with using these tools.
- ls: list all files in the local filesystem
- read_file: read a file from the local filesystem
- write_file: write to a file in the local filesystem
- edit_file: edit a file in the local filesystem"""

BASE_AGENT_PROMPT = """
In order to complete the objective that the user asks of you, you have access to a number of standard tools.
"""

# Prompt templates
WRITE_TODOS_SYSTEM_TEMPLATE = PromptTemplate(
    name="write_todos_system",
    template=WRITE_TODOS_SYSTEM_PROMPT,
    variables=[],
    prompt_type=PromptType.SYSTEM,
)

TASK_SYSTEM_TEMPLATE = PromptTemplate(
    name="task_system",
    template=TASK_SYSTEM_PROMPT,
    variables=[],
    prompt_type=PromptType.SYSTEM,
)

FILESYSTEM_SYSTEM_TEMPLATE = PromptTemplate(
    name="filesystem_system",
    template=FILESYSTEM_SYSTEM_PROMPT,
    variables=[],
    prompt_type=PromptType.SYSTEM,
)

BASE_AGENT_TEMPLATE = PromptTemplate(
    name="base_agent",
    template=BASE_AGENT_PROMPT,
    variables=[],
    prompt_type=PromptType.SYSTEM,
)

TASK_TOOL_DESCRIPTION_TEMPLATE = PromptTemplate(
    name="task_tool_description",
    template=TASK_TOOL_DESCRIPTION,
    variables=["other_agents"],
    prompt_type=PromptType.TOOL,
)


class PromptManager:
    """Manager for prompt templates and system messages."""

    def __init__(self):
        self.templates: dict[str, PromptTemplate] = {}
        self._register_default_templates()

    def _register_default_templates(self) -> None:
        """Register default prompt templates."""
        default_templates = [
            WRITE_TODOS_SYSTEM_TEMPLATE,
            TASK_SYSTEM_TEMPLATE,
            FILESYSTEM_SYSTEM_TEMPLATE,
            BASE_AGENT_TEMPLATE,
            TASK_TOOL_DESCRIPTION_TEMPLATE,
        ]

        for template in default_templates:
            self.register_template(template)

    def register_template(self, template: PromptTemplate) -> None:
        """Register a prompt template."""
        self.templates[template.name] = template

    def get_template(self, name: str) -> PromptTemplate | None:
        """Get a prompt template by name."""
        return self.templates.get(name)

    def format_template(self, name: str, **kwargs) -> str:
        """Format a prompt template with variables."""
        template = self.get_template(name)
        if not template:
            msg = f"Template '{name}' not found"
            raise ValueError(msg)
        return template.format(**kwargs)

    def get_system_prompt(self, components: list[str] | None = None) -> str:
        """Get a system prompt combining multiple components."""
        if not components:
            components = ["base_agent"]

        prompt_parts = []
        for component in components:
            if component in self.templates:
                template = self.templates[component]
                if template.prompt_type == PromptType.SYSTEM:
                    prompt_parts.append(template.template)

        return "\n\n".join(prompt_parts)

    def get_tool_description(self, tool_name: str, **kwargs) -> str:
        """Get a tool description with variable substitution."""
        if tool_name == "write_todos":
            return WRITE_TODOS_TOOL_DESCRIPTION
        if tool_name == "task":
            return self.format_template("task_tool_description", **kwargs)
        if tool_name == "list_files":
            return LIST_FILES_TOOL_DESCRIPTION
        if tool_name == "read_file":
            return READ_FILE_TOOL_DESCRIPTION
        if tool_name == "write_file":
            return WRITE_FILE_TOOL_DESCRIPTION
        if tool_name == "edit_file":
            return EDIT_FILE_TOOL_DESCRIPTION
        return f"Tool: {tool_name}"


# Global prompt manager instance
prompt_manager = PromptManager()


# Factory functions
def create_prompt_template(
    name: str,
    template: str,
    variables: list[str] | None = None,
    prompt_type: PromptType = PromptType.SYSTEM,
) -> PromptTemplate:
    """Create a prompt template."""
    return PromptTemplate(
        name=name, template=template, variables=variables or [], prompt_type=prompt_type
    )


def get_system_prompt(components: list[str] | None = None) -> str:
    """Get a system prompt combining multiple components."""
    return prompt_manager.get_system_prompt(components)


def get_tool_description(tool_name: str, **kwargs) -> str:
    """Get a tool description with variable substitution."""
    return prompt_manager.get_tool_description(tool_name, **kwargs)


def format_template(name: str, **kwargs) -> str:
    """Format a prompt template with variables."""
    return prompt_manager.format_template(name, **kwargs)


# Export all components
__all__ = [
    "BASE_AGENT_PROMPT",
    "BASE_AGENT_TEMPLATE",
    # Prompt constants and classes
    "DEEP_AGENT_PROMPTS",
    "EDIT_FILE_TOOL_DESCRIPTION",
    "FILESYSTEM_SYSTEM_PROMPT",
    "FILESYSTEM_SYSTEM_TEMPLATE",
    "LIST_FILES_TOOL_DESCRIPTION",
    "READ_FILE_TOOL_DESCRIPTION",
    "TASK_SYSTEM_PROMPT",
    "TASK_SYSTEM_TEMPLATE",
    "TASK_TOOL_DESCRIPTION",
    "TASK_TOOL_DESCRIPTION_TEMPLATE",
    "WRITE_FILE_TOOL_DESCRIPTION",
    # System prompts
    "WRITE_TODOS_SYSTEM_PROMPT",
    # Templates
    "WRITE_TODOS_SYSTEM_TEMPLATE",
    # Tool descriptions
    "WRITE_TODOS_TOOL_DESCRIPTION",
    "DeepAgentPrompts",
    "PromptManager",
    # Models
    "PromptTemplate",
    # Enums
    "PromptType",
    # Factory functions
    "create_prompt_template",
    "format_template",
    "get_system_prompt",
    "get_tool_description",
    # Global instance
    "prompt_manager",
]


# Prompt constants for DeepAgent operations
DEEP_AGENT_PROMPTS = {
    "system": "You are a DeepAgent for complex reasoning and task execution.",
    "task_execution": "Execute the following task: {task_description}",
    "reasoning": "Reason step by step about: {query}",
}


class DeepAgentPrompts:
    """Prompt templates for DeepAgent operations."""

    PROMPTS = DEEP_AGENT_PROMPTS
