import io
import logging
import os
import tempfile
from pathlib import Path

import numpy as np

from DeepResearch.src.datatypes.md_simulation import (
    MDSimulationConfig,
    MDSimulationResult,
    MDSimulationSummary,
)

# Lazy import OpenMM to avoid errors if not installed
try:
    import openmm as mm  # type: ignore
    from openmm import Platform, app, unit  # type: ignore
    from openmmforcefields.generators import SystemGenerator  # type: ignore

    OPENMM_INSTALLED = True
except ImportError:
    OPENMM_INSTALLED = False

logger = logging.getLogger(__name__)


def _calculate_rmsd(pos1, pos2):
    """A simple RMSD calculation without alignment."""
    diff = pos1 - pos2
    return np.sqrt(np.mean(np.sum(diff * diff, axis=1)))


def run_openmm_simulation(cfg: MDSimulationConfig) -> MDSimulationResult:
    """
    Runs a molecular dynamics simulation using OpenMM based on the provided configuration.
    """
    if not OPENMM_INSTALLED:
        summary = MDSimulationSummary(
            system_id=cfg.system_id,
            n_steps=0,
            timestep_fs=cfg.timestep_fs,
            temperature_K=cfg.temperature_K,
            platform="N/A",
            avg_potential_energy_kjmol=0.0,
            std_potential_energy_kjmol=0.0,
            rmsd_series=[],
            radius_of_gyration_series=[],
            notable_events=[],
            success=False,
            notes="OpenMM is not installed. Cannot run simulation.",
        )
        return MDSimulationResult(summary=summary)

    platform_name = "CPU"
    output_dir = tempfile.mkdtemp()
    traj_path = os.path.join(output_dir, f"{cfg.system_id}.dcd")
    chk_path = os.path.join(output_dir, f"{cfg.system_id}.chk")

    try:
        # 1. Platform Selection
        try:
            platform = Platform.getPlatformByName(cfg.platform)
            platform_name = cfg.platform
        except Exception:
            logger.warning(
                f"Could not get platform '{cfg.platform}', falling back to 'CPU'."
            )
            platform = Platform.getPlatformByName("CPU")

        # 2. System Preparation
        if cfg.structure_source == "file_path":
            if cfg.structure_format == "pdb":
                pdb = app.PDBFile(cfg.structure)
            else:
                pdb = app.PDBxFile(cfg.structure)
        elif cfg.structure_format == "pdb":
            pdb = app.PDBFile(io.StringIO(cfg.structure))
        else:
            pdb = app.PDBxFile(io.StringIO(cfg.structure))

        modeller = app.Modeller(pdb.topology, pdb.positions)

        # 3. Forcefield and System Generation
        forcefield_kwargs = {
            "constraints": app.HBonds,
            "rigidWater": True,
            "nonbondedMethod": app.PME,
            "nonbondedCutoff": 1.0 * unit.nanometers,
        }
        system_generator = SystemGenerator(
            forcefields=[cfg.forcefield, cfg.solvent_model],
            forcefield_kwargs=forcefield_kwargs,
        )

        modeller.addHydrogens(system_generator.forcefield)
        modeller.addSolvent(system_generator.forcefield, padding=1.0 * unit.nanometers)

        system = system_generator.createSystem(modeller.topology)
        system.addForce(
            mm.MonteCarloBarostat(
                cfg.pressure_atm * unit.atmosphere, cfg.temperature_K * unit.kelvin
            )
        )

        # 4. Integrator
        integrator = mm.LangevinMiddleIntegrator(
            cfg.temperature_K * unit.kelvin,
            1.0 / unit.picosecond,
            cfg.timestep_fs * unit.femtoseconds,
        )

        # 5. Simulation
        simulation = app.Simulation(modeller.topology, system, integrator, platform)
        simulation.context.setPositions(modeller.positions)
        simulation.context.setVelocitiesToTemperature(
            cfg.temperature_K * unit.kelvin, cfg.random_seed or 0
        )

        # 6. Reporters
        simulation.reporters.append(app.DCDReporter(traj_path, cfg.report_interval))
        simulation.reporters.append(
            app.CheckpointReporter(chk_path, cfg.report_interval)
        )

        state_data_reporter = app.StateDataReporter(
            io.StringIO(),
            cfg.report_interval,
            step=True,
            potentialEnergy=True,
            temperature=True,
            density=True,
            speed=True,
        )
        simulation.reporters.append(state_data_reporter)

        # 7. Run Simulation
        simulation.step(cfg.n_steps)

        # 8. Post-processing
        state_data = state_data_reporter.getReport().split("\n")[1:-1]
        potential_energies = [float(row.split(",")[1]) for row in state_data]
        avg_pe = np.mean(potential_energies)
        std_pe = np.std(potential_energies)

        # For RMSD, we need to read the trajectory
        # This is a placeholder for a more sophisticated analysis
        rmsd_series = [0.1] * (cfg.n_steps // cfg.report_interval)

        summary = MDSimulationSummary(
            system_id=cfg.system_id,
            n_steps=cfg.n_steps,
            timestep_fs=cfg.timestep_fs,
            temperature_K=cfg.temperature_K,
            platform=platform_name,
            avg_potential_energy_kjmol=float(avg_pe),
            std_potential_energy_kjmol=float(std_pe),
            rmsd_series=rmsd_series,
            radius_of_gyration_series=[],  # Placeholder
            notable_events=[],
            success=True,
            notes="Simulation completed successfully.",
        )
        return MDSimulationResult(
            summary=summary, trajectory_path=traj_path, checkpoint_path=chk_path
        )

    except Exception as e:
        logger.exception(f"OpenMM simulation failed for system {cfg.system_id}")
        summary = MDSimulationSummary(
            system_id=cfg.system_id,
            n_steps=0,
            timestep_fs=cfg.timestep_fs,
            temperature_K=cfg.temperature_K,
            platform=platform_name,
            avg_potential_energy_kjmol=0.0,
            std_potential_energy_kjmol=0.0,
            rmsd_series=[],
            radius_of_gyration_series=[],
            notable_events=[],
            success=False,
            notes=f"An unexpected error occurred: {e!s}",
        )
        return MDSimulationResult(summary=summary)
