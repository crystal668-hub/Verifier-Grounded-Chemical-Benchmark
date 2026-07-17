"""Quality, stability, and hard-gate aggregation."""

from verifier_grounded_benchmark.evaluation.common.scoring.aggregation import minimum


def gate_score(scores: list[float]) -> float:
    return minimum(scores) if scores else 1.0
