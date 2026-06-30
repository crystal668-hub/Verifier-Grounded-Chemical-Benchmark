from __future__ import annotations

from pathlib import Path

import pytest

from verifiers.backends import atomisticskills_matgl_properties
from verifiers.atomisticskills_backend import (
    AtomisticSkillsEnvironmentError,
    AtomisticSkillsTimeoutError,
    AtomisticSkillsToolError,
)


SI_CIF = (Path(__file__).resolve().parents[1] / "tasks" / "atomisticskills_smoke" / "fixtures" / "Si.cif").read_text()


def bandgap_spec() -> dict:
    return {
        "verifier_id": "matgl_bandgap_pbe_mcp_v1",
        "verifier_image": "verifier-grounded:dev",
        "property_name": "bandgap",
        "backend": {"type": "atomisticskills_mcp", "server": "matgl"},
        "matgl": {"task_name": "PBE"},
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
            "verifier_id": "matgl_formation_energy_mcp_v1",
            "property_name": "formation_energy",
            "matgl": {"model_name": "MEGNet-Eform-MP-2018.6.1", "device": "cpu"},
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
                "verifier_id": "matgl_bandgap_pbe_mcp_v1",
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
                "verifier_id": "matgl_formation_energy_mcp_v1",
                "min": -0.05,
                "max": 0.05,
                "sigma": 0.05,
            }
        ],
    }


def test_atomisticskills_matgl_bandgap_scores_fake_mcp_result(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, dict]] = []

    class FakeAdapter:
        def __init__(self, server_name: str) -> None:
            assert server_name == "matgl"

        def call_tool(self, tool_name: str, arguments: dict, timeout_seconds: float = 60.0) -> dict:
            calls.append((tool_name, arguments))
            assert Path(arguments["structure_data"]).exists()
            return {"bandgap": 0.9873989820480347, "unit": "eV"}

    monkeypatch.setattr(atomisticskills_matgl_properties, "AtomisticSkillsMCPAdapter", FakeAdapter)

    result = atomisticskills_matgl_properties.evaluate_atomisticskills_matgl_constraint(
        {"cif": SI_CIF},
        bandgap_task(),
        bandgap_task()["constraints"][0],
        bandgap_spec(),
    )

    assert result["status"] == "ok"
    assert result["verifier_id"] == "matgl_bandgap_pbe_mcp_v1"
    assert result["canonical_smiles"] is None
    assert result["properties"]["bandgap"] == pytest.approx(0.9873989820480347)
    assert result["properties"]["bandgap_unit"] == "eV"
    assert result["properties"]["reduced_formula"] == "Si"
    assert result["scores"]["constraint_scores"] == [{"property": "bandgap", "type": "window", "score": 1.0}]
    assert result["scores"]["score"] == 1.0
    assert calls[0][0] == "predict_bandgap"
    assert calls[0][1]["task_name"] == "PBE"


def test_atomisticskills_matgl_formation_energy_loads_model_and_scores_fake_mcp_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, dict]] = []

    class FakeAdapter:
        def __init__(self, server_name: str) -> None:
            assert server_name == "matgl"

        def call_tools(self, tool_calls: list[tuple[str, dict]], timeout_seconds: float = 60.0) -> list[dict | str]:
            calls.extend(tool_calls)
            assert Path(tool_calls[1][1]["structure_data"]).exists()
            return [
                "Successfully loaded MatGL model: MEGNet-Eform-MP-2018.6.1",
                {"formation_energy": 0.0052700042724609375, "unit": "eV"},
            ]

    monkeypatch.setattr(atomisticskills_matgl_properties, "AtomisticSkillsMCPAdapter", FakeAdapter)

    result = atomisticskills_matgl_properties.evaluate_atomisticskills_matgl_constraint(
        {"cif": SI_CIF},
        eform_task(),
        eform_task()["constraints"][0],
        eform_spec(),
    )

    assert result["status"] == "ok"
    assert result["properties"]["formation_energy"] == pytest.approx(0.0052700042724609375)
    assert result["properties"]["formation_energy_unit"] == "eV"
    assert result["scores"]["score"] == 1.0
    assert calls[0] == ("load_model", {"model_name": "MEGNet-Eform-MP-2018.6.1", "device": "cpu"})
    assert calls[1][0] == "predict_structure"


def test_atomisticskills_matgl_property_reports_parse_error_for_missing_cif() -> None:
    result = atomisticskills_matgl_properties.evaluate_atomisticskills_matgl_constraint(
        {"smiles": "CCO"},
        bandgap_task(),
        bandgap_task()["constraints"][0],
        bandgap_spec(),
    )

    assert result["status"] == "error"
    assert result["failure_type"] == "parse_error"
    assert result["scores"]["score"] == 0.0


def test_atomisticskills_matgl_property_reports_parse_error_for_invalid_cif() -> None:
    result = atomisticskills_matgl_properties.evaluate_atomisticskills_matgl_constraint(
        {"cif": "not a cif"},
        bandgap_task(),
        bandgap_task()["constraints"][0],
        bandgap_spec(),
    )

    assert result["status"] == "error"
    assert result["failure_type"] == "parse_error"
    assert "CIF parse failed" in str(result["message"])


def test_atomisticskills_matgl_property_reports_domain_error_for_disallowed_element() -> None:
    spec = bandgap_spec()
    spec["domain"] = {**spec["domain"], "allowed_elements": ["C"]}

    result = atomisticskills_matgl_properties.evaluate_atomisticskills_matgl_constraint(
        {"cif": SI_CIF},
        bandgap_task(),
        bandgap_task()["constraints"][0],
        spec,
    )

    assert result["status"] == "error"
    assert result["failure_type"] == "domain_error"
    assert result["scores"]["validity_gate"] == 1.0
    assert "disallowed elements: Si" in str(result["message"])


@pytest.mark.parametrize(
    ("exception", "failure_type"),
    [
        (AtomisticSkillsEnvironmentError("missing matgl-agent"), "verifier_environment_error"),
        (AtomisticSkillsToolError("tool failed"), "verifier_tool_error"),
        (AtomisticSkillsTimeoutError("timed out"), "verifier_timeout"),
    ],
)
def test_atomisticskills_matgl_property_maps_adapter_errors(
    monkeypatch: pytest.MonkeyPatch,
    exception: Exception,
    failure_type: str,
) -> None:
    class FakeAdapter:
        def __init__(self, server_name: str) -> None:
            assert server_name == "matgl"

        def call_tool(self, tool_name: str, arguments: dict, timeout_seconds: float = 60.0) -> dict:
            raise exception

    monkeypatch.setattr(atomisticskills_matgl_properties, "AtomisticSkillsMCPAdapter", FakeAdapter)

    result = atomisticskills_matgl_properties.evaluate_atomisticskills_matgl_constraint(
        {"cif": SI_CIF},
        bandgap_task(),
        bandgap_task()["constraints"][0],
        bandgap_spec(),
    )

    assert result["status"] == "error"
    assert result["failure_type"] == failure_type
    assert result["properties"]["reduced_formula"] == "Si"
    assert result["properties"]["atom_count"] == 2
    assert result["scores"]["validity_gate"] == 1.0
