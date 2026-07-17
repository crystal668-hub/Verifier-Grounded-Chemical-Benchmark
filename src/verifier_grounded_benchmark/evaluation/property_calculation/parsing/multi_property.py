"""Multi-property answer parsing with duplicate detection."""

from __future__ import annotations

from typing import Any


class PropertyAnswerParseError(ValueError):
    pass


def parse_multi_property(
    answer: dict[str, Any], requested_names: set[str]
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    items = answer.get("answers")
    if items is None:
        return {}, []
    if not isinstance(items, list):
        raise PropertyAnswerParseError("answers must be a list")
    submitted: dict[str, dict[str, Any]] = {}
    unknown: list[str] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            raise PropertyAnswerParseError("answer entries must be objects")
        name = item.get("property")
        if not isinstance(name, str) or not name:
            raise PropertyAnswerParseError("answer entries require a property string")
        if name in seen:
            raise PropertyAnswerParseError(f"duplicate property in answer: {name}")
        seen.add(name)
        if name not in requested_names:
            unknown.append(name)
            continue
        submitted[name] = {
            **({"value": item["value"]} if "value" in item else {}),
            **({"unit": item["unit"]} if "unit" in item else {}),
        }
    return submitted, unknown
