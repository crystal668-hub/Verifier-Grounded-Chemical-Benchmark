"""Already-structured candidate parsing."""

from __future__ import annotations

from typing import Any


def parse_structured_candidates(record: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = record.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("candidates must be a non-empty list")
    if not all(isinstance(candidate, dict) for candidate in candidates):
        raise ValueError("candidate entries must be objects")
    return candidates
