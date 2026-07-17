"""Constraint dispatch and open-generation task aggregation."""

from __future__ import annotations

from typing import Any, Mapping

from verifier_grounded_benchmark.evaluation.common.scoring.aggregation import geometric_mean
from verifier_grounded_benchmark.evaluation.open_generation.scoring.gates import gate_score
from verifier_grounded_benchmark.evaluation.open_generation.scoring.maximize import score_maximize
from verifier_grounded_benchmark.evaluation.open_generation.scoring.minimize import score_minimize
from verifier_grounded_benchmark.evaluation.open_generation.scoring.target import score_target
from verifier_grounded_benchmark.evaluation.open_generation.scoring.window import score_window


SCORERS = {
    "target": score_target,
    "window": score_window,
    "maximize": score_maximize,
    "minimize": score_minimize,
}


def score_constraint_value(value: float, profile: Mapping[str, Any]) -> float:
    try:
        scorer = SCORERS[str(profile["type"])]
    except KeyError as exc:
        raise ValueError(f"unsupported open-generation profile type: {profile.get('type')}") from exc
    return scorer(value, profile)


def score_open_generation_task(
    constraint_scores: list[Mapping[str, Any]], *, hard_gate: float = 1.0
) -> dict[str, float]:
    main = [float(item["score"]) for item in constraint_scores if item["role"] == "main"]
    quality = [float(item["score"]) for item in constraint_scores if item["role"] == "quality_gate"]
    stability = [float(item["score"]) for item in constraint_scores if item["role"] == "stability_gate"]
    if not main:
        raise ValueError("open-generation task requires at least one main constraint")
    property_score = geometric_mean(main)
    quality_score = gate_score(quality)
    stability_score = gate_score(stability)
    return {
        "property_score": property_score,
        "geometry_quality_score": quality_score,
        "stability_gate_score": stability_score,
        "score": hard_gate * property_score * quality_score * stability_score,
    }
