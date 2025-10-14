"""
Workflow Edge utilities for DeepCritical agent interaction design patterns.

This module vendors in the edge system from the _workflows directory, providing
edge management, routing, and validation functionality with minimal external dependencies.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar
from uuid import uuid4

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

logger = logging.getLogger(__name__)


def _extract_function_name(func: Callable[..., Any]) -> str:
    """Map a Python callable to a concise, human-focused identifier."""
    if hasattr(func, "__name__"):
        name = func.__name__
        return str(name) if name != "<lambda>" else "<lambda>"
    return "<callable>"


def _missing_callable(name: str) -> Callable[..., Any]:
    """Create a defensive placeholder for callables that cannot be restored."""

    def _raise(*_: Any, **__: Any) -> Any:
        msg = f"Callable '{name}' is unavailable after serialization"
        raise RuntimeError(msg)

    return _raise


@dataclass(init=False)
class Edge:
    """Model a directed, optionally-conditional hand-off between two executors."""

    ID_SEPARATOR: ClassVar[str] = "->"

    source_id: str
    target_id: str
    condition_name: str | None
    _condition: Callable[[Any], bool] | None = field(
        default=None, repr=False, compare=False
    )

    def __init__(
        self,
        source_id: str,
        target_id: str,
        condition: Callable[[Any], bool] | None = None,
        *,
        condition_name: str | None = None,
    ) -> None:
        """Initialize a fully-specified edge between two workflow executors."""
        if not source_id:
            msg = "Edge source_id must be a non-empty string"
            raise ValueError(msg)
        if not target_id:
            msg = "Edge target_id must be a non-empty string"
            raise ValueError(msg)
        self.source_id = source_id
        self.target_id = target_id
        self._condition = condition
        self.condition_name = (
            _extract_function_name(condition)
            if condition is not None
            else condition_name
        )

    @property
    def id(self) -> str:
        """Return the stable identifier used to reference this edge."""
        return f"{self.source_id}{self.ID_SEPARATOR}{self.target_id}"

    def should_route(self, data: Any) -> bool:
        """Evaluate the edge predicate against an incoming payload."""
        if self._condition is None:
            return True
        return self._condition(data)

    def to_dict(self) -> dict[str, Any]:
        """Produce a JSON-serialisable view of the edge metadata."""
        payload = {"source_id": self.source_id, "target_id": self.target_id}
        if self.condition_name is not None:
            payload["condition_name"] = self.condition_name
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Edge:
        """Reconstruct an Edge from its serialised dictionary form."""
        return cls(
            source_id=data["source_id"],
            target_id=data["target_id"],
            condition=None,
            condition_name=data.get("condition_name"),
        )


@dataclass
class Case:
    """Runtime wrapper combining a switch-case predicate with its target."""

    condition: Callable[[Any], bool]
    target: Any  # This would be an Executor in the full implementation


@dataclass
class Default:
    """Runtime representation of the default branch in a switch-case group."""

    target: Any  # This would be an Executor in the full implementation


@dataclass(init=False)
class EdgeGroup:
    """Bundle edges that share a common routing semantics under a single id."""

    id: str
    type: str
    edges: list[Edge]

    _TYPE_REGISTRY: ClassVar[dict[str, type[EdgeGroup]]] = {}

    def __init__(
        self,
        edges: Sequence[Edge] | None = None,
        *,
        id: str | None = None,
        type: str | None = None,
    ) -> None:
        """Construct an edge group shell around a set of Edge instances."""
        self.id = id or f"{self.__class__.__name__}/{uuid4()}"
        self.type = type or self.__class__.__name__
        self.edges = list(edges) if edges is not None else []

    @property
    def source_executor_ids(self) -> list[str]:
        """Return the deduplicated list of upstream executor ids."""
        return list(dict.fromkeys(edge.source_id for edge in self.edges))

    @property
    def target_executor_ids(self) -> list[str]:
        """Return the ordered, deduplicated list of downstream executor ids."""
        return list(dict.fromkeys(edge.target_id for edge in self.edges))

    def to_dict(self) -> dict[str, Any]:
        """Serialise the group metadata and contained edges into primitives."""
        return {
            "id": self.id,
            "type": self.type,
            "edges": [edge.to_dict() for edge in self.edges],
        }

    @classmethod
    def register(cls, subclass: type[EdgeGroup]) -> type[EdgeGroup]:
        """Register a subclass so deserialisation can recover the right type."""
        cls._TYPE_REGISTRY[subclass.__name__] = subclass
        return subclass

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EdgeGroup:
        """Hydrate the correct EdgeGroup subclass from serialised state."""
        group_type = data.get("type", "EdgeGroup")
        target_cls = cls._TYPE_REGISTRY.get(group_type, EdgeGroup)
        edges = [Edge.from_dict(entry) for entry in data.get("edges", [])]

        obj = target_cls.__new__(target_cls)
        EdgeGroup.__init__(obj, edges=edges, id=data.get("id"), type=group_type)

        # Handle FanOutEdgeGroup-specific attributes
        if isinstance(obj, FanOutEdgeGroup):
            obj.selection_func_name = data.get("selection_func_name")
            obj._selection_func = (
                None
                if obj.selection_func_name is None
                else _missing_callable(obj.selection_func_name)
            )
            obj._target_ids = [edge.target_id for edge in obj.edges]

        # Handle SwitchCaseEdgeGroup-specific attributes
        if isinstance(obj, SwitchCaseEdgeGroup):
            cases_payload = data.get("cases", [])
            restored_cases: list[
                SwitchCaseEdgeGroupCase | SwitchCaseEdgeGroupDefault
            ] = []
            for case_data in cases_payload:
                case_type = case_data.get("type")
                if case_type == "Default":
                    restored_cases.append(
                        SwitchCaseEdgeGroupDefault.from_dict(case_data)
                    )
                else:
                    restored_cases.append(SwitchCaseEdgeGroupCase.from_dict(case_data))
            obj.cases = restored_cases
            obj._selection_func = _missing_callable("switch_case_selection")

        return obj


@EdgeGroup.register
@dataclass(init=False)
class SingleEdgeGroup(EdgeGroup):
    """Convenience wrapper for a solitary edge, keeping the group API uniform."""

    def __init__(
        self,
        source_id: str,
        target_id: str,
        condition: Callable[[Any], bool] | None = None,
        *,
        id: str | None = None,
    ) -> None:
        """Create a one-to-one edge group between two executors."""
        edge = Edge(source_id=source_id, target_id=target_id, condition=condition)
        super().__init__([edge], id=id, type=self.__class__.__name__)


@EdgeGroup.register
@dataclass(init=False)
class FanOutEdgeGroup(EdgeGroup):
    """Represent a broadcast-style edge group with optional selection logic."""

    selection_func_name: str | None
    _selection_func: Callable[[Any, list[str]], list[str]] | None
    _target_ids: list[str]

    def __init__(
        self,
        source_id: str,
        target_ids: Sequence[str],
        selection_func: Callable[[Any, list[str]], list[str]] | None = None,
        *,
        selection_func_name: str | None = None,
        id: str | None = None,
    ) -> None:
        """Create a fan-out mapping from a single source to many targets."""
        if len(target_ids) <= 1:
            msg = "FanOutEdgeGroup must contain at least two targets."
            raise ValueError(msg)

        edges = [Edge(source_id=source_id, target_id=target) for target in target_ids]
        super().__init__(edges, id=id, type=self.__class__.__name__)

        self._target_ids = list(target_ids)
        self._selection_func = selection_func
        self.selection_func_name = (
            _extract_function_name(selection_func)
            if selection_func is not None
            else selection_func_name
        )

    @property
    def target_ids(self) -> list[str]:
        """Return a shallow copy of the configured downstream executor ids."""
        return list(self._target_ids)

    @property
    def selection_func(self) -> Callable[[Any, list[str]], list[str]] | None:
        """Expose the runtime callable used to select active fan-out targets."""
        return self._selection_func

    def to_dict(self) -> dict[str, Any]:
        """Serialise the fan-out group while preserving selection metadata."""
        payload = super().to_dict()
        payload["selection_func_name"] = self.selection_func_name
        return payload


@EdgeGroup.register
@dataclass(init=False)
class FanInEdgeGroup(EdgeGroup):
    """Represent a converging set of edges that feed a single downstream executor."""

    def __init__(
        self, source_ids: Sequence[str], target_id: str, *, id: str | None = None
    ) -> None:
        """Build a fan-in mapping that merges several sources into one target."""
        if len(source_ids) <= 1:
            msg = "FanInEdgeGroup must contain at least two sources."
            raise ValueError(msg)

        edges = [Edge(source_id=source, target_id=target_id) for source in source_ids]
        super().__init__(edges, id=id, type=self.__class__.__name__)


@dataclass(init=False)
class SwitchCaseEdgeGroupCase:
    """Persistable description of a single conditional branch in a switch-case."""

    target_id: str
    condition_name: str | None
    type: str
    _condition: Callable[[Any], bool] = field(repr=False, compare=False)

    def __init__(
        self,
        condition: Callable[[Any], bool] | None,
        target_id: str,
        *,
        condition_name: str | None = None,
    ) -> None:
        """Record the routing metadata for a conditional case branch."""
        if not target_id:
            msg = "SwitchCaseEdgeGroupCase requires a target_id"
            raise ValueError(msg)
        self.target_id = target_id
        self.type = "Case"
        if condition is not None:
            self._condition = condition
            self.condition_name = _extract_function_name(condition)
        else:
            safe_name = condition_name or "<missing_condition>"
            self._condition = _missing_callable(safe_name)
            self.condition_name = condition_name

    @property
    def condition(self) -> Callable[[Any], bool]:
        """Return the predicate associated with this case."""
        return self._condition

    def to_dict(self) -> dict[str, Any]:
        """Serialise the case metadata without the executable predicate."""
        payload = {"target_id": self.target_id, "type": self.type}
        if self.condition_name is not None:
            payload["condition_name"] = self.condition_name
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SwitchCaseEdgeGroupCase:
        """Instantiate a case from its serialised dictionary payload."""
        return cls(
            condition=None,
            target_id=data["target_id"],
            condition_name=data.get("condition_name"),
        )


@dataclass(init=False)
class SwitchCaseEdgeGroupDefault:
    """Persistable descriptor for the fallback branch of a switch-case group."""

    target_id: str
    type: str

    def __init__(self, target_id: str) -> None:
        """Point the default branch toward the given executor identifier."""
        if not target_id:
            msg = "SwitchCaseEdgeGroupDefault requires a target_id"
            raise ValueError(msg)
        self.target_id = target_id
        self.type = "Default"

    def to_dict(self) -> dict[str, Any]:
        """Serialise the default branch metadata for persistence or logging."""
        return {"target_id": self.target_id, "type": self.type}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SwitchCaseEdgeGroupDefault:
        """Recreate the default branch from its persisted form."""
        return cls(target_id=data["target_id"])


@EdgeGroup.register
@dataclass(init=False)
class SwitchCaseEdgeGroup(FanOutEdgeGroup):
    """Fan-out variant that mimics a traditional switch/case control flow."""

    cases: list[SwitchCaseEdgeGroupCase | SwitchCaseEdgeGroupDefault]

    def __init__(
        self,
        source_id: str,
        cases: Sequence[SwitchCaseEdgeGroupCase | SwitchCaseEdgeGroupDefault],
        *,
        id: str | None = None,
    ) -> None:
        """Configure a switch/case routing structure for a single source executor."""
        if len(cases) < 2:
            msg = "SwitchCaseEdgeGroup must contain at least two cases (including the default case)."
            raise ValueError(msg)

        default_cases = [
            case for case in cases if isinstance(case, SwitchCaseEdgeGroupDefault)
        ]
        if len(default_cases) != 1:
            msg = "SwitchCaseEdgeGroup must contain exactly one default case."
            raise ValueError(msg)

        if not isinstance(cases[-1], SwitchCaseEdgeGroupDefault):
            logger.warning(
                "Default case in the switch-case edge group is not the last case. "
                "This may result in unexpected behavior."
            )

        def selection_func(message: Any, targets: list[str]) -> list[str]:
            for case in cases:
                if isinstance(case, SwitchCaseEdgeGroupDefault):
                    return [case.target_id]
                try:
                    if case.condition(message):
                        return [case.target_id]
                except Exception as exc:
                    logger.warning(
                        "Error evaluating condition for case %s: %s",
                        case.target_id,
                        exc,
                    )
            msg = "No matching case found in SwitchCaseEdgeGroup"
            raise RuntimeError(msg)

        target_ids = [case.target_id for case in cases]
        # Call FanOutEdgeGroup constructor directly to avoid type checking issues
        edges = [Edge(source_id=source_id, target_id=target) for target in target_ids]
        EdgeGroup.__init__(self, edges, id=id, type=self.__class__.__name__)

        # Initialize FanOutEdgeGroup-specific attributes
        self._target_ids = list(target_ids)
        self._selection_func = selection_func
        self.selection_func_name = None
        self.cases = list(cases)

    def to_dict(self) -> dict[str, Any]:
        """Serialise the switch-case group, capturing all case descriptors."""
        payload = super().to_dict()
        payload["cases"] = [case.to_dict() for case in self.cases]
        return payload


# Export all edge components
__all__ = [
    "Case",
    "Default",
    "Edge",
    "EdgeGroup",
    "FanInEdgeGroup",
    "FanOutEdgeGroup",
    "SingleEdgeGroup",
    "SwitchCaseEdgeGroup",
    "SwitchCaseEdgeGroupCase",
    "SwitchCaseEdgeGroupDefault",
    "_extract_function_name",
    "_missing_callable",
]
