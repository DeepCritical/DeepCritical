from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from omegaconf import DictConfig, OmegaConf
from pydantic import BaseModel, ConfigDict, ValidationError

from DeepResearch.src.document_processing import (
    ComponentDescriptor,
    default_document_pipeline_spec,
)
from DeepResearch.src.document_processing.models import DiagnosticSeverity
from DeepResearch.src.document_processing.orchestration import (
    ComponentInstanceSpec,
    ComponentRegistration,
    ComponentRegistry,
    DiagnosticPresentCondition,
    EmptyComponentConfig,
    FunctionStagePlugin,
    LocalStageExecutor,
    OutputPresentCondition,
    PipelineCompiler,
    PipelineContract,
    PipelineDefinitionError,
    PipelineExecutionError,
    PipelineInputRef,
    PipelineOrchestrator,
    PipelineSpec,
    PortContract,
    StageContext,
    StageDiagnostic,
    StageExecutionStatus,
    StageOutputRef,
    StageResult,
    StageSpec,
)

TEXT = PortContract(
    schema_uri="urn:test:text",
    schema_version="test-text-v1",
    value_types=str,
)
OPTIONAL_TEXT = PortContract(
    schema_uri="urn:test:text",
    schema_version="test-text-v1",
    value_types=str,
    required=False,
)
NUMBER = PortContract(
    schema_uri="urn:test:number",
    schema_version="test-number-v1",
    value_types=int,
)


class PrefixConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    prefix: str


@dataclass(frozen=True, slots=True)
class _CallLog:
    stage_ids: list[str]


def _registration(
    component_id: str,
    *,
    input_ports: dict[str, PortContract],
    output_ports: dict[str, PortContract],
    handler: Any,
    configuration_model: type[BaseModel] = EmptyComponentConfig,
) -> ComponentRegistration:
    return ComponentRegistration(
        descriptor=ComponentDescriptor(
            component_id=component_id,
            component_version="1",
            capability=f"test.{component_id}",
        ),
        configuration_model=configuration_model,
        input_ports=input_ports,
        output_ports=output_ports,
        plugin=FunctionStagePlugin(handler),
    )


def _text_input() -> PipelineContract:
    return PipelineContract(
        schema_uri=TEXT.schema_uri,
        schema_version=TEXT.schema_version,
    )


def _pipeline(
    *,
    components: tuple[ComponentInstanceSpec, ...],
    stages: tuple[StageSpec, ...],
) -> PipelineSpec:
    return PipelineSpec(
        pipeline_id="test-pipeline",
        pipeline_version="1",
        inputs={"text": _text_input()},
        components=components,
        stages=stages,
    )


def test_checked_in_yaml_is_the_compiled_reference_graph() -> None:
    path = (
        Path(__file__).resolve().parents[2]
        / "configs"
        / "document_processing"
        / "default.yaml"
    )
    raw = OmegaConf.load(path)
    assert isinstance(raw, DictConfig)
    configured = PipelineSpec.model_validate(
        OmegaConf.to_container(raw.pipeline, resolve=True)
    )

    assert configured == default_document_pipeline_spec()
    assert all(
        set(component.configuration).isdisjoint(
            {"module", "callable", "class", "import"}
        )
        for component in configured.components
    )


