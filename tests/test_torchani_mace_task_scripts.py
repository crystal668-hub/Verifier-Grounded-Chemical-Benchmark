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
            "verification_script": "verifiers/torchani/torchani_total_energy.py",
            "property_name": spec_property,
            "backend": {"type": "native_torchani"},
        },
        "candidate": {},
    }


def test_torchani_property_script_rejects_property_mismatch() -> None:
    result = run_verification_script(
        ROOT / "verifiers" / "torchani" / "torchani_total_energy.py",
        torchani_payload(),
        timeout_seconds=60,
    )

    assert result["status"] == "error"
    assert result["failure_type"] == "verifier_spec_error"
    assert result["message"] == (
        "script property 'torchani_total_energy_hartree' does not match "
        "verifier_spec property 'torchani_energy_per_atom_hartree'"
    )


def mace_payload(spec_property: str = "mace_mp_energy_ev") -> dict:
    return {
        "task": {"task_id": "mace_script_001"},
        "constraint": {
            "type": "window",
            "property": "mace_mp_energy_per_atom_ev",
            "verifier_id": "mace_mp_energy_per_atom_small_v1",
            "min": -6.0,
            "max": -4.0,
            "sigma": 0.5,
        },
        "verifier_spec": {
            "verifier_id": "mace_mp_energy_per_atom_small_v1",
            "verification_script": "verifiers/mace_mp/mace_mp_energy_per_atom.py",
            "property_name": spec_property,
            "backend": {"type": "native_mace_mp"},
        },
        "candidate": {},
    }


def test_mace_property_script_rejects_property_mismatch() -> None:
    result = run_verification_script(
        ROOT / "verifiers" / "mace_mp" / "mace_mp_energy_per_atom.py",
        mace_payload(),
        timeout_seconds=60,
    )

    assert result["status"] == "error"
    assert result["failure_type"] == "verifier_spec_error"
    assert result["message"] == (
        "script property 'mace_mp_energy_per_atom_ev' does not match "
        "verifier_spec property 'mace_mp_energy_ev'"
    )
