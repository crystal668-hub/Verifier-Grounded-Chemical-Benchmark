#!/usr/bin/env python
"""Validate an explicit caller-supplied xTB answer file; no answers are bundled."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from verifier_grounded_benchmark import load_track  # noqa: E402
from verifier_grounded_benchmark.task.loader import (  # noqa: E402
    load_answers_jsonl_file,
)

MIN_SAMPLE_SCORE = 0.6


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--answers", required=True, type=Path, help="Explicit validation JSONL; there is no bundled default.")
    args = parser.parse_args(argv)
    answers = load_answers_jsonl_file(args.answers)
    if not answers:
        parser.error("--answers must contain at least one answer record")
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

    track = load_track("open_generation_xtb")
    report = track.evaluate_answers(answers)
    failing_rows = [
        row
        for row in report["rows"]
        if row.get("status") != "scored" or float(row.get("score") or 0.0) < MIN_SAMPLE_SCORE
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
