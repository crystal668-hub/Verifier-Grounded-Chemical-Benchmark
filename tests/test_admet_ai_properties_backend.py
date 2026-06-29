from __future__ import annotations

from typing import Any

import pytest

from verifiers.backends import admet_ai_properties


class FakeADMETModel:
    def __init__(self, outputs: dict[str, float]) -> None:
        self.outputs = outputs

    def predict(self, *, smiles: str) -> dict[str, float]:
        assert smiles == "CCO"
        return self.outputs


def payload(property_name: str = "hERG") -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    task = {"task_id": "admet_ai_herg_001", "version": 1, "object_type": "small_molecule"}
    constraint = {
        "type": "minimize_bounded",
        "property": property_name,
        "verifier_id": "admet_ai_herg_v1",
        "lower": 0.0,
        "upper": 1.0,
    }
    spec = {
        "verifier_id": "admet_ai_herg_v1",
        "property_name": "hERG",
        "verifier_image": "verifier-grounded:dev",
        "domain": {
            "allowed_elements": ["C", "N", "O", "F", "P", "S", "Cl", "Br", "I"],
            "heavy_atom_count": [1, 80],
            "mw": [1.0, 1000.0],
            "formal_charge": [-2, 2],
        },
    }
    candidate = {"smiles": "CCO"}
    return candidate, task, constraint, spec


def test_scores_fake_herg_prediction(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(admet_ai_properties, "load_model", lambda spec: FakeADMETModel({"hERG": 0.2}))
    candidate, task, constraint, spec = payload()

    result = admet_ai_properties.evaluate_admet_ai_constraint(candidate, task, constraint, spec)

    assert result["status"] == "ok"
    assert result["canonical_smiles"] == "CCO"
    assert result["properties"]["hERG"] == pytest.approx(0.2)
    assert result["scores"]["score"] == pytest.approx(0.8)


def test_missing_smiles_returns_parse_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(admet_ai_properties, "load_model", lambda spec: FakeADMETModel({"hERG": 0.2}))
    candidate, task, constraint, spec = payload()
    candidate = {}

    result = admet_ai_properties.evaluate_admet_ai_constraint(candidate, task, constraint, spec)

    assert result["status"] == "error"
    assert result["failure_type"] == "parse_error"


@pytest.mark.parametrize("smiles", ["[Na+]", "[Na+].[Cl-]"])
def test_disallowed_element_or_multicomponent_returns_domain_or_validity_error(
    smiles: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(admet_ai_properties, "load_model", lambda spec: FakeADMETModel({"hERG": 0.2}))
    candidate, task, constraint, spec = payload()
    candidate = {"smiles": smiles}

    result = admet_ai_properties.evaluate_admet_ai_constraint(candidate, task, constraint, spec)

    assert result["status"] == "error"
    assert result["failure_type"] in {"validity_error", "domain_error"}


def test_spec_property_mismatch_returns_verifier_spec_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(admet_ai_properties, "load_model", lambda spec: FakeADMETModel({"hERG": 0.2}))
    candidate, task, constraint, spec = payload("AMES")

    result = admet_ai_properties.evaluate_admet_ai_constraint(candidate, task, constraint, spec)

    assert result["status"] == "error"
    assert result["failure_type"] == "verifier_spec_error"
