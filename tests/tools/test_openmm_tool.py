import os
import pytest
from DeepResearch.src.tools.openmm_tool import OpenMMTool, OpenMMResult

@pytest.fixture
def openmm_tool():
    """Pytest fixture to provide an instance of the OpenMMTool."""
    return OpenMMTool()

@pytest.fixture
def test_pdb_path():
    """Pytest fixture to provide the path to the test PDB file."""
    return "tests/data/test_dipeptide.pdb"

def test_prep(openmm_tool, test_pdb_path):
    """Test the prep function of the OpenMMTool."""
    result = openmm_tool.prep(test_pdb_path)
    assert result.status == "ok"
    assert "pdb" in result.artifacts
    assert os.path.exists(result.artifacts["pdb"])
    os.remove(result.artifacts["pdb"])  # Clean up the created file

def test_minimize(openmm_tool, test_pdb_path):
    """Test the minimize function of the OpenMMTool."""
    result = openmm_tool.minimize(test_pdb_path)
    assert result.status == "ok"
    assert "pdb" in result.artifacts
    assert os.path.exists(result.artifacts["pdb"])
    assert "initial_energy_kj_mol" in result.metrics
    assert "final_energy_kj_mol" in result.metrics
    assert result.metrics["final_energy_kj_mol"] < result.metrics["initial_energy_kj_mol"]
    os.remove(result.artifacts["pdb"])  # Clean up the created file

def test_md_sample(openmm_tool, test_pdb_path):
    """Test the md_sample function of the OpenMMTool."""
    result = openmm_tool.md_sample(test_pdb_path, nsteps=100, report_interval=1) # Using a small number of steps for testing
    assert result.status == "ok"
    assert "traj" in result.artifacts
    assert "state" in result.artifacts
    assert os.path.exists(result.artifacts["traj"])
    assert os.path.exists(result.artifacts["state"])
    assert "rmsd_mean" in result.metrics
    assert "rg_mean" in result.metrics
    os.remove(result.artifacts["traj"])  # Clean up the created files
    os.remove(result.artifacts["state"])
