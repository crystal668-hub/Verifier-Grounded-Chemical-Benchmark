"""Verifier-spec schema validation."""

from __future__ import annotations

from typing import Any

from verifier_grounded_benchmark.task.schema.common import index_unique


def validate_verifier_specs(items: list[Any]) -> dict[str, dict[str, Any]]:
    return index_unique(items, "verifier_id", "verifier")
