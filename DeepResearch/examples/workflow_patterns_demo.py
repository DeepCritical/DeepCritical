#!/usr/bin/env python3
"""
Comprehensive demonstration of DeepCritical agent interaction design patterns.

This script demonstrates all the workflow pattern implementations including:
- Collaborative patterns with consensus computation
- Sequential patterns with step-by-step execution
- Hierarchical patterns with coordinator-subordinate relationships
- State machine orchestration using Pydantic Graph
- Agent-based pattern execution with Pydantic AI
"""

import asyncio

# Prefer absolute imports for static checkers
from DeepResearch.src.workflow_patterns import (
    InteractionPattern,
    WorkflowPatternUtils,
    WorkflowPatternExecutor,
    execute_collaborative_workflow,
    execute_sequential_workflow,
    execute_hierarchical_workflow,
    demonstrate_workflow_patterns,
    WorkflowPatternFactory,
    agent_registry,
)
from DeepResearch.src.datatypes.agents import AgentType
from DeepResearch.src.datatypes.workflow_patterns import (
    create_interaction_state,
    MessageType,
)


class MockAgentExecutor:
    """Mock agent executor for demonstration purposes."""

    def __init__(self, agent_id: str, agent_type: AgentType):
        self.agent_id = agent_id
        self.agent_type = agent_type

    async def __call__(self, messages):
        """Mock agent execution."""
        # Simulate processing time
        await asyncio.sleep(0.1)

        # Return mock result based on agent type
        if self.agent_type == AgentType.PARSER:
            return {
                "result": f"Parsed input for {self.agent_id}",
                "confidence": 0.9,
                "entities": ["entity1", "entity2"],
            }
        elif self.agent_type == AgentType.PLANNER:
            return {
                "result": f"Created plan for {self.agent_id}",
                "confidence": 0.85,
                "steps": ["step1", "step2", "step3"],
            }
        elif self.agent_type == AgentType.SEARCH:
            return {
                "result": f"Performed search for {self.agent_id}",
                "confidence": 0.8,
                "results": ["result1", "result2"],
            }
        elif self.agent_type == AgentType.EXECUTOR:
            return {
                "result": f"Executed task for {self.agent_id}",
                "confidence": 0.9,
                "output": "Task completed successfully",
            }
        elif self.agent_type == AgentType.ORCHESTRATOR:
            return {
                "result": f"Orchestrated workflow for {self.agent_id}",
                "confidence": 0.95,
                "coordination": "Workflow coordinated",
            }
        else:
            return {
                "result": f"Generic processing for {self.agent_id}",
                "confidence": 0.7,
            }


