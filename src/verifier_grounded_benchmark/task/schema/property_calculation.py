"""Property Calculation task schema v2 validation."""

from __future__ import annotations

from typing import Any

from verifier_grounded_benchmark.task.schema.common import (
    index_unique,
    linear_goal_from_profile,
    require_list,
    require_mapping,
    require_string,
)


def validate_property_calculation_task(
    task: dict[str, Any], profiles: dict[str, dict[str, Any]]
) -> None:
    task_id = task["task_id"]
    requested = index_unique(
        require_list(task.get("requested_properties"), f"task {task_id} requested_properties"),
        "name",
        "requested property",
    )
    gold = index_unique(
        require_list(task.get("gold_answers"), f"task {task_id} gold_answers"),
        "property",
        "gold property",
    )
    if set(requested) != set(gold):
        raise ValueError(f"task {task_id} requested and gold properties must match")
    scoring = require_mapping(task.get("scoring"), f"task {task_id} scoring")
    if scoring.get("aggregation") != "arithmetic_mean":
        raise ValueError(f"task {task_id} must use arithmetic_mean")
    groups = index_unique(
        require_list(scoring.get("comparison_groups"), f"task {task_id} comparison_groups"),
        "id",
        "comparison group",
    )
    for group_id, group in groups.items():
        if group.get("mode") != "all":
            raise ValueError(f"comparison group {group_id} must use mode all")
    used_groups: set[str] = set()
    for property_name, definition in requested.items():
        value_type = definition.get("value_type")
        if value_type not in {"number", "string"}:
            raise ValueError(f"unsupported value_type for {property_name}: {value_type}")
        group_id = require_string(definition.get("comparison_group"), "comparison_group")
        if group_id not in groups:
            raise ValueError(f"unknown comparison group: {group_id}")
        used_groups.add(group_id)
        gold_definition = gold[property_name]
        profile_id = require_string(gold_definition.get("scoring_profile"), "gold scoring_profile")
        try:
            profile = profiles[profile_id]
        except KeyError as exc:
            raise ValueError(f"unknown scoring profile: {profile_id}") from exc
        if profile["property"] != property_name:
            raise ValueError(f"gold/profile property mismatch for {profile_id}")
        expected_type = "numeric_gold" if value_type == "number" else "exact_string"
        if profile["type"] != expected_type:
            raise ValueError(f"gold/profile type mismatch for {profile_id}")
        if value_type == "number":
            unit = require_string(definition.get("unit"), f"numeric property {property_name} unit")
            if gold_definition.get("unit") != unit or profile.get("unit") != unit:
                raise ValueError(f"unit mismatch for {property_name}")
            linear_goal_from_profile(profile, gold=gold_definition.get("value"))
        elif not isinstance(gold_definition.get("value"), str):
            raise ValueError(f"string gold {property_name} must be a string")
    if used_groups != set(groups):
        raise ValueError(f"task {task_id} comparison groups do not match requested fields")
