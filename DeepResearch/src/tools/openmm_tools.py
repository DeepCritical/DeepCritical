"""OpenMM-based molecular simulation tools for DeepCritical.

This module provides lightweight wrappers around OpenMM to perform
energy minimization and short molecular dynamics simulations on user
provided PDB content. The tooling is intentionally conservative so it
can run inside CI environments without GPU acceleration.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
from typing import Any, cast

from openmm import LangevinIntegrator, NonbondedForce, System, unit as openmm_unit
from openmm.app import PDBFile, Simulation
from openmm.openmm import CustomExternalForce, HarmonicBondForce

from .base import ExecutionResult, ToolRunner, ToolSpec, registry

unit = cast(Any, openmm_unit)

_LJ_PARAMS = {
    "H": (0.106 * unit.nanometer, 0.0157 * unit.kilojoule_per_mole),
    "C": (0.339 * unit.nanometer, 0.359824 * unit.kilojoule_per_mole),
    "N": (0.325 * unit.nanometer, 0.71128 * unit.kilojoule_per_mole),
    "O": (0.295 * unit.nanometer, 0.87864 * unit.kilojoule_per_mole),
}
_DEFAULT_SIGMA = 0.3 * unit.nanometer
_DEFAULT_EPSILON = 0.1 * unit.kilojoule_per_mole


@dataclass
class OpenMMMinimizationTool(ToolRunner):
    """Perform OpenMM minimization and short dynamics on a PDB structure."""

    def __init__(self) -> None:
        super().__init__(
            ToolSpec(
                name="openmm_minimize",
                description=(
                    "Minimize a PDB structure with OpenMM and optionally run "
                    "a few simulation steps to estimate stability."
                ),
                inputs={"pdb_contents": "TEXT"},
                outputs={
                    "initial_potential_energy_kj_mol": "float",
                    "minimized_potential_energy_kj_mol": "float",
                    "post_dynamics_potential_energy_kj_mol": "float",
                    "energy_change_kj_mol": "float",
                    "energy_trajectory_kj_mol": "list[float]",
                    "minimized_pdb": "TEXT",
                },
            )
        )

    def _build_system(self, pdb: PDBFile) -> tuple[System, list[Any]]:
        """Create a basic OpenMM system with Lennard-Jones particles.

        We avoid heavy force fields to keep runtime predictable. Particle
        parameters are derived from element types with sensible defaults.
        """

        system = System()
        positions = pdb.positions
        atoms = list(pdb.topology.atoms())

        nonbonded_force = NonbondedForce()
        bond_force = HarmonicBondForce()
        restraint_force = CustomExternalForce("0.5*k*((x-x0)^2 + (y-y0)^2 + (z-z0)^2)")
        restraint_force.addGlobalParameter("k", 100.0)  # kJ/mol/nm^2
        restraint_force.addPerParticleParameter("x0")
        restraint_force.addPerParticleParameter("y0")
        restraint_force.addPerParticleParameter("z0")

        for idx, atom in enumerate(atoms):
            mass = atom.element.mass if atom.element else 12.0 * unit.amu
            system.addParticle(mass)

            sigma, epsilon = _LJ_PARAMS.get(
                atom.element.symbol if atom.element else None,
                (_DEFAULT_SIGMA, _DEFAULT_EPSILON),
            )
            nonbonded_force.addParticle(0.0, sigma, epsilon)

            pos = positions[idx].value_in_unit(unit.nanometer)
            restraint_force.addParticle(idx, pos)

        # Add harmonic bonds based on topology information when present
        any_bonds = False
        for bond in pdb.topology.bonds():
            bond_force.addBond(
                bond[0].index,
                bond[1].index,
                0.15,
                300.0,  # kJ/mol/nm^2
            )
            any_bonds = True

        system.addForce(nonbonded_force)
        system.addForce(restraint_force)
        if any_bonds:
            system.addForce(bond_force)

        return system, positions

    def run(self, params: dict[str, Any]) -> ExecutionResult:
        valid, error = self.validate(params)
        if not valid:
            return ExecutionResult(success=False, data={}, error=error)

        pdb_data = params["pdb_contents"]
        steps = int(params.get("simulation_steps", 5))
        temperature = float(params.get("temperature_kelvin", 300.0))
        friction = float(params.get("friction_coeff_ps", 1.0))
        timestep = float(params.get("timestep_fs", 1.0))

        try:
            pdb = PDBFile(StringIO(pdb_data))
        except Exception as exc:  # pragma: no cover - OpenMM provides context
            return ExecutionResult(
                success=False,
                data={},
                error=f"Failed to parse PDB contents: {exc}",
            )

        system, positions = self._build_system(pdb)
        integrator = LangevinIntegrator(
            temperature * unit.kelvin,
            friction / unit.picosecond,
            timestep * unit.femtoseconds,
        )
        simulation = Simulation(pdb.topology, system, integrator)
        simulation.context.setPositions(positions)

        initial_state = simulation.context.getState(getEnergy=True)
        initial_energy = initial_state.getPotentialEnergy().value_in_unit(
            unit.kilojoule_per_mole
        )

        simulation.minimizeEnergy(maxIterations=100)
        minimized_state = simulation.context.getState(getEnergy=True, getPositions=True)
        minimized_energy = minimized_state.getPotentialEnergy().value_in_unit(
            unit.kilojoule_per_mole
        )

        minimized_positions = minimized_state.getPositions()
        minimized_pdb_io = StringIO()
        PDBFile.writeFile(
            simulation.topology,
            minimized_positions,
            minimized_pdb_io,
        )
        minimized_pdb = minimized_pdb_io.getvalue()

        energy_trajectory: list[float] = []
        if steps > 0:
            simulation.context.setVelocitiesToTemperature(temperature * unit.kelvin)
            for _ in range(steps):
                simulation.step(1)
                state = simulation.context.getState(getEnergy=True)
                energy_trajectory.append(
                    state.getPotentialEnergy().value_in_unit(unit.kilojoule_per_mole)
                )
            final_energy = energy_trajectory[-1]
        else:
            final_energy = minimized_energy

        return ExecutionResult(
            success=True,
            data={
                "initial_potential_energy_kj_mol": float(initial_energy),
                "minimized_potential_energy_kj_mol": float(minimized_energy),
                "post_dynamics_potential_energy_kj_mol": float(final_energy),
                "energy_change_kj_mol": float(minimized_energy - initial_energy),
                "energy_trajectory_kj_mol": energy_trajectory,
                "minimized_pdb": minimized_pdb,
                "temperature_kelvin": temperature,
                "steps_run": steps,
            },
            error=None,
        )


registry.register("openmm_minimize", OpenMMMinimizationTool)

__all__ = ["OpenMMMinimizationTool"]
