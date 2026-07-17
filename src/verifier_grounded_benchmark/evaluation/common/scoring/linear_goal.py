"""Canonical linear distance scoring for continuous numeric goals."""

from __future__ import annotations

import math
from numbers import Real

from verifier_grounded_benchmark.task.models import LinearGoalSpec


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