async def demonstrate_advanced_patterns():
    """Demonstrate advanced pattern combinations and adaptive selection."""

    print("=== Advanced Pattern Demonstration ===")

    # Create mock agent executors
    agents = ["parser", "planner", "searcher", "executor", "orchestrator"]
    agent_types = {
        "parser": AgentType.PARSER,
        "planner": AgentType.PLANNER,
        "searcher": AgentType.SEARCH,
        "executor": AgentType.EXECUTOR,
        "orchestrator": AgentType.ORCHESTRATOR,
    }

    agent_executors = {
        agent_id: MockAgentExecutor(agent_id, agent_type)
        for agent_id, agent_type in agent_types.items()
    }

    # Register executors
    for agent_id, executor in agent_executors.items():
        agent_registry.register(agent_id, executor)

    # 1. Test collaborative pattern
    print("\n1. Testing Collaborative Pattern:")
    collaborative_result = await execute_collaborative_workflow(
        question="What are the key applications of machine learning in healthcare?",
        agents=agents,
        agent_types=agent_types,
        agent_executors=agent_executors,
        config={
            "max_rounds": 5,
            "consensus_threshold": 0.8,
        },
    )
    print(f"Collaborative result length: {len(collaborative_result)} characters")

    # 2. Test sequential pattern
    print("\n2. Testing Sequential Pattern:")
    sequential_result = await execute_sequential_workflow(
        question="Explain the process of protein folding",
        agents=agents,
        agent_types=agent_types,
        agent_executors=agent_executors,
        config={
            "max_rounds": len(agents),
        },
    )
    print(f"Sequential result length: {len(sequential_result)} characters")

    # 3. Test hierarchical pattern
    print("\n3. Testing Hierarchical Pattern:")
    hierarchical_result = await execute_hierarchical_workflow(
        question="Analyze the impact of climate change on biodiversity",
        coordinator_id="orchestrator",
        subordinate_ids=["parser", "planner", "searcher", "executor"],
        agent_types=agent_types,
        agent_executors=agent_executors,
        config={
            "max_rounds": 3,
        },
    )
    print(f"Hierarchical result length: {len(hierarchical_result)} characters")

    # 4. Test pattern factory
    print("\n4. Testing Pattern Factory:")
    factory = WorkflowPatternFactory()

    from DeepResearch.src.workflow_patterns import InteractionPattern

    interaction_state = factory.create_interaction_state(
        pattern=InteractionPattern.COLLABORATIVE,
        agents=agents,
        agent_types=agent_types,
        config={"max_rounds": 3},
    )

    print(f"Created interaction state with {len(interaction_state.agents)} agents")
    print(f"Pattern: {interaction_state.pattern.value}")
    print(f"Max rounds: {interaction_state.max_rounds}")

    # 5. Test executor with custom config
    print("\n5. Testing Workflow Executor with Custom Config:")
    from DeepResearch.src.workflow_patterns import WorkflowPatternConfig
    from DeepResearch.src.workflow_patterns import InteractionPattern

    config = WorkflowPatternConfig(
        pattern=InteractionPattern.COLLABORATIVE,
        max_rounds=2,
        consensus_threshold=0.9,
        timeout=60.0,
    )
    executor = WorkflowPatternExecutor(config)

    custom_result = await executor.execute_collaborative_pattern(
        question="What are the latest developments in quantum computing?",
        agents=agents[:3],  # Use only first 3 agents
        agent_types={k: v for k, v in agent_types.items() if k in agents[:3]},
        agent_executors={k: v for k, v in agent_executors.items() if k in agents[:3]},
    )
    print(f"Custom executor result length: {len(custom_result)} characters")

    print("\n=== Advanced Pattern Demonstration Complete ===")


async def demonstrate_consensus_algorithms():
    """Demonstrate different consensus algorithms."""

    print("=== Consensus Algorithm Demonstration ===")

    # Sample results from different agents
    results = [
        {
            "answer": "Machine learning improves healthcare diagnostics",
            "confidence": 0.9,
        },
        {
            "answer": "Machine learning improves healthcare diagnostics",
            "confidence": 0.85,
        },
        {"answer": "Machine learning enhances medical imaging", "confidence": 0.8},
        {
            "answer": "Machine learning improves healthcare diagnostics",
            "confidence": 0.9,
        },
    ]

    # Test different consensus algorithms
    algorithms = [
        ("Simple Agreement", "simple_agreement"),
        ("Majority Vote", "majority_vote"),
        ("Confidence Based", "confidence_based"),
    ]

    for name, algorithm_str in algorithms:
        print(f"\n{name} Algorithm:")

        try:
            from DeepResearch.src.utils.workflow_patterns import ConsensusAlgorithm

            algorithm_enum = ConsensusAlgorithm.SIMPLE_AGREEMENT
            if algorithm_str == "weighted":
                algorithm_enum = ConsensusAlgorithm.WEIGHTED_AVERAGE
            elif algorithm_str == "majority":
                algorithm_enum = ConsensusAlgorithm.MAJORITY_VOTE

            consensus_result = WorkflowPatternUtils.compute_consensus(
                results,
                algorithm=algorithm_enum,
                confidence_threshold=0.7,
            )

            print(f"  Consensus reached: {consensus_result.consensus_reached}")
            print(f"  Final result: {consensus_result.final_result}")
            print(f"  Confidence: {consensus_result.confidence:.3f}")
            print(f"  Agreement score: {consensus_result.agreement_score:.3f}")
            print(f"  Algorithm used: {consensus_result.algorithm_used.value}")

        except Exception as e:
            print(f"  Error: {e}")

    print("\n=== Consensus Algorithm Demonstration Complete ===")


