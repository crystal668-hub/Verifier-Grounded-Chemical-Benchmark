"""Shared CLI helper for MACE material property verifier scripts."""

from __future__ import annotations

import json
import sys
from typing import Any

from verifiers.backends.mace_properties import evaluate_mace_property_constraint


def main(property_name: str) -> None:
    payload: dict[str, Any] = json.load(sys.stdin)
    spec = payload.get("verifier_spec", {})
    if spec.get("property_name") != property_name:
        task = payload.get("task", {})
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
        result = evaluate_mace_property_constraint(
            payload.get("candidate", {}),
            payload.get("task", {}),
            payload.get("constraint", {}),
            spec,
        )
    json.dump(result, sys.stdout, sort_keys=True)

