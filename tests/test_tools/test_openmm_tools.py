from __future__ import annotations

import math

from DeepResearch.src.tools.openmm_tools import OpenMMMinimizationTool

SIMPLE_WATER_PDB = """\
ATOM      1  O   HOH A   1       0.000   0.000   0.000  1.00  0.00           O
ATOM      2  H1  HOH A   1       0.095   0.000   0.000  1.00  0.00           H
ATOM      3  H2  HOH A   1      -0.032   0.090   0.000  1.00  0.00           H
TER
END
"""


def test_openmm_minimize_produces_energy_and_pdb():
    tool = OpenMMMinimizationTool()
    result = tool.run({"pdb_contents": SIMPLE_WATER_PDB, "simulation_steps": 2})

    assert result.success, result.error
    minimized_energy = result.data["minimized_potential_energy_kj_mol"]
    assert math.isfinite(minimized_energy)
    assert len(result.data["minimized_pdb"]) > 0
    assert len(result.data["energy_trajectory_kj_mol"]) == 2
    assert (
        result.data["post_dynamics_potential_energy_kj_mol"]
        == result.data["energy_trajectory_kj_mol"][-1]
    )
