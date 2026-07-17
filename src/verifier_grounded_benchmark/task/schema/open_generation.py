"""Open-generation task schema v2 validation."""

from __future__ import annotations

from typing import Any

from verifier_grounded_benchmark.task.models import ConstraintSpec
from verifier_grounded_benchmark.task.schema.common import (
    linear_goal_from_profile,
    require_list,
    require_mapping,
    require_string,
)


OPEN_GENERATION_TYPES = {"target", "window", "maximize", "minimize"}
ROLES = {"main", "quality_gate", "stability_gate"}


def validate_open_generation_task(
    task: dict[str, Any],
    profiles: dict[str, dict[str, Any]],
    verifier_ids: set[str],
) -> tuple[ConstraintSpec, ...]:
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
    return tuple(constraints)