@pytest.mark.asyncio
async def test_compiler_and_local_executor_apply_validated_configuration() -> None:
    calls: list[str] = []

    async def prefix(context: StageContext, configuration: BaseModel) -> StageResult:
        calls.append(context.stage_id)
        assert isinstance(configuration, PrefixConfig)
        return StageResult(
            status=StageExecutionStatus.COMPLETE,
            outputs={
                "text": (configuration.prefix + context.require_input("text", str))
            },
        )

    async def finish(context: StageContext, _: BaseModel) -> StageResult:
        calls.append(context.stage_id)
        return StageResult(
            status=StageExecutionStatus.COMPLETE,
            outputs={"result": context.require_input("text", str).upper()},
        )

    registry = ComponentRegistry()
    registry.register(
        _registration(
            "prefix",
            input_ports={"text": TEXT},
            output_ports={"text": TEXT},
            handler=prefix,
            configuration_model=PrefixConfig,
        )
    )
    registry.register(
        _registration(
            "finish",
            input_ports={"text": TEXT},
            output_ports={"result": TEXT},
            handler=finish,
        )
    )
    spec = _pipeline(
        components=(
            ComponentInstanceSpec(
                instance_id="configured-prefix",
                component_id="prefix",
                configuration={"prefix": "safe:"},
            ),
            ComponentInstanceSpec(
                instance_id="finish",
                component_id="finish",
            ),
        ),
        stages=(
            StageSpec(
                stage_id="prefix",
                component="configured-prefix",
                inputs={
                    "text": PipelineInputRef(input_name="text"),
                },
                outputs=("text",),
            ),
            StageSpec(
                stage_id="finish",
                component="finish",
                depends_on=("prefix",),
                inputs={
                    "text": StageOutputRef(
                        stage_id="prefix",
                        output_name="text",
                    )
                },
                outputs=("result",),
            ),
        ),
    )

    compiled = PipelineCompiler(registry).compile(spec)
    execution = await PipelineOrchestrator().execute(
        compiled,
        {"text": "paper"},
        pipeline_run_id="pipeline-run-1",
    )

    assert calls == ["prefix", "finish"]
    assert execution.pipeline_run_id == "pipeline-run-1"
    assert execution.result_for("finish").outputs["result"] == "SAFE:PAPER"


@pytest.mark.asyncio
async def test_compiled_pipeline_rejects_post_validation_mutation() -> None:
    async def prefix(
        context: StageContext,
        configuration: BaseModel,
    ) -> StageResult:
        assert isinstance(configuration, PrefixConfig)
        return StageResult(
            status=StageExecutionStatus.COMPLETE,
            outputs={"text": configuration.prefix + context.require_input("text", str)},
        )

    registry = ComponentRegistry()
    registry.register(
        _registration(
            "prefix",
            input_ports={"text": TEXT},
            output_ports={"text": TEXT},
            handler=prefix,
            configuration_model=PrefixConfig,
        )
    )

    def compiled_pipeline():
        return PipelineCompiler(registry).compile(
            _pipeline(
                components=(
                    ComponentInstanceSpec(
                        instance_id="prefix",
                        component_id="prefix",
                        configuration={"prefix": "safe:"},
                    ),
                ),
                stages=(
                    StageSpec(
                        stage_id="prefix",
                        component="prefix",
                        inputs={"text": PipelineInputRef(input_name="text")},
                        outputs=("text",),
                    ),
                ),
            )
        )

    mutated_specification = compiled_pipeline()
    mutated_specification.spec.stages[0].inputs["text"] = PipelineInputRef(
        input_name="different"
    )
    with pytest.raises(
        PipelineExecutionError,
        match="specification changed after compilation",
    ):
        await PipelineOrchestrator().execute(
            mutated_specification,
            {"text": "paper"},
        )

    mutated_configuration = compiled_pipeline()
    object.__setattr__(
        mutated_configuration.stages[0].configuration,
        "prefix",
        "unsafe:",
    )
    with pytest.raises(
        PipelineExecutionError,
        match="configuration changed after pipeline compilation",
    ):
        await PipelineOrchestrator().execute(
            mutated_configuration,
            {"text": "paper"},
        )


def test_compiler_rejects_unknown_components_and_invalid_configuration() -> None:
    registry = ComponentRegistry()

    async def passthrough(context: StageContext, _: BaseModel) -> StageResult:
        return StageResult(
            status=StageExecutionStatus.COMPLETE,
            outputs={"text": context.require_input("text", str)},
        )

    registry.register(
        _registration(
            "known",
            input_ports={"text": TEXT},
            output_ports={"text": TEXT},
            handler=passthrough,
            configuration_model=PrefixConfig,
        )
    )
    unknown = _pipeline(
        components=(
            ComponentInstanceSpec(instance_id="unknown", component_id="not-registered"),
        ),
        stages=(
            StageSpec(
                stage_id="stage",
                component="unknown",
                inputs={"text": PipelineInputRef(input_name="text")},
                outputs=("text",),
            ),
        ),
    )
    with pytest.raises(PipelineDefinitionError, match="not registered"):
        PipelineCompiler(registry).compile(unknown)

    invalid = _pipeline(
        components=(
            ComponentInstanceSpec(
                instance_id="known",
                component_id="known",
                configuration={
                    "prefix": "ok",
                    "python_module": "untrusted.component",
                },
            ),
        ),
        stages=(
            StageSpec(
                stage_id="stage",
                component="known",
                inputs={"text": PipelineInputRef(input_name="text")},
                outputs=("text",),
            ),
        ),
    )
    with pytest.raises(PipelineDefinitionError, match="invalid configuration"):
        PipelineCompiler(registry).compile(invalid)


