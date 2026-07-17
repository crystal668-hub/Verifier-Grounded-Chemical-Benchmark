from __future__ import annotations

import pytest

from verifier_grounded_benchmark.evaluation.open_generation.verifiers.openmm import core_backend as openmm_core_properties
from verifier_grounded_benchmark.evaluation.open_generation.verifiers.openmm.runtime import OpenMMEnvironmentError, OpenMMToolError


SPEC = {
    "verifier_id": "openmm_core_energy_drop_v1",
    "verifier_image": "verifier-grounded:dev",
    "property_name": "energy_drop_kj_mol",
    "backend": {"type": "openmm_core", "platform": "Reference"},
}
TASK = {"task_id": "openmm_core_backend_probe"}
CONSTRAINT = {"type": "window", "property": "energy_drop_kj_mol", "min": 0.0, "max": 10.0, "sigma": 2.0}


def test_openmm_core_backend_scores_mocked_properties(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_compute(backend: dict) -> dict[str, float | str]:
        assert backend["platform"] == "Reference"
        return {
            "selected_platform": "Reference",
            "initial_energy_kj_mol": 4.5,
            "minimized_energy_kj_mol": 0.5,
            "energy_drop_kj_mol": 4.0,
            "final_max_force_kj_mol_nm": 0.01,
        }

    monkeypatch.setattr(openmm_core_properties, "compute_core_properties", fake_compute)

    result = openmm_core_properties.evaluate_openmm_core_constraint({}, TASK, CONSTRAINT, SPEC)

    assert result["outcome"] == "verified"
    assert result["properties"]["energy_drop_kj_mol"] == 4.0
    assert result["failure_type"] is None


def test_openmm_core_backend_reports_env_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def missing_env(backend: dict) -> dict[str, float | str]:
        raise OpenMMEnvironmentError("missing optional dependency: openmm")

    monkeypatch.setattr(openmm_core_properties, "compute_core_properties", missing_env)

    result = openmm_core_properties.evaluate_openmm_core_constraint({}, TASK, CONSTRAINT, SPEC)

    assert result["outcome"] != "verified"
    assert result["failure_type"] == "verifier_env_error"
    assert "openmm" in result["message"]


def test_openmm_core_backend_reports_tool_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def tool_failure(backend: dict) -> dict[str, float | str]:
        raise OpenMMToolError("OpenMM energy was not finite")

    monkeypatch.setattr(openmm_core_properties, "compute_core_properties", tool_failure)

    result = openmm_core_properties.evaluate_openmm_core_constraint({}, TASK, CONSTRAINT, SPEC)

    assert result["outcome"] != "verified"
    assert result["failure_type"] == "verifier_tool_error"
    assert "not finite" in result["message"]
