import os
from pathlib import Path

import pytest

from DeepResearch.src.tools.openmm_tool import OpenMMResult, OpenMMTool


@pytest.fixture
def openmm_tool():
    """Pytest fixture to provide an instance of the OpenMMTool."""
    return OpenMMTool()


@pytest.fixture
def test_pdb_path():
    """Pytest fixture to provide the path to the test PDB file."""
    return "tests/data/test_dipeptide.pdb"


@pytest.fixture
def test_fragment_pdb_path():
    """Pytest fixture to provide the path to the test fragment PDB file."""
    return "tests/data/test.pdb"


def test_prep(openmm_tool, test_pdb_path):
    """Test the prep function of the OpenMMTool."""
    result = openmm_tool.prep(test_pdb_path)
    assert result.status == "ok"
    assert "pdb" in result.artifacts
    assert os.path.exists(result.artifacts["pdb"])
    Path(result.artifacts["pdb"]).unlink()  # Clean up the created file


def test_minimize(openmm_tool, test_pdb_path):
    """Test the minimize function of the OpenMMTool."""
    result = openmm_tool.minimize(test_pdb_path)
    assert result.status == "ok"
    assert "pdb" in result.artifacts
    assert os.path.exists(result.artifacts["pdb"])
    assert "initial_energy_kj_mol" in result.metrics
    assert "final_energy_kj_mol" in result.metrics
    assert (
        result.metrics["final_energy_kj_mol"] < result.metrics["initial_energy_kj_mol"]
    )
    Path(result.artifacts["pdb"]).unlink()  # Clean up the created file


def test_md_sample(openmm_tool, test_pdb_path):
    """Test the md_sample function of the OpenMMTool."""
    result = openmm_tool.md_sample(
        test_pdb_path, nsteps=100, report_interval=1
    )  # Using a small number of steps for testing
    assert result.status == "ok"

def test_md_sample_fragment(openmm_tool, test_fragment_pdb_path):
    """Test the md_sample function of the OpenMMTool with a fragment."""
    result = openmm_tool.md_sample(
        test_fragment_pdb_path, nsteps=100, report_interval=1, ignore_external_bonds=True
    )
    assert result.status == "ok"
    assert "traj" in result.artifacts
    assert "state" in result.artifacts
    assert os.path.exists(result.artifacts["traj"])
    assert os.path.exists(result.artifacts["state"])
    assert "rmsd_mean" in result.metrics
    assert "rg_mean" in result.metrics
    Path(result.artifacts["traj"]).unlink()  # Clean up the created files
    Path(result.artifacts["state"]).unlink()
