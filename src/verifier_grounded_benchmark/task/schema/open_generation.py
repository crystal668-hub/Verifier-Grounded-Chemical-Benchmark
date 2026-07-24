"""Open-generation task schema v2 validation."""

from __future__ import annotations

import math
from typing import Any

from verifier_grounded_benchmark.task.models import ConstraintSpec, HardConstraintSpec
from verifier_grounded_benchmark.task.schema.common import (
    linear_goal_from_profile,
    require_list,
    require_mapping,
    require_string,
)


OPEN_GENERATION_TYPES = {"target", "window", "maximize", "minimize"}
ROLES = {"main", "quality_gate"}
HARD_CONSTRAINT_OPERATORS = {"lt", "le", "closed_window"}


def validate_open_generation_task(
    task: dict[str, Any],
    profiles: dict[str, dict[str, Any]],
    verifier_ids: set[str],
) -> tuple[tuple[ConstraintSpec, ...], tuple[HardConstraintSpec, ...]]:
    constraints: list[ConstraintSpec] = []
    for raw in require_list(task.get("constraints"), f"task {task['task_id']} constraints"):
        constraint = require_mapping(raw, "constraint")
        constraint_type = require_string(constraint.get("type"), "constraint type")
        if constraint_type not in OPEN_GENERATION_TYPES:
            raise ValueError(f"unsupported open-generation constraint type: {constraint_type}")
        property_name = require_string(constraint.get("property"), "constraint property")
        verifier_id = require_string(constraint.get("verifier_id"), "constraint verifier_id")
        if verifier_id not in verifier_ids:
            raise ValueError(f"unknown verifier_id: {verifier_id}")
        role = constraint.get("role", "main")
        if role not in ROLES:
            raise ValueError(f"unsupported constraint role: {role}")
        profile_id = require_string(constraint.get("scoring_profile"), "constraint scoring_profile")
        try:
            profile = profiles[profile_id]
        except KeyError as exc:
            raise ValueError(f"unknown scoring profile: {profile_id}") from exc
        if profile["type"] != constraint_type:
            raise ValueError(f"constraint/profile type mismatch for {profile_id}")
        if profile["property"] != property_name:
            raise ValueError(f"constraint/profile property mismatch for {profile_id}")
        linear_goal_from_profile(profile)
        constraints.append(ConstraintSpec(property_name, constraint_type, role, verifier_id, profile_id))
    hard_constraints: list[HardConstraintSpec] = []
    raw_hard_constraints = task.get("hard_constraints")
    hard_items = (
        []
        if raw_hard_constraints is None
        else require_list(
            raw_hard_constraints, f"task {task['task_id']} hard_constraints"
        )
    )
    for raw in hard_items:
        hard = require_mapping(raw, "hard constraint")
        property_name = require_string(hard.get("property"), "hard constraint property")
        verifier_id = require_string(hard.get("verifier_id"), "hard constraint verifier_id")
        if verifier_id not in verifier_ids:
            raise ValueError(f"unknown verifier_id: {verifier_id}")
        operator = require_string(hard.get("operator"), "hard constraint operator")
        if operator not in HARD_CONSTRAINT_OPERATORS:
            raise ValueError(f"unsupported hard constraint operator: {operator}")
        threshold = lower = upper = None
        if operator in {"lt", "le"}:
            threshold = _finite_number(hard.get("threshold"), "hard constraint threshold")
            if "lower" in hard or "upper" in hard:
                raise ValueError(f"hard constraint operator {operator} does not accept lower/upper")
        else:
            lower = _finite_number(hard.get("lower"), "hard constraint lower")
            upper = _finite_number(hard.get("upper"), "hard constraint upper")
            if lower > upper:
                raise ValueError("closed_window hard constraint requires lower <= upper")
            if "threshold" in hard:
                raise ValueError("closed_window hard constraint does not accept threshold")
        hard_constraints.append(
            HardConstraintSpec(property_name, verifier_id, operator, threshold, lower, upper)
        )
    return tuple(constraints), tuple(hard_constraints)


def _finite_number(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a finite number")
    numeric = float(value)
    if not math.isfinite(numeric):
        raise ValueError(f"{field} must be a finite number")
    return numeric
