"""
Verification tests for the refactoring of agent_orchestrator.py.

This module tests that the refactoring to move prompts and types to their
respective directories was successful and all imports work correctly.
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_refactoring_verification():
    """Test that all refactored components work correctly."""

    # Test datatypes imports
    from DeepResearch.src.datatypes.workflow_orchestration import (
        BreakConditionCheck,
        NestedLoopRequest,
        OrchestrationResult,
        OrchestratorDependencies,
        SubgraphSpawnRequest,
    )

    assert OrchestratorDependencies is not None
    assert NestedLoopRequest is not None
    assert SubgraphSpawnRequest is not None
    assert BreakConditionCheck is not None
    assert OrchestrationResult is not None

    # Test main datatypes package
    from DeepResearch.src.datatypes import (
        BreakConditionCheck as BCC1,
    )
    from DeepResearch.src.datatypes import (
        NestedLoopRequest as NLR1,
    )
    from DeepResearch.src.datatypes import (
        OrchestrationResult as OR1,
    )
    from DeepResearch.src.datatypes import (
        OrchestratorDependencies as OD1,
    )
    from DeepResearch.src.datatypes import (
        SubgraphSpawnRequest as SSR1,
    )

    assert OD1 is not None
    assert NLR1 is not None
    assert SSR1 is not None
    assert BCC1 is not None
    assert OR1 is not None

    # Test prompts
    from DeepResearch.src.prompts.orchestrator import (
        ORCHESTRATOR_INSTRUCTIONS,
        ORCHESTRATOR_SYSTEM_PROMPT,
        OrchestratorPrompts,
    )
    from DeepResearch.src.prompts.workflow_orchestrator import (
        WORKFLOW_ORCHESTRATOR_INSTRUCTIONS,
        WORKFLOW_ORCHESTRATOR_SYSTEM_PROMPT,
        WorkflowOrchestratorPrompts,
    )

    assert ORCHESTRATOR_SYSTEM_PROMPT is not None
    assert ORCHESTRATOR_INSTRUCTIONS is not None
    assert OrchestratorPrompts is not None
    assert isinstance(ORCHESTRATOR_SYSTEM_PROMPT, str)
    assert isinstance(ORCHESTRATOR_INSTRUCTIONS, list)
    assert WORKFLOW_ORCHESTRATOR_SYSTEM_PROMPT is not None
    assert WORKFLOW_ORCHESTRATOR_INSTRUCTIONS is not None
    assert WorkflowOrchestratorPrompts is not None
    assert isinstance(WORKFLOW_ORCHESTRATOR_SYSTEM_PROMPT, str)
    assert isinstance(WORKFLOW_ORCHESTRATOR_INSTRUCTIONS, list)

    # Test agent orchestrator
    from DeepResearch.src.agents.agent_orchestrator import AgentOrchestrator

    assert AgentOrchestrator is not None


if __name__ == "__main__":
    test_refactoring_verification()
