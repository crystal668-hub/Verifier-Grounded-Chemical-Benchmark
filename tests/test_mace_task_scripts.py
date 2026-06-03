from __future__ import annotations

from pathlib import Path

from benchmark.verifier_scripts import run_verification_script


ROOT = Path(__file__).resolve().parents[1]


def energy_payload() -> dict:
    return {
        "task": {"task_id": "mace_energy_window_si_001", "version": 1, "object_type": "crystal_structure"},
        "constraint": {
            "type": "window",
            "property": "energy",
            "verifier_id": "mace_energy_mcp_v1",
            "min": -20.0,
            "max": 20.0,
            "sigma": 5.0,
        },
        "verifier_spec": {
            "verifier_id": "mace_energy_mcp_v1",
            "verification_script": "verifiers/materials/mace_energy.py",
            "property_name": "energy",
            "backend": {"type": "atomisticskills_mcp", "server": "mace"},
        },
        "candidate": {},
    }


def test_mace_property_script_rejects_property_mismatch() -> None:
    payload = energy_payload()
    payload["verifier_spec"] = {**payload["verifier_spec"], "property_name": "formation_energy"}

    result = run_verification_script(ROOT / "verifiers" / "materials" / "mace_energy.py", payload, timeout_seconds=60)

    assert result["status"] == "error"
    assert result["task_id"] == "mace_energy_window_si_001"
    assert result["verifier_id"] == "mace_energy_mcp_v1"
    assert result["failure_type"] == "verifier_spec_error"
    assert "script property 'energy' does not match verifier_spec property 'formation_energy'" == result["message"]
    assert result["scores"]["score"] == 0.0


def test_mace_property_script_outputs_standard_json_result() -> None:
    result = run_verification_script(
        ROOT / "verifiers" / "materials" / "mace_energy.py",
        energy_payload(),
        timeout_seconds=60,
    )

    assert result["status"] == "error"
    assert result["task_id"] == "mace_energy_window_si_001"
    assert result["verifier_id"] == "mace_energy_mcp_v1"
    assert result["canonical_smiles"] is None
    assert result["failure_type"] == "parse_error"
    assert result["properties"] == {}
    assert result["scores"] == {
        "validity_gate": 0.0,
        "domain_gate": 0.0,
        "constraint_scores": [],
        "property_score": 0.0,
        "score": 0.0,
    }

