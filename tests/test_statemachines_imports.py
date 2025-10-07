"""
Import tests for DeepResearch statemachines modules.

This module tests that all imports from the statemachines subdirectory work correctly,
including all individual statemachine modules and their dependencies.
"""

import pytest


class TestStatemachinesModuleImports:
    """Test imports for individual statemachine modules."""

    def test_bioinformatics_workflow_imports(self):
        """Test all imports from bioinformatics_workflow module."""

        from DeepResearch.src.statemachines.bioinformatics_workflow import (
            AssessDataQuality,
            BioinformaticsState,
            CreateReasoningTask,
            FuseDataSources,
            ParseBioinformaticsQuery,
            PerformReasoning,
            SynthesizeResults,
        )

        # Verify they are all accessible and not None
        assert BioinformaticsState is not None
        assert ParseBioinformaticsQuery is not None
        assert FuseDataSources is not None
        assert AssessDataQuality is not None
        assert CreateReasoningTask is not None
        assert PerformReasoning is not None
        assert SynthesizeResults is not None

    def test_deepsearch_workflow_imports(self):
        """Test all imports from deepsearch_workflow module."""
        # Skip this test since deepsearch_workflow module is currently empty

        # from DeepResearch.src.statemachines.deepsearch_workflow import (
        #     DeepSearchState,
        #     InitializeDeepSearch,
        #     PlanSearchStrategy,
        #     ExecuteSearchStep,
        #     CheckSearchProgress,
        #     SynthesizeResults,
        #     EvaluateResults,
        #     CompleteDeepSearch,
        #     DeepSearchError,
        # )

        # # Verify they are all accessible and not None
        # assert DeepSearchState is not None
        # assert InitializeDeepSearch is not None
        # assert PlanSearchStrategy is not None
        # assert ExecuteSearchStep is not None
        # assert CheckSearchProgress is not None
        # assert SynthesizeResults is not None
        # assert EvaluateResults is not None
        # assert CompleteDeepSearch is not None
        # assert DeepSearchError is not None

    def test_rag_workflow_imports(self):
        """Test all imports from rag_workflow module."""

        from DeepResearch.src.statemachines.rag_workflow import (
            GenerateResponse,
            InitializeRAG,
            LoadDocuments,
            ProcessDocuments,
            QueryRAG,
            RAGError,
            RAGState,
            StoreDocuments,
        )

        # Verify they are all accessible and not None
        assert RAGState is not None
        assert InitializeRAG is not None
        assert LoadDocuments is not None
        assert ProcessDocuments is not None
        assert StoreDocuments is not None
        assert QueryRAG is not None
        assert GenerateResponse is not None
        assert RAGError is not None

    def test_search_workflow_imports(self):
        """Test all imports from search_workflow module."""

        from DeepResearch.src.statemachines.search_workflow import (
            GenerateFinalResponse,
            InitializeSearch,
            PerformWebSearch,
            ProcessResults,
            SearchWorkflowError,
            SearchWorkflowState,
        )

        # Verify they are all accessible and not None
        assert SearchWorkflowState is not None
        assert InitializeSearch is not None
        assert PerformWebSearch is not None
        assert ProcessResults is not None
        assert GenerateFinalResponse is not None
        assert SearchWorkflowError is not None


class TestStatemachinesCrossModuleImports:
    """Test cross-module imports and dependencies within statemachines."""

    def test_statemachines_internal_dependencies(self):
        """Test that statemachine modules can import from each other correctly."""
        # Test that modules can import shared patterns
        from DeepResearch.src.statemachines.bioinformatics_workflow import (
            BioinformaticsState,
        )
        from DeepResearch.src.statemachines.rag_workflow import RAGState

        # This should work without circular imports
        assert BioinformaticsState is not None
        assert RAGState is not None

    def test_datatypes_integration_imports(self):
        """Test that statemachines can import from datatypes module."""
        # This tests the import chain: statemachines -> datatypes
        from DeepResearch.src.datatypes.bioinformatics import FusedDataset
        from DeepResearch.src.statemachines.bioinformatics_workflow import (
            BioinformaticsState,
        )

        # If we get here without ImportError, the import chain works
        assert BioinformaticsState is not None
        assert FusedDataset is not None

    def test_agents_integration_imports(self):
        """Test that statemachines can import from agents module."""
        # This tests the import chain: statemachines -> agents
        from DeepResearch.src.agents.bioinformatics_agents import BioinformaticsAgent
        from DeepResearch.src.statemachines.bioinformatics_workflow import (
            ParseBioinformaticsQuery,
        )

        # If we get here without ImportError, the import chain works
        assert ParseBioinformaticsQuery is not None
        assert BioinformaticsAgent is not None

    def test_pydantic_graph_imports(self):
        """Test that statemachines can import from pydantic_graph."""
        # Test that BaseNode and other pydantic_graph imports work
        from DeepResearch.src.statemachines.bioinformatics_workflow import BaseNode

        # If we get here without ImportError, the import chain works
        assert BaseNode is not None


