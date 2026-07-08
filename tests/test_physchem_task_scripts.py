from __future__ import annotations

import io
import json
import sys
from typing import Any

import pytest

from verifiers.molgpka import cli as molgpka_property_script
from verifiers.soltrannet import cli as soltrannet_property_script


def run_in_process(
    main_func: Any,
    property_name: str,
    payload: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, Any]:
    stdout = io.StringIO()
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    monkeypatch.setattr(sys, "stdout", stdout)
    main_func(property_name)
    return json.loads(stdout.getvalue())


def soltrannet_payload(property_name: str = "soltrannet_log_s") -> dict[str, Any]:
    return {
        "task": {"task_id": "soltrannet_script_001"},
        "constraint": {"property": property_name, "type": "window", "min": 0, "max": 3},
        "verifier_spec": {
            "verifier_id": "soltrannet_log_s_v1",
            "property_name": property_name,
            "verifier_image": "verifier-grounded:dev",
        },
        "candidate": {"smiles": "CCO"},
    }


def molgpka_payload(property_name: str = "molgpka_pka_count") -> dict[str, Any]:
    return {
        "task": {"task_id": "molgpka_script_001"},
        "constraint": {"property": property_name, "type": "window", "min": 1, "max": 2},
        "verifier_spec": {
            "verifier_id": f"{property_name}_v1",
            "property_name": property_name,
            "verifier_image": "verifier-grounded:dev",
        },
        "candidate": {"smiles": "CC(O)=O"},
    }


def test_soltrannet_script_helper_calls_evaluator(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_evaluator(
        candidate: dict[str, Any],
        task: dict[str, Any],
        constraint: dict[str, Any],
        spec: dict[str, Any],
    ) -> dict[str, Any]:
        assert candidate == {"smiles": "CCO"}
        assert constraint["property"] == "soltrannet_log_s"
        return {
            "task_id": task["task_id"],
            "verifier_id": spec["verifier_id"],
            "status": "ok",
            "canonical_smiles": "CCO",
            "properties": {"soltrannet_log_s": 2.2},
            "scores": {
                "validity_gate": 1.0,
                "domain_gate": 1.0,
                "constraint_scores": [],
                "property_score": 1.0,
                "score": 1.0,
            },
            "failure_type": None,
            "message": None,
            "versions": {},
        }

    monkeypatch.setattr(soltrannet_property_script, "evaluate_soltrannet_constraint", fake_evaluator)

    result = run_in_process(soltrannet_property_script.main, "soltrannet_log_s", soltrannet_payload(), monkeypatch)

    assert result["status"] == "ok"
    assert result["properties"]["soltrannet_log_s"] == 2.2


def test_soltrannet_script_helper_rejects_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = soltrannet_payload(property_name="other")

    result = run_in_process(soltrannet_property_script.main, "soltrannet_log_s", payload, monkeypatch)

    assert result["status"] == "error"
    assert result["failure_type"] == "verifier_spec_error"


def test_molgpka_script_helper_calls_evaluator(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_evaluator(
        candidate: dict[str, Any],
        task: dict[str, Any],
        constraint: dict[str, Any],
        spec: dict[str, Any],
    ) -> dict[str, Any]:
        assert candidate == {"smiles": "CC(O)=O"}
        assert constraint["property"] == "molgpka_pka_count"
        return {
            "task_id": task["task_id"],
            "verifier_id": spec["verifier_id"],
            "status": "ok",
            "canonical_smiles": "CC(=O)O",
            "properties": {"molgpka_pka_count": 1, "molgpka_pka_values": [8.34]},
            "scores": {
                "validity_gate": 1.0,
                "domain_gate": 1.0,
                "constraint_scores": [],
                "property_score": 1.0,
                "score": 1.0,
            },
            "failure_type": None,
            "message": None,
            "versions": {},
        }

    monkeypatch.setattr(molgpka_property_script, "evaluate_molgpka_constraint", fake_evaluator)

    result = run_in_process(molgpka_property_script.main, "molgpka_pka_count", molgpka_payload(), monkeypatch)

    assert result["status"] == "ok"
    assert result["properties"]["molgpka_pka_count"] == 1


def test_molgpka_script_helper_rejects_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = molgpka_payload(property_name="molgpka_min_pka")

    result = run_in_process(molgpka_property_script.main, "molgpka_pka_count", payload, monkeypatch)

    assert result["status"] == "error"
    assert result["failure_type"] == "verifier_spec_error"
