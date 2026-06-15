#!/usr/bin/env python
"""Analyze xTB calibration result JSON files."""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser.parse_args()


def score_stats(rows: list[dict[str, Any]]) -> dict[str, float | int | None]:
    scores = [float(row.get("score") or 0.0) for row in rows]
    if not scores:
        return {"count": 0, "min": None, "median": None, "mean": None, "max": None}
    return {
        "count": len(scores),
        "min": min(scores),
        "median": statistics.median(scores),
        "mean": statistics.fmean(scores),
        "max": max(scores),
    }


def analyze(payload: dict[str, Any]) -> dict[str, Any]:
    by_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in payload.get("rows", []):
        by_task[str(row.get("task_id"))].append(row)

    tasks: dict[str, Any] = {}
    for task_id, rows in sorted(by_task.items()):
        roles = Counter(str(row.get("role")) for row in rows)
        failures = Counter(str(row.get("failure_type")) for row in rows if row.get("status") != "ok")
        ok_rows = [row for row in rows if row.get("status") == "ok"]
        positive_rows = [row for row in rows if row.get("role") == "positive_candidate"]
        negative_rows = [row for row in rows if row.get("role") == "negative_baseline"]
        tasks[task_id] = {
            "num_rows": len(rows),
            "num_ok": len(ok_rows),
            "num_error": len(rows) - len(ok_rows),
            "num_positive_candidates": roles.get("positive_candidate", 0),
            "num_negative_baselines": roles.get("negative_baseline", 0),
            "score_stats": score_stats(rows),
            "positive_score_stats": score_stats(positive_rows),
            "negative_score_stats": score_stats(negative_rows),
            "failure_types": dict(failures),
            "needs_attention": attention_flags(rows),
        }
    return {"tasks": tasks}


def attention_flags(rows: list[dict[str, Any]]) -> list[str]:
    flags: list[str] = []
    positive_scores = [float(row.get("score") or 0.0) for row in rows if row.get("role") == "positive_candidate"]
    negative_scores = [float(row.get("score") or 0.0) for row in rows if row.get("role") == "negative_baseline"]
    error_rows = [row for row in rows if row.get("status") != "ok"]
    if positive_scores and max(positive_scores) < 0.6:
        flags.append("no_positive_candidate_above_0.6")
    if negative_scores and max(negative_scores) > 0.35:
        flags.append("negative_baseline_above_0.35")
    if error_rows:
        flags.append("has_verifier_errors")
    return flags


def write_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# xTB Calibration Summary",
        "",
        "| Task | Rows | OK | Errors | Positive max | Negative max | Attention |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for task_id, task in summary["tasks"].items():
        positive_max = task["positive_score_stats"]["max"]
        negative_max = task["negative_score_stats"]["max"]
        lines.append(
            "| {task_id} | {rows} | {ok} | {errors} | {positive} | {negative} | {attention} |".format(
                task_id=task_id,
                rows=task["num_rows"],
                ok=task["num_ok"],
                errors=task["num_error"],
                positive="" if positive_max is None else f"{positive_max:.3f}",
                negative="" if negative_max is None else f"{negative_max:.3f}",
                attention=", ".join(task["needs_attention"]),
            )
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    payload = json.loads(args.input.read_text())
    summary = analyze(payload)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    (args.output_dir / "summary.md").write_text(write_markdown(summary))
    print(json.dumps({"status": "ok", "output_dir": str(args.output_dir)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
