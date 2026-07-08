from __future__ import annotations

import importlib

import pytest

from verifiers.rdkit_descriptors import backend as rdkit_descriptors
from verifiers.rdkit_descriptors.backend import evaluate_descriptor_constraint


SPEC = {
    "verifier_id": "rdkit_logp_v1",
    "verifier_image": "verifier-grounded:dev",
    "descriptor": "logp",
    "domain": {
        "allowed_elements": ["H", "B", "C", "N", "O", "F", "P", "S", "Cl", "Br", "I"],
        "heavy_atom_count": [5, 60],
        "mw": [0.0, 600.0],
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


def test_rdkit_backend_does_not_expose_unused_bulk_property_helper() -> None:
    assert not hasattr(rdkit_descriptors, "compute_properties")


def test_evaluate_descriptor_constraint_rejects_invalid_smiles() -> None:
    result = evaluate_descriptor_constraint({"smiles": "not a smiles"}, TASK, CONSTRAINT, SPEC)

    assert result["status"] == "error"
    assert result["failure_type"] == "parse_error"
    assert result["scores"]["score"] == 0.0


def test_sa_score_import_failure_only_affects_sa_score(monkeypatch: pytest.MonkeyPatch) -> None:
    real_import_module = importlib.import_module

    def fail_sa_scorer(name: str, package: str | None = None):
        if name == "rdkit.Contrib.SA_Score.sascorer":
            raise ImportError("missing SA scorer")
        return real_import_module(name, package)

    monkeypatch.setattr(rdkit_descriptors.importlib, "import_module", fail_sa_scorer)

    logp_result = evaluate_descriptor_constraint(
        {"smiles": "CC(=O)Oc1ccccc1C(=O)O"},
        TASK,
        CONSTRAINT,
        SPEC,
    )

    assert logp_result["status"] == "ok"
    assert logp_result["failure_type"] is None
    assert logp_result["properties"] == {"logp": pytest.approx(1.3101, abs=1e-4)}

    sa_spec = {**SPEC, "verifier_id": "rdkit_sa_score_v1", "descriptor": "sa_score"}
    sa_task = {"task_id": "rdkit_sa_score_minimize_001"}
    sa_constraint = {"type": "minimize_bounded", "property": "sa_score", "lower": 1.0, "upper": 10.0}

    sa_result = evaluate_descriptor_constraint(
        {"smiles": "CC(=O)Oc1ccccc1C(=O)O"},
        sa_task,
        sa_constraint,
        sa_spec,
    )

    assert sa_result["status"] == "error"
    assert sa_result["failure_type"] == "verifier_environment_error"
    assert "RDKit SA_Score scorer unavailable" in sa_result["message"]
    assert sa_result["scores"]["score"] == 0.0
