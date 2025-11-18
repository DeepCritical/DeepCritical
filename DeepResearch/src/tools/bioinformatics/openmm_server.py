from __future__ import annotations

import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from openmm import LangevinIntegrator, Platform, app  # type: ignore
from openmm.unit import femtosecond, kelvin, nanometer, picosecond  # type: ignore
from pdbfixer import PDBFixer  # type: ignore

from DeepResearch.src.tools.base import ExecutionResult, ToolRunner, ToolSpec


@dataclass
class OpenMMServer(ToolRunner):
    spec: ToolSpec = field(
        default_factory=lambda: ToolSpec(
            name="openmm_server",
            description="Clean a PDB file and run an energy minimization.",
            inputs={
                "pdb_file": "PATH",
            },
            outputs={
                "cleaned_pdb_file": "PATH",
                "energy": "TEXT",
            },
        )
    )

    def run(self, params: dict[str, str]) -> ExecutionResult:
        """Run the OpenMM server."""
        try:
            pdb_file = params["pdb_file"]

            # Clean PDB file
            fixer = PDBFixer(filename=pdb_file)
            fixer.findMissingResidues()
            fixer.findNonstandardResidues()
            fixer.replaceNonstandardResidues()
            fixer.removeHeterogens(True)
            fixer.findMissingAtoms()
            fixer.addMissingAtoms()
            fixer.addMissingHydrogens(7.0)

            with tempfile.NamedTemporaryFile(mode="w", suffix=".pdb", delete=False) as tmp:
                app.PDBFile.writeFile(fixer.topology, fixer.positions, tmp)
                cleaned_pdb_file = tmp.name

            # Run energy minimization
            pdb = app.PDBFile(cleaned_pdb_file)
            forcefield = app.ForceField("amber14-all.xml", "amber14/tip3pfb.xml")

            # Add ignoreExternalBonds=True to handle non-standard PDB files
            system = forcefield.createSystem(
                pdb.topology,
                nonbondedMethod=app.NoCutoff,
                nonbondedCutoff=1.0 * nanometer,
                constraints=app.HBonds,
                ignoreExternalBonds=True,
            )
            integrator = LangevinIntegrator(
                300 * kelvin, 1.0 / picosecond, 2.0 * femtosecond
            )
            platform = Platform.getPlatformByName("CPU")
            simulation = app.Simulation(
                pdb.topology, system, integrator, platform
            )
            simulation.context.setPositions(pdb.positions)
            simulation.minimizeEnergy()

            state = simulation.context.getState(getEnergy=True)
            energy = state.getPotentialEnergy()._value

            with tempfile.NamedTemporaryFile(mode="w", suffix=".pdb", delete=False) as tmp:
                positions = simulation.context.getState(getPositions=True).getPositions()
                app.PDBFile.writeFile(simulation.topology, positions, tmp)
                minimized_pdb_file = tmp.name

            return ExecutionResult(
                success=True,
                data={
                    "cleaned_pdb_file": minimized_pdb_file,
                    "energy": str(energy),
                },
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                error=str(e),
            )
