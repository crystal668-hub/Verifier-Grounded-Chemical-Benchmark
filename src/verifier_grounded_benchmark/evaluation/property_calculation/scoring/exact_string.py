"""Exact string scoring without implicit normalization."""

from __future__ import annotations

from typing import Any, Mapping


def score_exact_string(
    submitted: Mapping[str, Any] | None,
    gold: Mapping[str, Any],
    profile: Mapping[str, Any],
) -> float:
    if profile.get("normalization") != "exact":
        raise ValueError("unsupported string normalization")
    value = None if submitted is None else submitted.get("value")
    return float(isinstance(value, str) and value == gold.get("value"))
