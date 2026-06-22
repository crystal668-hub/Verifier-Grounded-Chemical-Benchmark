#!/usr/bin/env python
"""Run xTB property tiers for prepared real-dataset samples."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmark.evaluate import evaluate_one, load_verifier_specs
from verifiers.backends.xtb_properties import XTBParseError, check_domain, inspect_xyz, parse_xyz


TASK_DIR = ROOT / "tasks" / "xtb_xyz"
TIER_PROPERTIES = {
    "light": [
        "homo_lumo_gap",
        "dipole_moment",
        "lumo_energy",
        "polarizability_per_heavy_atom",
        "relaxation_energy",
    ],
    "medium": [
        "alpb_water_hexane_selectivity",
        "global_electrophilicity",
        "max_f_plus_on_carbon",
        "f_plus_contrast",
    ],
    "expensive": [
        "imaginary_frequency_count",
        "entropy_298_per_heavy_atom",
    ],
}
PROPERTY_VERIFIERS = {
    "homo_lumo_gap": "xtb_gap_gfn2_v1",
    "dipole_moment": "xtb_dipole_gfn2_v1",
    "lumo_energy": "xtb_lumo_gfn2_v1",
    "polarizability_per_heavy_atom": "xtb_polarizability_gfn2_v1",
    "relaxation_energy": "xtb_relaxation_energy_gfn2_v1",
    "alpb_water_hexane_selectivity": "xtb_solvation_selectivity_alpb_v1",
    "global_electrophilicity": "xtb_electrophilicity_gfn1_ipea_v1",
    "max_f_plus_on_carbon": "xtb_fukui_gfn1_v1",
    "f_plus_contrast": "xtb_fukui_gfn1_v1",
    "imaginary_frequency_count": "xtb_hessian_thermo_gfn2_v1",
    "entropy_298_per_heavy_atom": "xtb_hessian_thermo_gfn2_v1",
}
HESSIAN_DOMAIN = {"atom_count": [6, 48], "heavy_atom_count": [4, 18]}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sampled-records", type=Path, required=True)
    parser.add_argument("--tier", choices=sorted(TIER_PROPERTIES), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-records", type=int, default=None)
    parser.add_argument("--specs", type=Path, default=TASK_DIR / "verifier_specs.yaml")
    parser.add_argument("--resume", action="store_true", help="Reuse completed rows already present in --output")
    parser.add_argument("--checkpoint-every", type=int, default=0, help="Write partial output after this many newly completed records")
    parser.add_argument("--progress-every", type=int, default=0, help="Print progress after this many newly completed records")
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open() as handle:
        return [json.loads(line) for line in handle if line.strip()]


def row_key(row: dict[str, Any], tier: str | None = None) -> tuple[str, str, str]:
    return (
        str(row.get("tier") or tier or ""),
        str(row.get("dataset_name") or ""),
        str(row.get("record_id") or ""),
    )


def load_existing_rows(path: Path, tier: str) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text())
    except json.JSONDecodeError:
        return []
    rows = payload.get("rows")
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict) and row_key(row)[0] == tier]


def pending_records(records: list[dict[str, Any]], existing_rows: list[dict[str, Any]], tier: str) -> list[dict[str, Any]]:
    completed = {row_key(row) for row in existing_rows}
    return [record for record in records if row_key(record, tier) not in completed]


def hidden_task(property_name: str, verifier_id: str) -> dict[str, Any]:
    structural_domain = {"atom_count": [6, 48], "heavy_atom_count": [4, 18]} if property_name in {"imaginary_frequency_count", "entropy_298_per_heavy_atom"} else {}
    return {
        "task_id": hidden_task_id(property_name),
        "version": 1,
        "object_type": "small_molecule_3d",
        "answer_schema": {
            "format": "final_answer_block",
            "final_answer_prefix": "FINAL ANSWER:",
            "value_type": "xyz",
            "fence_language": "xyz",
            "cardinality": "one",
        },
        "constraints": [
            {
                "type": "window",
                "property": property_name,
                "verifier_id": verifier_id,
                "min": -1_000_000_000.0,
                "max": 1_000_000_000.0,
                "sigma": 1.0,
            }
        ],
        "structural_domain": structural_domain,
        "scoring": {"aggregation": "geometric_mean"},
    }


def hidden_task_id(property_name: str) -> str:
    return f"xtb_real_distribution_{property_name}"


def answer_for_record(record: dict[str, Any], property_name: str) -> dict[str, Any]:
    return {
        "task_id": hidden_task_id(property_name),
        "candidates": [{"xyz": record.get("xyz")}],
    }


def run_record(record: dict[str, Any], tier: str, tasks: dict[str, dict[str, Any]], specs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    started = time.perf_counter()
    merged_properties: dict[str, Any] = {}
    merged_versions: dict[str, Any] = {}
    failures: list[dict[str, Any]] = []
    property_statuses: dict[str, dict[str, Any]] = {}
    for property_name in TIER_PROPERTIES[tier]:
        skip_reason = property_skip_reason(record, property_name)
        if skip_reason is not None:
            property_statuses[property_name] = {
                "status": "skipped",
                "failure_type": "domain_skip",
                "message": skip_reason,
            }
            continue
        result = evaluate_one(answer_for_record(record, property_name), tasks, specs)
        if result.get("status") != "ok":
            failure_type = result.get("failure_type")
            if property_name in {"max_f_plus_on_carbon", "f_plus_contrast"} and no_carbon_fukui_property(result):
                failure_type = "domain_skip"
            failures.append(
                {
                    "property": property_name,
                    "failure_type": failure_type,
                    "message": result.get("message"),
                }
            )
            property_statuses[property_name] = {
                "status": "skipped" if failure_type == "domain_skip" else "error",
                "failure_type": failure_type,
                "message": result.get("message"),
            }
            continue
        for key, value in (result.get("properties") or {}).items():
            if key in TIER_PROPERTIES[tier] or key.endswith("_unit") or key in {"molecular_polarizability", "entropy_298", "gsolv_water_eV", "gsolv_hexane_eV", "max_f_plus_atom_index", "max_f_plus_atom_symbol"}:
                merged_properties[key] = value
        merged_versions.update(result.get("versions") or {})
        property_statuses[property_name] = {"status": "ok", "failure_type": None, "message": None}

    non_skipped = [item for item in property_statuses.values() if item["status"] != "skipped"]
    errors = [item for item in property_statuses.values() if item["status"] == "error"]
    ok_items = [item for item in property_statuses.values() if item["status"] == "ok"]
    if errors and ok_items:
        status = "partial"
    elif errors:
        status = "error"
    elif ok_items:
        status = "ok"
    elif non_skipped:
        status = "partial"
    else:
        status = "skipped"
    primary_failure = next((item["failure_type"] for item in property_statuses.values() if item["status"] == "error"), None)
    if primary_failure is None:
        primary_failure = next((item["failure_type"] for item in property_statuses.values() if item["status"] == "skipped"), None)
    return {
        "dataset_name": record.get("dataset_name"),
        "record_id": record.get("record_id"),
        "tier": tier,
        "status": status,
        "failure_type": primary_failure,
        "runtime_seconds": time.perf_counter() - started,
        "properties": merged_properties,
        "property_statuses": property_statuses,
        "versions": merged_versions,
        "failures": failures,
    }


def property_skip_reason(record: dict[str, Any], property_name: str) -> str | None:
    if property_name not in {"imaginary_frequency_count", "entropy_298_per_heavy_atom"}:
        return None
    try:
        molecule = parse_xyz(str(record.get("xyz", "")))
    except XTBParseError as exc:
        return str(exc)
    domain_error = check_domain(molecule, inspect_xyz(molecule), HESSIAN_DOMAIN)
    if domain_error:
        return domain_error
    return None


def no_carbon_fukui_property(result: dict[str, Any]) -> bool:
    message = str(result.get("message") or "")
    xyz_properties = result.get("properties") or {}
    return "missing Fukui properties" in message and int(xyz_properties.get("carbon_count") or 0) == 0


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    failures = Counter(str(row.get("failure_type")) for row in rows if row.get("status") != "ok")
    property_summary: dict[str, Counter[str]] = {}
    for row in rows:
        for property_name, status in (row.get("property_statuses") or {}).items():
            property_summary.setdefault(str(property_name), Counter())[str(status.get("status"))] += 1
    return {
        "num_rows": len(rows),
        "num_ok": sum(row.get("status") == "ok" for row in rows),
        "num_partial": sum(row.get("status") == "partial" for row in rows),
        "num_error": sum(row.get("status") == "error" for row in rows),
        "num_skipped": sum(row.get("status") == "skipped" for row in rows),
        "failure_types": dict(failures),
        "property_statuses": {property_name: dict(counter) for property_name, counter in sorted(property_summary.items())},
    }


def write_environment_error() -> int:
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


def write_results(
    path: Path,
    *,
    tier: str,
    sampled_records: Path,
    executable: str,
    rows: list[dict[str, Any]],
    complete: bool,
) -> None:
    payload = {
        "status": "ok" if complete else "running",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tier": tier,
        "properties": TIER_PROPERTIES[tier],
        "sampled_records": str(sampled_records),
        "xtb_executable": executable,
        "summary": summarize(rows),
        "rows": rows,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))


def main() -> int:
    args = parse_args()
    executable = shutil.which("xtb")
    if executable is None:
        return write_environment_error()

    specs = load_verifier_specs(args.specs)
    tasks = {
        hidden_task_id(property_name): hidden_task(property_name, PROPERTY_VERIFIERS[property_name])
        for property_name in TIER_PROPERTIES[args.tier]
    }
    records = load_jsonl(args.sampled_records)
    if args.max_records is not None:
        records = records[: args.max_records]

    rows = load_existing_rows(args.output, args.tier) if args.resume else []
    remaining_records = pending_records(records, rows, args.tier) if args.resume else records
    for completed_count, record in enumerate(remaining_records, start=1):
        rows.append(run_record(record, args.tier, tasks, specs))
        if args.checkpoint_every > 0 and completed_count % args.checkpoint_every == 0:
            write_results(args.output, tier=args.tier, sampled_records=args.sampled_records, executable=executable, rows=rows, complete=False)
        if args.progress_every > 0 and completed_count % args.progress_every == 0:
            print(
                json.dumps(
                    {
                        "status": "running",
                        "completed_new_records": completed_count,
                        "total_rows": len(rows),
                        "remaining_records": len(remaining_records) - completed_count,
                    },
                    sort_keys=True,
                ),
                flush=True,
            )
    write_results(args.output, tier=args.tier, sampled_records=args.sampled_records, executable=executable, rows=rows, complete=True)
    print(json.dumps({"status": "ok", "output": str(args.output), "summary": summarize(rows)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
