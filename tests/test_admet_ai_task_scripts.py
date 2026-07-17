from __future__ import annotations

from pathlib import Path
from typing import Any

from verifier_grounded_benchmark.evaluation.open_generation.verification.runner import run_verification_script


ROOT = Path(__file__).resolve().parents[1]


def payload(property_name: str) -> dict[str, Any]:
    return {
        "task": {"task_id": "admet_ai_property_001", "version": 1, "object_type": "small_molecule"},
        "constraint": {
            "type": "minimize_bounded",
            "property": property_name,
            "verifier_id": "admet_ai_property_v1",
            "lower": 0.0,
            "upper": 1.0,
        },
        "verifier_spec": {
            "verifier_id": "admet_ai_property_v1",
            "verification_script": "verifiers/admet_ai/admet_ai_herg.py",
            "property_name": property_name,
            "verifier_image": "verifier-grounded:dev",
            "admet_ai": {"include_physchem": False, "drugbank_percentiles": False, "num_workers": 0},
            "domain": {
                "allowed_elements": ["C", "N", "O", "F", "P", "S", "Cl", "Br", "I"],
                "heavy_atom_count": [1, 80],
                "mw": [1.0, 1000.0],
                "formal_charge": [-2, 2],
            },
        },
        "candidate": {"smiles": "CCO"},
    }


def test_admet_ai_herg_script_outputs_standard_json_result() -> None:
    result = run_verification_script(
        ROOT / "src" / "verifier_grounded_benchmark" / "evaluation" / "open_generation" / "verifiers" / "admet_ai" / "admet_ai_herg.py",
        payload("hERG"),
        timeout_seconds=90,
    )

    assert result["outcome"] == "verified"
    assert result["canonical_candidate"]["smiles"] == "CCO"
    assert 0.0 <= result["properties"]["hERG"] <= 1.0


def test_admet_ai_herg_script_rejects_property_mismatch() -> None:
    result = run_verification_script(
        ROOT / "src" / "verifier_grounded_benchmark" / "evaluation" / "open_generation" / "verifiers" / "admet_ai" / "admet_ai_herg.py",
        payload("AMES"),
        timeout_seconds=90,
    )

    assert result["outcome"] != "verified"
    assert result["failure_type"] == "verifier_spec_error"
