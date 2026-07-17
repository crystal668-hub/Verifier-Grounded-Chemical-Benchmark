from __future__ import annotations

import math

import pytest

from verifier_grounded_benchmark.evaluation.common.scoring.aggregation import (
    arithmetic_mean,
    geometric_mean,
    minimum,
)


def test_arithmetic_mean_aggregates_task_scores() -> None:
    assert arithmetic_mean([0.25, 0.75]) == 0.5


def test_geometric_mean_preserves_single_score() -> None:
    assert geometric_mean([0.25]) == 0.25


def test_geometric_mean_aggregates_main_constraint_scores() -> None:
    assert geometric_mean([1.0, 0.25]) == 0.5


def test_geometric_mean_is_zero_if_any_constraint_is_zero() -> None:
    assert geometric_mean([1.0, 0.0, 0.5]) == 0.0


def test_minimum_aggregates_group_and_gate_scores() -> None:
    assert minimum([0.75, 0.25, 0.5]) == 0.25


@pytest.mark.parametrize("aggregate", [arithmetic_mean, geometric_mean, minimum])
def test_aggregation_rejects_empty_values(aggregate: object) -> None:
    with pytest.raises(ValueError, match="at least one score"):
        aggregate([])  # type: ignore[operator]


@pytest.mark.parametrize("invalid", [-0.1, 1.1, math.nan, math.inf, True, "0.5"])
@pytest.mark.parametrize("aggregate", [arithmetic_mean, geometric_mean, minimum])
def test_aggregation_rejects_invalid_scores(aggregate: object, invalid: object) -> None:
    with pytest.raises(ValueError, match=r"finite numbers in \[0, 1\]"):
        aggregate([invalid])  # type: ignore[operator]
