from __future__ import annotations

import pytest

from verifier_grounded_benchmark.evaluation.open_generation.scoring.task_score import (
    score_open_generation_task,
)


def test_two_main_constraints_use_equal_weight_geometric_mean() -> None:
    scores = score_open_generation_task(
        [
            {"role": "main", "score": 0.8},
            {"role": "main", "score": 0.5},
        ]
    )

    assert scores["property_score"] == pytest.approx((0.8 * 0.5) ** 0.5)
    assert scores["score"] == scores["property_score"]


def test_zero_main_constraint_makes_property_score_zero() -> None:
    scores = score_open_generation_task(
        [
            {"role": "main", "score": 1.0},
            {"role": "main", "score": 0.0},
        ]
    )

    assert scores["property_score"] == 0.0
    assert scores["score"] == 0.0


def test_quality_gates_use_minimum_then_multiply() -> None:
    scores = score_open_generation_task(
        [
            {"role": "main", "score": 0.8},
            {"role": "quality_gate", "score": 0.75},
            {"role": "quality_gate", "score": 0.5},
        ]
    )

    assert scores["geometry_quality_score"] == 0.5
    assert "stability_gate_score" not in scores
    assert scores["score"] == pytest.approx(0.4)


def test_hard_gate_multiplies_task_score() -> None:
    scores = score_open_generation_task(
        [{"role": "main", "score": 1.0}], hard_gate=0.0
    )

    assert scores["score"] == 0.0
