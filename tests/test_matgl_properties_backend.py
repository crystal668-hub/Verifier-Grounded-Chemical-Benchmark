from __future__ import annotations

from pathlib import Path

import pytest

from verifiers.backends import matgl_properties


SI_CIF = (Path(__file__).resolve().parents[1] / "tasks" / "matgl_materials" / "fixtures" / "Si.cif").read_text()


def bandgap_spec() -> dict:
    return {
        "verifier_id": "matgl_bandgap_native_v1",
        "verifier_image": "verifier-grounded:dev",
        "property_name": "bandgap",
        "backend": {"type": "native_matgl"},
        "matgl": {"model_name": "MEGNet-Eform-MP-2018.6.1"},
        "domain": {
            "allowed_elements": ["Si"],
            "atom_count": [1, 8],
            "volume": [1.0, 300.0],
        },
    }


def eform_spec() -> dict:
    spec = bandgap_spec()
    spec.update(
        {
            "verifier_id": "matgl_formation_energy_native_v1",
            "property_name": "formation_energy",
        }
    )
    return spec


def bandgap_task() -> dict:
    return {
        "task_id": "matgl_bandgap_window_si_001",
        "constraints": [
            {
                "type": "window",
                "property": "bandgap",
                "verifier_id": "matgl_bandgap_native_v1",
                "min": 0.8,
                "max": 1.2,
                "sigma": 0.2,
            }
        ],
    }


def eform_task() -> dict:
    return {
        "task_id": "matgl_eform_window_si_002",
        "constraints": [
            {
                "type": "window",
                "property": "formation_energy",
                "verifier_id": "matgl_formation_energy_native_v1",
                "min": -0.05,
                "max": 0.05,
                "sigma": 0.05,
            }
        ],
    }


class FakeModel:
    def __init__(self, value: object) -> None:
        self.value = value
        self.seen_formulas: list[str] = []

    def predict_structure(self, structure: object) -> object:
        self.seen_formulas.append(structure.composition.reduced_formula)
        return self.value


