"""Allow-listed, schema-checked local pipeline orchestration.

Pipeline configuration is deliberately data, not executable code.  A
``PipelineSpec`` can select only components already present in a
``ComponentRegistry``; it cannot import a Python module or name a callable.
The compiler validates the complete graph before an executor sees any input.
"""

from __future__ import annotations

import time
import uuid
from collections import defaultdict
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Annotated, Any, Literal, Protocol, TypeAlias

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from .models import (
    ComponentDescriptor,
    DiagnosticSeverity,
    configuration_sha256,
    utc_now,
)


class PipelineDefinitionError(ValueError):
    """A declarative pipeline cannot be compiled safely."""


class PipelineExecutionError(RuntimeError):
    """A compiled pipeline could not satisfy its runtime contract."""


class ComponentRegistryError(ValueError):
    """A component registration is invalid or conflicts with an existing one."""


class _FrozenSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)


def _non_empty(value: str, *, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    return normalized


class PipelineContract(_FrozenSpec):
    """Serializable identity of a value crossing a pipeline port."""

    schema_uri: str
    schema_version: str

    @field_validator("schema_uri", "schema_version")
    @classmethod
    def _strip_contract_text(cls, value: str, info: Any) -> str:
        return _non_empty(value, field_name=info.field_name)


class PipelineInputRef(_FrozenSpec):
    """Reference to one invocation input."""

    source: Literal["pipeline"] = "pipeline"
    input_name: str

    @field_validator("input_name")
    @classmethod
    def _strip_input_name(cls, value: str) -> str:
        return _non_empty(value, field_name="input_name")


class StageOutputRef(_FrozenSpec):
    """Reference to one named output of an earlier stage."""

    source: Literal["stage"] = "stage"
    stage_id: str
    output_name: str

    @field_validator("stage_id", "output_name")
    @classmethod
    def _strip_output_ref(cls, value: str, info: Any) -> str:
        return _non_empty(value, field_name=info.field_name)


InputBinding: TypeAlias = Annotated[
    PipelineInputRef | StageOutputRef,
    Field(discriminator="source"),
]


class StageExecutionStatus(StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    FAILED = "failed"
    QUARANTINED = "quarantined"
    SKIPPED = "skipped"


class AlwaysCondition(_FrozenSpec):
    type: Literal["always"] = "always"


class OutputPresentCondition(_FrozenSpec):
    type: Literal["output_present"] = "output_present"
    stage_id: str
    output_name: str

    @field_validator("stage_id", "output_name")
    @classmethod
    def _strip_output_ref(cls, value: str, info: Any) -> str:
        return _non_empty(value, field_name=info.field_name)


class OutputAbsentCondition(_FrozenSpec):
    type: Literal["output_absent"] = "output_absent"
    stage_id: str
    output_name: str

    @field_validator("stage_id", "output_name")
    @classmethod
    def _strip_output_ref(cls, value: str, info: Any) -> str:
        return _non_empty(value, field_name=info.field_name)


class DiagnosticPresentCondition(_FrozenSpec):
    type: Literal["diagnostic_present"] = "diagnostic_present"
    stage_id: str
    code: str

    @field_validator("stage_id", "code")
    @classmethod
    def _strip_diagnostic_ref(cls, value: str, info: Any) -> str:
        return _non_empty(value, field_name=info.field_name)


class StageStatusCondition(_FrozenSpec):
    type: Literal["stage_status"] = "stage_status"
    stage_id: str
    statuses: tuple[StageExecutionStatus, ...] = Field(min_length=1)

    @field_validator("stage_id")
    @classmethod
    def _strip_stage_id(cls, value: str) -> str:
        return _non_empty(value, field_name="stage_id")

    @field_validator("statuses")
    @classmethod
    def _unique_statuses(
        cls, value: tuple[StageExecutionStatus, ...]
    ) -> tuple[StageExecutionStatus, ...]:
        if len(set(value)) != len(value):
            raise ValueError("condition statuses must be unique")
        return value


ConditionPredicate: TypeAlias = Annotated[
    AlwaysCondition
    | OutputPresentCondition
    | OutputAbsentCondition
    | DiagnosticPresentCondition
    | StageStatusCondition,
    Field(discriminator="type"),
]


class AllCondition(_FrozenSpec):
    type: Literal["all"] = "all"
    conditions: tuple[ConditionPredicate, ...] = Field(min_length=1)


class AnyCondition(_FrozenSpec):
    type: Literal["any"] = "any"
    conditions: tuple[ConditionPredicate, ...] = Field(min_length=1)


StageCondition: TypeAlias = Annotated[
    AlwaysCondition
    | OutputPresentCondition
    | OutputAbsentCondition
    | DiagnosticPresentCondition
    | StageStatusCondition
    | AllCondition
    | AnyCondition,
    Field(discriminator="type"),
]


class ComponentInstanceSpec(_FrozenSpec):
    """One configured use of an allow-listed component."""

    instance_id: str
    component_id: str
    configuration: dict[str, Any] = Field(default_factory=dict)

    @field_validator("instance_id", "component_id")
    @classmethod
    def _strip_component_text(cls, value: str, info: Any) -> str:
        return _non_empty(value, field_name=info.field_name)

    @field_validator("configuration")
    @classmethod
    def _require_canonical_json(cls, value: dict[str, Any]) -> dict[str, Any]:
        try:
            configuration_sha256(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("component configuration must be canonical JSON") from exc
        return value


class StageSpec(_FrozenSpec):
    """One node in a declarative pipeline graph."""

    stage_id: str
    component_instance_id: str = Field(alias="component")
    depends_on: tuple[str, ...] = ()
    inputs: dict[str, InputBinding] = Field(default_factory=dict)
    outputs: tuple[str, ...] = ()
    condition: StageCondition = Field(default_factory=AlwaysCondition)

    @field_validator("stage_id", "component_instance_id")
    @classmethod
    def _strip_stage_text(cls, value: str, info: Any) -> str:
        return _non_empty(value, field_name=info.field_name)

    @field_validator("depends_on", "outputs")
    @classmethod
    def _unique_names(cls, value: tuple[str, ...], info: Any) -> tuple[str, ...]:
        normalized = tuple(
            _non_empty(item, field_name=info.field_name) for item in value
        )
        if len(set(normalized)) != len(normalized):
            raise ValueError(f"{info.field_name} must not contain duplicates")
        return normalized

    @field_validator("inputs")
    @classmethod
    def _valid_input_port_names(
        cls, value: dict[str, InputBinding]
    ) -> dict[str, InputBinding]:
        normalized: dict[str, InputBinding] = {}
        for name, binding in value.items():
            normalized[_non_empty(name, field_name="input port name")] = binding
        if len(normalized) != len(value):
            raise ValueError("input port names must be unique after normalization")
        return normalized


class PipelineSpec(_FrozenSpec):
    """Versioned, non-executable pipeline configuration."""

    schema_version: Literal["deepcritical-pipeline-spec-v1"] = (
        "deepcritical-pipeline-spec-v1"
    )
    pipeline_id: str
    pipeline_version: str
    inputs: dict[str, PipelineContract]
    components: tuple[ComponentInstanceSpec, ...]
    stages: tuple[StageSpec, ...]

    @field_validator("pipeline_id", "pipeline_version")
    @classmethod
    def _strip_pipeline_text(cls, value: str, info: Any) -> str:
        return _non_empty(value, field_name=info.field_name)

    @field_validator("inputs")
    @classmethod
    def _valid_pipeline_input_names(
        cls, value: dict[str, PipelineContract]
    ) -> dict[str, PipelineContract]:
        if not value:
            raise ValueError("pipeline inputs must not be empty")
        normalized: dict[str, PipelineContract] = {}
        for name, contract in value.items():
            normalized[_non_empty(name, field_name="pipeline input name")] = contract
        if len(normalized) != len(value):
            raise ValueError("pipeline input names must be unique after normalization")
        return normalized

    @model_validator(mode="after")
    def _unique_graph_identifiers(self) -> PipelineSpec:
        component_ids = [component.instance_id for component in self.components]
        if len(set(component_ids)) != len(component_ids):
            raise ValueError("component instance IDs must be unique")
        stage_ids = [stage.stage_id for stage in self.stages]
        if len(set(stage_ids)) != len(stage_ids):
            raise ValueError("stage IDs must be unique")
        if not self.components:
            raise ValueError("pipeline components must not be empty")
        if not self.stages:
            raise ValueError("pipeline stages must not be empty")
        return self


@dataclass(frozen=True, slots=True)
class PortContract:
    """Registry-owned runtime contract for one component port."""

    schema_uri: str
    schema_version: str
    value_types: type[Any] | tuple[type[Any], ...]
    required: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "schema_uri",
            _non_empty(self.schema_uri, field_name="schema_uri"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _non_empty(self.schema_version, field_name="schema_version"),
        )
        value_types = (
            self.value_types
            if isinstance(self.value_types, tuple)
            else (self.value_types,)
        )
        if not value_types or any(not isinstance(item, type) for item in value_types):
            raise ValueError("value_types must contain runtime types")
        object.__setattr__(self, "value_types", value_types)

    @property
    def serializable(self) -> PipelineContract:
        return PipelineContract(
            schema_uri=self.schema_uri,
            schema_version=self.schema_version,
        )

    @property
    def runtime_types(self) -> tuple[type[Any], ...]:
        if isinstance(self.value_types, tuple):
            return self.value_types
        return (self.value_types,)

    def accepts(self, value: object) -> bool:
        return isinstance(value, self.runtime_types)


class StageDiagnostic(_FrozenSpec):
    """Small execution-layer diagnostic used by typed conditions."""

    code: str
    severity: DiagnosticSeverity
    message: str
    details: dict[str, Any] = Field(default_factory=dict)

    @field_validator("code", "message")
    @classmethod
    def _strip_diagnostic_text(cls, value: str, info: Any) -> str:
        return _non_empty(value, field_name=info.field_name)


@dataclass(frozen=True, slots=True)
class StageResult:
    """Result returned by one registered component invocation."""

    status: StageExecutionStatus
    outputs: Mapping[str, object] = field(default_factory=dict)
    diagnostics: tuple[StageDiagnostic, ...] = ()

    def __post_init__(self) -> None:
        outputs = dict(self.outputs)
        if any(not name.strip() for name in outputs):
            raise ValueError("stage output names must not be empty")
        if any(value is None for value in outputs.values()):
            raise ValueError("optional outputs must be omitted rather than set to None")
        object.__setattr__(self, "outputs", MappingProxyType(outputs))
        object.__setattr__(self, "diagnostics", tuple(self.diagnostics))


@dataclass(frozen=True, slots=True)
class StageContext:
    """Read-only local context passed to a component plugin."""

    pipeline_id: str
    pipeline_version: str
    pipeline_run_id: str
    stage_id: str
    inputs: Mapping[str, object]
    prior_results: Mapping[str, StageResult]

    def __post_init__(self) -> None:
        object.__setattr__(self, "inputs", MappingProxyType(dict(self.inputs)))
        object.__setattr__(
            self,
            "prior_results",
            MappingProxyType(dict(self.prior_results)),
        )

    def require_input(self, name: str, value_type: type[Any]) -> Any:
        try:
            value = self.inputs[name]
        except KeyError as exc:
            raise PipelineExecutionError(
                f"stage {self.stage_id!r} has no runtime input {name!r}"
            ) from exc
        if not isinstance(value, value_type):
            raise PipelineExecutionError(
                f"stage {self.stage_id!r} input {name!r} is not {value_type.__name__}"
            )
        return value


class StagePlugin(Protocol):
    """Local component implementation selected only through a registry."""

    async def execute(
        self,
        context: StageContext,
        configuration: BaseModel,
    ) -> StageResult: ...


StageHandler: TypeAlias = Callable[
    [StageContext, BaseModel],
    Awaitable[StageResult],
]


@dataclass(frozen=True, slots=True)
class FunctionStagePlugin:
    """Adapter for a bound async stage handler."""

    handler: StageHandler

    async def execute(
        self,
        context: StageContext,
        configuration: BaseModel,
    ) -> StageResult:
        return await self.handler(context, configuration)


@dataclass(frozen=True, slots=True)
class ComponentRegistration:
    """One allow-listed implementation and its complete port contract."""

    descriptor: ComponentDescriptor
    configuration_model: type[BaseModel]
    input_ports: Mapping[str, PortContract]
    output_ports: Mapping[str, PortContract]
    plugin: StagePlugin

    def __post_init__(self) -> None:
        if not issubclass(self.configuration_model, BaseModel):
            raise ValueError("configuration_model must be a Pydantic model")
        if not callable(getattr(self.plugin, "execute", None)):
            raise ValueError("plugin must provide an async execute method")
        input_ports = _validated_ports(self.input_ports, kind="input")
        output_ports = _validated_ports(self.output_ports, kind="output")
        object.__setattr__(self, "input_ports", MappingProxyType(input_ports))
        object.__setattr__(self, "output_ports", MappingProxyType(output_ports))


def _validated_ports(
    ports: Mapping[str, PortContract],
    *,
    kind: str,
) -> dict[str, PortContract]:
    validated: dict[str, PortContract] = {}
    for name, contract in ports.items():
        normalized = _non_empty(name, field_name=f"{kind} port name")
        if normalized in validated:
            raise ValueError(f"duplicate {kind} port {normalized!r}")
        validated[normalized] = contract
    return validated


class ComponentRegistry:
    """Mutable-at-construction allow-list of local component implementations."""

    def __init__(self) -> None:
        self._registrations: dict[str, ComponentRegistration] = {}

    def register(self, registration: ComponentRegistration) -> None:
        component_id = registration.descriptor.component_id
        if component_id in self._registrations:
            raise ComponentRegistryError(
                f"component {component_id!r} is already registered"
            )
        self._registrations[component_id] = registration

    def require(self, component_id: str) -> ComponentRegistration:
        try:
            return self._registrations[component_id]
        except KeyError as exc:
            raise PipelineDefinitionError(
                f"component {component_id!r} is not registered"
            ) from exc

    @property
    def component_ids(self) -> tuple[str, ...]:
        return tuple(self._registrations)

    @property
    def descriptors(self) -> tuple[ComponentDescriptor, ...]:
        return tuple(
            registration.descriptor for registration in self._registrations.values()
        )

    def contract_snapshot(self) -> dict[str, Any]:
        """Return a canonical description suitable for provenance hashing."""

        return {
            "schema": "deepcritical-component-registry-snapshot-v1",
            "components": [
                {
                    "descriptor": registration.descriptor.model_dump(mode="json"),
                    "configuration_schema": (
                        registration.configuration_model.model_json_schema(
                            mode="validation"
                        )
                    ),
                    "inputs": _port_snapshot(registration.input_ports),
                    "outputs": _port_snapshot(registration.output_ports),
                }
                for component_id in sorted(self._registrations)
                for registration in (self._registrations[component_id],)
            ],
        }


def _port_snapshot(
    ports: Mapping[str, PortContract],
) -> dict[str, dict[str, Any]]:
    return {
        name: {
            "schema_uri": contract.schema_uri,
            "schema_version": contract.schema_version,
            "required": contract.required,
            "runtime_types": [
                f"{value_type.__module__}.{value_type.__qualname__}"
                for value_type in contract.runtime_types
            ],
        }
        for name, contract in sorted(ports.items())
    }


@dataclass(frozen=True, slots=True)
class CompiledStage:
    spec: StageSpec
    registration: ComponentRegistration
    configuration: BaseModel
    configuration_sha256: str


@dataclass(frozen=True, slots=True)
class CompiledPipeline:
    spec: PipelineSpec
    stages: tuple[CompiledStage, ...]
    pipeline_input_types: Mapping[str, tuple[type[Any], ...]]
    specification_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "pipeline_input_types",
            MappingProxyType(dict(self.pipeline_input_types)),
        )


class PipelineCompiler:
    """Validate component configuration and the entire DAG before execution."""

    def __init__(self, registry: ComponentRegistry) -> None:
        self.registry = registry

    def compile(self, spec: PipelineSpec) -> CompiledPipeline:
        instances = {instance.instance_id: instance for instance in spec.components}
        stages = {stage.stage_id: stage for stage in spec.stages}
        registrations: dict[str, ComponentRegistration] = {}
        configurations: dict[str, BaseModel] = {}
        configuration_hashes: dict[str, str] = {}

        for instance in spec.components:
            registration = self.registry.require(instance.component_id)
            try:
                configuration = registration.configuration_model.model_validate(
                    instance.configuration
                )
            except ValidationError as exc:
                raise PipelineDefinitionError(
                    f"component instance {instance.instance_id!r} has invalid "
                    f"configuration: {exc}"
                ) from exc
            registrations[instance.instance_id] = registration
            configurations[instance.instance_id] = configuration
            configuration_hashes[instance.instance_id] = configuration_sha256(
                configuration.model_dump(mode="python")
            )

        input_runtime_types: dict[str, tuple[type[Any], ...]] = {}
        consumed_pipeline_inputs: set[str] = set()
        for stage in spec.stages:
            instance = instances.get(stage.component_instance_id)
            if instance is None:
                raise PipelineDefinitionError(
                    f"stage {stage.stage_id!r} references unknown component "
                    f"instance {stage.component_instance_id!r}"
                )
            registration = registrations[instance.instance_id]
            self._validate_stage_shape(stage, registration)
            self._validate_dependencies(stage, stages)
            self._validate_condition(stage, stages, registrations, instances)
            for port_name, binding in stage.inputs.items():
                target = registration.input_ports[port_name]
                if isinstance(binding, PipelineInputRef):
                    source = spec.inputs.get(binding.input_name)
                    if source is None:
                        raise PipelineDefinitionError(
                            f"stage {stage.stage_id!r} references unknown pipeline "
                            f"input {binding.input_name!r}"
                        )
                    _require_schema_compatibility(
                        source,
                        target.serializable,
                        source_label=f"pipeline input {binding.input_name!r}",
                        target_label=f"{stage.stage_id}.{port_name}",
                    )
                    consumed_pipeline_inputs.add(binding.input_name)
                    previous_types = input_runtime_types.get(binding.input_name)
                    if (
                        previous_types is not None
                        and previous_types != target.runtime_types
                    ):
                        raise PipelineDefinitionError(
                            f"pipeline input {binding.input_name!r} has incompatible "
                            "runtime consumers"
                        )
                    input_runtime_types[binding.input_name] = target.runtime_types
                    continue

                source_stage = stages.get(binding.stage_id)
                if source_stage is None:
                    raise PipelineDefinitionError(
                        f"stage {stage.stage_id!r} input {port_name!r} references "
                        f"unknown stage {binding.stage_id!r}"
                    )
                if binding.stage_id not in stage.depends_on:
                    raise PipelineDefinitionError(
                        f"stage {stage.stage_id!r} must declare input source "
                        f"{binding.stage_id!r} in depends_on"
                    )
                source_instance = instances[source_stage.component_instance_id]
                source_registration = registrations[source_instance.instance_id]
                source_port = source_registration.output_ports.get(binding.output_name)
                if (
                    source_port is None
                    or binding.output_name not in source_stage.outputs
                ):
                    raise PipelineDefinitionError(
                        f"stage {stage.stage_id!r} references undeclared output "
                        f"{binding.stage_id}.{binding.output_name}"
                    )
                _require_port_compatibility(
                    source_port,
                    target,
                    source_label=f"{binding.stage_id}.{binding.output_name}",
                    target_label=f"{stage.stage_id}.{port_name}",
                )
                if (
                    target.required
                    and _output_may_be_absent(source_stage, source_port)
                    and not _condition_guarantees_output(
                        stage.condition,
                        binding.stage_id,
                        binding.output_name,
                    )
                ):
                    raise PipelineDefinitionError(
                        f"required input {stage.stage_id}.{port_name} consumes "
                        f"potentially absent output "
                        f"{binding.stage_id}.{binding.output_name} "
                        "without an output_present guard"
                    )

        ordered_ids = _topological_order(spec.stages)
        unused_inputs = set(spec.inputs) - consumed_pipeline_inputs
        if unused_inputs:
            names = ", ".join(sorted(unused_inputs))
            raise PipelineDefinitionError(f"unused pipeline inputs: {names}")

        compiled = tuple(
            CompiledStage(
                spec=stages[stage_id],
                registration=registrations[
                    instances[stages[stage_id].component_instance_id].instance_id
                ],
                configuration=configurations[
                    instances[stages[stage_id].component_instance_id].instance_id
                ],
                configuration_sha256=configuration_hashes[
                    instances[stages[stage_id].component_instance_id].instance_id
                ],
            )
            for stage_id in ordered_ids
        )
        return CompiledPipeline(
            spec=spec,
            stages=compiled,
            pipeline_input_types=input_runtime_types,
            specification_sha256=configuration_sha256(
                spec.model_dump(mode="python", by_alias=True)
            ),
        )

    @staticmethod
    def _validate_stage_shape(
        stage: StageSpec,
        registration: ComponentRegistration,
    ) -> None:
        declared_inputs = set(stage.inputs)
        known_inputs = set(registration.input_ports)
        unknown_inputs = declared_inputs - known_inputs
        if unknown_inputs:
            names = ", ".join(sorted(unknown_inputs))
            raise PipelineDefinitionError(
                f"stage {stage.stage_id!r} has unknown input ports: {names}"
            )
        missing_inputs = {
            name
            for name, contract in registration.input_ports.items()
            if contract.required and name not in declared_inputs
        }
        if missing_inputs:
            names = ", ".join(sorted(missing_inputs))
            raise PipelineDefinitionError(
                f"stage {stage.stage_id!r} is missing required inputs: {names}"
            )
        declared_outputs = set(stage.outputs)
        known_outputs = set(registration.output_ports)
        if declared_outputs != known_outputs:
            missing = known_outputs - declared_outputs
            unknown = declared_outputs - known_outputs
            details: list[str] = []
            if missing:
                details.append(f"missing {', '.join(sorted(missing))}")
            if unknown:
                details.append(f"unknown {', '.join(sorted(unknown))}")
            raise PipelineDefinitionError(
                f"stage {stage.stage_id!r} output declaration does not match "
                f"the registered component ({'; '.join(details)})"
            )

    @staticmethod
    def _validate_dependencies(
        stage: StageSpec,
        stages: Mapping[str, StageSpec],
    ) -> None:
        for dependency in stage.depends_on:
            if dependency == stage.stage_id:
                raise PipelineDefinitionError(
                    f"stage {stage.stage_id!r} cannot depend on itself"
                )
            if dependency not in stages:
                raise PipelineDefinitionError(
                    f"stage {stage.stage_id!r} has unknown dependency {dependency!r}"
                )

    @staticmethod
    def _validate_condition(
        stage: StageSpec,
        stages: Mapping[str, StageSpec],
        registrations: Mapping[str, ComponentRegistration],
        instances: Mapping[str, ComponentInstanceSpec],
    ) -> None:
        for predicate in _condition_predicates(stage.condition):
            if isinstance(predicate, AlwaysCondition):
                continue
            referenced_stage = stages.get(predicate.stage_id)
            if referenced_stage is None:
                raise PipelineDefinitionError(
                    f"stage {stage.stage_id!r} condition references unknown stage "
                    f"{predicate.stage_id!r}"
                )
            if predicate.stage_id not in stage.depends_on:
                raise PipelineDefinitionError(
                    f"stage {stage.stage_id!r} must declare condition source "
                    f"{predicate.stage_id!r} in depends_on"
                )
            if isinstance(
                predicate,
                (OutputPresentCondition, OutputAbsentCondition),
            ):
                instance = instances[referenced_stage.component_instance_id]
                registration = registrations[instance.instance_id]
                if (
                    predicate.output_name not in registration.output_ports
                    or predicate.output_name not in referenced_stage.outputs
                ):
                    raise PipelineDefinitionError(
                        f"stage {stage.stage_id!r} condition references undeclared "
                        f"output {predicate.stage_id}.{predicate.output_name}"
                    )


def _require_schema_compatibility(
    source: PipelineContract,
    target: PipelineContract,
    *,
    source_label: str,
    target_label: str,
) -> None:
    if source != target:
        raise PipelineDefinitionError(
            f"incompatible schemas between {source_label} and {target_label}: "
            f"{source.schema_uri}@{source.schema_version} != "
            f"{target.schema_uri}@{target.schema_version}"
        )


def _require_port_compatibility(
    source: PortContract,
    target: PortContract,
    *,
    source_label: str,
    target_label: str,
) -> None:
    _require_schema_compatibility(
        source.serializable,
        target.serializable,
        source_label=source_label,
        target_label=target_label,
    )
    if source.runtime_types != target.runtime_types:
        raise PipelineDefinitionError(
            f"incompatible runtime types between {source_label} and {target_label}"
        )


def _condition_predicates(
    condition: StageCondition,
) -> tuple[ConditionPredicate, ...]:
    if isinstance(condition, (AllCondition, AnyCondition)):
        return condition.conditions
    return (condition,)


def _condition_guarantees_output(
    condition: StageCondition,
    stage_id: str,
    output_name: str,
) -> bool:
    def matches(predicate: ConditionPredicate) -> bool:
        return (
            isinstance(predicate, OutputPresentCondition)
            and predicate.stage_id == stage_id
            and predicate.output_name == output_name
        )

    if isinstance(condition, AllCondition):
        return any(matches(predicate) for predicate in condition.conditions)
    if isinstance(condition, AnyCondition):
        return all(matches(predicate) for predicate in condition.conditions)
    return matches(condition)


def _output_may_be_absent(
    source_stage: StageSpec,
    source_port: PortContract,
) -> bool:
    """Return whether a declared output can be absent at runtime."""

    return not source_port.required or not isinstance(
        source_stage.condition, AlwaysCondition
    )


def _topological_order(stages: Sequence[StageSpec]) -> tuple[str, ...]:
    positions = {stage.stage_id: index for index, stage in enumerate(stages)}
    indegree = {stage.stage_id: len(stage.depends_on) for stage in stages}
    dependents: dict[str, list[str]] = defaultdict(list)
    for stage in stages:
        for dependency in stage.depends_on:
            dependents[dependency].append(stage.stage_id)
    ready = sorted(
        (stage_id for stage_id, degree in indegree.items() if degree == 0),
        key=positions.__getitem__,
    )
    ordered: list[str] = []
    while ready:
        stage_id = ready.pop(0)
        ordered.append(stage_id)
        for dependent in sorted(
            dependents[stage_id],
            key=positions.__getitem__,
        ):
            indegree[dependent] -= 1
            if indegree[dependent] == 0:
                ready.append(dependent)
                ready.sort(key=positions.__getitem__)
    if len(ordered) != len(stages):
        blocked = ", ".join(
            sorted(stage_id for stage_id, degree in indegree.items() if degree > 0)
        )
        raise PipelineDefinitionError(f"pipeline contains a cycle involving: {blocked}")
    return tuple(ordered)


class StageExecutor(Protocol):
    async def execute(
        self,
        stage: CompiledStage,
        context: StageContext,
    ) -> StageResult: ...


@dataclass(frozen=True, slots=True)
class StageFailure:
    """Typed context for an unexpected component or executor exception."""

    pipeline_id: str
    pipeline_version: str
    pipeline_run_id: str
    stage_id: str
    component: ComponentDescriptor
    configuration: Mapping[str, Any]
    configuration_sha256: str
    input_identity: Mapping[str, str]
    exception: Exception
    started_at: datetime
    started_clock: float

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "configuration",
            MappingProxyType(dict(self.configuration)),
        )
        object.__setattr__(
            self,
            "input_identity",
            MappingProxyType(dict(self.input_identity)),
        )


class StageFailureObserver(Protocol):
    """Domain-owned persistence hook for unexpected stage failures."""

    async def record_failure(self, failure: StageFailure) -> None: ...


class LocalStageExecutor:
    """Execute allow-listed plugins in the current process."""

    async def execute(
        self,
        stage: CompiledStage,
        context: StageContext,
    ) -> StageResult:
        try:
            current_configuration_sha256 = configuration_sha256(
                stage.configuration.model_dump(mode="python")
            )
        except (TypeError, ValueError) as exc:
            raise PipelineExecutionError(
                f"stage {stage.spec.stage_id!r} configuration is no longer "
                "canonical JSON"
            ) from exc
        if current_configuration_sha256 != stage.configuration_sha256:
            raise PipelineExecutionError(
                f"stage {stage.spec.stage_id!r} configuration changed after "
                "pipeline compilation"
            )
        result = await stage.registration.plugin.execute(
            context,
            stage.configuration,
        )
        if not isinstance(result, StageResult):
            raise PipelineExecutionError(
                f"component {stage.registration.descriptor.component_id!r} returned "
                "a non-StageResult value"
            )
        if result.status is StageExecutionStatus.SKIPPED:
            raise PipelineExecutionError(
                "SKIPPED is reserved for condition handling by the orchestrator"
            )
        declared = set(stage.spec.outputs)
        unknown = set(result.outputs) - declared
        if unknown:
            names = ", ".join(sorted(unknown))
            raise PipelineExecutionError(
                f"stage {stage.spec.stage_id!r} returned undeclared outputs: {names}"
            )
        if result.status in {
            StageExecutionStatus.COMPLETE,
            StageExecutionStatus.PARTIAL,
        }:
            missing = {
                name
                for name, contract in stage.registration.output_ports.items()
                if contract.required and name not in result.outputs
            }
            if missing:
                names = ", ".join(sorted(missing))
                raise PipelineExecutionError(
                    f"stage {stage.spec.stage_id!r} omitted required outputs: {names}"
                )
        for name, value in result.outputs.items():
            contract = stage.registration.output_ports[name]
            if not contract.accepts(value):
                expected = ", ".join(item.__name__ for item in contract.runtime_types)
                raise PipelineExecutionError(
                    f"stage {stage.spec.stage_id!r} output {name!r} does not "
                    f"match runtime type {expected}"
                )
        return result


@dataclass(frozen=True, slots=True)
class PipelineExecution:
    pipeline_run_id: str
    results: Mapping[str, StageResult]

    def __post_init__(self) -> None:
        object.__setattr__(self, "results", MappingProxyType(dict(self.results)))

    def result_for(self, stage_id: str) -> StageResult:
        try:
            return self.results[stage_id]
        except KeyError as exc:
            raise KeyError(f"pipeline has no stage {stage_id!r}") from exc


class PipelineOrchestrator:
    """Evaluate typed conditions and schedule a compiled DAG locally."""

    def __init__(
        self,
        executor: StageExecutor | None = None,
        *,
        failure_observer: StageFailureObserver | None = None,
    ) -> None:
        self.executor = executor or LocalStageExecutor()
        self.failure_observer = failure_observer

    async def execute(
        self,
        pipeline: CompiledPipeline,
        inputs: Mapping[str, object],
        *,
        pipeline_run_id: str | None = None,
        input_identity: Mapping[str, str] | None = None,
    ) -> PipelineExecution:
        try:
            current_specification_sha256 = configuration_sha256(
                pipeline.spec.model_dump(mode="python", by_alias=True)
            )
        except (TypeError, ValueError) as exc:
            raise PipelineExecutionError(
                "pipeline specification is no longer canonical JSON"
            ) from exc
        if current_specification_sha256 != pipeline.specification_sha256:
            raise PipelineExecutionError(
                "pipeline specification changed after compilation"
            )
        expected_inputs = set(pipeline.spec.inputs)
        actual_inputs = set(inputs)
        missing = expected_inputs - actual_inputs
        unknown = actual_inputs - expected_inputs
        if missing or unknown:
            details: list[str] = []
            if missing:
                details.append(f"missing {', '.join(sorted(missing))}")
            if unknown:
                details.append(f"unknown {', '.join(sorted(unknown))}")
            raise PipelineExecutionError(
                f"pipeline input mismatch ({'; '.join(details)})"
            )
        for name, value in inputs.items():
            value_types = pipeline.pipeline_input_types[name]
            if not isinstance(value, value_types):
                expected = ", ".join(item.__name__ for item in value_types)
                raise PipelineExecutionError(
                    f"pipeline input {name!r} does not match runtime type {expected}"
                )

        execution_id = pipeline_run_id or f"pipeline-{uuid.uuid4()}"
        resolved_input_identity = dict(input_identity or {})
        if self.failure_observer is not None:
            if not resolved_input_identity:
                raise PipelineExecutionError(
                    "input_identity is required when a failure observer is configured"
                )
            if any(
                not isinstance(name, str)
                or not name.strip()
                or not isinstance(value, str)
                or not value.strip()
                for name, value in resolved_input_identity.items()
            ):
                raise PipelineExecutionError(
                    "input_identity names and values must be non-empty strings"
                )
        results: dict[str, StageResult] = {}
        for stage in pipeline.stages:
            if not _evaluate_condition(stage.spec.condition, results):
                results[stage.spec.stage_id] = StageResult(
                    status=StageExecutionStatus.SKIPPED
                )
                continue
            runtime_inputs: dict[str, object] = {}
            for port_name, binding in stage.spec.inputs.items():
                if isinstance(binding, PipelineInputRef):
                    runtime_inputs[port_name] = inputs[binding.input_name]
                    continue
                source = results[binding.stage_id]
                if binding.output_name in source.outputs:
                    runtime_inputs[port_name] = source.outputs[binding.output_name]
                    continue
                target = stage.registration.input_ports[port_name]
                if target.required:
                    raise PipelineExecutionError(
                        f"stage {stage.spec.stage_id!r} required input {port_name!r} "
                        f"was not produced by {binding.stage_id}.{binding.output_name}"
                    )
            context = StageContext(
                pipeline_id=pipeline.spec.pipeline_id,
                pipeline_version=pipeline.spec.pipeline_version,
                pipeline_run_id=execution_id,
                stage_id=stage.spec.stage_id,
                inputs=runtime_inputs,
                prior_results=results,
            )
            started_at = utc_now()
            started_clock = time.perf_counter()
            try:
                results[stage.spec.stage_id] = await self.executor.execute(
                    stage,
                    context,
                )
            except Exception as exc:
                if self.failure_observer is not None:
                    failure = StageFailure(
                        pipeline_id=pipeline.spec.pipeline_id,
                        pipeline_version=pipeline.spec.pipeline_version,
                        pipeline_run_id=execution_id,
                        stage_id=stage.spec.stage_id,
                        component=stage.registration.descriptor,
                        configuration=stage.configuration.model_dump(mode="python"),
                        configuration_sha256=stage.configuration_sha256,
                        input_identity=resolved_input_identity,
                        exception=exc,
                        started_at=started_at,
                        started_clock=started_clock,
                    )
                    try:
                        await self.failure_observer.record_failure(failure)
                    except Exception as observer_error:
                        exc.add_note(
                            "the stage failure observer also failed: "
                            f"{type(observer_error).__name__}: {observer_error}"
                        )
                        raise exc from observer_error
                raise
        return PipelineExecution(pipeline_run_id=execution_id, results=results)


def _evaluate_condition(
    condition: StageCondition,
    results: Mapping[str, StageResult],
) -> bool:
    def evaluate(predicate: ConditionPredicate) -> bool:
        if isinstance(predicate, AlwaysCondition):
            return True
        result = results.get(predicate.stage_id)
        if isinstance(predicate, OutputPresentCondition):
            return result is not None and predicate.output_name in result.outputs
        if isinstance(predicate, OutputAbsentCondition):
            return result is None or predicate.output_name not in result.outputs
        if isinstance(predicate, DiagnosticPresentCondition):
            return result is not None and any(
                diagnostic.code == predicate.code for diagnostic in result.diagnostics
            )
        if isinstance(predicate, StageStatusCondition):
            return result is not None and result.status in predicate.statuses
        raise AssertionError(f"unsupported typed condition: {type(predicate).__name__}")

    if isinstance(condition, AllCondition):
        return all(evaluate(predicate) for predicate in condition.conditions)
    if isinstance(condition, AnyCondition):
        return any(evaluate(predicate) for predicate in condition.conditions)
    return evaluate(condition)


class EmptyComponentConfig(_FrozenSpec):
    """Explicit no-configuration contract for deterministic components."""


__all__ = [
    "AllCondition",
    "AlwaysCondition",
    "AnyCondition",
    "CompiledPipeline",
    "CompiledStage",
    "ComponentInstanceSpec",
    "ComponentRegistration",
    "ComponentRegistry",
    "ComponentRegistryError",
    "DiagnosticPresentCondition",
    "EmptyComponentConfig",
    "FunctionStagePlugin",
    "InputBinding",
    "LocalStageExecutor",
    "OutputAbsentCondition",
    "OutputPresentCondition",
    "PipelineCompiler",
    "PipelineContract",
    "PipelineDefinitionError",
    "PipelineExecution",
    "PipelineExecutionError",
    "PipelineInputRef",
    "PipelineOrchestrator",
    "PipelineSpec",
    "PortContract",
    "StageCondition",
    "StageContext",
    "StageDiagnostic",
    "StageExecutionStatus",
    "StageExecutor",
    "StageFailure",
    "StageFailureObserver",
    "StageOutputRef",
    "StagePlugin",
    "StageResult",
    "StageSpec",
    "StageStatusCondition",
]
