#!/usr/bin/env python
"""Run real-xTB validation for xTB direct-XYZ sample answers."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from benchmark.evaluate import evaluate_many, load_answers_jsonl, load_tasks, load_verifier_specs  # noqa: E402


TASK_DIR = ROOT / "tasks" / "xtb_xyz"
MIN_SAMPLE_SCORE = 0.6


def main() -> int:
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

    report = evaluate_many(
        load_answers_jsonl(TASK_DIR / "sample_answers.jsonl"),
        load_tasks(TASK_DIR / "tasks.yaml"),
        load_verifier_specs(TASK_DIR / "verifier_specs.yaml"),
    )
    failing_rows = [
        row
        for row in report["rows"]
        if row.get("status") != "ok" or float(row.get("score") or 0.0) < MIN_SAMPLE_SCORE
    ]
    payload = {
        "status": "ok" if not failing_rows else "error",
        "failure_type": None if not failing_rows else "sample_score_error",
        "min_sample_score": MIN_SAMPLE_SCORE,
        "xtb_executable": executable,
        "summary": report["summary"],
        "failing_rows": [
            {
                "task_id": row.get("task_id"),
                "status": row.get("status"),
                "failure_type": row.get("failure_type"),
                "score": row.get("score"),
                "properties": row.get("properties", {}),
            }
            for row in failing_rows
        ],
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not failing_rows else 1


if __name__ == "__main__":
    raise SystemExit(main())
