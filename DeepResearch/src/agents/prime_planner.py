from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from DeepResearch.src.datatypes.execution import WorkflowDAG, WorkflowStep
from DeepResearch.src.datatypes.tool_specs import ToolCategory, ToolSpec

from .prime_parser import ScientificIntent, StructuredProblem


@dataclass
class PlanGenerator:
    """PRIME Plan Generator agent for constructing computational strategies."""

    def __post_init__(self):
        """Initialize the tool library and domain heuristics."""
        self.tool_library = self._build_tool_library()
        self.domain_heuristics = self._build_domain_heuristics()

    def plan(self, problem: StructuredProblem) -> WorkflowDAG:
        """
        Generate a computational strategy as a DAG.

        Args:
            problem: Structured research problem from QueryParser

        Returns:
            WorkflowDAG: Executable computational workflow
        """
        # Select appropriate tools based on intent and requirements
        selected_tools = self._select_tools(problem)

        # Generate workflow steps
        steps = self._generate_workflow_steps(problem, selected_tools)

        # Resolve dependencies and create DAG
        dependencies = self._resolve_dependencies(steps)
        execution_order = self._topological_sort(dependencies)

        # Add metadata
        metadata = {
            "intent": problem.intent.value,
            "domain": problem.domain,
            "complexity": problem.complexity,
            "constraints": problem.constraints,
            "success_criteria": problem.success_criteria,
        }

        return WorkflowDAG(
            steps=steps,
            dependencies=dependencies,
            execution_order=execution_order,
            metadata=metadata,
        )

    def _build_tool_library(self) -> dict[str, ToolSpec]:
        """Build the PRIME tool library with 65+ tools."""
        return {
            # Knowledge Query Tools
            "uniprot_query": ToolSpec(
                name="uniprot_query",
                category=ToolCategory.KNOWLEDGE_QUERY,
                input_schema={"query": "string", "organism": "string"},
                output_schema={"sequences": "list", "annotations": "dict"},
                success_criteria={"min_sequences": 1},
            ),
            "pubmed_search": ToolSpec(
                name="pubmed_search",
                category=ToolCategory.KNOWLEDGE_QUERY,
                input_schema={"keywords": "list", "max_results": "int"},
                output_schema={"papers": "list", "abstracts": "list"},
                success_criteria={"min_papers": 1},
            ),
            # Sequence Analysis Tools
            "blast_search": ToolSpec(
                name="blast_search",
                category=ToolCategory.SEQUENCE_ANALYSIS,
                input_schema={"sequence": "string", "database": "string"},
                output_schema={"hits": "list", "e_values": "list"},
                success_criteria={"max_e_value": 1e-5},
            ),
            "hmmer_search": ToolSpec(
                name="hmmer_search",
                category=ToolCategory.SEQUENCE_ANALYSIS,
                input_schema={"sequence": "string", "profile": "string"},
                output_schema={"domains": "list", "scores": "list"},
                success_criteria={"min_score": 20},
            ),
            "prot_trek": ToolSpec(
                name="prot_trek",
                category=ToolCategory.SEQUENCE_ANALYSIS,
                input_schema={"sequence": "string", "mode": "string"},
                output_schema={"similarity": "float", "clusters": "list"},
                success_criteria={"min_similarity": 0.7},
            ),
            # Structure Prediction Tools
            "alphafold2": ToolSpec(
                name="alphafold2",
                category=ToolCategory.STRUCTURE_PREDICTION,
                input_schema={"sequence": "string", "template_mode": "string"},
                output_schema={"structure": "pdb", "confidence": "dict"},
                success_criteria={"min_plddt": 70},
            ),
            "esmfold": ToolSpec(
                name="esmfold",
                category=ToolCategory.STRUCTURE_PREDICTION,
                input_schema={"sequence": "string"},
                output_schema={"structure": "pdb", "confidence": "dict"},
                success_criteria={"min_confidence": 0.7},
            ),
            # Molecular Docking Tools
            "autodock_vina": ToolSpec(
                name="autodock_vina",
                category=ToolCategory.MOLECULAR_DOCKING,
                input_schema={"receptor": "pdb", "ligand": "sdf", "center": "list"},
                output_schema={"poses": "list", "binding_affinity": "float"},
                success_criteria={"max_affinity": -5.0},
            ),
            "diffdock": ToolSpec(
                name="diffdock",
                category=ToolCategory.MOLECULAR_DOCKING,
                input_schema={"receptor": "pdb", "ligand": "sdf"},
                output_schema={"poses": "list", "confidence": "float"},
                success_criteria={"min_confidence": 0.5},
            ),
            # De Novo Design Tools
            "rfdiffusion": ToolSpec(
                name="rfdiffusion",
                category=ToolCategory.DE_NOVO_DESIGN,
                input_schema={"constraints": "dict", "num_designs": "int"},
                output_schema={"structures": "list", "sequences": "list"},
                success_criteria={"min_confidence": 0.8},
            ),
            "diffab": ToolSpec(
                name="diffab",
                category=ToolCategory.DE_NOVO_DESIGN,
                input_schema={"antigen": "pdb", "epitope": "list"},
                output_schema={"antibodies": "list", "binding_scores": "list"},
                success_criteria={"min_binding": -8.0},
            ),
            # Function Prediction Tools
            "evolla": ToolSpec(
                name="evolla",
                category=ToolCategory.FUNCTION_PREDICTION,
                input_schema={"sequence": "string", "structure": "pdb"},
                output_schema={"function": "string", "confidence": "float"},
                success_criteria={"min_confidence": 0.7},
            ),
            "saprot": ToolSpec(
                name="saprot",
                category=ToolCategory.FUNCTION_PREDICTION,
                input_schema={"sequence": "string", "task": "string"},
                output_schema={"predictions": "dict", "embeddings": "tensor"},
                success_criteria={"min_accuracy": 0.8},
            ),
        }

    def _build_domain_heuristics(self) -> dict[ScientificIntent, list[str]]:
        """Build domain-specific heuristics for tool selection."""
        return {
            ScientificIntent.PROTEIN_DESIGN: [
                "uniprot_query",
                "alphafold2",
                "rfdiffusion",
                "evolla",
            ],
            ScientificIntent.BINDING_ANALYSIS: [
                "uniprot_query",
                "alphafold2",
                "autodock_vina",
                "diffdock",
            ],
            ScientificIntent.STRUCTURE_PREDICTION: [
                "uniprot_query",
                "alphafold2",
                "esmfold",
            ],
            ScientificIntent.FUNCTION_PREDICTION: [
                "uniprot_query",
                "hmmer_search",
                "evolla",
                "saprot",
            ],
            ScientificIntent.SEQUENCE_ANALYSIS: [
                "uniprot_query",
                "blast_search",
                "hmmer_search",
                "prot_trek",
            ],
            ScientificIntent.DE_NOVO_DESIGN: [
                "uniprot_query",
                "alphafold2",
                "rfdiffusion",
                "diffab",
            ],
            ScientificIntent.CLASSIFICATION: ["uniprot_query", "saprot", "evolla"],
            ScientificIntent.REGRESSION: ["uniprot_query", "saprot", "evolla"],
            ScientificIntent.INTERACTION_PREDICTION: [
                "uniprot_query",
                "alphafold2",
                "autodock_vina",
                "diffdock",
            ],
        }

    def _select_tools(self, problem: StructuredProblem) -> list[str]:
        """Select appropriate tools based on problem characteristics."""
        # Get base tools for the intent
        base_tools = self.domain_heuristics.get(problem.intent, [])

        # Add tools based on input requirements
        additional_tools = []
        if "sequence" in problem.input_data:
            additional_tools.extend(["blast_search", "hmmer_search"])
        if "structure" in problem.input_data:
            additional_tools.extend(["autodock_vina", "diffdock"])

        # Add tools based on output requirements
        if "classification" in problem.output_requirements:
            additional_tools.append("saprot")
        if "binding" in problem.output_requirements:
            additional_tools.extend(["autodock_vina", "diffdock"])

        # Combine and deduplicate
        selected = list(set(base_tools + additional_tools))

        # Limit based on complexity
        if problem.complexity == "simple":
            selected = selected[:3]
        elif problem.complexity == "moderate":
            selected = selected[:5]
        # Complex tasks can use all selected tools

        return selected

    def _generate_workflow_steps(
        self, problem: StructuredProblem, tools: list[str]
    ) -> list[WorkflowStep]:
        """Generate workflow steps from selected tools."""
        steps = []

        for i, tool_name in enumerate(tools):
            tool_spec = self.tool_library[tool_name]

            # Generate parameters based on problem requirements
            parameters = self._generate_parameters(tool_spec, problem)

            # Define inputs and outputs
            inputs = self._define_inputs(tool_spec, problem, i)
            outputs = self._define_outputs(tool_spec, i)

            # Set success criteria
            success_criteria = tool_spec.success_criteria.copy()

            # Add retry configuration
            retry_config = {
                "max_retries": 3,
                "backoff_factor": 2,
                "retry_on_failure": True,
            }

            step = WorkflowStep(
                tool=tool_name,
                parameters=parameters,
                inputs=inputs,
                outputs=outputs,
                success_criteria=success_criteria,
                retry_config=retry_config,
            )

            steps.append(step)

        return steps

    def _generate_parameters(
        self, tool_spec: ToolSpec, problem: StructuredProblem
    ) -> dict[str, Any]:
        """Generate parameters for a tool based on problem requirements."""
        params = tool_spec.parameters.copy()

        # Set default parameters based on tool type
        if tool_spec.category == ToolCategory.KNOWLEDGE_QUERY:
            params.update({"max_results": 100, "organism": "all"})
        elif tool_spec.category == ToolCategory.SEQUENCE_ANALYSIS:
            params.update({"e_value": 1e-5, "max_target_seqs": 100})
        elif tool_spec.category == ToolCategory.STRUCTURE_PREDICTION:
            params.update({"template_mode": "pdb70", "use_amber": True})
        elif tool_spec.category == ToolCategory.MOLECULAR_DOCKING:
            params.update({"exhaustiveness": 8, "num_modes": 9})

        return params

    def _define_inputs(
        self, tool_spec: ToolSpec, problem: StructuredProblem, step_index: int
    ) -> dict[str, str]:
        """Define input mappings for a workflow step."""
        inputs = {}

        # Map inputs based on tool requirements and available data
        for input_name in tool_spec.input_schema:
            if input_name == "sequence" and "sequence" in problem.input_data:
                inputs[input_name] = "user_input.sequence"
            elif input_name == "structure" and "structure" in problem.input_data:
                inputs[input_name] = "user_input.structure"
            elif step_index > 0:
                # Use output from previous step
                inputs[input_name] = f"step_{step_index - 1}.output"
            else:
                # Use default or user input
                inputs[input_name] = f"user_input.{input_name}"

        return inputs

    def _define_outputs(self, tool_spec: ToolSpec, step_index: int) -> dict[str, str]:
        """Define output mappings for a workflow step."""
        outputs = {}

        for output_name in tool_spec.output_schema:
            outputs[output_name] = f"step_{step_index}.{output_name}"

        return outputs

    def _resolve_dependencies(self, steps: list[WorkflowStep]) -> dict[str, list[str]]:
        """Resolve dependencies between workflow steps."""
        dependencies = {}

        for i, step in enumerate(steps):
            step_name = f"step_{i}"
            step_deps = []

            # Check if this step depends on outputs from previous steps
            for input_source in step.inputs.values():
                if input_source.startswith("step_"):
                    dep_step = input_source.split(".")[0]
                    if dep_step not in step_deps:
                        step_deps.append(dep_step)

            dependencies[step_name] = step_deps

        return dependencies

    def _topological_sort(self, dependencies: dict[str, list[str]]) -> list[str]:
        """Perform topological sort to determine execution order."""
        # Simple topological sort implementation
        in_degree = dict.fromkeys(dependencies, 0)

        # Calculate in-degrees
        for step, deps in dependencies.items():
            for dep in deps:
                if dep in in_degree:
                    in_degree[step] += 1

        # Find steps with no dependencies
        queue = [step for step, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            current = queue.pop(0)
            result.append(current)

            # Update in-degrees for dependent steps
            for step, deps in dependencies.items():
                if current in deps:
                    in_degree[step] -= 1
                    if in_degree[step] == 0:
                        queue.append(step)

        return result


def generate_plan(problem: StructuredProblem) -> WorkflowDAG:
    """Convenience function to generate a workflow plan."""
    planner = PlanGenerator()
    return planner.plan(problem)