def test_matgl_formation_energy_scores_fake_native_model(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_model = FakeModel(0.0052700042724609375)
    loaded_models: list[dict] = []

    def fake_load(spec: dict) -> FakeModel:
        loaded_models.append(spec)
        return fake_model

    monkeypatch.setattr(matgl_properties, "load_matgl_model", fake_load)

    result = matgl_properties.evaluate_matgl_constraint(
        {"cif": SI_CIF},
        eform_task(),
        eform_task()["constraints"][0],
        eform_spec(),
    )

    assert result["status"] == "ok"
    assert result["verifier_id"] == "matgl_formation_energy_native_v1"
    assert result["canonical_smiles"] is None
    assert result["properties"]["formation_energy"] == pytest.approx(0.0052700042724609375)
    assert result["properties"]["formation_energy_unit"] == "eV/atom"
    assert result["properties"]["reduced_formula"] == "Si"
    assert result["properties"]["atom_count"] == 2
    assert result["properties"]["volume"] == pytest.approx(160.191477991)
    assert result["properties"]["elements"] == ["Si"]
    assert result["scores"]["constraint_scores"] == [
        {"property": "formation_energy", "type": "window", "score": 1.0}
    ]
    assert result["scores"]["score"] == 1.0
    assert fake_model.seen_formulas == ["Si"]
    assert loaded_models[0]["matgl"]["model_name"] == "MEGNet-Eform-MP-2018.6.1"


def test_matgl_bandgap_scores_fake_native_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(matgl_properties, "load_matgl_model", lambda spec: FakeModel(0.9873989820480347))

    result = matgl_properties.evaluate_matgl_constraint(
        {"cif": SI_CIF},
        bandgap_task(),
        bandgap_task()["constraints"][0],
        bandgap_spec(),
    )

    assert result["status"] == "ok"
    assert result["properties"]["bandgap"] == pytest.approx(0.9873989820480347)
    assert result["properties"]["bandgap_unit"] == "eV"
    assert result["scores"]["score"] == 1.0


@pytest.mark.parametrize("candidate", [{"smiles": "CCO"}, {"cif": "not a cif"}])
def test_matgl_property_reports_parse_error_for_missing_or_invalid_cif(candidate: dict) -> None:
    result = matgl_properties.evaluate_matgl_constraint(
        candidate,
        bandgap_task(),
        bandgap_task()["constraints"][0],
        bandgap_spec(),
    )

    assert result["status"] == "error"
    assert result["failure_type"] == "parse_error"
    assert result["scores"]["score"] == 0.0


def test_matgl_property_mismatch_returns_spec_error_before_model_load(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_load(spec: dict) -> object:
        raise AssertionError("model should not load when property names mismatch")

    monkeypatch.setattr(matgl_properties, "load_matgl_model", fail_load)
    spec = bandgap_spec()
    spec["property_name"] = "formation_energy"

    result = matgl_properties.evaluate_matgl_constraint(
        {"cif": SI_CIF},
        bandgap_task(),
        bandgap_task()["constraints"][0],
        spec,
    )

    assert result["status"] == "error"
    assert result["failure_type"] == "verifier_spec_error"
    assert "does not match constraint property" in str(result["message"])


def test_matgl_property_reports_domain_error_for_disallowed_element(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_load(spec: dict) -> object:
        raise AssertionError("model should not load when domain checks fail")

    monkeypatch.setattr(matgl_properties, "load_matgl_model", fail_load)
    spec = bandgap_spec()
    spec["domain"] = {**spec["domain"], "allowed_elements": ["C"]}

    result = matgl_properties.evaluate_matgl_constraint(
        {"cif": SI_CIF},
        bandgap_task(),
        bandgap_task()["constraints"][0],
        spec,
    )

    assert result["status"] == "error"
    assert result["failure_type"] == "domain_error"
    assert result["properties"]["reduced_formula"] == "Si"
    assert result["properties"]["elements"] == ["Si"]
    assert result["scores"]["validity_gate"] == 1.0
    assert result["scores"]["domain_gate"] == 0.0
    assert "disallowed elements: Si" in str(result["message"])


def test_matgl_import_error_maps_to_environment_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def missing_matgl(spec: dict) -> object:
        raise ModuleNotFoundError("No module named 'matgl'")

    monkeypatch.setattr(matgl_properties, "load_matgl_model", missing_matgl)

    result = matgl_properties.evaluate_matgl_constraint(
        {"cif": SI_CIF},
        bandgap_task(),
        bandgap_task()["constraints"][0],
        bandgap_spec(),
    )

    assert result["status"] == "error"
    assert result["failure_type"] == "verifier_environment_error"


def test_matgl_prediction_failure_maps_to_tool_error_and_preserves_structure_properties(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailingModel:
        def predict_structure(self, structure: object) -> object:
            raise RuntimeError("prediction failed")

    monkeypatch.setattr(matgl_properties, "load_matgl_model", lambda spec: FailingModel())

    result = matgl_properties.evaluate_matgl_constraint(
        {"cif": SI_CIF},
        bandgap_task(),
        bandgap_task()["constraints"][0],
        bandgap_spec(),
    )

    assert result["status"] == "error"
    assert result["failure_type"] == "verifier_tool_error"
    assert result["properties"]["reduced_formula"] == "Si"
    assert result["properties"]["atom_count"] == 2
    assert "prediction failed" in str(result["message"])


def test_float_value_handles_scalar_array_and_tensor_like_patterns() -> None:
    class FakeNumpyArray:
        size = 1

        def item(self) -> float:
            return 1.25

    class FakeTensor:
        def detach(self) -> FakeTensor:
            return self

        def cpu(self) -> FakeTensor:
            return self

        def numpy(self) -> FakeNumpyArray:
            return FakeNumpyArray()

    assert matgl_properties.float_value(2) == 2.0
    assert matgl_properties.float_value(FakeNumpyArray()) == 1.25
    assert matgl_properties.float_value(FakeTensor()) == 1.25


def test_float_value_rejects_non_scalar_array_like() -> None:
    class FakeArray:
        size = 2

        def item(self) -> float:
            raise ValueError("can only convert an array of size 1")

    with pytest.raises(ValueError, match="exactly one element"):
        matgl_properties.float_value(FakeArray())
