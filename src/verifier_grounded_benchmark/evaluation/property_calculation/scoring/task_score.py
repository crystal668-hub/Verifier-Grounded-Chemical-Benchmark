"""Property Calculation task aggregation."""

from verifier_grounded_benchmark.evaluation.common.scoring.aggregation import (
    arithmetic_mean,
)


def score_task(field_scores: list[float]) -> float:
    return arithmetic_mean(field_scores)
