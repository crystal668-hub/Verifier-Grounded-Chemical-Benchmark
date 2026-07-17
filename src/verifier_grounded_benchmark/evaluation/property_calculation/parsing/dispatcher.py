"""Dispatch Property Calculation answers by declared answer shape."""

from __future__ import annotations

from typing import Any

from verifier_grounded_benchmark.evaluation.property_calculation.parsing.multi_property import (
    parse_multi_property,
)
from verifier_grounded_benchmark.evaluation.property_calculation.parsing.single_value import (
    parse_single_value,
)


def parse_answer(
    answer: dict[str, Any], requested_names: list[str]
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    if len(requested_names) == 1 and "answers" not in answer:
        return parse_single_value(answer, requested_names[0]), []
    return parse_multi_property(answer, set(requested_names))
