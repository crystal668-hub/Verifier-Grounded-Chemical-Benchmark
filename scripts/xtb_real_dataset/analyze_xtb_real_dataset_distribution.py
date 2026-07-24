#!/usr/bin/env python
"""Analyze xTB real-dataset distribution result JSON files."""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


PERCENTILES = {
    "p1": 0.01,
    "p5": 0.05,
    "p10": 0.10,
    "p25": 0.25,
    "p50": 0.50,
    "p75": 0.75,
    "p90": 0.90,
    "p95": 0.95,
    "p99": 0.99,
}
DIAGNOSTIC_THRESHOLDS = [0.2, 0.5, 0.8, 0.95]
HESSIAN_RUNTIME_FAILURE_TYPES = {
    "verifier_environment_error",
    "verifier_timeout",
    "verifier_tool_error",
    "parser_error",
    "parse_error",
    "runtime_error",
    "xtb_runtime_error",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, nargs="+", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expanded-readiness", action="store_true")
    return parser.parse_args()


def load_rows(paths: list[Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in paths:
        payload = json.loads(path.read_text())
        tier = payload.get("tier")
        tier_properties = [str(property_name) for property_name in payload.get("properties", [])]
        if not tier_properties:
            seen = {
                str(name)
                for row in payload.get("rows", [])
                for name, value in (row.get("properties") or {}).items()
                if not str(name).endswith("_unit") and isinstance(value, int | float) and not isinstance(value, bool)
            }
            seen.update(
                str(name)
                for row in payload.get("rows", [])
                for name in (row.get("property_statuses") or {})
            )
            tier_properties = sorted(seen)
        for row in payload.get("rows", []):
            rows.append({**row, "_input": str(path), "_tier": tier or row.get("tier"), "_tier_properties": tier_properties})
    return rows


def numeric_properties(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    by_property: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        properties = row.get("properties") or {}
        tier_properties = set(row.get("_tier_properties") or [])
        for name in sorted(tier_properties):
            value = properties.get(name)
            if isinstance(value, bool) or name.endswith("_unit"):
                continue
            if isinstance(value, int | float) and math.isfinite(float(value)):
                by_property[name].append(row)
        for name in tier_properties:
            by_property.setdefault(name, [])
    return by_property


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = fraction * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def property_values(rows: list[dict[str, Any]], property_name: str) -> list[float]:
    values: list[float] = []
    for row in rows:
        value = (row.get("properties") or {}).get(property_name)
        if isinstance(value, bool):
            continue
        if isinstance(value, int | float) and math.isfinite(float(value)):
            values.append(float(value))
    return values


def summarize_slice(all_rows: list[dict[str, Any]], value_rows: list[dict[str, Any]], property_name: str) -> dict[str, Any]:
    values = property_values(value_rows, property_name)
    statuses = [property_status(row, property_name) for row in all_rows]
    ok_count = sum(status == "ok" for status in statuses)
    error_count = sum(status == "error" for status in statuses)
    skipped_count = sum(status == "skipped" for status in statuses)
    attempted_count = ok_count + error_count
    summary: dict[str, Any] = {
        "count": len(values),
        "ok_count": ok_count,
        "error_count": error_count,
        "skipped_count": skipped_count,
        "attempted_count": attempted_count,
        "error_rate": (error_count / attempted_count) if attempted_count else None,
        "min": min(values) if values else None,
        "max": max(values) if values else None,
        "mean": statistics.fmean(values) if values else None,
        "standard_deviation": statistics.pstdev(values) if len(values) > 1 else 0.0 if values else None,
        "fraction_failing_relaxation_energy_gate": fraction_failing_relaxation_gate(all_rows),
        "fraction_failing_zero_imaginary_constraint": fraction_failing_zero_imaginary_constraint(
            all_rows
        ),
    }
    for label, fraction in PERCENTILES.items():
        summary[label] = percentile(values, fraction)
    for threshold in DIAGNOSTIC_THRESHOLDS:
        summary[f"fraction_score_gte_{threshold:g}"] = None
    return summary


def property_status(row: dict[str, Any], property_name: str) -> str:
    statuses = row.get("property_statuses") or {}
    status = statuses.get(property_name)
    if isinstance(status, dict) and status.get("status"):
        return str(status["status"])
    if property_name in (row.get("properties") or {}):
        return "ok"
    return "error" if row.get("status") != "ok" else "ok"


def fraction_failing_relaxation_gate(rows: list[dict[str, Any]]) -> float | None:
    values = property_values(rows, "relaxation_energy")
    if not values:
        return None
    return sum(value > 0.35 for value in values) / len(values)


def fraction_failing_zero_imaginary_constraint(
    rows: list[dict[str, Any]],
) -> float | None:
    values = property_values(rows, "imaginary_frequency_count")
    if not values:
        return None
    return sum(value > 0 for value in values) / len(values)


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_property = numeric_properties(rows)
    properties: dict[str, Any] = {}
    for property_name, value_rows in sorted(by_property.items()):
        slices: dict[str, Any] = {}
        property_all_rows = [row for row in rows if property_name in set(row.get("_tier_properties") or []) or property_name in (row.get("properties") or {})]
        slices["all"] = summarize_slice(property_all_rows, value_rows, property_name)
        datasets = sorted({str(row.get("dataset_name")) for row in property_all_rows})
        for dataset_name in datasets:
            dataset_all_rows = [row for row in property_all_rows if str(row.get("dataset_name")) == dataset_name]
            dataset_value_rows = [row for row in value_rows if str(row.get("dataset_name")) == dataset_name]
            slices[dataset_name] = summarize_slice(dataset_all_rows, dataset_value_rows, property_name)
        properties[property_name] = slices
    return {"properties": properties}


def failure_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counter: Counter[tuple[str, str | None]] = Counter()
    for row in rows:
        if row.get("status") == "ok":
            continue
        counter[(str(row.get("dataset_name")), row.get("failure_type"))] += 1
    return [
        {"dataset_name": dataset_name, "failure_type": failure_type, "count": count}
        for (dataset_name, failure_type), count in sorted(counter.items())
    ]


def write_summary_csv(path: Path, summary: dict[str, Any], *, per_dataset: bool) -> None:
    fieldnames = [
        "property",
        "dataset",
        "count",
        "ok_count",
        "error_count",
        "skipped_count",
        "attempted_count",
        "error_rate",
        "min",
        *PERCENTILES.keys(),
        "max",
        "mean",
        "standard_deviation",
        "fraction_failing_relaxation_energy_gate",
        "fraction_failing_zero_imaginary_constraint",
    ]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for property_name, slices in summary["properties"].items():
            for dataset_name, values in slices.items():
                if per_dataset and dataset_name == "all":
                    continue
                if not per_dataset and dataset_name != "all":
                    continue
                writer.writerow({"property": property_name, "dataset": dataset_name, **{key: values.get(key) for key in fieldnames if key not in {"property", "dataset"}}})


def write_failure_csv(path: Path, failures: list[dict[str, Any]]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["dataset_name", "failure_type", "count"])
        writer.writeheader()
        writer.writerows(failures)


def fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def write_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# xTB Real-Dataset Property Distribution Summary",
        "",
        "| Property | Dataset | Count | P5 | P50 | P95 | Mean | Errors |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for property_name, slices in summary["properties"].items():
        for dataset_name, values in slices.items():
            lines.append(
                "| {property_name} | {dataset_name} | {count} | {p5} | {p50} | {p95} | {mean} | {errors} |".format(
                    property_name=property_name,
                    dataset_name=dataset_name,
                    count=fmt(values.get("count")),
                    p5=fmt(values.get("p5")),
                    p50=fmt(values.get("p50")),
                    p95=fmt(values.get("p95")),
                    mean=fmt(values.get("mean")),
                    errors=fmt(values.get("error_count")),
                )
            )
    return "\n".join(lines) + "\n"


def write_recommendations(path: Path, summary: dict[str, Any], failures: list[dict[str, Any]]) -> None:
    total_failures = sum(int(item["count"]) for item in failures)
    recommendation = "needs_more_data"
    if total_failures:
        recommendation = "needs_parser_or_runtime_fix"
    lines = [
        "# Score Threshold Recommendations",
        "",
        "| Task | Recommendation | Rationale |",
        "| --- | --- | --- |",
    ]
    tasks = [
        "xtb_gap_window_001",
        "xtb_dipole_window_002",
        "xtb_gap_max_003",
        "xtb_gap_min_004",
        "xtb_dipole_max_005",
        "xtb_low_gap_high_dipole_opt_006",
        "xtb_gap_dipole_window_007",
        "xtb_lumo_min_008",
        "xtb_polarizability_dipole_opt_009",
        "xtb_solvation_selectivity_alpb_010",
        "xtb_electrophilicity_max_011",
        "xtb_fukui_carbon_site_012",
        "xtb_hessian_thermo_stability_013",
    ]
    property_count = len(summary.get("properties", {}))
    rationale = f"Generated from {property_count} measured properties; score diagnostics require official task scoring in a follow-up analysis."
    for task_id in tasks:
        lines.append(f"| {task_id} | {recommendation} | {rationale} |")
    path.write_text("\n".join(lines) + "\n")


def expanded_readiness(rows: list[dict[str, Any]]) -> dict[str, Any]:
    non_qm9_ok_records = len(
        {
            (str(row.get("dataset_name")), str(row.get("record_id")))
            for row in rows
            if str(row.get("dataset_name")) != "qm9" and row_has_property_ok(row)
        }
    )

    attempted_property_count = 0
    error_property_count = 0
    hessian_runtime_failures = 0
    for row in rows:
        for property_name, status in (row.get("property_statuses") or {}).items():
            if not isinstance(status, dict):
                continue
            property_status = status.get("status")
            if property_status == "skipped":
                continue
            attempted_property_count += 1
            if property_status == "error":
                error_property_count += 1
                failure_type = status.get("failure_type")
                if (
                    property_name in {"imaginary_frequency_count", "entropy_298_per_heavy_atom"}
                    and str(failure_type) in HESSIAN_RUNTIME_FAILURE_TYPES
                ):
                    hessian_runtime_failures += 1

    property_error_rate = (error_property_count / attempted_property_count) if attempted_property_count else None
    blockers: list[str] = []
    if non_qm9_ok_records < 100:
        blockers.append("non_qm9_ok_records_below_100")
    if property_error_rate is None:
        blockers.append("no_attempted_properties")
    elif property_error_rate > 0.05:
        blockers.append("property_error_rate_above_5_percent")
    if hessian_runtime_failures:
        blockers.append("hessian_runtime_or_parser_failures")

    return {
        "ready_for_expanded_run": not blockers,
        "non_qm9_ok_records": non_qm9_ok_records,
        "attempted_property_count": attempted_property_count,
        "error_property_count": error_property_count,
        "property_error_rate": property_error_rate,
        "hessian_runtime_failures": hessian_runtime_failures,
        "blockers": blockers,
    }


def row_has_property_ok(row: dict[str, Any]) -> bool:
    statuses = row.get("property_statuses") or {}
    if any(isinstance(status, dict) and status.get("status") == "ok" for status in statuses.values()):
        return True
    return bool(row.get("properties")) and row.get("status") == "ok"


def write_readiness_markdown(readiness: dict[str, Any]) -> str:
    decision = "ready" if readiness["ready_for_expanded_run"] else "not_ready"
    error_rate = readiness["property_error_rate"]
    error_rate_text = fmt(error_rate) if error_rate is not None else "n/a"
    blockers = readiness["blockers"] or ["none"]
    lines = [
        "# Expanded Run Readiness",
        "",
        f"- Decision: `{decision}`",
        f"- Non-QM9 ok records: {readiness['non_qm9_ok_records']}",
        f"- Attempted property count: {readiness['attempted_property_count']}",
        f"- Error property count: {readiness['error_property_count']}",
        f"- Property error rate: {error_rate_text}",
        f"- Hessian runtime/parser failures: {readiness['hessian_runtime_failures']}",
        f"- Blockers: {', '.join(blockers)}",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    rows = load_rows(args.inputs)
    summary = summarize(rows)
    failures = failure_summary(rows)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "property_distribution_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    write_summary_csv(args.output_dir / "property_distribution_summary.csv", summary, per_dataset=False)
    write_summary_csv(args.output_dir / "per_dataset_quantiles.csv", summary, per_dataset=True)
    (args.output_dir / "property_distribution_summary.md").write_text(write_markdown(summary))
    write_failure_csv(args.output_dir / "failure_summary.csv", failures)
    write_recommendations(args.output_dir / "score_threshold_recommendations.md", summary, failures)
    if args.expanded_readiness:
        readiness = expanded_readiness(rows)
        (args.output_dir / "expanded_run_readiness.json").write_text(json.dumps(readiness, indent=2, sort_keys=True))
        (args.output_dir / "expanded_run_readiness.md").write_text(write_readiness_markdown(readiness))
    print(json.dumps({"status": "ok", "output_dir": str(args.output_dir)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
