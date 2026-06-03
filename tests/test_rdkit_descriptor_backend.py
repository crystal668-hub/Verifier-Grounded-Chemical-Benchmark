from __future__ import annotations

import pytest

from verifiers.backends.rdkit_descriptors import evaluate_descriptor_constraint


SPEC = {
    "verifier_id": "rdkit_logp_v1",
    "verifier_image": "verifier-grounded:dev",
    "descriptor": "logp",
    "domain": {
        "allowed_elements": ["H", "B", "C", "N", "O", "F", "P", "S", "Cl", "Br", "I"],
        "heavy_atom_count": [5, 60],
        "mw": [80.0, 600.0],
        "formal_charge": [-1, 1],
    },
}


TASK = {
    "task_id": "rdkit_logp_window_003",
}

CONSTRAINT = {"type": "window", "property": "logp", "min": 1.0, "max": 3.0, "sigma": 0.5}


def test_evaluate_descriptor_constraint_scores_valid_smiles() -> None:
    result = evaluate_descriptor_constraint({"smiles": "CC(=O)Oc1ccccc1C(=O)O"}, TASK, CONSTRAINT, SPEC)

    assert result["status"] == "ok"
    assert result["task_id"] == "rdkit_logp_window_003"
    assert result["verifier_id"] == "rdkit_logp_v1"
    assert result["canonical_smiles"] == "CC(=O)Oc1ccccc1C(=O)O"
    assert result["properties"] == {"logp": pytest.approx(1.3101, abs=1e-4)}
    assert result["scores"]["constraint_scores"] == [{"property": "logp", "type": "window", "score": 1.0}]
    assert result["scores"]["score"] == 1.0
    assert result["versions"]["verifier_image"] == "verifier-grounded:dev"


def test_evaluate_descriptor_constraint_rejects_invalid_smiles() -> None:
    result = evaluate_descriptor_constraint({"smiles": "not a smiles"}, TASK, CONSTRAINT, SPEC)

    assert result["status"] == "error"
    assert result["failure_type"] == "parse_error"
    assert result["scores"]["score"] == 0.0
