"""OpenMM core fixed-fixture backend."""

from __future__ import annotations

from importlib import metadata
from typing import Any

from verifier_grounded_benchmark.evaluation.open_generation.verifiers.openmm.runtime import (
    ENV_FAILURE,
    TOOL_FAILURE,
    OpenMMEnvironmentError,
    OpenMMToolError,
    run_core_smoke,
)
from verifier_grounded_benchmark.evaluation.open_generation.verifiers.common.result import base_result, error_result, verified_result


def evaluate_openmm_core_constraint(
    candidate: dict[str, Any],
    task: dict[str, Any],
    constraint: dict[str, Any],
    spec: dict[str, Any],
) -> dict[str, Any]:
    del candidate
    result = base_result(task["task_id"], spec.get("verifier_id"), openmm_core_versions(spec))
    property_name = spec.get("property_name")
    allowed_properties = {property_name, *(spec.get("additional_property_names") or [])}
    if constraint.get("property") not in allowed_properties:
        return error_result(
            result,
            "verifier_spec_error",
            f"verifier property {property_name!r} does not match constraint property {constraint.get('property')!r}",
        )

    try:
        properties = compute_core_properties(spec.get("backend") or {})
    except OpenMMEnvironmentError as exc:
        return error_result(result, ENV_FAILURE, str(exc))
    except OpenMMToolError as exc:
        return error_result(result, TOOL_FAILURE, str(exc))
    except Exception as exc:
        return error_result(result, TOOL_FAILURE, f"OpenMM core calculation failed: {exc}")

    return verified_result(result, properties)


def compute_core_properties(backend: dict[str, Any]) -> dict[str, float | str]:
    preferred_platform = str(backend.get("platform", "Reference"))
    smoke = run_core_smoke(preferred_platform=preferred_platform)
    return {
        "selected_platform": str(smoke["selected_platform"]),
        "initial_energy_kj_mol": float(smoke["initial_energy_kj_mol"]),
        "minimized_energy_kj_mol": float(smoke["minimized_energy_kj_mol"]),
        "energy_drop_kj_mol": float(smoke["energy_drop_kj_mol"]),
        "final_max_force_kj_mol_nm": float(smoke["final_max_force_kj_mol_nm"]),
    }


def openmm_core_versions(spec: dict[str, Any]) -> dict[str, Any]:
    versions = {
        "verifier_image": spec.get("verifier_image"),
        "openmm_core_backend": "fixed_fixture_v1",
    }
    try:
        versions["openmm"] = metadata.version("openmm")
    except metadata.PackageNotFoundError:
        versions["openmm"] = None
    return versions
