"""
Global test fixtures for DeepCritical testing framework.
"""

from pathlib import Path

import pytest

from tests.utils.mocks.mock_data import create_test_directory_structure


@pytest.fixture(scope="session")
def test_artifacts_dir():
    """Create test artifacts directory."""
    artifacts_dir = Path("test_artifacts")
    artifacts_dir.mkdir(exist_ok=True)
    return artifacts_dir


@pytest.fixture
def temp_workspace(tmp_path):
    """Create temporary workspace for testing."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    # Create subdirectory structure
    (workspace / "input").mkdir()
    (workspace / "output").mkdir()
    (workspace / "temp").mkdir()

    return workspace


@pytest.fixture
def sample_bioinformatics_data(temp_workspace):
    """Create sample bioinformatics data for testing."""
    data_dir = temp_workspace / "data"
    data_dir.mkdir()

    # Create sample files using mock data generator
    structure = create_test_directory_structure(data_dir)

    return {"workspace": temp_workspace, "data_dir": data_dir, "files": structure}


@pytest.fixture
def mock_llm_response():
    """Mock LLM response for testing."""
    return {
        "success": True,
        "response": "This is a mock LLM response for testing purposes.",
        "tokens_used": 150,
        "model": "mock-model",
        "timestamp": "2024-01-01T00:00:00Z",
    }


@pytest.fixture
def mock_agent_dependencies():
    """Mock agent dependencies for testing."""
    return {
        "model_name": "anthropic:claude-sonnet-4-0",
        "temperature": 0.7,
        "max_tokens": 100,
        "timeout": 30,
        "api_key": "mock-api-key",
    }


@pytest.fixture
def sample_workflow_state():
    """Sample workflow state for testing."""
    return {
        "query": "test query",
        "step": 0,
        "results": {},
        "errors": [],
        "metadata": {"start_time": "2024-01-01T00:00:00Z", "workflow_type": "test"},
    }
