from __future__ import annotations

import json
import sys
import textwrap
from pathlib import Path

from benchmark.verifier_scripts import build_script_payload, run_verification_script


ROOT = Path(__file__).resolve().parents[1]


def test_build_script_payload_uses_first_candidate() -> None:
    structural_domain = {"carbon_count_min": 2, "formula_denylist": ["H2O"]}
    structure_identity = {
        "reference_smiles": "CCO",
        "require_stereochemistry": False,
    }
    task = {
        "task_id": "task_1",
        "constraints": [],
        "structural_domain": structural_domain,
        "structure_identity": structure_identity,
    }
    constraint = {"type": "window", "property": "logp", "verifier_id": "rdkit_logp_v1"}
    spec = {"verifier_id": "rdkit_logp_v1", "verification_script": "verifiers/rdkit_descriptors/rdkit_logp.py"}
    answer = {
        "task_id": "task_1",
        "candidates": [{"smiles": "CCO"}],
        "raw_answer": "FINAL ANSWER: CCO",
        "extracted_answer": "CCO",
    }

    payload = build_script_payload(answer, task, constraint, spec)

    assert payload == {
        "task": {
            "task_id": "task_1",
            "structural_domain": structural_domain,
            "structure_identity": structure_identity,
        },
        "constraint": constraint,
        "verifier_spec": spec,
        "candidate": {"smiles": "CCO"},
    }
    assert "raw_answer" not in payload
    assert "extracted_answer" not in payload


def test_run_verification_script_resolves_legacy_root_relative_script_path() -> None:
    result = run_verification_script(
        ROOT / "verifiers" / "xtb" / "xtb_gap.py",
        {
            "task": {"task_id": "xtb_gap_window_001"},
            "constraint": {"property": "homo_lumo_gap", "verifier_id": "xtb_gap_gfn2_v1"},
            "verifier_spec": {
                "verifier_id": "xtb_gap_gfn2_v1",
                "property_name": "homo_lumo_gap",
                "domain": {},
            },
            "candidate": {},
        },
        timeout_seconds=5,
        python_executable=sys.executable,
    )

    assert result["status"] == "error"
    assert result["failure_type"] == "parse_error"
    assert result["message"] == "candidate must include an XYZ string"


def test_run_verification_script_round_trips_json(tmp_path: Path) -> None:
    script = tmp_path / "echo_verifier.py"
    script.write_text(
        "import json, sys\n"
        "payload = json.load(sys.stdin)\n"
        "json.dump({'task_id': payload['task']['task_id'], 'status': 'ok', 'failure_type': None, 'properties': {}, 'scores': {'score': 1.0, 'constraint_scores': []}, 'versions': {}}, sys.stdout)\n"
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


def test_run_verification_script_returns_structured_timeout_error(tmp_path: Path) -> None:
    script = tmp_path / "slow_verifier.py"
    script.write_text("import time\ntime.sleep(10)\n")

    result = run_verification_script(
        script,
        {
            "task": {"task_id": "task_1"},
            "constraint": {},
            "verifier_spec": {"verifier_id": "slow_v1"},
            "candidate": {},
        },
        timeout_seconds=0.01,
        python_executable=sys.executable,
    )

    assert result["task_id"] == "task_1"
    assert result["verifier_id"] == "slow_v1"
    assert result["status"] == "error"
    assert result["failure_type"] == "verifier_timeout"
    assert "timed out" in result["message"]
    assert result["canonical_smiles"] is None
    assert result["properties"] == {}
    assert result["scores"]["score"] == 0.0
    assert result["scores"]["constraint_scores"] == []


def test_run_verification_script_rejects_json_that_is_not_an_object(tmp_path: Path) -> None:
    script = tmp_path / "list_verifier.py"
    script.write_text("import json, sys\njson.dump([], sys.stdout)\n")

    result = run_verification_script(
        script,
        {
            "task": {"task_id": "task_1"},
            "constraint": {},
            "verifier_spec": {"verifier_id": "list_v1"},
            "candidate": {},
        },
        timeout_seconds=5,
        python_executable=sys.executable,
    )

    assert result["task_id"] == "task_1"
    assert result["verifier_id"] == "list_v1"
    assert result["status"] == "error"
    assert result["failure_type"] == "verifier_tool_error"
    assert "JSON object" in result["message"]


def test_run_verification_script_rejects_ok_result_without_constraint_scores(tmp_path: Path) -> None:
    script = tmp_path / "incomplete_verifier.py"
    script.write_text(
        textwrap.dedent(
            """
            import json, sys
            json.dump({
                "task_id": "task_1",
                "verifier_id": "incomplete_v1",
                "status": "ok",
                "properties": {},
                "scores": {"score": 1.0},
                "failure_type": None,
                "message": None,
                "versions": {},
            }, sys.stdout)
            """
        )
    )

    result = run_verification_script(
        script,
        {
            "task": {"task_id": "task_1"},
            "constraint": {},
            "verifier_spec": {"verifier_id": "incomplete_v1"},
            "candidate": {},
        },
        timeout_seconds=5,
        python_executable=sys.executable,
    )

    assert result["task_id"] == "task_1"
    assert result["verifier_id"] == "incomplete_v1"
    assert result["status"] == "error"
    assert result["failure_type"] == "verifier_tool_error"
    assert "scores.constraint_scores" in result["message"]
