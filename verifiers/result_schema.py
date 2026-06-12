"""Shared result helpers for property-level verifier backends."""

from __future__ import annotations

from typing import Any


def base_result(
    task_id: str,
    verifier_id: Any,
    versions: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "task_id": task_id,
        "verifier_id": verifier_id,
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
        "failure_type": None,
        "message": None,
        "versions": dict(versions or {}),
    }


def error_result(
    result: dict[str, Any],
    failure_type: str,
    message: str,
    *,
    properties: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result["failure_type"] = failure_type
    result["message"] = message
    if properties is not None:
        result["properties"] = properties
        result["scores"]["validity_gate"] = 1.0
    if failure_type == "domain_error":
        result["scores"]["validity_gate"] = 1.0
    return result
