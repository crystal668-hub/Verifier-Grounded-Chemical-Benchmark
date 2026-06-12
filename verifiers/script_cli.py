"""Shared CLI wrapper for property-level verifier scripts."""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from typing import Any

from verifiers.result_schema import base_result, error_result

Evaluator = Callable[[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]], dict[str, Any]]


def run_property_script(
    *,
    expected_name: str,
    spec_field: str,
    mismatch_label: str,
    evaluator: Evaluator,
    sort_keys: bool = True,
) -> None:
    payload: dict[str, Any] = json.load(sys.stdin)
    task = payload.get("task", {})
    constraint = payload.get("constraint", {})
    spec = payload.get("verifier_spec", {})
    candidate = payload.get("candidate", {})

    actual_name = spec.get(spec_field)
    if actual_name != expected_name:
        result = error_result(
            base_result(
                task.get("task_id"),
                spec.get("verifier_id"),
                {"verifier_image": spec.get("verifier_image")},
            ),
            "verifier_spec_error",
            f"script {mismatch_label} {expected_name!r} does not match verifier_spec {mismatch_label} {actual_name!r}",
        )
    else:
        result = evaluator(candidate, task, constraint, spec)

    json.dump(result, sys.stdout, sort_keys=sort_keys)
