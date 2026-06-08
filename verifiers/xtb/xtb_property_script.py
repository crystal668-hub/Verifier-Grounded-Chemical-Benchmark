"""Shared CLI helper for xTB direct-XYZ property verifier scripts."""

from __future__ import annotations

import json
import sys
from typing import Any

from verifiers.backends.xtb_properties import evaluate_xtb_property_constraint


def main(property_name: str) -> None:
    payload: dict[str, Any] = json.loads(sys.stdin.read())
    task = payload.get("task", {})
    constraint = payload.get("constraint", {})
    spec = payload.get("verifier_spec", {})
    candidate = payload.get("candidate", {})
    if spec.get("property_name") != property_name:
        result = {
            "task_id": task.get("task_id"),
            "verifier_id": spec.get("verifier_id"),
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
            "failure_type": "verifier_spec_error",
            "message": f"script property {property_name!r} does not match verifier_spec property {spec.get('property_name')!r}",
            "versions": {"verifier_image": spec.get("verifier_image")},
        }
    else:
        result = evaluate_xtb_property_constraint(candidate, task, constraint, spec)
    json.dump(result, sys.stdout)


__all__ = ["main"]
