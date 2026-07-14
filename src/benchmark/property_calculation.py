"""Gold-answer evaluation for fixed-input property-calculation tasks."""

from __future__ import annotations

import math
from typing import Any


class TaskSchemaError(ValueError):
    pass


class AnswerShapeError(ValueError):
    pass


def evaluate_property_calculation(
    answer: dict[str, Any],
    task: dict[str, Any],
) -> dict[str, Any]:
    task_id = str(task.get("task_id"))
    try:
        requested, gold, groups = _validate_task(task)
    except TaskSchemaError as exc:
        return _error_result(task_id, "task_error", str(exc))

    try:
        submitted = _submitted_answers(answer, requested)
    except AnswerShapeError as exc:
        return _error_result(task_id, "parse_error", str(exc))

    property_scores = {
        name: _property_score(submitted.get(name), requested[name], gold[name])
        for name in requested
    }
    constraint_scores: list[dict[str, Any]] = []
    for group_id in groups:
        members = [
            name
            for name, definition in requested.items()
            if definition["comparison_group"] == group_id
        ]
        score = float(all(property_scores[name] == 1.0 for name in members))
        comparison_type = (
            "absolute_tolerance"
            if all(requested[name]["value_type"] == "number" for name in members)
            else "exact_mapping"
        )
        constraint_scores.append(
            {
                "property": group_id,
                "type": comparison_type,
                "score": score,
            }
        )

    property_score = sum(item["score"] for item in constraint_scores) / len(
        constraint_scores
    )
    return {
        "task_id": task_id,
        "status": "ok",
        "canonical_smiles": None,
        "properties": {
            "submitted_answers": submitted,
            "gold_answers": {
                name: {
                    "value": definition["value"],
                    **(
                        {"unit": definition["unit"]}
                        if "unit" in definition
                        else {}
                    ),
                }
                for name, definition in gold.items()
            },
        },
        "scores": {
            "validity_gate": 1.0,
            "domain_gate": 1.0,
            "constraint_scores": constraint_scores,
            "property_score": property_score,
            "score": property_score,
        },
        "failure_type": None,
        "message": None,
        "versions": {"property_calculation_evaluator": 1},
    }


def _validate_task(
    task: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], list[str]]:
    requested_items = task.get("requested_properties")
    gold_items = task.get("gold_answers")
    scoring = task.get("scoring")
    if not isinstance(requested_items, list) or not requested_items:
        raise TaskSchemaError("requested_properties must be a non-empty list")
    if not isinstance(gold_items, list) or not gold_items:
        raise TaskSchemaError("gold_answers must be a non-empty list")
    if not isinstance(scoring, dict):
        raise TaskSchemaError("scoring must be an object")
    if scoring.get("aggregation") != "arithmetic_mean":
        raise TaskSchemaError("property calculation aggregation must be arithmetic_mean")

    requested = _index_items(requested_items, "name", "requested property")
    gold = _index_items(gold_items, "property", "gold property")
    if set(requested) != set(gold):
        raise TaskSchemaError("requested and gold property names must match")

    group_items = scoring.get("comparison_groups")
    if not isinstance(group_items, list) or not group_items:
        raise TaskSchemaError("comparison_groups must be a non-empty list")
    groups_by_id = _index_items(group_items, "id", "comparison group")
    for group_id, group in groups_by_id.items():
        if group.get("mode") != "all":
            raise TaskSchemaError(f"comparison group {group_id} must use mode all")

    for name, definition in requested.items():
        value_type = definition.get("value_type")
        if value_type not in {"number", "string"}:
            raise TaskSchemaError(f"unsupported value_type for {name}: {value_type}")
        group_id = definition.get("comparison_group")
        if group_id not in groups_by_id:
            raise TaskSchemaError(f"unknown comparison group for {name}: {group_id}")
        gold_definition = gold[name]
        if value_type == "number":
            unit = definition.get("unit")
            if not isinstance(unit, str) or not unit:
                raise TaskSchemaError(f"numeric property {name} requires a unit")
            if gold_definition.get("unit") != unit:
                raise TaskSchemaError(f"gold unit does not match requested unit for {name}")
            tolerance = gold_definition.get("absolute_tolerance")
            if not _finite_number(tolerance) or float(tolerance) <= 0:
                raise TaskSchemaError(f"numeric property {name} requires positive tolerance")
            if not _finite_number(gold_definition.get("value")):
                raise TaskSchemaError(f"numeric property {name} requires finite gold value")
        elif not isinstance(gold_definition.get("value"), str):
            raise TaskSchemaError(f"string property {name} requires string gold value")

    used_groups = {definition["comparison_group"] for definition in requested.values()}
    if used_groups != set(groups_by_id):
        raise TaskSchemaError("comparison groups must match requested property groups")
    return requested, gold, list(groups_by_id)


def _index_items(
    items: list[Any],
    key: str,
    label: str,
) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict):
            raise TaskSchemaError(f"{label} entries must be objects")
        item_id = item.get(key)
        if not isinstance(item_id, str) or not item_id:
            raise TaskSchemaError(f"{label} entries require {key}")
        if item_id in indexed:
            raise TaskSchemaError(f"duplicate {label}: {item_id}")
        indexed[item_id] = item
    return indexed


def _submitted_answers(
    answer: dict[str, Any],
    requested: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    if len(requested) == 1 and "answers" not in answer:
        name = next(iter(requested))
        if "answer" not in answer and "unit" not in answer:
            return {}
        submitted: dict[str, Any] = {}
        if "answer" in answer:
            submitted["value"] = answer["answer"]
        if "unit" in answer:
            submitted["unit"] = answer["unit"]
        return {name: submitted}

    items = answer.get("answers")
    if items is None:
        return {}
    if not isinstance(items, list):
        raise AnswerShapeError("answers must be a list")
    submitted_by_name: dict[str, dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict):
            raise AnswerShapeError("answer entries must be objects")
        name = item.get("property")
        if not isinstance(name, str) or not name:
            raise AnswerShapeError("answer entries require a property string")
        if name in submitted_by_name:
            raise AnswerShapeError(f"duplicate property in answer: {name}")
        if name not in requested:
            continue
        submitted_by_name[name] = {
            **({"value": item["value"]} if "value" in item else {}),
            **({"unit": item["unit"]} if "unit" in item else {}),
        }
    return submitted_by_name


def _property_score(
    submitted: dict[str, Any] | None,
    requested: dict[str, Any],
    gold: dict[str, Any],
) -> float:
    if submitted is None:
        return 0.0
    value = submitted.get("value")
    if requested["value_type"] == "string":
        return float(isinstance(value, str) and value == gold["value"])
    if not _finite_number(value) or submitted.get("unit") != requested["unit"]:
        return 0.0
    error = abs(float(value) - float(gold["value"]))
    tolerance = float(gold["absolute_tolerance"])
    return float(error <= tolerance or math.isclose(error, tolerance, abs_tol=1e-12))


def _finite_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _error_result(task_id: str, failure_type: str, message: str) -> dict[str, Any]:
    return {
        "task_id": task_id,
        "status": "error",
        "canonical_smiles": None,
        "properties": {},
        "scores": {
            "validity_gate": 0.0,
            "domain_gate": 0.0,
            "constraint_scores": [],
            "property_score": 0.0,
            "score": 0.0,
        },
        "failure_type": failure_type,
        "message": message,
        "versions": {"property_calculation_evaluator": 1},
    }
