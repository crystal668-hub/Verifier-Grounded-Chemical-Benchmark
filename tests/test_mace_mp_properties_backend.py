from __future__ import annotations

from pathlib import Path

import pytest

from verifiers.backends import mace_mp_properties


SI_CIF = (Path(__file__).resolve().parent / "fixtures" / "Si.cif").read_text()


def spec(property_name: str = "mace_mp_energy_per_atom_ev") -> dict:
    return {
        "verifier_id": f"{property_name}_small_v1",
        "verifier_image": "verifier-grounded:dev",
        "property_name": property_name,
        "backend": {"type": "native_mace_mp"},
        "mace_mp": {"model": "small", "device": "cpu", "default_dtype": "float32"},
        "domain": {
            "allowed_elements": ["Si"],
            "atom_count": [1, 8],
            "volume": [1.0, 300.0],
        },
    }


def task(property_name: str, constraint_type: str = "window") -> dict:
    if constraint_type == "minimize_bounded":
        constraint = {"type": constraint_type, "property": property_name, "lower": 0.0, "upper": 1.0}
    else:
        constraint = {"type": "window", "property": property_name, "min": -6.0, "max": -4.0, "sigma": 0.5}
    constraint["verifier_id"] = f"{property_name}_small_v1"
    return {"task_id": f"{property_name}_task", "constraints": [constraint]}


def test_mace_scores_fake_energy_per_atom(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        mace_mp_properties,
        "predict_mace_mp_properties",
        lambda atoms, current_spec: {
            "mace_mp_energy_ev": -10.738468170166016,
            "mace_mp_energy_per_atom_ev": -5.369234085083008,
            "mace_mp_max_force_ev_per_angstrom": 0.000001,
            "mace_mp_stress_norm_ev_per_angstrom3": 0.0152,
        },
    )
    current_task = task("mace_mp_energy_per_atom_ev")

    result = mace_mp_properties.evaluate_mace_mp_constraint(
        {"cif": SI_CIF},
        current_task,
        current_task["constraints"][0],
        spec(),
    )

    assert result["status"] == "ok"
    assert result["properties"]["mace_mp_energy_per_atom_ev"] == pytest.approx(-5.369234085083008)
    assert result["properties"]["reduced_formula"] == "Si"
    assert result["properties"]["atom_count"] == 2
    assert result["scores"]["score"] == 1.0


def test_mace_scores_force_property(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        mace_mp_properties,
        "predict_mace_mp_properties",
        lambda atoms, current_spec: {
            "mace_mp_energy_ev": -10.7,
            "mace_mp_energy_per_atom_ev": -5.35,
            "mace_mp_max_force_ev_per_angstrom": 0.25,
            "mace_mp_stress_norm_ev_per_angstrom3": 0.1,
        },
    )
    current_task = task("mace_mp_max_force_ev_per_angstrom", "minimize_bounded")

    result = mace_mp_properties.evaluate_mace_mp_constraint(
        {"cif": SI_CIF},
        current_task,
        current_task["constraints"][0],
        spec("mace_mp_max_force_ev_per_angstrom"),
    )

    assert result["status"] == "ok"
    assert result["scores"]["score"] == pytest.approx(0.75)


def test_mace_rejects_invalid_cif() -> None:
    current_task = task("mace_mp_energy_per_atom_ev")

    result = mace_mp_properties.evaluate_mace_mp_constraint(
        {"cif": "not a cif"},
        current_task,
        current_task["constraints"][0],
        spec(),
    )

    assert result["status"] == "error"
    assert result["failure_type"] == "parse_error"


def test_mace_domain_error_preserves_structure_properties(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_predict(atoms: object, current_spec: dict) -> dict:
        raise AssertionError("model should not run after domain error")

    monkeypatch.setattr(mace_mp_properties, "predict_mace_mp_properties", fail_predict)
    current_spec = spec()
    current_spec["domain"] = {**current_spec["domain"], "allowed_elements": ["C"]}
    current_task = task("mace_mp_energy_per_atom_ev")

    result = mace_mp_properties.evaluate_mace_mp_constraint(
        {"cif": SI_CIF},
        current_task,
        current_task["constraints"][0],
        current_spec,
    )

    assert result["status"] == "error"
    assert result["failure_type"] == "domain_error"
    assert result["properties"]["reduced_formula"] == "Si"
    assert result["scores"]["validity_gate"] == 1.0


def test_mace_maps_missing_package_to_environment_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def missing_model(atoms: object, current_spec: dict) -> dict:
        raise ModuleNotFoundError("No module named 'mace'")

    monkeypatch.setattr(mace_mp_properties, "predict_mace_mp_properties", missing_model)
    current_task = task("mace_mp_energy_per_atom_ev")

    result = mace_mp_properties.evaluate_mace_mp_constraint(
        {"cif": SI_CIF},
        current_task,
        current_task["constraints"][0],
        spec(),
    )

    assert result["status"] == "error"
    assert result["failure_type"] == "verifier_environment_error"
    assert result["properties"]["reduced_formula"] == "Si"
