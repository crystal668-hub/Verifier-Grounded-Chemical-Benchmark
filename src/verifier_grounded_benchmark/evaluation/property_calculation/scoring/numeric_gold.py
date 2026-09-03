"""Numeric Gold scoring through the shared linear goal kernel."""

from __future__ import annotations

import math
from collections.abc import Mapping
from numbers import Real
from typing import Any

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
    transform = profile.get("value_transform", "identity")
    numeric_value = float(value)
    numeric_gold = gold.get("value")
    if transform == "absolute":
        numeric_value = abs(numeric_value)
        numeric_gold = abs(float(numeric_gold))
    elif transform == "log10":
        if numeric_value <= 0 or not isinstance(numeric_gold, Real) or float(numeric_gold) <= 0:
            return 0.0
        numeric_value = math.log10(numeric_value)
        numeric_gold = math.log10(float(numeric_gold))
    elif transform != "identity":
        raise ValueError(f"unsupported numeric gold value_transform: {transform}")
    region = linear_goal_from_profile(profile, gold=numeric_gold)
    return score(numeric_value, region)
