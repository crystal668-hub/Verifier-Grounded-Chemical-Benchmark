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


def test_expert_domain_counts_all_atoms_and_oxygen_fraction() -> None:
    spec = {
        **SPEC,
        "verifier_id": "rdkit_logp_expert_v1",
        "domain": {
            "allowed_elements": ["H", "C", "O", "N", "S", "F", "Cl"],
            "atom_count": [1, 40],
            "element_fraction_min": {"O": 0.10},
        },
    }
    constraint = {
        "type": "target_distance",
        "property": "logp",
        "target": 3.0,
        "scale": 0.5,
    }

    result = evaluate_descriptor_constraint(
        {"smiles": "CCCCCC(=O)O"},
        {"task_id": "rdkit_logp_target_011"},
        constraint,
        spec,
    )

    assert result["status"] == "ok"
    assert result["properties"]["atom_count"] == 20
    assert result["properties"]["element_counts"] == {"C": 6, "H": 12, "O": 2}
    assert result["properties"]["element_fractions"]["O"] == pytest.approx(0.10)


@pytest.mark.parametrize(
    ("smiles", "domain", "expected_status"),
    [
        ("CCCCCCCCCCCCN", {"atom_count": [1, 40]}, "ok"),
        ("CCCCCCCCCCCCCN", {"atom_count": [1, 40]}, "error"),
        ("CCCCCC(=O)O", {"element_fraction_min": {"O": 0.10}}, "ok"),
        ("CCCCCCC(=O)O", {"element_fraction_min": {"O": 0.10}}, "error"),
        ("C(C(=O)O)[NH3+]", {"element_fraction_min": {"O": 0.10}}, "ok"),
    ],
)
def test_expert_domain_boundaries(
    smiles: str,
    domain: dict,
    expected_status: str,
) -> None:
    spec = {
        **SPEC,
        "domain": {
            "allowed_elements": ["H", "C", "O", "N", "S", "F", "Cl"],
            **domain,
        },
    }
    result = evaluate_descriptor_constraint(
        {"smiles": smiles},
        {"task_id": "expert"},
        {"type": "target_distance", "property": "logp", "target": 3.0, "scale": 0.5},
        spec,
    )

    assert result["status"] == expected_status
    if expected_status == "error":
        assert result["failure_type"] == "domain_error"


def test_expert_domain_rejects_disallowed_elements() -> None:
    spec = {
        **SPEC,
        "domain": {
            "allowed_elements": ["H", "C", "O", "N", "S", "F", "Cl"],
            "atom_count": [1, 40],
            "element_fraction_min": {"O": 0.10},
        },
    }

    result = evaluate_descriptor_constraint(
        {"smiles": "O=C(O)c1ccc(Br)cc1"},
        {"task_id": "expert"},
        {"type": "target_distance", "property": "logp", "target": 3.0, "scale": 0.5},
        spec,
    )

    assert result["status"] == "error"
    assert result["failure_type"] == "domain_error"
    assert "Br" in result["message"]


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
