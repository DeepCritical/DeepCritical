from typing import Dict, List, Literal, Optional

from pydantic import BaseModel


class MDSimulationConfig(BaseModel):
    system_id: str  # logical name, e.g. "APP_ectodomain_mutant_X"
    structure_format: Literal["pdb", "mmcif"]
    structure_source: Literal["file_path", "inline_string"]
    structure: str  # path or PDB/mmCIF text
    ligand_sdf: str | None = None  # path or SDF text
    forcefield: str = "amber/protein.ff14SB.xml"
    solvent_model: str = "amber/tip3p_standard.xml"
    temperature_K: float = 300.0
    pressure_atm: float = 1.0
    timestep_fs: float = 2.0
    n_steps: int = 50_000  # default short run
    platform: Literal["CUDA", "OpenCL", "CPU"] = "CPU"
    save_trajectory: bool = True
    trajectory_format: Literal["dcd", "pdb"] = "dcd"
    report_interval: int = 1_000
    random_seed: int | None = None


class MDSimulationSummary(BaseModel):
    system_id: str
    n_steps: int
    timestep_fs: float
    temperature_K: float
    platform: str
    avg_potential_energy_kjmol: float
    std_potential_energy_kjmol: float
    rmsd_series: list[float]  # per report
    radius_of_gyration_series: list[float]
    notable_events: list[str]  # “loop 45-60 unfolds”, “ligand leaves pocket” etc.
    success: bool
    notes: str = ""


class MDSimulationResult(BaseModel):
    summary: MDSimulationSummary
    trajectory_path: str | None = None
    checkpoint_path: str | None = None
    metadata: dict[str, str] = {}
