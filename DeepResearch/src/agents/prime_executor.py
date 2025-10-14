from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from DeepResearch.src.datatypes.execution import ExecutionContext
from DeepResearch.src.datatypes.tools import ExecutionResult
from DeepResearch.src.utils.execution_history import ExecutionHistory, ExecutionItem
from DeepResearch.src.utils.execution_status import ExecutionStatus

from .prime_planner import WorkflowDAG, WorkflowStep

if TYPE_CHECKING:
    from DeepResearch.src.utils.tool_registry import ToolRegistry


@dataclass
class ToolExecutor:
    """PRIME Tool Executor agent for precise parameter configuration and tool invocation."""

    def __init__(self, registry: ToolRegistry, retries: int = 3):
        self.registry = registry
        self.retries = retries
        self.validation_enabled = True

    def execute_workflow(self, context: ExecutionContext) -> dict[str, Any]:
        """
        Execute a complete workflow with adaptive re-planning.

        Args:
            context: Execution context with workflow and configuration

        Returns:
            Dict containing final results and execution metadata
        """
        results = {}

        for step_name in context.workflow.execution_order:
            step_index = int(step_name.split("_")[1])
            step = context.workflow.steps[step_index]

            # Execute step with retry logic
            step_result = self._execute_step_with_retry(step, context)

            if step_result.success:
                # Store results in data bag
                for output_name, output_value in step_result.data.items():
                    context.data_bag[f"{step_name}.{output_name}"] = output_value
                    context.data_bag[output_name] = output_value

                results[step_name] = step_result.data
                context.history.add_item(
                    ExecutionItem(
                        step_name=step_name,
                        tool=step.tool,
                        status=ExecutionStatus.SUCCESS,
                        result=step_result.data,
                        timestamp=time.time(),
                    )
                )
            else:
                # Handle failure with adaptive re-planning
                if context.adaptive_replanning:
                    replan_result = self._handle_failure_with_replanning(step, context)
                    if replan_result:
                        results[step_name] = replan_result
                        continue

                # Record failure
                context.history.add_item(
                    ExecutionItem(
                        step_name=step_name,
                        tool=step.tool,
                        status=ExecutionStatus.FAILED,
                        error=step_result.error,
                        timestamp=time.time(),
                    )
                )

                # Decide whether to continue or abort
                if not self._should_continue_after_failure(step, context):
                    break

        return {
            "results": results,
            "data_bag": context.data_bag,
            "history": context.history,
            "success": len(results) == len(context.workflow.steps),
        }

    def _execute_step_with_retry(
        self, step: WorkflowStep, context: ExecutionContext
    ) -> ExecutionResult:
        """Execute a single step with retry logic."""
        for attempt in range(self.retries + 1):
            try:
                # Validate inputs before execution
                if self.validation_enabled:
                    validation_result = self._validate_step_inputs(step, context)
                    if not validation_result.success:
                        return validation_result

                # Prepare parameters with data substitution
                parameters = self._prepare_parameters(step, context)

                # Manual confirmation if enabled
                if context.manual_confirmation:
                    if not self._request_manual_confirmation(step, parameters):
                        return ExecutionResult(
                            success=False, error="Manual confirmation denied", data={}
                        )

                # Execute the tool
                result = self.registry.execute_tool(step.tool, parameters)

                # Validate outputs
                if self.validation_enabled and result.success:
                    output_validation = self._validate_step_outputs(step, result)
                    if not output_validation.success:
                        result = output_validation

                # Check success criteria
                if result.success:
                    success_check = self._check_success_criteria(step, result)
                    if not success_check.success:
                        result = success_check

                if result.success:
                    return result

                # If not successful and we have retries left, wait before retrying
                if attempt < self.retries:
                    wait_time = step.retry_config.get("backoff_factor", 2) ** attempt
                    time.sleep(wait_time)

            except Exception as e:
                if attempt == self.retries:
                    return ExecutionResult(
                        success=False,
                        error=f"Execution failed after {self.retries} retries: {e!s}",
                        data={},
                    )

        return ExecutionResult(
            success=False, error=f"Step failed after {self.retries} retries", data={}
        )

    def _validate_step_inputs(
        self, step: WorkflowStep, context: ExecutionContext
    ) -> ExecutionResult:
        """Validate inputs for a workflow step."""
        tool_spec = self.registry.get_tool_spec(step.tool)
        if not tool_spec:
            return ExecutionResult(
                success=False,
                error=f"Tool specification not found: {step.tool}",
                data={},
            )

        # Check semantic consistency
        for input_name, input_source in step.inputs.items():
            if input_name not in tool_spec.input_schema:
                return ExecutionResult(
                    success=False,
                    error=f"Invalid input '{input_name}' for tool '{step.tool}'",
                    data={},
                )

            # Check if input data exists
            if input_source not in context.data_bag:
                return ExecutionResult(
                    success=False,
                    error=f"Input data not found: {input_source}",
                    data={},
                )

            # Validate data type
            expected_type = tool_spec.input_schema[input_name]
            actual_data = context.data_bag[input_source]
            if not self._validate_data_type(actual_data, expected_type):
                return ExecutionResult(
                    success=False,
                    error=f"Type mismatch for input '{input_name}': expected {expected_type}, got {type(actual_data)}",
                    data={},
                )

        return ExecutionResult(success=True, data={})

    def _validate_step_outputs(
        self, step: WorkflowStep, result: ExecutionResult
    ) -> ExecutionResult:
        """Validate outputs from a workflow step."""
        tool_spec = self.registry.get_tool_spec(step.tool)
        if not tool_spec:
            return result  # Can't validate without spec

        # Check output schema compliance
        for output_name, expected_type in tool_spec.output_schema.items():
            if output_name not in result.data:
                return ExecutionResult(
                    success=False,
                    error=f"Missing output '{output_name}' from tool '{step.tool}'",
                    data={},
                )

            # Validate data type
            actual_data = result.data[output_name]
            if not self._validate_data_type(actual_data, expected_type):
                return ExecutionResult(
                    success=False,
                    error=f"Type mismatch for output '{output_name}': expected {expected_type}, got {type(actual_data)}",
                    data={},
                )

        return result

    def _validate_data_type(self, data: Any, expected_type: str) -> bool:
        """Validate that data matches expected type."""
        type_mapping = {
            "string": str,
            "int": int,
            "float": float,
            "list": list,
            "dict": dict,
            "pdb": str,  # PDB files are strings
            "sdf": str,  # SDF files are strings
            "fasta": str,  # FASTA files are strings
            "tensor": Any,  # Tensors can be various types
        }

        expected_python_type = type_mapping.get(expected_type, Any)
        return isinstance(data, expected_python_type)

    def _prepare_parameters(
        self, step: WorkflowStep, context: ExecutionContext
    ) -> dict[str, Any]:
        """Prepare parameters with data substitution."""
        parameters = step.parameters.copy()

        # Substitute input data
        for input_name, input_source in step.inputs.items():
            if input_source in context.data_bag:
                parameters[input_name] = context.data_bag[input_source]

        return parameters

    def _check_success_criteria(
        self, step: WorkflowStep, result: ExecutionResult
    ) -> ExecutionResult:
        """Check if step results meet success criteria."""
        for criterion, threshold in step.success_criteria.items():
            if criterion == "min_sequences" and "sequences" in result.data:
                if len(result.data["sequences"]) < threshold:
                    return ExecutionResult(
                        success=False,
                        error=f"Success criterion not met: {criterion} (got {len(result.data['sequences'])}, need {threshold})",
                        data={},
                    )

            elif criterion == "max_e_value" and "e_values" in result.data:
                if any(e_val > threshold for e_val in result.data["e_values"]):
                    return ExecutionResult(
                        success=False,
                        error=f"Success criterion not met: {criterion} (got values > {threshold})",
                        data={},
                    )

            elif criterion == "min_plddt" and "confidence" in result.data:
                if result.data["confidence"].get("plddt", 0) < threshold:
                    return ExecutionResult(
                        success=False,
                        error=f"Success criterion not met: {criterion} (got {result.data['confidence'].get('plddt', 0)}, need {threshold})",
                        data={},
                    )

        return result

    def _request_manual_confirmation(
        self, step: WorkflowStep, parameters: dict[str, Any]
    ) -> bool:
        """Request manual confirmation for step execution."""

        response = input("Proceed with execution? (y/n): ").lower().strip()
        return response in ["y", "yes"]

    def _handle_failure_with_replanning(
        self, failed_step: WorkflowStep, context: ExecutionContext
    ) -> dict[str, Any] | None:
        """Handle step failure with adaptive re-planning."""
        # Strategic re-planning: substitute with alternative tool
        alternative_tool = self._find_alternative_tool(failed_step.tool)
        if alternative_tool:
            # Create new step with alternative tool
            new_step = WorkflowStep(
                tool=alternative_tool,
                parameters=failed_step.parameters,
                inputs=failed_step.inputs,
                outputs=failed_step.outputs,
                success_criteria=failed_step.success_criteria,
                retry_config=failed_step.retry_config,
            )

            # Execute alternative step
            result = self._execute_step_with_retry(new_step, context)
            if result.success:
                return result.data

        # Tactical re-planning: adjust parameters
        adjusted_params = self._adjust_parameters_tactically(failed_step)
        if adjusted_params:
            # Create new step with adjusted parameters
            new_step = WorkflowStep(
                tool=failed_step.tool,
                parameters=adjusted_params,
                inputs=failed_step.inputs,
                outputs=failed_step.outputs,
                success_criteria=failed_step.success_criteria,
                retry_config=failed_step.retry_config,
            )

            # Execute with adjusted parameters
            result = self._execute_step_with_retry(new_step, context)
            if result.success:
                return result.data

        return None

    def _find_alternative_tool(self, tool_name: str) -> str | None:
        """Find alternative tool for strategic re-planning."""
        alternatives = {
            "blast_search": "prot_trek",
            "prot_trek": "blast_search",
            "alphafold2": "esmfold",
            "esmfold": "alphafold2",
            "autodock_vina": "diffdock",
            "diffdock": "autodock_vina",
        }

        return alternatives.get(tool_name)

    def _adjust_parameters_tactically(
        self, step: WorkflowStep
    ) -> dict[str, Any] | None:
        """Adjust parameters for tactical re-planning."""
        adjusted = step.parameters.copy()

        # Adjust E-value for BLAST searches
        if step.tool == "blast_search" and "e_value" in adjusted:
            adjusted["e_value"] = min(adjusted["e_value"] * 10, 1e-3)  # More lenient

        # Adjust exhaustiveness for docking
        elif step.tool == "autodock_vina" and "exhaustiveness" in adjusted:
            adjusted["exhaustiveness"] = min(
                adjusted["exhaustiveness"] * 2, 32
            )  # More thorough

        # Adjust confidence thresholds
        elif "min_confidence" in step.success_criteria:
            adjusted["min_confidence"] = (
                step.success_criteria["min_confidence"] * 0.8
            )  # More lenient

        return adjusted if adjusted != step.parameters else None

    def _should_continue_after_failure(
        self, step: WorkflowStep, context: ExecutionContext
    ) -> bool:
        """Determine whether to continue execution after a step failure."""
        # Don't continue if this is a critical step
        critical_tools = ["uniprot_query", "alphafold2", "rfdiffusion"]
        if step.tool in critical_tools:
            return False

        # Don't continue if too many steps have failed
        failed_steps = sum(
            1 for item in context.history.items if item.status == ExecutionStatus.FAILED
        )
        return not failed_steps > len(context.workflow.steps) // 2


def execute_workflow(
    workflow: WorkflowDAG,
    registry: ToolRegistry,
    manual_confirmation: bool = False,
    adaptive_replanning: bool = True,
) -> dict[str, Any]:
    """Convenience function to execute a workflow."""
    executor = ToolExecutor(registry)
    history = ExecutionHistory()
    context = ExecutionContext(
        workflow=workflow,
        history=history,
        manual_confirmation=manual_confirmation,
        adaptive_replanning=adaptive_replanning,
    )

    return executor.execute_workflow(context)
