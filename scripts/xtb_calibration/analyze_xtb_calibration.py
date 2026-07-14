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


def numeric_stats(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {"count": 0, "min": None, "median": None, "mean": None, "max": None}
    return {
        "count": len(values),
        "min": min(values),
        "median": statistics.median(values),
        "mean": statistics.fmean(values),
        "max": max(values),
    }


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


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
        runtime_values = [
            float(row["wall_time_seconds"])
            for row in rows
            if isinstance(row.get("wall_time_seconds"), int | float)
            and not isinstance(row.get("wall_time_seconds"), bool)
        ]
        property_values = [
            float(row["properties"][row["property_name"]])
            for row in ok_rows
            if isinstance(row.get("properties"), dict)
            and isinstance(row.get("property_name"), str)
            and isinstance(row["properties"].get(row["property_name"]), int | float)
            and not isinstance(row["properties"].get(row["property_name"]), bool)
        ]
        convergence_values = [
            row["converged"] for row in rows if isinstance(row.get("converged"), bool)
        ]
        identity_rows = [row.get("identity") or {} for row in rows]
        retention_failures = sum(
            any(value is False for value in identity.values())
            for identity in identity_rows
        )
        runtime_stats = numeric_stats(runtime_values)
        runtime_stats["p95"] = percentile(runtime_values, 0.95)
        tasks[task_id] = {
            "num_rows": len(rows),
            "num_ok": len(ok_rows),
            "num_error": len(rows) - len(ok_rows),
            "success_rate": len(ok_rows) / len(rows) if rows else None,
            "positive_success_rate": (
                sum(row.get("status") == "ok" for row in positive_rows)
                / len(positive_rows)
                if positive_rows
                else None
            ),
            "num_positive_candidates": roles.get("positive_candidate", 0),
            "num_negative_baselines": roles.get("negative_baseline", 0),
            "timeout_count": failures.get("verifier_timeout", 0),
            "runtime_seconds": runtime_stats,
            "property_names": sorted(
                {
                    str(row["property_name"])
                    for row in rows
                    if isinstance(row.get("property_name"), str)
                }
            ),
            "property_stats": numeric_stats(property_values),
            "convergence": {
                "num_applicable": len(convergence_values),
                "num_converged": sum(convergence_values),
                "success_rate": (
                    sum(convergence_values) / len(convergence_values)
                    if convergence_values
                    else None
                ),
            },
            "structure_retention_failures": retention_failures,
            "peak_memory_statuses": dict(
                Counter(str(row.get("peak_memory_status", "unreported")) for row in rows)
            ),
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
        "| Task | Rows | OK | Timeouts | Runtime p95 (s) | Property range | Retention failures | Attention |",
        "| --- | ---: | ---: | ---: | ---: | --- | ---: | --- |",
    ]
    for task_id, task in summary["tasks"].items():
        runtime_p95 = task["runtime_seconds"]["p95"]
        property_min = task["property_stats"]["min"]
        property_max = task["property_stats"]["max"]
        property_range = (
            ""
            if property_min is None or property_max is None
            else f"{property_min:.6g} to {property_max:.6g}"
        )
        lines.append(
            "| {task_id} | {rows} | {ok} | {timeouts} | {runtime} | {property_range} | {retention} | {attention} |".format(
                task_id=task_id,
                rows=task["num_rows"],
                ok=task["num_ok"],
                timeouts=task["timeout_count"],
                runtime="" if runtime_p95 is None else f"{runtime_p95:.3f}",
                property_range=property_range,
                retention=task["structure_retention_failures"],
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
