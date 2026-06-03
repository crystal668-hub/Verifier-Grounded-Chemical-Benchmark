"""Standard task/verifier routing flow."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from benchmark.answer_extraction import normalize_answer_record
from benchmark.verifier_scripts import build_script_payload, run_verification_script


ROOT = Path(__file__).resolve().parents[1]


def load_tasks(path: str | Path) -> dict[str, dict[str, Any]]:
    with Path(path).open() as handle:
        payload = yaml.safe_load(handle)
    return {task["task_id"]: task for task in payload["tasks"]}


def load_verifier_specs(path: str | Path) -> dict[str, dict[str, Any]]:
    with Path(path).open() as handle:
        payload = yaml.safe_load(handle)
    return {spec["verifier_id"]: spec for spec in payload["verifiers"]}


def load_answers_jsonl(path: str | Path) -> list[dict[str, Any]]:
    with Path(path).open() as handle:
        return [json.loads(line) for line in handle if line.strip()]


def evaluate_one(
    answer: dict[str, Any],
    tasks: dict[str, dict[str, Any]],
    specs: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    task_id = answer.get("task_id")
    if not isinstance(task_id, str) or not task_id:
        return routing_error(None, "task_error", "answer must include a task_id string")

    task = tasks.get(task_id)
    if task is None:
        return routing_error(task_id, "task_error", f"unknown task_id: {task_id}")

    extraction = normalize_answer_record(answer, task)
    if not extraction.ok:
        return routing_error(task_id, extraction.failure_type or "parse_error", extraction.message or "answer parse failed")
    normalized_answer = extraction.answer or answer

    constraints = task.get("constraints")
    if not isinstance(constraints, list) or not constraints:
        return routing_error(task_id, "verifier_spec_error", "task must include at least one constraint")

    results: list[dict[str, Any]] = []
    for constraint in constraints:
        if not isinstance(constraint, dict):
            return routing_error(task_id, "verifier_spec_error", "task constraints must be objects")
        verifier_id = constraint.get("verifier_id")
        if not isinstance(verifier_id, str) or not verifier_id:
            return routing_error(task_id, "verifier_spec_error", "constraint is missing verifier_id")
        spec = specs.get(verifier_id)
        if spec is None:
            return routing_error(task_id, "verifier_spec_error", f"missing verifier spec: {verifier_id}")
        verification_script = spec.get("verification_script")
        if not isinstance(verification_script, str) or not verification_script:
            return routing_error(task_id, "verifier_spec_error", f"verifier spec is missing verification_script: {verifier_id}")

        payload = build_script_payload(normalized_answer, task, constraint, spec)
        result = run_verification_script(
            ROOT / verification_script,
            payload,
            timeout_seconds=float(spec.get("timeout_seconds", 60.0)),
        )
        if result.get("status") != "ok":
            for field in ("raw_answer", "extracted_answer"):
                if field in normalized_answer:
                    result[field] = normalized_answer[field]
            return result
        results.append(result)

    result = aggregate_constraint_results(task, results)
    for field in ("raw_answer", "extracted_answer"):
        if field in normalized_answer:
            result[field] = normalized_answer[field]
    return result


def evaluate_many(
    answers: list[dict[str, Any]],
    tasks: dict[str, dict[str, Any]],
    specs: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    rows = [summarize_row(evaluate_one(answer, tasks, specs)) for answer in answers]
    return {
        "summary": summarize_rows(rows),
        "rows": rows,
    }


def summarize_row(result: dict[str, Any]) -> dict[str, Any]:
    scores = result.get("scores") or {}
    row = {
        "task_id": result.get("task_id"),
        "status": result.get("status"),
        "failure_type": result.get("failure_type"),
        "canonical_smiles": result.get("canonical_smiles"),
        "score": scores.get("score", 0.0),
        "properties": result.get("properties", {}),
        "constraint_scores": scores.get("constraint_scores", []),
    }
    for field in ("raw_answer", "extracted_answer"):
        if field in result:
            row[field] = result[field]
    return row


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    scores = [float(row.get("score") or 0.0) for row in rows]
    ok_count = sum(row.get("status") == "ok" for row in rows)
    error_count = len(rows) - ok_count
    return {
        "num_answers": len(rows),
        "num_ok": ok_count,
        "num_error": error_count,
        "min_score": min(scores) if scores else None,
        "max_score": max(scores) if scores else None,
        "mean_score": sum(scores) / len(scores) if scores else None,
    }


def aggregate_constraint_results(task: dict[str, Any], results: list[dict[str, Any]]) -> dict[str, Any]:
    constraint_scores: list[dict[str, Any]] = []
    properties: dict[str, Any] = {}
    for result in results:
        properties.update(result.get("properties") or {})
        scores = result.get("scores") or {}
        constraint_scores.extend(scores.get("constraint_scores") or [])

    property_score = aggregate_scores(
        [item.get("score", 0.0) for item in constraint_scores],
        task.get("scoring", {}).get("aggregation", "geometric_mean"),
    )
    first = results[0]
    return {
        "task_id": task.get("task_id"),
        "status": "ok",
        "canonical_smiles": first.get("canonical_smiles"),
        "properties": properties,
        "scores": {
            "validity_gate": 1.0,
            "domain_gate": 1.0,
            "constraint_scores": constraint_scores,
            "property_score": property_score,
            "score": property_score,
        },
        "failure_type": None,
        "message": None,
        "versions": merge_versions(results),
    }


def aggregate_scores(values: list[Any], aggregation: str) -> float:
    scores = [max(0.0, min(1.0, float(value))) for value in values]
    if not scores:
        return 0.0
    if aggregation != "geometric_mean":
        raise ValueError(f"unsupported aggregation: {aggregation}")
    if any(score == 0.0 for score in scores):
        return 0.0
    product = 1.0
    for score in scores:
        product *= score
    return product ** (1.0 / len(scores))


def merge_versions(results: list[dict[str, Any]]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    verifiers: dict[str, Any] = {}
    for result in results:
        versions = result.get("versions") or {}
        for key, value in versions.items():
            if key == "verifier_id":
                continue
            merged.setdefault(key, value)
        verifier_id = result.get("verifier_id")
        if verifier_id:
            verifiers[str(verifier_id)] = versions
    if verifiers:
        merged["descriptor_verifiers"] = verifiers
    return merged


def routing_error(task_id: str | None, failure_type: str, message: str) -> dict[str, Any]:
    return {
        "task_id": task_id,
        "status": "error",
        "canonical_smiles": None,
        "properties": {},
        "scores": {
            "validity_gate": 0.0,
            "domain_gate": 0.0,
            "constraint_scores": [],
            "property_score": 0.0,
            "score": 0.0,
        },
        "failure_type": failure_type,
        "message": message,
        "versions": {},
    }
