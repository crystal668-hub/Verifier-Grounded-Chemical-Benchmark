"""Comparison group aggregation."""

from verifier_grounded_benchmark.evaluation.common.scoring.aggregation import minimum


def score_comparison_group(field_scores: list[float]) -> float:
    return minimum(field_scores)
