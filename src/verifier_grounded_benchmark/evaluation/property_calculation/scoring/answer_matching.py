"""Answer matching policies for property-calculation tasks."""

from __future__ import annotations

from collections.abc import Mapping
from itertools import permutations
from typing import Any

from verifier_grounded_benchmark.evaluation.common.scoring.aggregation import (
    arithmetic_mean,
)
from verifier_grounded_benchmark.evaluation.property_calculation.scoring.numeric_gold import (
    score_numeric_gold,
)


def match_unordered_numeric_answers(
    submitted: dict[str, dict[str, Any]],
    property_names: list[str],
    gold: dict[str, dict[str, Any]],
    profiles: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Assign submitted values to gold properties using the highest mean score."""

    best_score = -1.0
    best_match: dict[str, dict[str, Any]] = {}
    for submitted_order in permutations(property_names):
        matched = {
            gold_name: submitted[submitted_name]
            for gold_name, submitted_name in zip(
                property_names, submitted_order, strict=True
            )
            if submitted_name in submitted
        }
        scores = []
        for property_name in property_names:
            gold_definition = gold[property_name]
            profile = profiles[gold_definition["scoring_profile"]]
            scores.append(
                score_numeric_gold(matched.get(property_name), gold_definition, profile)
            )
        assignment_score = arithmetic_mean(scores)
        if assignment_score > best_score:
            best_score = assignment_score
            best_match = matched
    return best_match
