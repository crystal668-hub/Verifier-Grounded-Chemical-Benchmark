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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sampled-records", type=Path, required=True)
    parser.add_argument("--tier", choices=sorted(TIER_PROPERTIES), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-records", type=int, default=None)
    parser.add_argument("--specs", type=Path, default=TASK_DIR / "verifier_specs.yaml")
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open() as handle:
        return [json.loads(line) for line in handle if line.strip()]


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
    for property_name in TIER_PROPERTIES[tier]:
        result = evaluate_one(answer_for_record(record, property_name), tasks, specs)
        if result.get("status") != "ok":
            failures.append(
                {
                    "property": property_name,
                    "failure_type": result.get("failure_type"),
                    "message": result.get("message"),
                }
            )
            continue
        for key, value in (result.get("properties") or {}).items():
            if key in TIER_PROPERTIES[tier] or key.endswith("_unit") or key in {"molecular_polarizability", "entropy_298", "gsolv_water_eV", "gsolv_hexane_eV", "max_f_plus_atom_index", "max_f_plus_atom_symbol"}:
                merged_properties[key] = value
        merged_versions.update(result.get("versions") or {})

    status = "ok" if not failures else "error"
    return {
        "dataset_name": record.get("dataset_name"),
        "record_id": record.get("record_id"),
        "tier": tier,
        "status": status,
        "failure_type": failures[0]["failure_type"] if failures else None,
        "runtime_seconds": time.perf_counter() - started,
        "properties": merged_properties,
        "versions": merged_versions,
        "failures": failures,
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    failures = Counter(str(row.get("failure_type")) for row in rows if row.get("status") != "ok")
    return {
        "num_rows": len(rows),
        "num_ok": sum(row.get("status") == "ok" for row in rows),
        "num_error": sum(row.get("status") != "ok" for row in rows),
        "failure_types": dict(failures),
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

    rows = [run_record(record, args.tier, tasks, specs) for record in records]
    payload = {
        "status": "ok",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tier": args.tier,
        "properties": TIER_PROPERTIES[args.tier],
        "sampled_records": str(args.sampled_records),
        "xtb_executable": executable,
        "summary": summarize(rows),
        "rows": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True))
    print(json.dumps({"status": "ok", "output": str(args.output), "summary": payload["summary"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
