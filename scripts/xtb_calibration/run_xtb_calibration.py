#!/usr/bin/env python
"""Run real-xTB calibration for xTB direct-XYZ tasks."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
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
        result = evaluate_one(answer, tasks, specs)
        scores = result.get("scores") or {}
        rows.append(
            {
                "candidate_id": answer.get("candidate_id"),
                "role": answer.get("role"),
                "task_id": result.get("task_id"),
                "status": result.get("status"),
                "failure_type": result.get("failure_type"),
                "score": scores.get("score", 0.0),
                "property_score": scores.get("property_score", 0.0),
                "geometry_quality_score": scores.get("geometry_quality_score"),
                "stability_gate_score": scores.get("stability_gate_score"),
                "properties": result.get("properties", {}),
                "constraint_scores": scores.get("constraint_scores", []),
                "message": result.get("message"),
            }
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
