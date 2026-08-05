# ADR 0002: Allow-listed local pipeline

- Status: Accepted
- Date: 2026-07-29

## Context

The first document-processing implementation encoded routing, native adapters,
Docling, GROBID, OCR fallback, alignment, integrity checks, and result assembly
in one orchestration method. Its persisted contracts were already generic, but
adding a scientific extraction or verification stage would still require
editing that method. Loading component implementations directly from YAML
would make configuration executable and would turn untrusted configuration
into a Python import boundary.

The project also expects distributed execution eventually. Implementing a
queue before the local stage contracts are proven would couple scientific
pipeline design to transport, leasing, retry, and worker-lifecycle decisions.

## Decision

DeepCritical uses a versioned `PipelineSpec` whose component instances refer
only to IDs in a process-owned `ComponentRegistry`.

Each registered component declares:

- a stable `ComponentDescriptor`;
- a Pydantic configuration model with unknown fields rejected;
- named input and output ports with exact schema URI and version;
- local runtime value types and whether each port is required; and
- one `StagePlugin` implementation.

`PipelineCompiler` validates the complete graph before execution. It rejects
unknown components, invalid configuration, duplicate identifiers, missing or
unknown ports, incompatible contracts, undeclared dependencies, cycles,
unknown condition references, and unsafe consumption of conditional outputs.
Pipeline conditions use a closed discriminated union; arbitrary code and
expression evaluation are not supported.

An output is potentially absent when its registered port is optional or its
producing stage has any condition other than `always`. A required downstream
input may consume such an output only when its own condition proves that exact
output is present. For `all`, one conjunct proving presence is sufficient; for
`any`, every alternative must prove presence. This intentionally conservative
rule prevents a skipped producer with a nominally required port from creating a
runtime-only missing-input failure.

`PipelineOrchestrator` schedules the compiled graph through the
`StageExecutor` protocol. The only implementation in this change is
`LocalStageExecutor`. The existing document-processing behavior is represented
by the checked-in YAML graph and runs through these interfaces while preserving
the existing `ProcessingRun`, `DataProductRef`, diagnostic, recovery, and
artifact-lineage semantics.

Expected parser and validation failures remain owned by document components:
the component persists its terminal `ProcessingRun` and returns a typed stage
result. Unexpected ordinary exceptions are observed by the generic
orchestrator through an optional `StageFailureObserver`. The observation
contains pipeline/run identity, stage and registered component identity, the
validated component configuration and hash, caller-supplied input identity,
timing, and the original exception. The generic engine does not import
document storage or document models.

The document-processing implementation supplies
`DocumentProcessingFailureRecorder`. It checks whether the failing stage
already persisted a terminal run during that invocation. If so, it does
nothing; otherwise it persists exactly one failed `ProcessingRun`. Downstream
stages are not scheduled and the original exception is re-raised. Cancellation
is outside the ordinary-exception observer path and is re-raised without being
converted into a failure record. A custom executor may change execution
mechanics, but the document orchestrator retains this recorder ownership.

## Consequences

New local components can be added without giving YAML import authority, and a
bad graph fails before parser work begins. Optional outputs and conditional
branches are explicit contracts rather than implicit control flow.

The local flow still passes Python runtime values between some orchestration
stages. A future distributed executor must introduce a serializable task
envelope and content-addressed handoff contract rather than serializing those
private local values or adding queue-specific nullable fields to
`DocumentArtifact`.

This decision does not introduce the project-owned `CanonicalDocumentView`,
OCR-correction or study-type components, a queue executor, remote workers, or a
general-purpose plugin import system. Those remain separate follow-ups;
scientific claim extraction, evidence appraisal, Alzheimer’s-specific
reasoning, hypothesis generation, and experiment design are also outside this
decision.
