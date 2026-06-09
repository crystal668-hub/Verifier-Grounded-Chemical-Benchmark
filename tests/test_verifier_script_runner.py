from __future__ import annotations

import json
import sys
from pathlib import Path

from benchmark.verifier_scripts import build_script_payload, run_verification_script


def test_build_script_payload_uses_first_candidate() -> None:
    structural_domain = {"carbon_count_min": 2, "formula_denylist": ["H2O"]}
    task = {"task_id": "task_1", "constraints": [], "structural_domain": structural_domain}
    constraint = {"type": "window", "property": "logp", "verifier_id": "rdkit_logp_v1"}
    spec = {"verifier_id": "rdkit_logp_v1", "verification_script": "verifiers/descriptors/rdkit_logp.py"}
    answer = {
        "task_id": "task_1",
        "candidates": [{"smiles": "CCO"}],
        "raw_answer": "FINAL ANSWER: CCO",
        "extracted_answer": "CCO",
    }

    payload = build_script_payload(answer, task, constraint, spec)

    assert payload == {
        "task": {"task_id": "task_1", "structural_domain": structural_domain},
        "constraint": constraint,
        "verifier_spec": spec,
        "candidate": {"smiles": "CCO"},
    }
    assert "raw_answer" not in payload
    assert "extracted_answer" not in payload


def test_run_verification_script_round_trips_json(tmp_path: Path) -> None:
    script = tmp_path / "echo_verifier.py"
    script.write_text(
        "import json, sys\n"
        "payload = json.load(sys.stdin)\n"
        "json.dump({'task_id': payload['task']['task_id'], 'status': 'ok', 'failure_type': None, 'properties': {}, 'scores': {'score': 1.0}, 'versions': {}}, sys.stdout)\n"
    )

    result = run_verification_script(
        script,
        {"task": {"task_id": "task_1"}, "constraint": {}, "verifier_spec": {}, "candidate": {"smiles": "CCO"}},
        timeout_seconds=5,
        python_executable=sys.executable,
    )

    assert result["task_id"] == "task_1"
    assert result["status"] == "ok"
    assert result["scores"]["score"] == 1.0
