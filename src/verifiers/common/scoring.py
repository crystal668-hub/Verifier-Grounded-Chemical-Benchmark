"""Shared property constraint scoring helpers."""

from __future__ import annotations

import math
from typing import Any


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def score_constraint(properties: dict[str, Any], constraint: dict[str, Any]) -> float:
    kind = constraint["type"]
    prop = constraint["property"]
    value = float(properties[prop])

    if kind == "window":
        minimum = float(constraint["min"])
        maximum = float(constraint["max"])
        sigma = float(constraint.get("sigma", 1.0))
        if sigma <= 0:
            raise ValueError("window sigma must be positive")
        if minimum <= value <= maximum:
            return 1.0
        distance = minimum - value if value < minimum else value - maximum
        return clamp(math.exp(-distance / sigma))

    if kind == "target_distance":
        target = float(constraint["target"])
        scale = float(constraint["scale"])
        if scale <= 0:
            raise ValueError("target_distance scale must be positive")
        return clamp(math.exp(-abs(value - target) / scale))

    if kind in {"maximize_bounded", "minimize_bounded"}:
        forbidden = {"good_at", "baseline"} & set(constraint)
        if forbidden:
            raise ValueError(f"bounded scoring does not accept {sorted(forbidden)}")
        lower = float(constraint["lower"])
        upper = float(constraint["upper"])
        if upper <= lower:
            raise ValueError("bounded scoring requires upper > lower")
        if kind == "maximize_bounded":
            return clamp((value - lower) / (upper - lower))
        return clamp((upper - value) / (upper - lower))

    raise ValueError(f"unsupported constraint type: {kind}")
