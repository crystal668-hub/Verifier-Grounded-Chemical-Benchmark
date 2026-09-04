"""Deterministic scoring for atom-index and element answers."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

ATOM_IDENTITY = re.compile(r"(?:(?P<index>0|[1-9][0-9]*) )?(?P<element>[A-Z][a-z]?)")


def score_atom_identity(
    submitted: Mapping[str, Any] | None,
    gold: Mapping[str, Any],
    profile: Mapping[str, Any],
) -> float:
    if profile.get("normalization") != "atom_identity":
        raise ValueError("atom identity profile must use atom_identity normalization")
    value = None if submitted is None else submitted.get("value")
    gold_value = gold.get("value")
    if not isinstance(value, str) or not isinstance(gold_value, str):
        return 0.0
    submitted_match = ATOM_IDENTITY.fullmatch(value)
    gold_match = ATOM_IDENTITY.fullmatch(gold_value)
    if submitted_match is None or gold_match is None:
        return 0.0
    if submitted_match.groups() == gold_match.groups():
        return 1.0
    if submitted_match["element"] == gold_match["element"]:
        return float(profile.get("element_partial_score", 0.0))
    return 0.0
