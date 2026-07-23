from __future__ import annotations

import importlib

import pytest

from verifier_grounded_benchmark.evaluation.open_generation.verifiers.rdkit_descriptors import backend as rdkit_descriptors
from verifier_grounded_benchmark.evaluation.open_generation.verifiers.rdkit_descriptors.backend import evaluate_descriptor_constraint


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

    assert result["outcome"] == "verified"
    assert result["task_id"] == "rdkit_logp_window_003"
    assert result["verifier_id"] == "rdkit_logp_v1"
    assert result["canonical_candidate"]["smiles"] == "CC(=O)Oc1ccccc1C(=O)O"
    assert result["properties"] == {"logp": pytest.approx(1.3101, abs=1e-4)}
    assert result["versions"]["verifier_image"] == "verifier-grounded:dev"


def test_rdkit_backend_does_not_expose_unused_bulk_property_helper() -> None:
    assert not hasattr(rdkit_descriptors, "compute_properties")


def test_evaluate_descriptor_constraint_rejects_invalid_smiles() -> None:
    result = evaluate_descriptor_constraint({"smiles": "not a smiles"}, TASK, CONSTRAINT, SPEC)

    assert result["outcome"] != "verified"
    assert result["failure_type"] == "parse_error"


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

    assert result["outcome"] == "verified"
    assert result["properties"]["atom_count"] == 20
    assert result["properties"]["element_counts"] == {"C": 6, "H": 12, "O": 2}
    assert result["properties"]["element_fractions"]["O"] == pytest.approx(0.10)


