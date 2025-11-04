"""
Import tests for DeepResearch.app module.

This module tests that the main application module can be imported
without errors, specifically checking for import-time failures like
forward reference errors in type hints.
"""

import pytest


class TestAppModuleImport:
    """Test imports for the main application module."""

    def test_app_module_can_be_imported(self):
        """Test that DeepResearch.app can be imported without errors.

        This test specifically guards against:
        - Forward reference errors (NameError with undefined classes)
        - Module-level code execution issues
        - Import-time Graph instantiation problems

        Regression test for: NameError: name 'PrepareChallenge' is not defined
        """
        try:
            import DeepResearch.app

            # Verify the module loaded successfully
            assert DeepResearch.app is not None
            assert hasattr(DeepResearch.app, "main")
            assert hasattr(DeepResearch.app, "run_graph")

        except NameError as e:
            pytest.fail(
                f"Import failed with NameError (likely forward reference issue): {e}"
            )
        except ImportError as e:
            pytest.fail(f"Import failed with ImportError: {e}")

    def test_app_main_function_exists(self):
        """Test that the main() function is accessible."""
        from DeepResearch.app import main

        assert main is not None
        assert callable(main)

    def test_app_run_graph_function_exists(self):
        """Test that run_graph() function is accessible."""
        from DeepResearch.app import run_graph

        assert run_graph is not None
        assert callable(run_graph)

    def test_app_state_class_exists(self):
        """Test that ResearchState class is accessible."""
        from DeepResearch.app import ResearchState

        assert ResearchState is not None
        # Verify it's a dataclass
        assert hasattr(ResearchState, "__dataclass_fields__")

    def test_app_node_classes_exist(self):
        """Test that key node classes are accessible."""
        from DeepResearch.app import (
            Analyze,
            EvaluateChallenge,
            Plan,
            PrepareChallenge,
            RunChallenge,
            Search,
            Synthesize,
        )

        assert Plan is not None
        assert Search is not None
        assert Analyze is not None
        assert Synthesize is not None
        assert PrepareChallenge is not None
        assert RunChallenge is not None
        assert EvaluateChallenge is not None
