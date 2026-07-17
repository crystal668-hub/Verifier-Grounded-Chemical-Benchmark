"""Single-value Property Calculation answer parsing."""

from __future__ import annotations

from typing import Any


def parse_single_value(answer: dict[str, Any], property_name: str) -> dict[str, dict[str, Any]]:
    if "answer" not in answer and "unit" not in answer:
        return {}
    submitted: dict[str, Any] = {}
    if "answer" in answer:
        submitted["value"] = answer["answer"]
    if "unit" in answer:
        submitted["unit"] = answer["unit"]
    return {property_name: submitted}
