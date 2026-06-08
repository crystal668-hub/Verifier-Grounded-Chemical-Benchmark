from __future__ import annotations

from pathlib import Path

from benchmark.verifier_scripts import run_verification_script


ROOT = Path(__file__).resolve().parents[1]


def gap_payload() -> dict:
    return {
        "task": {"task_id": "xtb_gap_window_001", "version": 1, "object_type": "small_molecule_3d"},
        "constraint": {
            "type": "window",
            "property": "homo_lumo_gap",
            "verifier_id": "xtb_gap_gfn2_v1",
            "min": 4.0,
            "max": 6.0,
            "sigma": 0.75,
        },
        "verifier_spec": {
            "verifier_id": "xtb_gap_gfn2_v1",
            "verification_script": "verifiers/xtb/xtb_gap.py",
            "property_name": "homo_lumo_gap",
            "backend": {"type": "local_xtb", "executable": "xtb", "charge": 0, "uhf": 0},
            "domain": {
                "allowed_elements": ["H", "C", "N", "O", "F", "P", "S", "Cl", "Br"],
                "atom_count": [3, 80],
                "heavy_atom_count": [1, 40],
                "max_absolute_coordinate": 30.0,
                "min_interatomic_distance": 0.45,
                "inferred_components": 1,
            },
        },
        "candidate": {},
    }


def test_xtb_property_script_rejects_property_mismatch() -> None:
    payload = gap_payload()
    payload["verifier_spec"] = {**payload["verifier_spec"], "property_name": "dipole_moment"}

    result = run_verification_script(ROOT / "verifiers" / "xtb" / "xtb_gap.py", payload, timeout_seconds=60)

    assert result["status"] == "error"
    assert result["task_id"] == "xtb_gap_window_001"
    assert result["verifier_id"] == "xtb_gap_gfn2_v1"
    assert result["failure_type"] == "verifier_spec_error"
    assert "script property 'homo_lumo_gap' does not match verifier_spec property 'dipole_moment'" == result["message"]
    assert result["scores"]["score"] == 0.0


def test_xtb_property_script_outputs_standard_json_result_for_missing_candidate() -> None:
    result = run_verification_script(
        ROOT / "verifiers" / "xtb" / "xtb_gap.py",
        gap_payload(),
        timeout_seconds=60,
    )

    assert result["status"] == "error"
    assert result["task_id"] == "xtb_gap_window_001"
    assert result["verifier_id"] == "xtb_gap_gfn2_v1"
    assert result["canonical_smiles"] is None
    assert result["failure_type"] == "parse_error"
    assert result["message"] == "candidate must include an XYZ string"
    assert result["properties"] == {}
    assert result["scores"] == {
        "validity_gate": 0.0,
        "domain_gate": 0.0,
        "constraint_scores": [],
        "property_score": 0.0,
        "score": 0.0,
    }


def test_all_xtb_property_scripts_reject_mismatched_property() -> None:
    cases = [
        ("xtb_gap.py", "homo_lumo_gap", "dipole_moment"),
        ("xtb_dipole.py", "dipole_moment", "homo_lumo_gap"),
        ("xtb_relaxation_energy.py", "relaxation_energy", "homo_lumo_gap"),
    ]
    for script, constraint_property, spec_property in cases:
        payload = gap_payload()
        payload["constraint"] = {**payload["constraint"], "property": constraint_property}
        payload["verifier_spec"] = {**payload["verifier_spec"], "property_name": spec_property}

        result = run_verification_script(ROOT / "verifiers" / "xtb" / script, payload, timeout_seconds=60)

        assert result["status"] == "error"
        assert result["failure_type"] == "verifier_spec_error"
