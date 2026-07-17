"""Maximize profile adapter."""

from typing import Any, Mapping

from verifier_grounded_benchmark.evaluation.common.scoring.linear_goal import score
from verifier_grounded_benchmark.task.schema.common import linear_goal_from_profile


def score_maximize(value: float, profile: Mapping[str, Any]) -> float:
    return score(value, linear_goal_from_profile(profile))
