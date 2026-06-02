from __future__ import annotations

from pathlib import Path

import yaml

from benchmark.verifier_scripts import run_verification_script


ROOT = Path(__file__).resolve().parents[1]
TASKS_PATH = ROOT / "tasks" / "rdkit_baseline" / "tasks.yaml"


def load_tasks() -> list[dict]:
    with TASKS_PATH.open() as handle:
        return yaml.safe_load(handle)["tasks"]


def test_rdkit_task_script_outputs_result_json() -> None:
    task = next(task for task in load_tasks() if task["task_id"] == "rdkit_logp_window_003")
    spec = {
        "verifier_id": "rdkit_logp_window_003_v1",
        "verifier_image": "verifier-grounded:dev",
        "verification_script": "verifiers/tasks/rdkit_logp_window_003.py",
        "timeout_seconds": 60,
        "domain": {
            "allowed_elements": ["H", "B", "C", "N", "O", "F", "P", "S", "Cl", "Br", "I"],
            "heavy_atom_count": [5, 60],
            "mw": [80.0, 600.0],
            "formal_charge": [-1, 1],
        },
    }
    payload = {"task": task, "verifier_spec": spec, "candidate": {"smiles": "CC(=O)Oc1ccccc1C(=O)O"}}

    result = run_verification_script(ROOT / spec["verification_script"], payload, timeout_seconds=60)

    assert result["status"] == "ok"
    assert result["task_id"] == "rdkit_logp_window_003"
    assert result["canonical_smiles"] == "CC(=O)Oc1ccccc1C(=O)O"
    assert result["scores"]["score"] == 1.0
