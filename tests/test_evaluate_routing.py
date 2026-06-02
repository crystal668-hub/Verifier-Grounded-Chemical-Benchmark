from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from benchmark.evaluate import (
    evaluate_many,
    evaluate_one,
    load_answers_jsonl,
    load_tasks,
    load_verifier_specs,
    summarize_row,
)
from verifiers.registry import UnknownVerifierError, get_verifier


ROOT = Path(__file__).resolve().parents[1]
TASKS_PATH = ROOT / "tasks" / "rdkit_baseline" / "tasks.yaml"
SPECS_PATH = ROOT / "tasks" / "rdkit_baseline" / "verifier_specs.yaml"
ANSWERS_PATH = ROOT / "tasks" / "rdkit_baseline" / "sample_answers.jsonl"

FINAL_ANSWER_SCHEMA = {
    "format": "final_answer_line",
    "final_answer_prefix": "FINAL ANSWER:",
    "value_type": "smiles",
    "cardinality": "one",
}


def test_registry_rejects_unknown_verifier() -> None:
    with pytest.raises(UnknownVerifierError, match="unknown verifier_id"):
        get_verifier("missing_verifier_v1")


def test_evaluate_one_routes_by_task_and_verifier_id() -> None:
    tasks = load_tasks(TASKS_PATH)
    specs = load_verifier_specs(SPECS_PATH)
    answer = {"task_id": "rdkit_qed_max_001", "candidates": [{"smiles": "COc1ccc2cc([C@@H](C)C(=O)O)ccc2c1"}]}

    result = evaluate_one(answer, tasks, specs)

    assert specs[tasks["rdkit_qed_max_001"]["verifier_id"]]["verification_script"].endswith("rdkit_qed_max_001.py")
    assert result["status"] == "ok"
    assert result["task_id"] == "rdkit_qed_max_001"
    assert result["canonical_smiles"] == "COc1ccc2cc([C@@H](C)C(=O)O)ccc2c1"
    assert result["scores"]["score"] == pytest.approx(0.8810778082204156)


def test_evaluate_one_extracts_raw_response_before_routing() -> None:
    tasks = load_tasks(TASKS_PATH)
    tasks["rdkit_qed_max_001"]["answer_schema"] = FINAL_ANSWER_SCHEMA
    specs = load_verifier_specs(SPECS_PATH)
    answer = {
        "task_id": "rdkit_qed_max_001",
        "response": "QED should be high for this candidate.\nFINAL ANSWER: COc1ccc2cc([C@@H](C)C(=O)O)ccc2c1",
    }

    result = evaluate_one(answer, tasks, specs)

    assert result["status"] == "ok"
    assert result["task_id"] == "rdkit_qed_max_001"
    assert result["canonical_smiles"] == "COc1ccc2cc([C@@H](C)C(=O)O)ccc2c1"
    assert result["raw_answer"] == answer["response"]
    assert result["extracted_answer"] == "COc1ccc2cc([C@@H](C)C(=O)O)ccc2c1"
    assert result["scores"]["score"] == pytest.approx(0.8810778082204156)


def test_evaluate_one_returns_parse_error_for_missing_final_answer_line() -> None:
    tasks = load_tasks(TASKS_PATH)
    tasks["rdkit_qed_max_001"]["answer_schema"] = FINAL_ANSWER_SCHEMA
    specs = load_verifier_specs(SPECS_PATH)
    answer = {"task_id": "rdkit_qed_max_001", "response": "I choose CCO."}

    result = evaluate_one(answer, tasks, specs)

    assert result["status"] == "error"
    assert result["failure_type"] == "parse_error"
    assert result["scores"]["score"] == 0.0
    assert "missing final answer line" in result["message"]


def test_summarize_row_preserves_extraction_fields_when_present() -> None:
    row = summarize_row(
        {
            "task_id": "task_1",
            "status": "ok",
            "failure_type": None,
            "canonical_smiles": "CCO",
            "raw_answer": "Reasoning\nFINAL ANSWER: CCO",
            "extracted_answer": "CCO",
            "properties": {},
            "scores": {"score": 1.0, "constraint_scores": []},
        }
    )

    assert row["raw_answer"] == "Reasoning\nFINAL ANSWER: CCO"
    assert row["extracted_answer"] == "CCO"


def test_evaluate_many_scores_sample_answers_with_summary() -> None:
    tasks = load_tasks(TASKS_PATH)
    specs = load_verifier_specs(SPECS_PATH)
    answers = load_answers_jsonl(ANSWERS_PATH)

    report = evaluate_many(answers, tasks, specs)

    assert report["summary"]["num_answers"] == 12
    assert report["summary"]["num_ok"] == 12
    assert report["summary"]["num_error"] == 0
    assert report["summary"]["min_score"] == pytest.approx(0.863812109226767)
    assert report["summary"]["max_score"] == 1.0
    assert len(report["rows"]) == 12


def test_unknown_task_id_returns_structured_error() -> None:
    result = evaluate_one({"task_id": "missing_task", "candidates": [{"smiles": "CCO"}]}, {}, {})

    assert result["status"] == "error"
    assert result["failure_type"] == "task_error"
    assert result["scores"]["score"] == 0.0


def test_missing_verifier_spec_returns_structured_error() -> None:
    tasks = {
        "task_1": {
            "task_id": "task_1",
            "verifier_id": "small_molecule_rdkit_v1",
        }
    }

    result = evaluate_one({"task_id": "task_1", "candidates": [{"smiles": "CCO"}]}, tasks, {})

    assert result["status"] == "error"
    assert result["failure_type"] == "verifier_spec_error"


def test_unknown_registry_verifier_returns_structured_error() -> None:
    tasks = {
        "task_1": {
            "task_id": "task_1",
            "verifier_id": "unknown_verifier_v1",
        }
    }
    specs = {"unknown_verifier_v1": {"verifier_id": "unknown_verifier_v1"}}

    result = evaluate_one({"task_id": "task_1", "candidates": [{"smiles": "CCO"}]}, tasks, specs)

    assert result["status"] == "error"
    assert result["failure_type"] == "verifier_registry_error"


def test_score_answers_cli_outputs_summary_json() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/score_answers.py",
            "--answers",
            str(ANSWERS_PATH),
        ],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )

    report = json.loads(completed.stdout)
    assert report["summary"]["num_answers"] == 12
    assert report["summary"]["num_ok"] == 12
    assert report["summary"]["num_error"] == 0
    assert len(report["rows"]) == 12