@pytest.mark.parametrize(
    ("smiles", "domain", "expected_outcome"),
    [
        ("CCCCCCCCCCCCN", {"atom_count": [1, 40]}, "verified"),
        ("CCCCCCCCCCCCCN", {"atom_count": [1, 40]}, "candidate_rejected"),
        ("CCCCCC(=O)O", {"element_fraction_min": {"O": 0.10}}, "verified"),
        ("CCCCCCC(=O)O", {"element_fraction_min": {"O": 0.10}}, "candidate_rejected"),
        ("C(C(=O)O)[NH3+]", {"element_fraction_min": {"O": 0.10}}, "verified"),
    ],
)
def test_expert_domain_boundaries(
    smiles: str,
    domain: dict,
    expected_outcome: str,
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

    assert result["outcome"] == expected_outcome
    if expected_outcome == "candidate_rejected":
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

    assert result["outcome"] != "verified"
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

    assert logp_result["outcome"] == "verified"
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

    assert sa_result["outcome"] != "verified"
    assert sa_result["failure_type"] == "verifier_environment_error"
    assert "RDKit SA_Score scorer unavailable" in sa_result["message"]


def test_expert_sa_logp_domain_requires_carbon_but_not_oxygen() -> None:
    domain = {
        "allowed_elements": ["H", "C", "O", "N", "S", "F", "Cl"],
        "atom_count": [1, 40],
        "element_count_min": {"C": 1},
    }
    sa_result = evaluate_descriptor_constraint(
        {"smiles": "CCCC"},
        {"task_id": "rdkit_sa_logp_target_012"},
        {"property": "sa_score"},
        {
            **SPEC,
            "descriptor": "sa_score",
            "domain": domain,
            "report_domain_properties": True,
        },
    )
    no_carbon_result = evaluate_descriptor_constraint(
        {"smiles": "O"},
        {"task_id": "rdkit_sa_logp_target_012"},
        {"property": "sa_score"},
        {**SPEC, "descriptor": "sa_score", "domain": domain},
    )

    assert sa_result["outcome"] == "verified"
    assert sa_result["properties"]["atom_count"] == 14
    assert sa_result["properties"]["element_counts"] == {"C": 4, "H": 10}
    assert no_carbon_result["failure_type"] == "domain_error"


def test_caffeine_hard_property_verifier_reports_frozen_reference_sa() -> None:
    spec = {
        **SPEC,
        "verifier_id": "rdkit_caffeine_properties_v1",
        "descriptor": "logp",
        "descriptors": ["logp", "sa_score", "qed"],
        "domain": {},
        "reference": {
            "canonical_smiles": "Cn1c(=O)c2c(ncn2C)n(C)c1=O",
            "sa_score": 2.29798245679401,
            "sa_tolerance": 1e-12,
        },
    }

    result = evaluate_descriptor_constraint(
        {"smiles": "Cn1c(=O)c2c(ncn2C)n(C)c1=O"},
        {"task_id": "rdkit_caffeine_similarity_max_014"},
        {"property": "logp"},
        spec,
    )

    assert result["outcome"] == "verified"
    assert result["properties"] == {
        "logp": pytest.approx(-1.0293),
        "sa_score": pytest.approx(2.29798245679401),
        "qed": pytest.approx(0.5384628262372215),
        "reference_sa_score": pytest.approx(2.29798245679401),
    }


def test_caffeine_reference_sa_mismatch_is_task_failure() -> None:
    spec = {
        **SPEC,
        "descriptor": "logp",
        "descriptors": ["logp", "sa_score", "qed"],
        "domain": {},
        "reference": {
            "canonical_smiles": "Cn1c(=O)c2c(ncn2C)n(C)c1=O",
            "sa_score": 2.0,
            "sa_tolerance": 1e-12,
        },
    }

    result = evaluate_descriptor_constraint(
        {"smiles": "CCO"},
        {"task_id": "rdkit_caffeine_similarity_max_014"},
        {"property": "logp"},
        spec,
    )

    assert result["outcome"] == "evaluation_failed"
    assert result["failure_scope"] == "task"
    assert result["failure_type"] == "verifier_spec_error"


def test_caffeine_morgan_similarity_uses_frozen_fingerprint() -> None:
    reference = "Cn1c(=O)c2c(ncn2C)n(C)c1=O"
    spec = {
        **SPEC,
        "descriptor": "caffeine_morgan_tanimoto",
        "domain": {},
        "reference": {"canonical_smiles": reference},
        "fingerprint": {
            "generator": "Morgan",
            "radius": 2,
            "fp_size": 2048,
            "include_chirality": False,
            "use_bond_types": True,
            "fingerprint_type": "bit_vector",
            "similarity": "Tanimoto",
        },
    }

    first = evaluate_descriptor_constraint(
        {"smiles": reference},
        {"task_id": "rdkit_caffeine_similarity_max_014"},
        {"property": "caffeine_morgan_tanimoto"},
        spec,
    )
    equivalent = evaluate_descriptor_constraint(
        {"smiles": "Cn1c(=O)c2c(ncn2C)n(C)c1=O"},
        {"task_id": "rdkit_caffeine_similarity_max_014"},
        {"property": "caffeine_morgan_tanimoto"},
        spec,
    )

    assert first["properties"] == {
        "caffeine_morgan_tanimoto": 1.0,
        "fingerprint_radius": 2,
        "fingerprint_size": 2048,
    }
    assert equivalent["properties"] == first["properties"]


def test_caffeine_fingerprint_parameter_change_is_task_failure() -> None:
    spec = {
        **SPEC,
        "descriptor": "caffeine_morgan_tanimoto",
        "domain": {},
        "reference": {
            "canonical_smiles": "Cn1c(=O)c2c(ncn2C)n(C)c1=O"
        },
        "fingerprint": {
            "generator": "Morgan",
            "radius": 3,
            "fp_size": 2048,
            "include_chirality": False,
            "use_bond_types": True,
            "fingerprint_type": "bit_vector",
            "similarity": "Tanimoto",
        },
    }

    result = evaluate_descriptor_constraint(
        {"smiles": "CCO"},
        {"task_id": "rdkit_caffeine_similarity_max_014"},
        {"property": "caffeine_morgan_tanimoto"},
        spec,
    )

    assert result["failure_type"] == "verifier_spec_error"
