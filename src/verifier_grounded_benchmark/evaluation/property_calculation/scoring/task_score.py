"""Property Calculation task aggregation."""

from collections.abc import Mapping, Sequence
from typing import cast

from verifier_grounded_benchmark.evaluation.common.scoring.aggregation import (
    arithmetic_mean,
)


def score_task(
    field_scores: Mapping[str, float],
    comparison_groups: Sequence[Mapping[str, object]] | None = None,
) -> tuple[float, list[dict[str, object]]]:
    if comparison_groups is None:
        return arithmetic_mean(list(field_scores.values())), []

    group_scores: list[dict[str, object]] = []
    for group in comparison_groups:
        properties = list(cast(Sequence[str], group["properties"]))
        member_scores = [field_scores[name] for name in properties]
        score = (
            float(all(member_score == 1.0 for member_score in member_scores))
            if group["aggregation"] == "all_correct"
            else arithmetic_mean(member_scores)
        )
        group_scores.append(
            {
                "group": group["id"],
                "aggregation": group["aggregation"],
                "properties": properties,
                "score": score,
            }
        )
    return arithmetic_mean([float(group["score"]) for group in group_scores]), group_scores
