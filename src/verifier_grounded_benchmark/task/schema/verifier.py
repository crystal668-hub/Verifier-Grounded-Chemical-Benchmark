"""Verifier-spec schema validation."""

from __future__ import annotations

from typing import Any

from verifier_grounded_benchmark.task.schema.common import (
    index_unique,
    require_mapping,
    require_string,
)


def validate_verifier_specs(
    items: list[Any], *, require_module_executor: bool = False
) -> dict[str, dict[str, Any]]:
    indexed = index_unique(items, "verifier_id", "verifier")
    if require_module_executor:
        for verifier_id, spec in indexed.items():
            executor = require_mapping(spec.get("executor"), f"verifier {verifier_id} executor")
            if executor.get("type") != "python_module":
                raise ValueError(f"verifier {verifier_id} must use python_module executor")
            require_string(executor.get("module"), f"verifier {verifier_id} module")
            if "verification_script" in spec:
                raise ValueError(f"verifier {verifier_id} must not use verification_script")
    return indexed
