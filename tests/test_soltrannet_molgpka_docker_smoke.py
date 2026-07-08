from __future__ import annotations

import os

import pytest

from verifiers.molgpka import backend as molgpka_properties
from verifiers.soltrannet import backend as soltrannet_properties


pytestmark = pytest.mark.skipif(
    os.environ.get("VGB_RUN_DOCKER_SMOKE") != "1",
    reason="set VGB_RUN_DOCKER_SMOKE=1 to run live Docker model smoke tests",
)


DOMAIN = {
    "allowed_elements": ["C", "N", "O", "F", "P", "S", "Cl", "Br", "I"],
    "heavy_atom_count": [1, 80],
    "mw": [1.0, 1000.0],
    "formal_charge": [-2, 2],
}


@pytest.mark.parametrize("smiles", ["CCO", "c1ccccc1"])
def test_live_soltrannet_predicts_small_molecule(smiles: str) -> None:
    value = soltrannet_properties.predict_soltrannet_log_s(smiles, {"soltrannet": {}})

    assert isinstance(value, float)


def test_live_soltrannet_backend_scores_ethanol() -> None:
    result = soltrannet_properties.evaluate_soltrannet_constraint(
        {"smiles": "CCO"},
        {"task_id": "live_soltrannet"},
        {
            "type": "window",
            "property": "soltrannet_log_s",
            "verifier_id": "soltrannet_log_s_v1",
            "min": 1.0,
            "max": 3.5,
            "sigma": 1.0,
        },
        {
            "verifier_id": "soltrannet_log_s_v1",
            "property_name": "soltrannet_log_s",
            "domain": DOMAIN,
            "soltrannet": {},
        },
    )

    assert result["status"] == "ok"
    assert isinstance(result["properties"]["soltrannet_log_s"], float)


def test_live_molgpka_predicts_acetic_acid() -> None:
    properties = molgpka_properties.predict_molgpka_properties("CC(=O)O", {"molgpka": {}})

    assert properties["molgpka_pka_count"] >= 1
    assert properties["molgpka_pka_values"]


def test_live_molgpka_backend_scores_acetic_acid_count() -> None:
    result = molgpka_properties.evaluate_molgpka_constraint(
        {"smiles": "CC(O)=O"},
        {"task_id": "live_molgpka"},
        {
            "type": "window",
            "property": "molgpka_pka_count",
            "verifier_id": "molgpka_pka_count_v1",
            "min": 1,
            "max": 3,
            "sigma": 1.0,
        },
        {
            "verifier_id": "molgpka_pka_count_v1",
            "property_name": "molgpka_pka_count",
            "domain": DOMAIN,
            "molgpka": {},
        },
    )

    assert result["status"] == "ok"
    assert result["properties"]["molgpka_pka_count"] >= 1
