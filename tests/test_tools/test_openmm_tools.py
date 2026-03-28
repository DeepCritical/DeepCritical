from __future__ import annotations

import math

from DeepResearch.src.tools.openmm_tools import OpenMMMinimizationTool

SIMPLE_WATER_PDB = """\
ATOM      1  O   HOH A   1       0.000   0.000   0.000  1.00  0.00           O
ATOM      2  H1  HOH A   1       0.957   0.000   0.000  1.00  0.00           H
ATOM      3  H2  HOH A   1      -0.240   0.927   0.000  1.00  0.00           H
TER
END
"""


def test_openmm_minimize_produces_energy_and_pdb():
    tool = OpenMMMinimizationTool()
    result = tool.run({"pdb_contents": SIMPLE_WATER_PDB, "simulation_steps": 2})

    assert result.success, result.error
    initial_energy = result.data["initial_potential_energy_kj_mol"]
    minimized_energy = result.data["minimized_potential_energy_kj_mol"]
    assert math.isfinite(initial_energy)
    assert math.isfinite(minimized_energy)
    assert minimized_energy <= initial_energy
    assert len(result.data["minimized_pdb"]) > 0
    assert len(result.data["energy_trajectory_kj_mol"]) == 2
    assert (
        result.data["post_dynamics_potential_energy_kj_mol"]
        == result.data["energy_trajectory_kj_mol"][-1]
    )


def test_openmm_minimize_without_dynamics_returns_minimized_energy():
    tool = OpenMMMinimizationTool()
    result = tool.run({"pdb_contents": SIMPLE_WATER_PDB, "simulation_steps": 0})

    assert result.success, result.error
    assert result.data["steps_run"] == 0
    assert result.data["energy_trajectory_kj_mol"] == []
    assert (
        result.data["post_dynamics_potential_energy_kj_mol"]
        == result.data["minimized_potential_energy_kj_mol"]
    )


def test_openmm_tool_spec_exposes_optional_runtime_parameters():
    tool = OpenMMMinimizationTool()
    valid, error = tool.validate({"pdb_contents": SIMPLE_WATER_PDB})

    assert valid, error
    assert tool.spec.inputs["simulation_steps"] == "int (optional, default 5)"
    assert tool.spec.inputs["temperature_kelvin"] == "float (optional, default 300.0)"
    assert tool.spec.inputs["friction_coeff_ps"] == "float (optional, default 1.0)"
    assert tool.spec.inputs["timestep_fs"] == "float (optional, default 1.0)"
