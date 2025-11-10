# deepcritical/tools/openmm_tool.py
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import mdtraj as md  # type: ignore
import numpy as np
from openmm import LangevinMiddleIntegrator, Platform, app, unit  # type: ignore
from openmm.app import (  # type: ignore
    ForceField,
    Modeller,
    PDBFile,
    PDBReporter,
    Simulation,
    StateDataReporter,
)
from pdbfixer import PDBFixer  # type: ignore

from .base import ExecutionResult, ToolRunner, ToolSpec, registry


@dataclass
class OpenMMResult:
    status: str
    artifacts: dict[
        str, str
    ]  # paths: { "traj": ".../traj.xtc", "pdb": ".../final.pdb" }
    metrics: dict[str, float]  # energies, rmsd, rg, hbonds, ss_fraction, etc.
    logs: list[str]


class OpenMMTool(ToolRunner):
    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(
            ToolSpec(
                name="openmm_tool",
                description="Run molecular dynamics simulations using OpenMM.",
                inputs={
                    "action": "TEXT",  # e.g., 'prep', 'minimize', 'md_sample'
                    "pdb_path": "PATH",
                    "nsteps": "INTEGER",
                },
                outputs={
                    "result": "JSON",
                },
            )
        )
        self.cfg = config if config else {}

    def run(self, params: dict[str, Any]) -> ExecutionResult:
        action = params.get("action")
        pdb_path = params.get("pdb_path")

        if not action or not pdb_path:
            return ExecutionResult(
                success=False, error="Missing required parameters: action, pdb_path"
            )

        try:
            ignore_external_bonds = params.get("ignore_external_bonds", False)
            if action == "prep":
                result = self.prep(pdb_path)
            elif action == "minimize":
                result = self.minimize(pdb_path, ignore_external_bonds)
            elif action == "md_sample":
                nsteps = int(params.get("nsteps", 250000))
                report_interval = int(params.get("report_interval", 1000))
                result = self.md_sample(
                    pdb_path, nsteps, report_interval, ignore_external_bonds
                )
            else:
                return ExecutionResult(success=False, error=f"Unknown action: {action}")

            return ExecutionResult(success=True, data=result.__dict__)
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))

    def _create_simulation(self, pdb_path: str, ignore_external_bonds: bool = False):
        """Helper function to create a simulation object."""
        pdb = PDBFile(pdb_path)
        ff = ForceField("amber14-all.xml", "amber14/tip3pfb.xml")
        modeller = Modeller(pdb.topology, pdb.positions)
        modeller.addHydrogens(ff)
        system = ff.createSystem(
            modeller.topology,
            nonbondedMethod=app.NoCutoff,
            ignoreExternalBonds=ignore_external_bonds,
        )
        integrator = LangevinMiddleIntegrator(
            300 * unit.kelvin, 1 / unit.picoseconds, 0.002 * unit.picoseconds
        )  # type: ignore
        platform = Platform.getPlatformByName(self.cfg.get("platform", "CPU"))
        simulation = Simulation(modeller.topology, system, integrator, platform)
        simulation.context.setPositions(modeller.positions)
        return simulation

    def prep(self, input_structure_path: str) -> OpenMMResult:
        """Fix PDB/mmCIF with PDBFixer; return path to cleaned PDB."""
        fixer = PDBFixer(filename=input_structure_path)
        fixer.findMissingResidues()
        fixer.findNonstandardResidues()
        fixer.replaceNonstandardResidues()
        fixer.removeHeterogens(True)
        fixer.findMissingAtoms()
        fixer.addMissingAtoms()
        fixer.addMissingHydrogens(7.0)

        output_path = f"prepped_{uuid.uuid4()}.pdb"
        with open(output_path, "w") as f:
            PDBFile.writeFile(fixer.topology, fixer.positions, f)

        return OpenMMResult(
            status="ok",
            artifacts={"pdb": output_path},
            metrics={},
            logs=[f"Structure prepped and saved to {output_path}"],
        )

    def minimize(
        self, pdb_path: str, ignore_external_bonds: bool = False
    ) -> OpenMMResult:
        """Build system, minimize energy, save minimized PDB."""
        sim = self._create_simulation(pdb_path, ignore_external_bonds)

        initial_energy = sim.context.getState(getEnergy=True).getPotentialEnergy()
        sim.minimizeEnergy()
        final_energy = sim.context.getState(getEnergy=True).getPotentialEnergy()

        output_path = f"minimized_{uuid.uuid4()}.pdb"
        with open(output_path, "w") as f:
            PDBFile.writeFile(
                sim.topology, sim.context.getState(getPositions=True).getPositions(), f
            )

        return OpenMMResult(
            status="ok",
            artifacts={"pdb": output_path},
            metrics={
                "initial_energy_kj_mol": initial_energy.value_in_unit(
                    unit.kilojoule_per_mole
                ),
                "final_energy_kj_mol": final_energy.value_in_unit(
                    unit.kilojoule_per_mole
                ),
            },
            logs=[f"Energy minimized and saved to {output_path}"],
        )

    def md_sample(
        self,
        pdb_path: str,
        nsteps: int = 250000,
        report_interval: int = 1000,
        ignore_external_bonds: bool = False,
    ) -> OpenMMResult:
        """Short MD; returns trajectory + basic analysis (RMSD/Rg/SS)."""
        sim = self._create_simulation(pdb_path, ignore_external_bonds)
        sim.minimizeEnergy()

        run_uuid = uuid.uuid4()
        traj_path = f"traj_{run_uuid}.pdb"
        state_path = f"state_{run_uuid}.csv"
        sim.reporters.append(PDBReporter(traj_path, report_interval))
        sim.reporters.append(
            StateDataReporter(
                state_path, 1000, step=True, potentialEnergy=True, temperature=True
            )
        )
        sim.step(nsteps)

        # quick analysis with MDTraj
        t = md.load(traj_path)
        rmsd_val = md.rmsd(t, t, 0).mean()
        rg_val = md.compute_rg(t).mean()

        return OpenMMResult(
            status="ok",
            artifacts={"traj": traj_path, "state": state_path},
            metrics={"rmsd_mean": float(rmsd_val), "rg_mean": float(rg_val)},
            logs=[],
        )


# Register the tool
registry.register("openmm_tool", OpenMMTool)
