"""Numeric Gold scoring through the shared linear goal kernel."""

from __future__ import annotations

import math
from numbers import Real
from typing import Any, Mapping

from verifier_grounded_benchmark.evaluation.common.scoring.linear_goal import score
from verifier_grounded_benchmark.task.schema.common import linear_goal_from_profile


def score_numeric_gold(
    submitted: Mapping[str, Any] | None,
    gold: Mapping[str, Any],
    profile: Mapping[str, Any],
) -> float:
    if submitted is None or submitted.get("unit") != gold.get("unit"):
        return 0.0
    value = submitted.get("value")
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(float(value)):
        return 0.0
    region = linear_goal_from_profile(profile, gold=gold.get("value"))
    return score(float(value), region)
