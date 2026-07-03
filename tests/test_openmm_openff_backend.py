from __future__ import annotations

import pytest

from verifiers.backends import openmm_openff_properties
from verifiers.backends.openmm_runtime import OpenMMEnvironmentError, OpenMMToolError


SPEC = {
    "verifier_id": "openmm_openff_ligand_energy_drop_v1",
    "verifier_image": "verifier-grounded:dev",
    "property_name": "energy_drop_kj_mol",
    "backend": {
        "type": "openmm_openff_ligand",
        "forcefield_family": "openff",
        "forcefield_name": "openff-2.2.1.offxml",
        "platform": "Reference",
    },
    "domain": {
        "allowed_elements": ["H", "C", "N", "O", "F", "P", "S", "Cl", "Br", "I"],
        "heavy_atom_count": [2, 60],
        "formal_charge": [-1, 1],
    },
}
TASK = {"task_id": "openmm_openff_backend_probe"}
CONSTRAINT = {"type": "window", "property": "energy_drop_kj_mol", "min": 0.0, "max": 20.0, "sigma": 5.0}


def test_openmm_openff_backend_scores_mocked_properties(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_compute(smiles: str, backend: dict) -> dict[str, float | int | str]:
        assert smiles == "CCO"
        assert backend["forcefield_family"] == "openff"
        return {
            "forcefield_family": "openff",
            "forcefield_name": "openff-2.2.1.offxml",
            "charge_method": "am1bcc",
            "parameterization_success": 1,
            "system_particle_count": 9,
            "selected_platform": "Reference",
            "initial_energy_kj_mol": 8.0,
            "minimized_energy_kj_mol": 1.0,
            "energy_drop_kj_mol": 7.0,
            "final_max_force_kj_mol_nm": 0.03,
        }

    monkeypatch.setattr(openmm_openff_properties, "compute_ligand_properties", fake_compute)

    result = openmm_openff_properties.evaluate_openmm_openff_constraint({"smiles": "CCO"}, TASK, CONSTRAINT, SPEC)

    assert result["status"] == "ok"
    assert result["canonical_smiles"] == "CCO"
    assert result["properties"]["energy_drop_kj_mol"] == 7.0
    assert result["failure_type"] is None


def test_openmm_openff_backend_rejects_invalid_smiles() -> None:
    result = openmm_openff_properties.evaluate_openmm_openff_constraint(
        {"smiles": "not a smiles"},
        TASK,
        CONSTRAINT,
        SPEC,
    )

    assert result["status"] == "error"
    assert result["failure_type"] == "parse_error"


def test_openmm_openff_backend_rejects_multi_component_smiles() -> None:
    result = openmm_openff_properties.evaluate_openmm_openff_constraint(
        {"smiles": "CCO.O"},
        TASK,
        CONSTRAINT,
        SPEC,
    )

    assert result["status"] == "error"
    assert result["failure_type"] == "validity_error"


def test_openmm_openff_backend_rejects_disallowed_element() -> None:
    result = openmm_openff_properties.evaluate_openmm_openff_constraint(
        {"smiles": "C[Na]"},
        TASK,
        CONSTRAINT,
        {**SPEC, "domain": {**SPEC["domain"], "allowed_elements": ["H", "C"]}},
    )

    assert result["status"] == "error"
    assert result["failure_type"] == "domain_error"


def test_openmm_openff_backend_reports_env_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def missing_env(smiles: str, backend: dict) -> dict[str, float | int | str]:
        raise OpenMMEnvironmentError("missing optional dependency: openff.toolkit")

    monkeypatch.setattr(openmm_openff_properties, "compute_ligand_properties", missing_env)

    result = openmm_openff_properties.evaluate_openmm_openff_constraint({"smiles": "CCO"}, TASK, CONSTRAINT, SPEC)

    assert result["status"] == "error"
    assert result["failure_type"] == "verifier_env_error"
    assert "openff.toolkit" in result["message"]


def test_openmm_openff_backend_reports_tool_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def tool_failure(smiles: str, backend: dict) -> dict[str, float | int | str]:
        raise OpenMMToolError("OpenFF parameterization failed: no parameters")

    monkeypatch.setattr(openmm_openff_properties, "compute_ligand_properties", tool_failure)

    result = openmm_openff_properties.evaluate_openmm_openff_constraint({"smiles": "CCO"}, TASK, CONSTRAINT, SPEC)

    assert result["status"] == "error"
    assert result["failure_type"] == "verifier_tool_error"
