"""Verifier-spec schema validation."""

from __future__ import annotations

from typing import Any

from verifier_grounded_benchmark.task.schema.common import (
    index_unique,
    require_list,
    require_mapping,
    require_string,
)


def validate_verifier_specs(
    items: list[Any], *, require_module_executor: bool = False
) -> dict[str, dict[str, Any]]:
    indexed = index_unique(items, "verifier_id", "verifier")
    for verifier_id, spec in indexed.items():
        _validate_external_dependencies(verifier_id, spec)
        if require_module_executor:
            executor = require_mapping(spec.get("executor"), f"verifier {verifier_id} executor")
            if executor.get("type") != "python_module":
                raise ValueError(f"verifier {verifier_id} must use python_module executor")
            require_string(executor.get("module"), f"verifier {verifier_id} module")
            if "verification_script" in spec:
                raise ValueError(f"verifier {verifier_id} must not use verification_script")
    return indexed


def _validate_external_dependencies(verifier_id: str, spec: dict[str, Any]) -> None:
    if "external_dependencies" not in spec:
        return
    dependencies = require_list(
        spec["external_dependencies"],
        f"verifier {verifier_id} external_dependencies",
    )
    executable_names: set[str] = set()
    for index, item in enumerate(dependencies):
        field = f"verifier {verifier_id} external_dependencies[{index}]"
        dependency = require_mapping(item, field)
        executable = require_string(dependency.get("executable"), f"{field} executable")
        require_string(dependency.get("version"), f"{field} version")
        if "conda_environment" in dependency:
            require_string(
                dependency["conda_environment"], f"{field} conda_environment"
            )
        unexpected = set(dependency) - {"executable", "version", "conda_environment"}
        if unexpected:
            raise ValueError(f"{field} has unsupported fields: {sorted(unexpected)}")
        if executable in executable_names:
            raise ValueError(
                f"verifier {verifier_id} repeats external dependency {executable}"
            )
        executable_names.add(executable)
