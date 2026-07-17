from __future__ import annotations

import importlib.util

from verifier_grounded_benchmark.evaluation import EvaluationEngine
from verifier_grounded_benchmark.task.loader import load_task_pack
from verifier_grounded_benchmark.task.resources import package_resource


PACK = load_task_pack(
    package_resource("experimental/rdkit_forcefield", "tasks.yaml"),
    package_resource("experimental/rdkit_forcefield", "verifier_specs.yaml"),
)


def load_tasks() -> list[dict]:
    return list(PACK.tasks_by_id.values())


def load_specs() -> dict[str, dict]:
    return PACK.verifier_specs_by_id


def load_samples() -> list[dict]:
    from verifier_grounded_benchmark.task.loader import load_answers_jsonl_file

    return load_answers_jsonl_file(
        package_resource("experimental/rdkit_forcefield", "sample_answers.jsonl")
    )


def test_rdkit_forcefield_task_pack_binds_to_specs() -> None:
    tasks = load_tasks()
    specs = load_specs()

    assert len(tasks) == 2
    assert {task["task_id"] for task in tasks} == {
        "rdkit_forcefield_energy_range_window_001",
        "rdkit_forcefield_convergence_max_002",
    }
    for task in tasks:
        assert task["object_type"] == "small_molecule"
        assert task["formal_track"] is False
        assert task["answer_schema"]["value_type"] == "smiles"
        for constraint in task["constraints"]:
            spec = specs[constraint["verifier_id"]]
            assert spec["backend"]["type"] == "rdkit_forcefield"
            assert spec["property_name"] == constraint["property"] or constraint["property"] in spec.get(
                "additional_property_names", []
            )
            assert importlib.util.find_spec(spec["executor"]["module"]) is not None


def test_rdkit_forcefield_sample_answers_score_successfully() -> None:
    engine = EvaluationEngine(PACK)

    for sample in load_samples():
        result = engine.evaluate_one(sample)
        assert result["status"] == "scored"
        assert result["failure_type"] is None
        assert result["canonical_smiles"]
        assert 0.0 <= result["scores"]["score"] <= 1.0
