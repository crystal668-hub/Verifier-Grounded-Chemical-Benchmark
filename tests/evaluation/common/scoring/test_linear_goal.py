from __future__ import annotations

import math

import pytest

from verifier_grounded_benchmark.evaluation.common.scoring.linear_goal import (
    LinearGoalSpec,
    linear_goal_distance,
    score,
)


def test_two_sided_region_has_exact_boundary_scores() -> None:
    region = LinearGoalSpec(lower=2.0, upper=4.0, lower_width=2.0, upper_width=4.0)

    assert score(0.0, region) == 0.0
    assert score(2.0, region) == 1.0
    assert score(4.0, region) == 1.0
    assert score(8.0, region) == 0.0


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0.5, 0.25),
        (1.0, 0.5),
        (1.5, 0.75),
        (5.0, 0.75),
        (6.0, 0.5),
        (7.0, 0.25),
    ],
)
def test_two_sided_region_has_linear_decay_points(value: float, expected: float) -> None:
    region = LinearGoalSpec(lower=2.0, upper=4.0, lower_width=2.0, upper_width=4.0)

    assert score(value, region) == expected


def test_window_scores_every_point_in_full_score_region_as_one() -> None:
    region = LinearGoalSpec(lower=-3.0, upper=0.0, lower_width=1.0, upper_width=2.0)

    assert score(-2.25, region) == 1.0


def test_maximize_saturates_at_and_above_target() -> None:
    region = LinearGoalSpec(lower=-2.0, upper=None, lower_width=4.0, upper_width=None)

    assert score(-6.0, region) == 0.0
    assert score(-4.0, region) == 0.5
    assert score(-2.0, region) == 1.0
    assert score(0.0, region) == 1.0
    assert score(100.0, region) == 1.0


def test_minimize_saturates_at_and_below_target() -> None:
    region = LinearGoalSpec(lower=None, upper=0.0, lower_width=None, upper_width=2.0)

    assert score(-100.0, region) == 1.0
    assert score(0.0, region) == 1.0
    assert score(1.0, region) == 0.5
    assert score(2.0, region) == 0.0


def test_target_and_numeric_gold_shape_support_asymmetric_widths() -> None:
    region = LinearGoalSpec(lower=3.0, upper=3.0, lower_width=2.0, upper_width=4.0)

    assert score(1.0, region) == 0.0
    assert score(2.0, region) == 0.5
    assert score(3.0, region) == 1.0
    assert score(5.0, region) == 0.5
    assert score(7.0, region) == 0.0


@pytest.mark.parametrize("target", [-5.0, 0.0, 5.0])
def test_target_is_sign_independent(target: float) -> None:
    region = LinearGoalSpec(
        lower=target,
        upper=target,
        lower_width=2.0,
        upper_width=2.0,
    )

    assert score(target - 1.0, region) == 0.5
    assert score(target, region) == 1.0
    assert score(target + 1.0, region) == 0.5


def test_consistent_unit_conversion_does_not_change_score() -> None:
    electron_volts = LinearGoalSpec(lower=2.0, upper=4.0, lower_width=1.0, upper_width=2.0)
    millielectron_volts = LinearGoalSpec(
        lower=2000.0,
        upper=4000.0,
        lower_width=1000.0,
        upper_width=2000.0,
    )

    assert score(5000.0, millielectron_volts) == score(5.0, electron_volts)


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf, True, "1"])
def test_score_rejects_non_finite_or_non_numeric_values(value: object) -> None:
    region = LinearGoalSpec(lower=0.0, upper=1.0, lower_width=1.0, upper_width=1.0)

    with pytest.raises(ValueError, match="value must be a finite number"):
        score(value, region)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"lower": None, "upper": None, "lower_width": None, "upper_width": None},
        {"lower": 2.0, "upper": 1.0, "lower_width": 1.0, "upper_width": 1.0},
        {"lower": math.nan, "upper": 1.0, "lower_width": 1.0, "upper_width": 1.0},
        {"lower": 0.0, "upper": math.inf, "lower_width": 1.0, "upper_width": 1.0},
        {"lower": 0.0, "upper": 1.0, "lower_width": 0.0, "upper_width": 1.0},
        {"lower": 0.0, "upper": 1.0, "lower_width": 1.0, "upper_width": -1.0},
        {"lower": None, "upper": 1.0, "lower_width": 1.0, "upper_width": 1.0},
        {"lower": 0.0, "upper": None, "lower_width": 1.0, "upper_width": 1.0},
    ],
)
def test_region_rejects_invalid_parameters(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        LinearGoalSpec(**kwargs)  # type: ignore[arg-type]


def test_inactive_decay_side_rejects_out_of_domain_value() -> None:
    region = LinearGoalSpec(lower=0.0, upper=20.0, lower_width=None, upper_width=10.0)

    assert score(10.0, region) == 1.0
    with pytest.raises(ValueError, match="inactive lower decay side"):
        score(-1.0, region)


def test_named_kernel_entry_point_uses_same_formula() -> None:
    region = LinearGoalSpec(lower=1.0, upper=None, lower_width=1.0, upper_width=None)

    assert linear_goal_distance(0.5, region) == score(0.5, region)
