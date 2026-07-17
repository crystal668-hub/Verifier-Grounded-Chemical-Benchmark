"""Immutable task-domain models created at the configuration boundary."""

from __future__ import annotations

import math
from dataclasses import dataclass
from numbers import Real
from types import MappingProxyType
from typing import Any, Mapping


@dataclass(frozen=True)
class LinearGoalSpec:
    lower: float | None
    upper: float | None
    lower_width: float | None
    upper_width: float | None

    def __post_init__(self) -> None:
        lower = _optional_finite_number(self.lower, "lower")
        upper = _optional_finite_number(self.upper, "upper")
        lower_width = _optional_positive_number(self.lower_width, "lower_width")
        upper_width = _optional_positive_number(self.upper_width, "upper_width")
        if lower is None and upper is None:
            raise ValueError("linear goal requires at least one full-score boundary")
        if lower is not None and upper is not None and lower > upper:
            raise ValueError("linear goal requires lower <= upper")
        if lower is None and lower_width is not None:
            raise ValueError("lower_width requires a lower boundary")
        if upper is None and upper_width is not None:
            raise ValueError("upper_width requires an upper boundary")
        object.__setattr__(self, "lower", lower)
        object.__setattr__(self, "upper", upper)
        object.__setattr__(self, "lower_width", lower_width)
        object.__setattr__(self, "upper_width", upper_width)


@dataclass(frozen=True)
class ConstraintSpec:
    property: str
    type: str
    role: str
    verifier_id: str
    scoring_profile: str


@dataclass(frozen=True)
class VerifierSpec:
    verifier_id: str
    raw: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self.raw)


@dataclass(frozen=True)
class TaskSpec:
    task_id: str
    task_type: str
    raw: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self.raw)


@dataclass(frozen=True)
class OpenGenerationTaskSpec(TaskSpec):
    constraints: tuple[ConstraintSpec, ...]


@dataclass(frozen=True)
class PropertyCalculationTaskSpec(TaskSpec):
    pass


@dataclass(frozen=True)
class TaskPack:
    schema_version: int
    pack_id: str
    version: str
    scoring_version: str
    tasks: tuple[TaskSpec, ...]
    verifier_specs: tuple[VerifierSpec, ...]
    scoring_profiles: Mapping[str, Mapping[str, Any]]

    @property
    def tasks_by_id(self) -> dict[str, dict[str, Any]]:
        return {task.task_id: task.to_dict() for task in self.tasks}

    @property
    def verifier_specs_by_id(self) -> dict[str, dict[str, Any]]:
        return {spec.verifier_id: spec.to_dict() for spec in self.verifier_specs}

    @classmethod
    def create(
        cls,
        *,
        schema_version: int,
        pack_id: str,
        version: str,
        scoring_version: str,
        tasks: list[TaskSpec],
        verifier_specs: list[VerifierSpec],
        scoring_profiles: Mapping[str, Mapping[str, Any]],
    ) -> TaskPack:
        return cls(
            schema_version=schema_version,
            pack_id=pack_id,
            version=version,
            scoring_version=scoring_version,
            tasks=tuple(tasks),
            verifier_specs=tuple(verifier_specs),
            scoring_profiles=_freeze(scoring_profiles),
        )


def freeze_mapping(value: Mapping[str, Any]) -> Mapping[str, Any]:
    return _freeze(value)


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def _finite_number(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{field} must be a finite number")
    numeric = float(value)
    if not math.isfinite(numeric):
        raise ValueError(f"{field} must be a finite number")
    return numeric


def _optional_finite_number(value: object, field: str) -> float | None:
    if value is None:
        return None
    return _finite_number(value, field)


def _optional_positive_number(value: object, field: str) -> float | None:
    if value is None:
        return None
    numeric = _finite_number(value, field)
    if numeric <= 0.0:
        raise ValueError(f"{field} must be positive")
    return numeric
