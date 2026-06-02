from __future__ import annotations

import json
import sys
from pathlib import Path

from benchmark.verifier_scripts import build_script_payload, run_verification_script


def test_build_script_payload_uses_first_candidate() -> None:
    task = {"task_id": "task_1", "constraints": []}
    spec = {"verifier_id": "verifier_1", "verification_script": "verifiers/tasks/example.py"}
    answer = {"task_id": "task_1", "candidates": [{"smiles": "CCO"}]}

    payload = build_script_payload(answer, task, spec)

    assert payload == {
        "task": task,
        "verifier_spec": spec,
        "candidate": {"smiles": "CCO"},
    }


def test_run_verification_script_round_trips_json(tmp_path: Path) -> None:
    script = tmp_path / "echo_verifier.py"
    script.write_text(
        "import json, sys\n"
        "payload = json.load(sys.stdin)\n"
        "json.dump({'task_id': payload['task']['task_id'], 'status': 'ok', 'failure_type': None, 'properties': {}, 'scores': {'score': 1.0}, 'versions': {}}, sys.stdout)\n"
    )

    result = run_verification_script(
        script,
        {"task": {"task_id": "task_1"}, "verifier_spec": {}, "candidate": {"smiles": "CCO"}},
        timeout_seconds=5,
        python_executable=sys.executable,
    )

    assert result["task_id"] == "task_1"
    assert result["status"] == "ok"
    assert result["scores"]["score"] == 1.0