def test_pipeline_spec_rejects_duplicate_ids_and_arbitrary_expressions() -> None:
    component = ComponentInstanceSpec(
        instance_id="same",
        component_id="component",
    )
    stage = {
        "stage_id": "same",
        "component": "same",
        "inputs": {
            "text": {
                "source": "pipeline",
                "input_name": "text",
            }
        },
        "outputs": ["text"],
    }
    with pytest.raises(ValidationError, match="component instance IDs must be unique"):
        PipelineSpec.model_validate(
            {
                "pipeline_id": "pipeline",
                "pipeline_version": "1",
                "inputs": {"text": _text_input().model_dump()},
                "components": [
                    component.model_dump(),
                    component.model_dump(),
                ],
                "stages": [stage],
            }
        )
    with pytest.raises(ValidationError, match="stage IDs must be unique"):
        PipelineSpec.model_validate(
            {
                "pipeline_id": "pipeline",
                "pipeline_version": "1",
                "inputs": {"text": _text_input().model_dump()},
                "components": [component.model_dump()],
                "stages": [stage, stage],
            }
        )
    with pytest.raises(ValidationError):
        PipelineSpec.model_validate(
            {
                "pipeline_id": "pipeline",
                "pipeline_version": "1",
                "inputs": {"text": _text_input().model_dump()},
                "components": [component.model_dump()],
                "stages": [
                    {
                        **stage,
                        "condition": {
                            "type": "expression",
                            "expression": "__import__('os').system('false')",
                        },
                    }
                ],
            }
        )
    with pytest.raises(ValidationError, match="canonical JSON"):
        ComponentInstanceSpec(
            instance_id="unsafe",
            component_id="component",
            configuration={"callback": lambda: None},
        )


def test_compiler_rejects_cycles_missing_inputs_and_incompatible_schemas() -> None:
    async def no_op(_: StageContext, __: BaseModel) -> StageResult:
        return StageResult(
            status=StageExecutionStatus.COMPLETE,
            outputs={"text": "value"},
        )

    registry = ComponentRegistry()
    registry.register(
        _registration(
            "text",
            input_ports={"text": TEXT},
            output_ports={"text": TEXT},
            handler=no_op,
        )
    )
    registry.register(
        _registration(
            "number",
            input_ports={"number": NUMBER},
            output_ports={"text": TEXT},
            handler=no_op,
        )
    )
    cycle = _pipeline(
        components=(ComponentInstanceSpec(instance_id="text", component_id="text"),),
        stages=(
            StageSpec(
                stage_id="first",
                component="text",
                depends_on=("second",),
                inputs={
                    "text": StageOutputRef(
                        stage_id="second",
                        output_name="text",
                    )
                },
                outputs=("text",),
            ),
            StageSpec(
                stage_id="second",
                component="text",
                depends_on=("first",),
                inputs={
                    "text": StageOutputRef(
                        stage_id="first",
                        output_name="text",
                    )
                },
                outputs=("text",),
            ),
        ),
    )
    with pytest.raises(PipelineDefinitionError, match="cycle"):
        PipelineCompiler(registry).compile(cycle)

    missing = _pipeline(
        components=(ComponentInstanceSpec(instance_id="text", component_id="text"),),
        stages=(
            StageSpec(
                stage_id="missing",
                component="text",
                outputs=("text",),
            ),
        ),
    )
    with pytest.raises(PipelineDefinitionError, match="missing required inputs"):
        PipelineCompiler(registry).compile(missing)

    incompatible = _pipeline(
        components=(
            ComponentInstanceSpec(instance_id="number", component_id="number"),
        ),
        stages=(
            StageSpec(
                stage_id="number",
                component="number",
                inputs={"number": PipelineInputRef(input_name="text")},
                outputs=("text",),
            ),
        ),
    )
    with pytest.raises(PipelineDefinitionError, match="incompatible schemas"):
        PipelineCompiler(registry).compile(incompatible)


