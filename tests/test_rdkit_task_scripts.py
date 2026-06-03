from __future__ import annotations

from pathlib import Path

import yaml

from benchmark.verifier_scripts import run_verification_script


ROOT = Path(__file__).resolve().parents[1]
TASKS_PATH = ROOT / "tasks" / "rdkit_baseline" / "tasks.yaml"
SPECS_PATH = ROOT / "tasks" / "rdkit_baseline" / "verifier_specs.yaml"


def load_tasks() -> list[dict]:
    with TASKS_PATH.open() as handle:
        return yaml.safe_load(handle)["tasks"]


def load_specs() -> dict[str, dict]:
    with SPECS_PATH.open() as handle:
        payload = yaml.safe_load(handle)
    return {spec["verifier_id"]: spec for spec in payload["verifiers"]}


def test_rdkit_descriptor_script_outputs_single_constraint_result_json() -> None:
    task = next(task for task in load_tasks() if task["task_id"] == "rdkit_logp_window_003")
    constraint = task["constraints"][0]
    spec = load_specs()[constraint["verifier_id"]]
    payload = {
        "task": {"task_id": task["task_id"], "version": task["version"], "object_type": task["object_type"]},
        "constraint": constraint,
        "verifier_spec": spec,
        "candidate": {"smiles": "CC(=O)Oc1ccccc1C(=O)O"},
    }

    result = run_verification_script(ROOT / spec["verification_script"], payload, timeout_seconds=60)

    assert result["status"] == "ok"
    assert result["task_id"] == "rdkit_logp_window_003"
    assert result["verifier_id"] == "rdkit_logp_v1"
    assert result["canonical_smiles"] == "CC(=O)Oc1ccccc1C(=O)O"
    assert set(result["properties"]) == {"logp"}
    assert result["scores"]["constraint_scores"] == [{"property": "logp", "type": "window", "score": 1.0}]
    assert result["scores"]["score"] == 1.0
