"""Evidence result helpers shared by concrete verifier backends."""

from __future__ import annotations

from typing import Any


CANDIDATE_FAILURES = {
    "parse_error",
    "validity_error",
    "domain_error",
    "identity_error",
    "structure_identity_error",
}


def base_result(
    task_id: str,
    verifier_id: Any,
    versions: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "outcome": "evaluation_failed",
        "task_id": task_id,
        "verifier_id": verifier_id,
        "canonical_candidate": {},
        "properties": {},
        "diagnostics": {},
        "failure_scope": None,
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
    result["outcome"] = (
        "candidate_rejected" if failure_type in CANDIDATE_FAILURES else "evaluation_failed"
    )
    result["failure_scope"] = (
        "candidate"
        if failure_type in CANDIDATE_FAILURES
        else "task"
        if failure_type in {"task_error", "verifier_spec_error"}
        else "infrastructure"
    )
    result["failure_type"] = failure_type
    result["message"] = message
    if properties is not None:
        result["properties"] = properties
    return result


def verified_result(
    result: dict[str, Any],
    properties: dict[str, Any],
    *,
    canonical_candidate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result.update(
        {
            "outcome": "verified",
            "canonical_candidate": canonical_candidate or {},
            "properties": properties,
            "failure_scope": None,
            "failure_type": None,
            "message": None,
        }
    )
    return result
