"""Aggregation functions shared by evaluation topics."""

from __future__ import annotations

import math
from collections.abc import Iterable
from numbers import Real


def arithmetic_mean(values: Iterable[float]) -> float:
    scores = _validated_scores(values)
    return sum(scores) / len(scores)


def geometric_mean(values: Iterable[float]) -> float:
    scores = _validated_scores(values)
    if any(value == 0.0 for value in scores):
        return 0.0
    return math.prod(scores) ** (1.0 / len(scores))


def minimum(values: Iterable[float]) -> float:
    return min(_validated_scores(values))


def _validated_scores(values: Iterable[float]) -> list[float]:
    scores: list[float] = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, Real):
            raise ValueError("scores must be finite numbers in [0, 1]")
        score = float(value)
        if not math.isfinite(score) or not 0.0 <= score <= 1.0:
            raise ValueError("scores must be finite numbers in [0, 1]")
        scores.append(score)
    if not scores:
        raise ValueError("aggregation requires at least one score")
    return scores
