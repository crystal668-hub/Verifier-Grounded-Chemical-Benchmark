from __future__ import annotations

from pathlib import Path

from benchmark.verifier_scripts import run_verification_script


ROOT = Path(__file__).resolve().parents[1]


def torchani_payload(spec_property: str = "torchani_energy_per_atom_hartree") -> dict:
    return {
        "task": {"task_id": "torchani_script_001"},
        "constraint": {
            "type": "window",
            "property": "torchani_total_energy_hartree",
            "verifier_id": "torchani_total_energy_ani2x_v1",
            "min": -80.0,
            "max": -70.0,
            "sigma": 2.0,
        },
        "verifier_spec": {
            "verifier_id": "torchani_total_energy_ani2x_v1",
            "verification_script": "verifiers/quantum_ml/torchani_total_energy.py",
            "property_name": spec_property,
            "backend": {"type": "native_torchani"},
        },
        "candidate": {},
    }


def test_torchani_property_script_rejects_property_mismatch() -> None:
    result = run_verification_script(
        ROOT / "verifiers" / "quantum_ml" / "torchani_total_energy.py",
        torchani_payload(),
        timeout_seconds=60,
    )

    assert result["status"] == "error"
    assert result["failure_type"] == "verifier_spec_error"
    assert result["message"] == (
        "script property 'torchani_total_energy_hartree' does not match "
        "verifier_spec property 'torchani_energy_per_atom_hartree'"
    )
