from __future__ import annotations

import importlib.util

from verifier_grounded_benchmark.evaluation import EvaluationEngine
from verifier_grounded_benchmark.task.loader import load_task_pack
from verifier_grounded_benchmark.task.resources import package_resource

PACK = load_task_pack(
    package_resource("rdkit", "tasks.yaml"),
    package_resource("rdkit", "verifier_specs.yaml"),
)


def test_formal_terminal_atom_distance_task_binds_to_uff_spec() -> None:
    task = PACK.tasks_by_id["rdkit_chain_end_to_end_max_013"]
    constraint = task["constraints"][0]
    spec = PACK.verifier_specs_by_id[constraint["verifier_id"]]
    chain_smarts = spec["domain"]["chain_smarts"]

    assert task["formal_track"] is True
    assert task["answer_schema"]["value_type"] == "smiles"
    assert chain_smarts in task["prompt"]
    assert "Universal Force Field (UFF)" in task["prompt"]
    assert "lowest-energy converged UFF conformer" in task["prompt"]
    assert "exactly one non-hydrogen neighbor" in task["prompt"]
    assert "Hydrogens are not terminal-atom candidates" in task["prompt"]
    assert "terminal carbon" not in task["prompt"]
    assert constraint["property"] == "terminal_atom_distance"
    assert spec["version"] == 2
    assert spec["backend"]["forcefield"] == "UFF"
    assert "forcefield_priority" not in spec["backend"]
    assert spec["backend"]["num_conformers"] == 20
    assert importlib.util.find_spec(spec["executor"]["module"]) is not None


def test_formal_chain_distance_sample_scores_successfully() -> None:
    engine = EvaluationEngine(PACK)
    sample = {
        "task_id": "rdkit_chain_end_to_end_max_013",
        "candidates": [{"smiles": "CCCCCC"}],
    }

    result = engine.evaluate_one(sample)

    assert result["status"] == "scored"
    assert result["failure_type"] is None
    assert result["properties"]["forcefield_name"] == "UFF"
    assert result["properties"]["terminal_atom_distance"] == 6.368444271087647
    assert 0.0 <= result["scores"]["score"] <= 1.0
