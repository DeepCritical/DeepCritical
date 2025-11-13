from dataclasses import dataclass
from typing import Any, Dict

from DeepResearch.src.datatypes.md_simulation import (
    MDSimulationConfig,
    MDSimulationResult,
)
from DeepResearch.src.datatypes.tool_specs import ToolCategory, ToolSpec
from DeepResearch.src.datatypes.tools import ExecutionResult, ToolRunner
from DeepResearch.src.simulations.openmm_backend import run_openmm_simulation
from DeepResearch.src.utils.tool_registry import registry

OPENMM_MD_SPEC = ToolSpec(
    name="openmm_md",
    category=ToolCategory.MOLECULAR_SIMULATION,
    input_schema={
        "structure": "pdb",
        "ligand": "sdf",
        "simulation_config": "dict",
    },
    output_schema={
        "summary": "dict",
        "trajectory_path": "string",
        "checkpoint_path": "string",
    },
    parameters={},
    success_criteria={"min_steps": 1000},
)


class OpenMMMDRunner(ToolRunner):
    def run(self, parameters: dict[str, Any]) -> ExecutionResult:
        # Validate input (the ToolRunner base already checks basic types)
        # The base __init__ sets self.spec, which is needed for validate_inputs
        validation = self.validate_inputs(parameters)
        if not validation.success:
            return validation

        try:
            # Build config from default + overrides
            cfg_dict = (
                parameters.get("simulation_config", {})
                | {
                    "system_id": parameters.get("system_id", "unknown_system"),
                    "structure": parameters["structure"],
                    "structure_format": "pdb",
                    "structure_source": "inline_string",  # or "file_path", depending on usage
                }
            )

            cfg = MDSimulationConfig(**cfg_dict)
            result: MDSimulationResult = run_openmm_simulation(cfg)

            if not result.summary.success:
                return ExecutionResult(
                    success=False,
                    data={},
                    error=result.summary.notes or "OpenMM MD failed",
                )

            return ExecutionResult(
                success=True,
                data={
                    "summary": result.summary.model_dump(),
                    "trajectory_path": result.trajectory_path,
                    "checkpoint_path": result.checkpoint_path,
                },
                metadata={"tool": "openmm_md"},
            )

        except Exception as exc:
            return ExecutionResult(
                success=False,
                data={},
                error=f"OpenMM MD execution error: {exc!s}",
            )


# Register tool in global registry
registry.register_tool(OPENMM_MD_SPEC, OpenMMMDRunner)