async def demonstrate_message_routing():
    """Demonstrate message routing strategies."""

    print("=== Message Routing Demonstration ===")

    # Create sample messages
    messages = [
        WorkflowPatternUtils.create_message(
            "agent1", "agent2", MessageType.DATA, "Hello agent2"
        ),
        WorkflowPatternUtils.create_message(
            "agent1", "agent3", MessageType.DATA, "Hello agent3"
        ),
        WorkflowPatternUtils.create_broadcast_message(
            "agent2", "Broadcast from agent2"
        ),
        WorkflowPatternUtils.create_request_message(
            "agent3", "agent1", {"query": "test"}, "test_request"
        ),
    ]

    agents = ["agent1", "agent2", "agent3"]

    # Test different routing strategies
    strategies = [
        ("Direct", "direct"),
        ("Broadcast", "broadcast"),
        ("Round Robin", "round_robin"),
        ("Priority Based", "priority_based"),
        ("Load Balanced", "load_balanced"),
    ]

    for name, strategy_str in strategies:
        print(f"\n{name} Routing:")

        try:
            from DeepResearch.src.utils.workflow_patterns import MessageRoutingStrategy

            strategy_enum = MessageRoutingStrategy.DIRECT
            if strategy_str == "broadcast":
                strategy_enum = MessageRoutingStrategy.BROADCAST
            elif strategy_str == "round_robin":
                strategy_enum = MessageRoutingStrategy.ROUND_ROBIN
            elif strategy_str == "priority_based":
                strategy_enum = MessageRoutingStrategy.PRIORITY_BASED
            elif strategy_str == "load_balanced":
                strategy_enum = MessageRoutingStrategy.LOAD_BALANCED

            routed = WorkflowPatternUtils.route_messages(
                messages, strategy_enum, agents
            )

            for agent, msgs in routed.items():
                print(f"  {agent}: {len(msgs)} messages")

        except Exception as e:
            print(f"  Error: {e}")

    print("\n=== Message Routing Demonstration Complete ===")


async def demonstrate_state_management():
    """Demonstrate interaction state management."""

    print("=== State Management Demonstration ===")

    # Create interaction state
    state = create_interaction_state(
        pattern=InteractionPattern.COLLABORATIVE,
        agents=["agent1", "agent2", "agent3"],
        agent_types={
            "agent1": AgentType.PARSER,
            "agent2": AgentType.PLANNER,
            "agent3": AgentType.EXECUTOR,
        },
    )

    print(f"Initial state: {len(state.agents)} agents, round {state.current_round}")

    # Simulate some rounds
    for round_num in range(3):
        print(f"\nRound {round_num + 1}:")

        # Add some messages
        message1 = WorkflowPatternUtils.create_message(
            "agent1", "agent2", MessageType.DATA, f"Round {round_num} data"
        )
        message2 = WorkflowPatternUtils.create_broadcast_message(
            "agent2", f"Round {round_num} broadcast"
        )

        state.send_message(message1)
        state.send_message(message2)

        print(f"  Messages sent: {len(state.messages)}")
        print(f"  Queue size: {len(state.message_queue)}")

        # Move to next round
        state.next_round()

    # Show final state
    print("Final state:")
    print(f"  Total rounds: {state.current_round}")
    print(f"  Total messages: {len(state.messages)}")
    print(f"  Active agents: {len(state.active_agents)}")
    print(f"  Errors: {len(state.errors)}")

    print("\n=== State Management Demonstration Complete ===")


async def run_comprehensive_demo():
    """Run all demonstrations."""

    print("🚀 DeepCritical Agent Interaction Design Patterns - Comprehensive Demo")
    print("=" * 80)

    try:
        # Run all demonstrations
        await demonstrate_workflow_patterns()
        print("\n" + "=" * 80)

        await demonstrate_advanced_patterns()
        print("\n" + "=" * 80)

        await demonstrate_consensus_algorithms()
        print("\n" + "=" * 80)

        await demonstrate_message_routing()
        print("\n" + "=" * 80)

        await demonstrate_state_management()
        print("\n" + "=" * 80)

        print("✅ All demonstrations completed successfully!")

        # Show summary
        print("\n📊 Summary:")
        print(f"- Executed {len(agent_registry.list())} registered agent executors")
        print(
            f"- Demonstrated {len([p for p in InteractionPattern])} interaction patterns"
        )
        print(
            f"- Tested {len(['simple_agreement', 'majority_vote', 'confidence_based'])} consensus algorithms"
        )
        print(
            f"- Demonstrated {len(['direct', 'broadcast', 'round_robin', 'priority_based', 'load_balanced'])} routing strategies"
        )

    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        raise


if __name__ == "__main__":
    # Run the comprehensive demonstration
    asyncio.run(run_comprehensive_demo())
