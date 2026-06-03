from __future__ import annotations

from pathlib import Path

import pytest

from verifiers.atomisticskills_backend import (
    AtomisticSkillsEnvironmentError,
    AtomisticSkillsTimeoutError,
    AtomisticSkillsToolError,
)
from verifiers.backends import mace_properties


SI_CIF = (Path(__file__).resolve().parents[1] / "tasks" / "atomisticskills_smoke" / "fixtures" / "Si.cif").read_text()


def energy_spec() -> dict:
    return {
        "verifier_id": "mace_energy_mcp_v1",
        "verifier_image": "verifier-grounded:dev",
        "property_name": "energy",
        "backend": {"type": "atomisticskills_mcp", "server": "mace"},
        "mace": {"model_name": "MACE-MP-small", "device": "cpu"},
        "domain": {
            "allowed_elements": ["Si"],
            "atom_count": [1, 8],
            "volume": [1.0, 300.0],
        },
    }


def energy_task() -> dict:
    return {
        "task_id": "mace_energy_window_si_001",
        "constraints": [
            {
                "type": "window",
                "property": "energy",
                "verifier_id": "mace_energy_mcp_v1",
                "min": -20.0,
                "max": 20.0,
                "sigma": 5.0,
            }
        ],
    }


def test_mace_energy_loads_model_predicts_structure_and_scores_fake_mcp_result(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, dict]] = []

    class FakeAdapter:
        def __init__(self, server_name: str) -> None:
            assert server_name == "mace"

        def call_tools(self, tool_calls: list[tuple[str, dict]], timeout_seconds: float = 60.0) -> list[dict | str]:
            calls.extend(tool_calls)
            assert Path(tool_calls[1][1]["structure_data"]).exists()
            return [
                "Successfully loaded MACE model: MACE-MP-small",
                {"energy": -10.25, "forces": [[0.0, 0.0, 0.0]], "stress": [0.0, 0.0, 0.0]},
            ]

    monkeypatch.setattr(mace_properties, "AtomisticSkillsMCPAdapter", FakeAdapter)

    result = mace_properties.evaluate_mace_property_constraint(
        {"cif": SI_CIF},
        energy_task(),
        energy_task()["constraints"][0],
        energy_spec(),
    )

    assert result["status"] == "ok"
    assert result["verifier_id"] == "mace_energy_mcp_v1"
    assert result["canonical_smiles"] is None
    assert result["properties"]["energy"] == pytest.approx(-10.25)
    assert result["properties"]["energy_unit"] == "eV"
    assert result["properties"]["reduced_formula"] == "Si"
    assert result["scores"]["constraint_scores"] == [{"property": "energy", "type": "window", "score": 1.0}]
    assert result["scores"]["score"] == 1.0
    assert calls[0] == ("load_model", {"model_name": "MACE-MP-small", "device": "cpu"})
    assert calls[1][0] == "predict_structure"


def test_mace_property_reports_parse_error_for_missing_cif() -> None:
    result = mace_properties.evaluate_mace_property_constraint(
        {"smiles": "CCO"},
        energy_task(),
        energy_task()["constraints"][0],
        energy_spec(),
    )

    assert result["status"] == "error"
    assert result["failure_type"] == "parse_error"
    assert result["scores"]["score"] == 0.0


def test_mace_property_reports_domain_error_for_disallowed_element() -> None:
    spec = energy_spec()
    spec["domain"] = {**spec["domain"], "allowed_elements": ["C"]}

    result = mace_properties.evaluate_mace_property_constraint(
        {"cif": SI_CIF},
        energy_task(),
        energy_task()["constraints"][0],
        spec,
    )

    assert result["status"] == "error"
    assert result["failure_type"] == "domain_error"
    assert result["scores"]["validity_gate"] == 1.0
    assert "disallowed elements: Si" in str(result["message"])


@pytest.mark.parametrize(
    ("exception", "failure_type"),
    [
        (AtomisticSkillsEnvironmentError("missing mace-agent"), "verifier_environment_error"),
        (AtomisticSkillsToolError("tool failed"), "verifier_tool_error"),
        (AtomisticSkillsTimeoutError("timed out"), "verifier_timeout"),
    ],
)
def test_mace_property_maps_adapter_errors(
    monkeypatch: pytest.MonkeyPatch,
    exception: Exception,
    failure_type: str,
) -> None:
    class FakeAdapter:
        def __init__(self, server_name: str) -> None:
            assert server_name == "mace"

        def call_tools(self, tool_calls: list[tuple[str, dict]], timeout_seconds: float = 60.0) -> list[dict | str]:
            raise exception

    monkeypatch.setattr(mace_properties, "AtomisticSkillsMCPAdapter", FakeAdapter)

    result = mace_properties.evaluate_mace_property_constraint(
        {"cif": SI_CIF},
        energy_task(),
        energy_task()["constraints"][0],
        energy_spec(),
    )

    assert result["status"] == "error"
    assert result["failure_type"] == failure_type
