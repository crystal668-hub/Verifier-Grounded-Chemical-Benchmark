from __future__ import annotations

import pytest

from verifiers.torchani import backend as torchani_properties


WATER_XYZ = """3
water
O 0.000000 0.000000 0.000000
H 0.758602 0.000000 0.504284
H -0.758602 0.000000 0.504284
"""


def spec(property_name: str = "torchani_total_energy_hartree") -> dict:
    return {
        "verifier_id": f"{property_name}_ani2x_v1",
        "verifier_image": "verifier-grounded:dev",
        "property_name": property_name,
        "backend": {"type": "native_torchani"},
        "torchani": {"model_name": "ANI2x", "device": "cpu"},
        "domain": {
            "allowed_elements": ["H", "C", "N", "O", "F", "S", "Cl"],
            "atom_count": [2, 80],
            "heavy_atom_count": [1, 40],
        },
    }


def task(property_name: str, constraint_type: str = "window") -> dict:
    if constraint_type == "minimize_bounded":
        constraint = {
            "type": constraint_type,
            "property": property_name,
            "lower": 0.0,
            "upper": 0.2,
        }
    else:
        constraint = {
            "type": "window",
            "property": property_name,
            "min": -80.0,
            "max": -70.0,
            "sigma": 2.0,
        }
    constraint["verifier_id"] = f"{property_name}_ani2x_v1"
    return {"task_id": f"{property_name}_task", "constraints": [constraint]}


def test_torchani_scores_fake_total_energy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        torchani_properties,
        "predict_torchani_properties",
        lambda atoms, current_spec: {
            "torchani_total_energy_hartree": -76.38121032714844,
            "torchani_energy_per_atom_hartree": -25.460403442382812,
            "torchani_max_force_hartree_per_angstrom": 0.01,
        },
    )

    current_task = task("torchani_total_energy_hartree")
    result = torchani_properties.evaluate_torchani_constraint(
        {"xyz": WATER_XYZ},
        current_task,
        current_task["constraints"][0],
        spec(),
    )

    assert result["status"] == "ok"
    assert result["properties"]["torchani_total_energy_hartree"] == pytest.approx(-76.38121032714844)
    assert result["properties"]["torchani_energy_per_atom_hartree"] == pytest.approx(-25.460403442382812)
    assert result["properties"]["torchani_max_force_hartree_per_angstrom"] == pytest.approx(0.01)
    assert result["properties"]["formula"] == "H2O"
    assert result["scores"]["score"] == 1.0


def test_torchani_scores_force_property(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        torchani_properties,
        "predict_torchani_properties",
        lambda atoms, current_spec: {
            "torchani_total_energy_hartree": -76.0,
            "torchani_energy_per_atom_hartree": -25.333333333333332,
            "torchani_max_force_hartree_per_angstrom": 0.05,
        },
    )
    current_task = task("torchani_max_force_hartree_per_angstrom", "minimize_bounded")

    result = torchani_properties.evaluate_torchani_constraint(
        {"xyz": WATER_XYZ},
        current_task,
        current_task["constraints"][0],
        spec("torchani_max_force_hartree_per_angstrom"),
    )

    assert result["status"] == "ok"
    assert result["scores"]["score"] == pytest.approx(0.75)


def test_torchani_rejects_property_mismatch() -> None:
    current_task = task("torchani_total_energy_hartree")

    result = torchani_properties.evaluate_torchani_constraint(
        {"xyz": WATER_XYZ},
        current_task,
        current_task["constraints"][0],
        spec("torchani_energy_per_atom_hartree"),
    )

    assert result["status"] == "error"
    assert result["failure_type"] == "verifier_spec_error"


def test_torchani_maps_missing_xyz_to_parse_error() -> None:
    current_task = task("torchani_total_energy_hartree")

    result = torchani_properties.evaluate_torchani_constraint(
        {"smiles": "O"},
        current_task,
        current_task["constraints"][0],
        spec(),
    )

    assert result["status"] == "error"
    assert result["failure_type"] == "parse_error"


def test_torchani_maps_model_import_error_to_environment_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def missing_model(atoms: object, current_spec: dict) -> dict:
        raise ModuleNotFoundError("No module named 'torchani'")

    monkeypatch.setattr(torchani_properties, "predict_torchani_properties", missing_model)
    current_task = task("torchani_total_energy_hartree")

    result = torchani_properties.evaluate_torchani_constraint(
        {"xyz": WATER_XYZ},
        current_task,
        current_task["constraints"][0],
        spec(),
    )

    assert result["status"] == "error"
    assert result["failure_type"] == "verifier_environment_error"
    assert result["properties"]["formula"] == "H2O"