@pytest.mark.asyncio
async def test_conditional_output_requires_and_honors_typed_presence_guard() -> None:
    async def maybe(_: StageContext, __: BaseModel) -> StageResult:
        return StageResult(status=StageExecutionStatus.COMPLETE)

    async def consume(context: StageContext, _: BaseModel) -> StageResult:
        return StageResult(
            status=StageExecutionStatus.COMPLETE,
            outputs={"text": context.require_input("text", str)},
        )

    registry = ComponentRegistry()
    registry.register(
        _registration(
            "maybe",
            input_ports={"text": TEXT},
            output_ports={"text": OPTIONAL_TEXT},
            handler=maybe,
        )
    )
    registry.register(
        _registration(
            "consume",
            input_ports={"text": TEXT},
            output_ports={"text": TEXT},
            handler=consume,
        )
    )
    components = (
        ComponentInstanceSpec(instance_id="maybe", component_id="maybe"),
        ComponentInstanceSpec(instance_id="consume", component_id="consume"),
    )
    stages = (
        StageSpec(
            stage_id="maybe",
            component="maybe",
            inputs={"text": PipelineInputRef(input_name="text")},
            outputs=("text",),
        ),
        StageSpec(
            stage_id="consume",
            component="consume",
            depends_on=("maybe",),
            inputs={
                "text": StageOutputRef(
                    stage_id="maybe",
                    output_name="text",
                )
            },
            outputs=("text",),
        ),
    )
    with pytest.raises(PipelineDefinitionError, match="output_present guard"):
        PipelineCompiler(registry).compile(
            _pipeline(components=components, stages=stages)
        )

    guarded = _pipeline(
        components=components,
        stages=(
            stages[0],
            stages[1].model_copy(
                update={
                    "condition": OutputPresentCondition(
                        stage_id="maybe",
                        output_name="text",
                    )
                }
            ),
        ),
    )
    execution = await PipelineOrchestrator().execute(
        PipelineCompiler(registry).compile(guarded),
        {"text": "input"},
    )
    assert execution.result_for("maybe").status is StageExecutionStatus.COMPLETE
    assert execution.result_for("consume").status is StageExecutionStatus.SKIPPED


@pytest.mark.asyncio
async def test_diagnostic_condition_is_typed_and_local_executor_fails_closed() -> None:
    async def diagnose(_: StageContext, __: BaseModel) -> StageResult:
        return StageResult(
            status=StageExecutionStatus.PARTIAL,
            outputs={"text": "recoverable"},
            diagnostics=(
                StageDiagnostic(
                    code="NEEDS_REVIEW",
                    severity=DiagnosticSeverity.WARNING,
                    message="Review is required.",
                ),
            ),
        )

    async def bad_output(_: StageContext, __: BaseModel) -> StageResult:
        return StageResult(
            status=StageExecutionStatus.COMPLETE,
            outputs={"result": 42},
        )

    registry = ComponentRegistry()
    registry.register(
        _registration(
            "diagnose",
            input_ports={"text": TEXT},
            output_ports={"text": TEXT},
            handler=diagnose,
        )
    )
    registry.register(
        _registration(
            "bad",
            input_ports={"text": TEXT},
            output_ports={"result": TEXT},
            handler=bad_output,
        )
    )
    spec = _pipeline(
        components=(
            ComponentInstanceSpec(instance_id="diagnose", component_id="diagnose"),
            ComponentInstanceSpec(instance_id="bad", component_id="bad"),
        ),
        stages=(
            StageSpec(
                stage_id="diagnose",
                component="diagnose",
                inputs={"text": PipelineInputRef(input_name="text")},
                outputs=("text",),
            ),
            StageSpec(
                stage_id="bad",
                component="bad",
                depends_on=("diagnose",),
                inputs={
                    "text": StageOutputRef(
                        stage_id="diagnose",
                        output_name="text",
                    )
                },
                outputs=("result",),
                condition=DiagnosticPresentCondition(
                    stage_id="diagnose",
                    code="NEEDS_REVIEW",
                ),
            ),
        ),
    )
    with pytest.raises(PipelineExecutionError, match="does not match runtime type"):
        await PipelineOrchestrator(LocalStageExecutor()).execute(
            PipelineCompiler(registry).compile(spec),
            {"text": "input"},
        )
