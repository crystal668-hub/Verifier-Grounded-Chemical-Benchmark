"""Comparison group aggregation."""

from itertools import permutations
from typing import Any

from verifier_grounded_benchmark.evaluation.common.scoring.aggregation import minimum
from verifier_grounded_benchmark.evaluation.property_calculation.scoring.numeric_gold import (
    score_numeric_gold,
)


def score_comparison_group(field_scores: list[float]) -> float:
    return minimum(field_scores)


def score_unordered_numeric_group(
    submitted: dict[str, dict[str, Any]],
    members: list[str],
    gold: dict[str, dict[str, Any]],
    profiles: dict[str, dict[str, Any]],
) -> float:
    """Score numeric fields after the best one-to-one assignment to gold values."""

    assignment_scores: list[float] = []
    for gold_order in permutations(members):
        field_scores = []
        for submitted_name, gold_name in zip(members, gold_order, strict=True):
            gold_definition = gold[gold_name]
            profile = profiles[gold_definition["scoring_profile"]]
            field_scores.append(
                score_numeric_gold(submitted.get(submitted_name), gold_definition, profile)
            )
        assignment_scores.append(score_comparison_group(field_scores))
    return max(assignment_scores)
