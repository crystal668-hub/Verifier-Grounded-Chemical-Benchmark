from __future__ import annotations

from pathlib import Path

import pytest

from verifier_grounded_benchmark.evaluation.open_generation.verification.runner import run_verification_script


ROOT = Path(__file__).resolve().parents[1]


def bandgap_payload() -> dict:
    return {
        "task": {"task_id": "matgl_bandgap_window_si_001", "version": 1, "object_type": "crystal_structure"},
        "constraint": {
            "type": "window",
            "property": "bandgap",
            "verifier_id": "matgl_bandgap_native_v1",
            "min": 0.8,
            "max": 1.2,
            "sigma": 0.2,
        },
        "verifier_spec": {
            "verifier_id": "matgl_bandgap_native_v1",
            "verification_script": "verifiers/matgl/matgl_bandgap.py",
            "property_name": "formation_energy",
            "backend": {"type": "native_matgl"},
        },
        "candidate": {},
    }


def formation_energy_payload() -> dict:
    return {
        "task": {"task_id": "matgl_eform_window_si_002", "version": 1, "object_type": "crystal_structure"},
        "constraint": {
            "type": "window",
            "property": "formation_energy",
            "verifier_id": "matgl_formation_energy_native_v1",
            "min": -0.05,
            "max": 0.05,
            "sigma": 0.05,
        },
        "verifier_spec": {
            "verifier_id": "matgl_formation_energy_native_v1",
            "verification_script": "verifiers/matgl/matgl_formation_energy.py",
            "property_name": "bandgap",
            "backend": {"type": "native_matgl"},
        },
        "candidate": {},
    }


@pytest.mark.parametrize(
    ("script_name", "payload", "expected_message"),
    [
        (
            "matgl_bandgap.py",
            bandgap_payload(),
            "script property 'bandgap' does not match verifier_spec property 'formation_energy'",
        ),
        (
            "matgl_formation_energy.py",
            formation_energy_payload(),
            "script property 'formation_energy' does not match verifier_spec property 'bandgap'",
        ),
    ],
)
def test_matgl_property_scripts_reject_property_mismatch(
    script_name: str,
    payload: dict,
    expected_message: str,
) -> None:
    result = run_verification_script(
        ROOT / "src" / "verifier_grounded_benchmark" / "evaluation" / "open_generation" / "verifiers" / "matgl" / script_name,
        payload,
        timeout_seconds=60,
    )

    assert result["outcome"] != "verified"
    assert result["task_id"] == payload["task"]["task_id"]
    assert result["verifier_id"] == payload["verifier_spec"]["verifier_id"]
    assert result["failure_type"] == "verifier_spec_error"
    assert result["message"] == expected_message
    assert result["failure_scope"] == "task"
    assert "scores" not in result
