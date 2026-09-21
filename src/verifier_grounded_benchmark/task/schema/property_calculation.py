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
    """Validate requested fields, gold answers, domains, and scoring references without verifiers."""
    task_id = task["task_id"]
    requested = index_unique(
        require_list(
            task.get("requested_properties"), f"task {task_id} requested_properties"
        ),
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
    comparison_groups = scoring.get("comparison_groups")
    if comparison_groups is not None:
        groups = index_unique(
            require_list(
                comparison_groups, f"task {task_id} comparison_groups"
            ),
            "id",
            "comparison group",
        )
        grouped_properties: set[str] = set()
        for group_id, group in groups.items():
            if group.get("aggregation") not in {"arithmetic_mean", "all_correct"}:
                raise ValueError(
                    f"comparison group {group_id} must use arithmetic_mean or "
                    "all_correct aggregation"
                )
            properties = require_list(
                group.get("properties"),
                f"comparison group {group_id} properties",
            )
            for property_name in properties:
                property_name = require_string(
                    property_name, f"comparison group {group_id} property"
                )
                if property_name not in requested:
                    raise ValueError(
                        f"comparison group {group_id} has unknown property: "
                        f"{property_name}"
                    )
                if property_name in grouped_properties:
                    raise ValueError(
                        f"property {property_name} belongs to multiple comparison groups"
                    )
                grouped_properties.add(property_name)
        if grouped_properties != set(requested):
            raise ValueError(
                f"task {task_id} comparison groups must cover all requested properties"
            )
    answer_matching = scoring.get("answer_matching", "by_property")
    if answer_matching not in {"by_property", "unordered_numeric"}:
        raise ValueError(
            f"task {task_id} has unsupported answer_matching: {answer_matching}"
        )
    if answer_matching == "unordered_numeric" and len(requested) < 2:
        raise ValueError(
            f"task {task_id} unordered_numeric answer matching requires at least two properties"
        )
    for property_name, definition in requested.items():
        value_type = definition.get("value_type")
        if value_type not in {"number", "string"}:
            raise ValueError(
                f"unsupported value_type for {property_name}: {value_type}"
            )
        if answer_matching == "unordered_numeric" and value_type != "number":
            raise ValueError(
                f"task {task_id} unordered_numeric answer matching only supports numeric properties"
            )
        gold_definition = gold[property_name]
        profile_id = require_string(
            gold_definition.get("scoring_profile"), "gold scoring_profile"
        )
        try:
            profile = profiles[profile_id]
        except KeyError as exc:
            raise ValueError(f"unknown scoring profile: {profile_id}") from exc
        if profile["property"] != property_name:
            raise ValueError(f"gold/profile property mismatch for {profile_id}")
        expected_types = (
            {"numeric_gold"}
            if value_type == "number"
            else {"exact_string", "atom_identity"}
        )
        if profile["type"] not in expected_types:
            raise ValueError(f"gold/profile type mismatch for {profile_id}")
        if value_type == "number":
            unit = require_string(
                definition.get("unit"), f"numeric property {property_name} unit"
            )
            if gold_definition.get("unit") != unit or profile.get("unit") != unit:
                raise ValueError(f"unit mismatch for {property_name}")
            linear_goal_from_profile(profile, gold=gold_definition.get("value"))
            if (
                "minimum_value" in profile
                and gold_definition["value"] < profile["minimum_value"]
            ):
                raise ValueError(f"numeric gold {property_name} is below minimum_value")
        elif not isinstance(gold_definition.get("value"), str):
            raise ValueError(f"string gold {property_name} must be a string")
