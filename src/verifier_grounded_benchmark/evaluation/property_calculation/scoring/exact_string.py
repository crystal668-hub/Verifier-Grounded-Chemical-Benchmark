"""Exact string scoring without implicit normalization."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def score_exact_string(
    submitted: Mapping[str, Any] | None,
    gold: Mapping[str, Any],
    profile: Mapping[str, Any],
) -> float:
    if profile.get("normalization") != "exact":
        raise ValueError("unsupported string normalization")
    value = None if submitted is None else submitted.get("value")
    if not isinstance(value, str):
        return 0.0
    if value == gold.get("value"):
        return 1.0
    return float(profile.get("partial_scores", {}).get(value, 0.0))
