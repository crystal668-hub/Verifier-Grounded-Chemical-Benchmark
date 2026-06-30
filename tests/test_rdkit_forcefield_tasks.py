from __future__ import annotations

import json
from pathlib import Path

import yaml

from benchmark.evaluate import evaluate_one


ROOT = Path(__file__).resolve().parents[1]
TASK_DIR = ROOT / "tasks" / "rdkit_forcefield"


def load_tasks() -> list[dict]:
    with (TASK_DIR / "tasks.yaml").open() as handle:
        return yaml.safe_load(handle)["tasks"]


def load_specs() -> dict[str, dict]:
    with (TASK_DIR / "verifier_specs.yaml").open() as handle:
        payload = yaml.safe_load(handle)
    return {spec["verifier_id"]: spec for spec in payload["verifiers"]}


def load_samples() -> list[dict]:
    with (TASK_DIR / "sample_answers.jsonl").open() as handle:
        return [json.loads(line) for line in handle if line.strip()]


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
            assert (ROOT / spec["verification_script"]).exists()


def test_rdkit_forcefield_sample_answers_score_successfully() -> None:
    tasks = {task["task_id"]: task for task in load_tasks()}
    specs = load_specs()

    for sample in load_samples():
        result = evaluate_one(sample, tasks, specs)
        assert result["status"] == "ok"
        assert result["failure_type"] is None
        assert result["canonical_smiles"]
        assert 0.0 <= result["scores"]["score"] <= 1.0
