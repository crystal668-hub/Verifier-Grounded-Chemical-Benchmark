"""RDKit verifier for deterministic small-molecule property tasks."""

from __future__ import annotations

from typing import Any

from verifiers.backends.rdkit_descriptors import clamp, evaluate_candidate, geometric_mean, score_constraint


def evaluate_answer(answer: dict[str, Any], task: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    candidates = answer.get("candidates")
    if not candidates:
        return evaluate_candidate({}, task, spec)
    candidate = candidates[0] if isinstance(candidates[0], dict) else {}
    return evaluate_candidate(candidate, task, spec)
