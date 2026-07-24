"""Result schema v2 construction helpers."""

from __future__ import annotations

from typing import Any

from verifier_grounded_benchmark.evaluation.common.failures import FailureScope


RESULT_SCHEMA_VERSION = "2"


def scored_result(
    *,
    task_id: str,
    properties: dict[str, Any],
    scores: dict[str, Any],
    versions: dict[str, Any],
    failure_scope: FailureScope | None = None,
    failure_type: str | None = None,
    message: str | None = None,
) -> dict[str, Any]:
    score = scores.get("score")
    if not isinstance(score, (int, float)) or isinstance(score, bool) or not 0.0 <= float(score) <= 1.0:
        raise ValueError("scored result requires a score in [0, 1]")
    return {
        "schema_version": 2,
        "task_id": task_id,
        "status": "scored",
        "failure_scope": failure_scope,
        "failure_type": failure_type,
        "message": message,
        "canonical_smiles": None,
        "properties": properties,
        "scores": scores,
        "versions": {**versions, "result_schema": RESULT_SCHEMA_VERSION},
    }


def error_result(
    *,
    task_id: str | None,
    failure_scope: FailureScope,
    failure_type: str,
    message: str,
    versions: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": 2,
        "task_id": task_id,
        "status": "error",
        "failure_scope": failure_scope,
        "failure_type": failure_type,
        "message": message,
        "canonical_smiles": None,
        "properties": {},
        "scores": {
            "validity_gate": None,
            "domain_gate": None,
            "identity_gate": None,
            "constraint_scores": [],
            "property_score": None,
            "geometry_quality_score": None,
            "score": None,
        },
        "versions": {**versions, "result_schema": RESULT_SCHEMA_VERSION},
    }
