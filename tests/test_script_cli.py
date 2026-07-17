from __future__ import annotations

import io
import json
import sys
from typing import Any

import pytest

from verifier_grounded_benchmark.evaluation.open_generation.verifiers.common.property_cli import run_property_script
from verifier_grounded_benchmark.evaluation.open_generation.verifiers.xtb import cli as xtb_cli


def run_cli_with_payload(
    payload: dict[str, Any],
    *,
    expected_name: str,
    spec_field: str,
    mismatch_label: str,
    evaluator,
    sort_keys: bool = True,
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, Any]:
    stdout = io.StringIO()
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    monkeypatch.setattr(sys, "stdout", stdout)

    run_property_script(
        expected_name=expected_name,
        spec_field=spec_field,
        mismatch_label=mismatch_label,
        evaluator=evaluator,
        sort_keys=sort_keys,
    )

    return json.loads(stdout.getvalue())


def test_run_property_script_returns_standard_mismatch_error(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "task": {"task_id": "task_1"},
        "constraint": {"property": "logp"},
        "verifier_spec": {
            "verifier_id": "rdkit_logp_v1",
            "descriptor": "logp",
            "verifier_image": "verifier-grounded:dev",
        },
        "candidate": {"smiles": "CCO"},
    }

    def evaluator(candidate: dict[str, Any], task: dict[str, Any], constraint: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
        raise AssertionError("evaluator should not be called for mismatched scripts")

    result = run_cli_with_payload(
        payload,
        expected_name="qed",
        spec_field="descriptor",
        mismatch_label="descriptor",
        evaluator=evaluator,
        monkeypatch=monkeypatch,
    )

    assert result == {
        "canonical_candidate": {},
        "diagnostics": {},
        "failure_type": "verifier_spec_error",
        "failure_scope": "task",
        "message": "script descriptor 'qed' does not match verifier_spec descriptor 'logp'",
        "outcome": "evaluation_failed",
        "properties": {},
        "task_id": "task_1",
        "verifier_id": "rdkit_logp_v1",
        "versions": {"verifier_image": "verifier-grounded:dev"},
    }


def test_run_property_script_calls_evaluator_with_payload_parts(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "task": {"task_id": "xtb_gap_window_001"},
        "constraint": {"property": "homo_lumo_gap"},
        "verifier_spec": {"verifier_id": "xtb_gap_gfn2_v1", "property_name": "homo_lumo_gap"},
        "candidate": {"xyz": "3\nwater\nO 0 0 0\nH 0 0 1\nH 1 0 0"},
    }
    calls: list[tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]] = []

    def evaluator(candidate: dict[str, Any], task: dict[str, Any], constraint: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
        calls.append((candidate, task, constraint, spec))
        return {
            "outcome": "verified",
            "task_id": task["task_id"],
            "verifier_id": spec["verifier_id"],
            "canonical_candidate": candidate,
            "properties": {"homo_lumo_gap": 4.2},
            "diagnostics": {},
            "failure_scope": None,
            "failure_type": None,
            "message": None,
            "versions": {"backend": "fake"},
        }

    result = run_cli_with_payload(
        payload,
        expected_name="homo_lumo_gap",
        spec_field="property_name",
        mismatch_label="property",
        evaluator=evaluator,
        sort_keys=False,
        monkeypatch=monkeypatch,
    )

    assert calls == [
        (
            payload["candidate"],
            payload["task"],
            payload["constraint"],
            payload["verifier_spec"],
        )
    ]
    assert result["outcome"] == "verified"
    assert result["properties"] == {"homo_lumo_gap": 4.2}


def test_xtb_cli_outputs_sorted_json_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "task": {"task_id": "xtb_gap_window_001"},
        "constraint": {"property": "homo_lumo_gap"},
        "verifier_spec": {"verifier_id": "xtb_gap_gfn2_v1", "property_name": "homo_lumo_gap"},
        "candidate": {"xyz": "3\nwater\nO 0 0 0\nH 0 0 1\nH 1 0 0"},
    }
    stdout = io.StringIO()

    def evaluator(candidate: dict[str, Any], task: dict[str, Any], constraint: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
        return {"z_key": 1, "a_key": {"z_nested": 2, "a_nested": 3}}

    monkeypatch.setattr(xtb_cli, "evaluate_xtb_property_constraint", evaluator)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    monkeypatch.setattr(sys, "stdout", stdout)

    xtb_cli.main("homo_lumo_gap")

    assert stdout.getvalue() == '{"a_key": {"a_nested": 3, "z_nested": 2}, "z_key": 1}'
