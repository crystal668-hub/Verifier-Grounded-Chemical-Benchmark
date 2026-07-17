"""Canonical linear distance scoring for continuous numeric goals."""

from __future__ import annotations

import math
from dataclasses import dataclass
from numbers import Real


@dataclass(frozen=True)
class LinearGoalSpec:
    """Full-score region and optional linear decay widths on either side."""

    lower: float | None
    upper: float | None
    lower_width: float | None
    upper_width: float | None

    def __post_init__(self) -> None:
        lower = _optional_finite_number(self.lower, "lower")
        upper = _optional_finite_number(self.upper, "upper")
        lower_width = _optional_positive_number(self.lower_width, "lower_width")
        upper_width = _optional_positive_number(self.upper_width, "upper_width")

        if lower is None and upper is None:
            raise ValueError("linear goal requires at least one full-score boundary")
        if lower is not None and upper is not None and lower > upper:
            raise ValueError("linear goal requires lower <= upper")
        if lower is None and lower_width is not None:
            raise ValueError("lower_width requires a lower boundary")
        if upper is None and upper_width is not None:
            raise ValueError("upper_width requires an upper boundary")

        object.__setattr__(self, "lower", lower)
        object.__setattr__(self, "upper", upper)
        object.__setattr__(self, "lower_width", lower_width)
        object.__setattr__(self, "upper_width", upper_width)


def score(value: float, region: LinearGoalSpec) -> float:
    """Score a finite value against a canonical full-score region."""

    numeric_value = _finite_number(value, "value")

    if region.lower is not None and numeric_value < region.lower:
        if region.lower_width is None:
            raise ValueError("value violates the inactive lower decay side")
        violation = (region.lower - numeric_value) / region.lower_width
        return _clip_unit_interval(1.0 - violation)

    if region.upper is not None and numeric_value > region.upper:
        if region.upper_width is None:
            raise ValueError("value violates the inactive upper decay side")
        violation = (numeric_value - region.upper) / region.upper_width
        return _clip_unit_interval(1.0 - violation)

    return 1.0


def linear_goal_distance(value: float, region: LinearGoalSpec) -> float:
    """Named entry point for the canonical linear goal distance kernel."""

    return score(value, region)


def _clip_unit_interval(value: float) -> float:
    return max(0.0, min(1.0, value))


def _finite_number(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{field} must be a finite number")
    numeric = float(value)
    if not math.isfinite(numeric):
        raise ValueError(f"{field} must be a finite number")
    return numeric


def _optional_finite_number(value: object, field: str) -> float | None:
    if value is None:
        return None
    return _finite_number(value, field)


def _optional_positive_number(value: object, field: str) -> float | None:
    if value is None:
        return None
    numeric = _finite_number(value, field)
    if numeric <= 0.0:
        raise ValueError(f"{field} must be positive")
    return numeric
