from __future__ import annotations

import pytest

from verifier_grounded_benchmark.evaluation.open_generation.verifiers.rdkit_forcefield.backend import evaluate_forcefield_constraint


SPEC = {
    "verifier_id": "rdkit_forcefield_energy_range_v1",
    "verifier_image": "verifier-grounded:dev",
    "property_name": "energy_range_kcal_mol",
    "backend": {
        "type": "rdkit_forcefield",
        "embedder": "ETKDGv3",
        "random_seed": 61453,
        "num_conformers": 12,
        "prune_rms_thresh": 0.5,
        "forcefield_priority": ["MMFF94s", "MMFF94", "UFF"],
        "max_iters": 200,
    },
    "domain": {
        "allowed_elements": ["H", "B", "C", "N", "O", "F", "P", "S", "Cl", "Br", "I"],
        "heavy_atom_count": [5, 60],
        "mw": [0.0, 600.0],
        "formal_charge": [-1, 1],
    },
}

TASK = {"task_id": "rdkit_forcefield_energy_range_window_001"}
CONSTRAINT = {
    "type": "window",
    "property": "energy_range_kcal_mol",
    "min": 0.0,
    "max": 20.0,
    "sigma": 5.0,
}


def test_evaluate_forcefield_constraint_scores_conformer_ensemble() -> None:
    result = evaluate_forcefield_constraint(
        {"smiles": "CCOc1ccc(NC(=O)C)cc1"},
        TASK,
        CONSTRAINT,
        SPEC,
    )

    assert result["outcome"] == "verified"
    assert result["task_id"] == TASK["task_id"]
    assert result["verifier_id"] == "rdkit_forcefield_energy_range_v1"
    assert result["canonical_candidate"]["smiles"] == "CCOc1ccc(NC(C)=O)cc1"
    assert result["properties"]["forcefield_name"] in {"MMFF94s", "MMFF94"}
    assert result["properties"]["forcefield_parameterized"] == 1
    assert result["properties"]["conformer_count"] >= 1
    assert 0.0 < result["properties"]["embedding_success_rate"] <= 1.0
    assert result["properties"]["optimization_converged_fraction"] >= 0.0
    assert result["properties"]["best_energy_kcal_mol"] == pytest.approx(
        result["properties"]["min_energy_kcal_mol"]
    )
    assert result["properties"]["energy_range_kcal_mol"] >= 0.0
    assert result["properties"]["min_nonbonded_distance_angstrom"] > 0.0
    assert result["versions"]["rdkit"]


def test_evaluate_forcefield_constraint_allows_secondary_property_names() -> None:
    spec = {**SPEC, "property_name": "energy_range_kcal_mol", "additional_property_names": ["optimization_converged_fraction"]}
    constraint = {
        "type": "maximize_bounded",
        "property": "optimization_converged_fraction",
        "lower": 0.0,
        "upper": 1.0,
    }

    result = evaluate_forcefield_constraint({"smiles": "CCOc1ccc(NC(=O)C)cc1"}, TASK, constraint, spec)

    assert result["outcome"] == "verified"
    assert "optimization_converged_fraction" in result["properties"]


def test_evaluate_forcefield_constraint_rejects_invalid_smiles() -> None:
    result = evaluate_forcefield_constraint({"smiles": "not a smiles"}, TASK, CONSTRAINT, SPEC)

    assert result["outcome"] != "verified"
    assert result["failure_type"] == "parse_error"


def test_evaluate_forcefield_constraint_rejects_multi_component_smiles() -> None:
    result = evaluate_forcefield_constraint({"smiles": "CCO.O"}, TASK, CONSTRAINT, SPEC)

    assert result["outcome"] != "verified"
    assert result["failure_type"] == "validity_error"


def test_evaluate_forcefield_constraint_reports_parameterization_failure() -> None:
    spec = {
        **SPEC,
        "backend": {**SPEC["backend"], "forcefield_priority": ["MMFF94"]},
        "domain": {**SPEC["domain"], "allowed_elements": ["H", "C", "Na"], "heavy_atom_count": [1, 60]},
    }

    result = evaluate_forcefield_constraint({"smiles": "[Na]CC"}, TASK, CONSTRAINT, spec)

    assert result["outcome"] != "verified"
    assert result["failure_type"] == "verifier_tool_error"
    assert "parameters" in result["message"]
