#!/usr/bin/env python
"""Run real-xTB calibration for xTB direct-XYZ tasks."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmark.evaluate import evaluate_one, load_answers_jsonl, load_tasks, load_verifier_specs


TASK_DIR = ROOT / "tasks" / "xtb_xyz"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--answers", type=Path, default=TASK_DIR / "calibration_answers.jsonl")
    parser.add_argument("--tasks", type=Path, default=TASK_DIR / "tasks.yaml")
    parser.add_argument("--specs", type=Path, default=TASK_DIR / "verifier_specs.yaml")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-candidates", type=int, default=None)
    return parser.parse_args()


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    scores = [float(row.get("score") or 0.0) for row in rows]
    ok_count = sum(row.get("status") == "ok" for row in rows)
    return {
        "num_answers": len(rows),
        "num_ok": ok_count,
        "num_error": len(rows) - ok_count,
        "min_score": min(scores) if scores else None,
        "max_score": max(scores) if scores else None,
        "mean_score": sum(scores) / len(scores) if scores else None,
    }


def calculation_mode(property_name: str | None, spec: dict[str, Any]) -> str | None:
    backend = spec.get("backend") or {}
    configured_mode = backend.get("calculation_mode")
    if isinstance(configured_mode, str):
        return configured_mode
    if property_name == "relaxation_energy":
        return "submitted_singlepoint_then_optimized"
    if property_name == "entropy_298_per_heavy_atom":
        return "optimized_hessian"
    if property_name:
        return "optimized"
    return None


def build_calibration_row(
    *,
    answer: dict[str, Any],
    result: dict[str, Any],
    task: dict[str, Any],
    spec: dict[str, Any],
    wall_time_seconds: float,
) -> dict[str, Any]:
    scores = result.get("scores") or {}
    properties = result.get("properties") or {}
    constraints = task.get("constraints") or []
    primary_constraint = constraints[0] if constraints else {}
    property_name = primary_constraint.get("property")
    mode = calculation_mode(property_name, spec)
    failure_type = result.get("failure_type")
    if mode in {"submitted_singlepoint", None}:
        converged = None
    elif result.get("status") == "ok":
        converged = True
    elif failure_type in {"verifier_timeout", "verifier_tool_error"}:
        converged = False
    else:
        converged = None

    return {
        "candidate_id": answer.get("candidate_id"),
        "role": answer.get("role"),
        "task_id": result.get("task_id"),
        "status": result.get("status"),
        "failure_type": failure_type,
        "score": scores.get("score", 0.0),
        "property_score": scores.get("property_score", 0.0),
        "geometry_quality_score": scores.get("geometry_quality_score"),
        "stability_gate_score": scores.get("stability_gate_score"),
        "property_name": property_name,
        "calculation_mode": mode,
        "resolved_charge": properties.get("charge"),
        "resolved_uhf": properties.get("uhf"),
        "wall_time_seconds": wall_time_seconds,
        "converged": converged,
        "identity": {
            "graph_match": properties.get("graph_match"),
            "stereochemistry_match": properties.get("stereochemistry_match"),
            "post_optimization_graph_match": properties.get(
                "post_optimization_graph_match"
            ),
            "post_optimization_stereochemistry_match": properties.get(
                "post_optimization_stereochemistry_match"
            ),
        },
        # The shared process cannot attribute its high-water RSS to one candidate.
        "peak_memory_mb": None,
        "peak_memory_status": "unavailable",
        "properties": properties,
        "constraint_scores": scores.get("constraint_scores", []),
        "message": result.get("message"),
    }


def main() -> int:
    args = parse_args()
    executable = shutil.which("xtb")
    if executable is None:
        print(
            json.dumps(
                {
                    "status": "error",
                    "failure_type": "verifier_environment_error",
                    "message": "xTB executable not found on PATH",
                    "xtb_executable": None,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 1

    tasks = load_tasks(args.tasks)
    specs = load_verifier_specs(args.specs)
    answers = load_answers_jsonl(args.answers)
    if args.max_candidates is not None:
        answers = answers[: args.max_candidates]

    rows: list[dict[str, Any]] = []
    for answer in answers:
        task = tasks.get(str(answer.get("task_id")), {})
        constraints = task.get("constraints") or []
        primary_constraint = constraints[0] if constraints else {}
        spec = specs.get(str(primary_constraint.get("verifier_id")), {})
        started_at = time.perf_counter()
        result = evaluate_one(answer, tasks, specs)
        rows.append(
            build_calibration_row(
                answer=answer,
                result=result,
                task=task,
                spec=spec,
                wall_time_seconds=time.perf_counter() - started_at,
            )
        )

    payload = {
        "status": "ok",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "xtb_executable": executable,
        "answers_path": str(args.answers),
        "tasks_path": str(args.tasks),
        "specs_path": str(args.specs),
        "summary": summarize(rows),
        "rows": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True))
    print(json.dumps({"status": "ok", "output": str(args.output), "summary": payload["summary"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
