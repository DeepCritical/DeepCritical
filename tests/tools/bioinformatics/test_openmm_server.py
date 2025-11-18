from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from DeepResearch.src.tools.bioinformatics.openmm_server import OpenMMServer

# Sample PDB content for testing
PDB_CONTENT = """
ATOM      1  N   ALA A   1      27.278  39.027  58.236  1.00  0.00           N
ATOM      2  CA  ALA A   1      28.125  36.892  57.886  1.00  0.00           C
ATOM      3  C   ALA A   1      27.391  37.476  56.918  1.00  0.00           C
ATOM      4  O   ALA A   1      26.963  38.289  57.292  1.00  0.00           O
ATOM      5  CB  ALA A   1      29.049  37.892  58.236  1.00  0.00           C
ATOM      6  N   ALA A   2      27.878  39.527  58.736  1.00  0.00           N
ATOM      7  CA  ALA A   2      28.625  37.392  58.386  1.00  0.00           C
ATOM      8  C   ALA A   2      27.891  37.976  57.418  1.00  0.00           C
ATOM      9  O   ALA A   2      27.463  38.789  57.792  1.00  0.00           O
ATOM     10  CB  ALA A   2      29.549  38.392  58.736  1.00  0.00           C
"""


@pytest.fixture
def pdb_file() -> str:
    """Create a temporary PDB file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".pdb", delete=False) as tmp:
        tmp.write(PDB_CONTENT.encode())
        return tmp.name


def test_openmm_server(pdb_file: str):
    """Test the OpenMM server."""
    server = OpenMMServer()
    result = server.run({"pdb_file": pdb_file})

    assert result.success
    assert "cleaned_pdb_file" in result.data
    assert "energy" in result.data

    # Verify that the output file exists
    cleaned_pdb_path = Path(result.data["cleaned_pdb_file"])
    assert cleaned_pdb_path.exists()

    # Verify that the energy is a float
    energy = float(result.data["energy"])
    assert isinstance(energy, float)
