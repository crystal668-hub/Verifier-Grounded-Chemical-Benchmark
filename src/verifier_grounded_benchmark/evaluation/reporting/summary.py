"""Evaluation row normalization and report serialization."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from verifier_grounded_benchmark.evaluation.reporting.coverage import summarize_coverage


@dataclass(frozen=True)
class EvaluationReport:
    summary: dict[str, Any]
    rows: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {"summary": deepcopy(self.summary), "rows": deepcopy(self.rows)}

    def to_json(self, *, indent: int | None = 2, sort_keys: bool = True) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=sort_keys)

    def to_jsonl_rows(self, *, sort_keys: bool = True) -> str:
        return "\n".join(json.dumps(row, sort_keys=sort_keys) for row in self.rows)


def build_report(
    results: list[dict[str, Any]],
    answers: list[dict[str, Any]],
    task_ids: list[str],
) -> EvaluationReport:
    rows = [summarize_row(result) for result in results]
    scores = [float(row["score"]) for row in rows if row["score"] is not None]
    coverage = summarize_coverage(answers, task_ids)
    evaluation_errors = sum(row["status"] == "error" for row in rows)
    mean_score = sum(scores) / len(scores) if scores else None
    summary = {
        "num_answers": len(rows),
        "num_scored": sum(row["status"] == "scored" for row in rows),
        "num_ok": sum(row["status"] == "scored" for row in rows),
        "num_error": evaluation_errors,
        "num_submission_rejected": sum(row["failure_scope"] == "submission" for row in rows),
        "num_candidate_rejected": sum(row["failure_scope"] == "candidate" for row in rows),
        "min_score": min(scores) if scores else None,
        "max_score": max(scores) if scores else None,
        "mean_score": mean_score,
        "evaluated_mean_score": mean_score,
        "coverage": coverage,
        "benchmark_score": (
            mean_score if coverage["complete"] and evaluation_errors == 0 else None
        ),
    }
    return EvaluationReport(summary, rows)


def summarize_row(result: dict[str, Any]) -> dict[str, Any]:
    scores = result.get("scores") or {}
    row = {
        "schema_version": result.get("schema_version"),
        "task_id": result.get("task_id"),
        "status": result.get("status"),
        "failure_scope": result.get("failure_scope"),
        "failure_type": result.get("failure_type"),
        "message": result.get("message"),
        "canonical_smiles": result.get("canonical_smiles"),
        "score": scores.get("score"),
        "properties": result.get("properties", {}),
        "constraint_scores": scores.get("constraint_scores", []),
        "versions": result.get("versions", {}),
    }
    for field in ("raw_answer", "extracted_answer"):
        if field in result:
            row[field] = result[field]
    return row