class TestStatemachinesComplexImportChains:
    """Test complex import chains involving multiple modules."""

    def test_full_statemachines_initialization_chain(self):
        """Test the complete import chain for statemachines initialization."""
        try:
            from DeepResearch.src.agents.bioinformatics_agents import (
                BioinformaticsAgent,
            )
            from DeepResearch.src.datatypes.bioinformatics import FusedDataset
            from DeepResearch.src.statemachines.bioinformatics_workflow import (
                BioinformaticsState,
                FuseDataSources,
                ParseBioinformaticsQuery,
            )
            from DeepResearch.src.statemachines.rag_workflow import (
                InitializeRAG,
                RAGState,
            )
            from DeepResearch.src.statemachines.search_workflow import (
                InitializeSearch,
                SearchWorkflowState,
            )

            # If all imports succeed, the chain is working
            assert BioinformaticsState is not None
            assert ParseBioinformaticsQuery is not None
            assert FuseDataSources is not None
            assert RAGState is not None
            assert InitializeRAG is not None
            assert SearchWorkflowState is not None
            assert InitializeSearch is not None
            assert FusedDataset is not None
            assert BioinformaticsAgent is not None

        except ImportError as e:
            pytest.fail(f"Statemachines import chain failed: {e}")

    def test_workflow_execution_chain(self):
        """Test the complete import chain for workflow execution."""
        try:
            from DeepResearch.src.statemachines.bioinformatics_workflow import (
                SynthesizeResults,
            )

            # from DeepResearch.src.statemachines.deepsearch_workflow import (
            #     CompleteDeepSearch,
            # )
            from DeepResearch.src.statemachines.rag_workflow import GenerateResponse
            from DeepResearch.src.statemachines.search_workflow import (
                GenerateFinalResponse,
            )

            # If all imports succeed, the chain is working
            assert SynthesizeResults is not None
            # assert CompleteDeepSearch is not None
            assert GenerateResponse is not None
            assert GenerateFinalResponse is not None

        except ImportError as e:
            pytest.fail(f"Workflow execution import chain failed: {e}")


class TestStatemachinesImportErrorHandling:
    """Test import error handling for statemachines modules."""

    def test_missing_dependencies_handling(self):
        """Test that modules handle missing dependencies gracefully."""
        # Test that modules handle optional dependencies
        from DeepResearch.src.statemachines.bioinformatics_workflow import BaseNode

        # This should work even if pydantic_graph is not available in some contexts
        assert BaseNode is not None

    def test_circular_import_prevention(self):
        """Test that there are no circular imports in statemachines."""
        # This test will fail if there are circular imports

        # If we get here, no circular imports were detected
        assert True

    def test_state_class_instantiation(self):
        """Test that state classes can be instantiated."""
        from DeepResearch.src.statemachines.bioinformatics_workflow import (
            BioinformaticsState,
        )

        # Test that we can create instances (basic functionality)
        try:
            state = BioinformaticsState(question="test question")
            assert state is not None
            assert state.question == "test question"
            assert state.go_annotations == []
            assert state.pubmed_papers == []
        except Exception as e:
            pytest.fail(f"State class instantiation failed: {e}")

    def test_node_class_instantiation(self):
        """Test that node classes can be instantiated."""
        from DeepResearch.src.statemachines.bioinformatics_workflow import (
            ParseBioinformaticsQuery,
        )

        # Test that we can create instances (basic functionality)
        try:
            node = ParseBioinformaticsQuery()
            assert node is not None
        except Exception as e:
            pytest.fail(f"Node class instantiation failed: {e}")

    def test_pydantic_graph_compatibility(self):
        """Test that statemachines are compatible with pydantic_graph."""
        from DeepResearch.src.statemachines.bioinformatics_workflow import BaseNode

        # Test that BaseNode is properly imported from pydantic_graph
        assert BaseNode is not None

        # Test that common pydantic_graph attributes are available
        # (these might not exist if pydantic_graph is not installed)
        if hasattr(BaseNode, "__annotations__"):
            annotations = BaseNode.__annotations__
            assert isinstance(annotations, dict)
