#!/usr/bin/env python
"""Prepare domain-filtered real-dataset samples for xTB distribution runs."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import yaml

from verifier_grounded_benchmark.evaluation.open_generation.verifiers.xtb.backend import XTBParseError, check_domain, inspect_xyz, parse_xyz


DEFAULT_SEED = 20260615
XTB_DOMAIN: dict[str, Any] = {
    "allowed_elements": ["H", "C", "N", "O", "F", "P", "S", "Cl", "Br"],
    "atom_count": [3, 80],
    "heavy_atom_count": [1, 40],
    "max_absolute_coordinate": 30.0,
    "min_interatomic_distance": 0.45,
    "inferred_components": 1,
}
HEAVY_ATOM_BINS = {
    "small": (1, 8),
    "medium": (9, 18),
    "large": (19, 40),
}
HETERO_ATOM_BINS = {
    "low": (0, 1),
    "medium": (2, 4),
    "high": (5, 40),
}
FLEXIBILITY_BINS = {
    "low": (0, 2),
    "medium": (3, 6),
    "high": (7, 80),
}
PILOT_LIGHT_QUOTAS = {"qm9": 500, "qmugs": 1000, "geom_drugs": 500, "tartarus_opv": 250}
INTERMEDIATE_LIGHT_QUOTAS = {"qm9": 250, "qmugs": 500, "geom_drugs": 250, "tartarus_opv": 100}
INTERMEDIATE_MEDIUM_QUOTAS = {"qm9": 100, "qmugs": 250, "geom_drugs": 150, "tartarus_opv": 50}
INTERMEDIATE_EXPENSIVE_QUOTAS = {"qm9": 75, "qmugs": 75, "geom_drugs": 50, "tartarus_opv": 0}
EXPANDED_LIGHT_QUOTAS = {"qm9": 5000, "qmugs": 3000, "geom_drugs": 2000, "tartarus_opv": 0}
EXPANDED_MEDIUM_QUOTAS = {"qm9": 1000, "qmugs": 700, "geom_drugs": 300, "tartarus_opv": 0}
EXPANDED_EXPENSIVE_QUOTAS = {"qm9": 250, "qmugs": 150, "geom_drugs": 100, "tartarus_opv": 0}
EXPANDED_TIER_TARGETS = {"light": 10000, "medium": 2000, "expensive": 500}
HESSIAN_DOMAIN = {"atom_count": [6, 48], "heavy_atom_count": [4, 18]}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-manifest", type=Path, default=ROOT / "data" / "xtb_real_dataset_sources.yaml")
    parser.add_argument("--input-jsonl", type=Path, action="append", default=[])
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--pilot", action="store_true")
    mode.add_argument("--intermediate", action="store_true")
    mode.add_argument("--expanded", action="store_true")
    return parser.parse_args()


def mode_name(args: argparse.Namespace) -> str:
    if args.expanded:
        return "expanded"
    if args.intermediate:
        return "intermediate"
    return "pilot"


def load_jsonl(paths: Iterable[Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in paths:
        with path.open() as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                record = json.loads(line)
                record.setdefault("_source_jsonl", str(path))
                record.setdefault("_source_line", line_number)
                rows.append(record)
    return rows


def bin_value(value: int, bins: dict[str, tuple[int, int]]) -> str:
    for label, (lower, upper) in bins.items():
        if lower <= value <= upper:
            return label
    return "unknown"


def stable_key(record: dict[str, Any]) -> tuple[str, str]:
    return (str(record.get("dataset_name", "")), str(record.get("record_id", "")))


def is_hessian_eligible(record: dict[str, Any]) -> bool:
    atom_count = int(record.get("atom_count", 0))
    heavy_atom_count = int(record.get("heavy_atom_count", 0))
    return (
        HESSIAN_DOMAIN["atom_count"][0] <= atom_count <= HESSIAN_DOMAIN["atom_count"][1]
        and HESSIAN_DOMAIN["heavy_atom_count"][0] <= heavy_atom_count <= HESSIAN_DOMAIN["heavy_atom_count"][1]
    )


def output_order_key(record: dict[str, Any]) -> tuple[str, int, str, str]:
    return (
        str(record.get("_source_jsonl", "")),
        int(record.get("_source_line", 0)),
        str(record.get("dataset_name", "")),
        str(record.get("record_id", "")),
    )


def stratification_key(record: dict[str, Any]) -> tuple[str, ...]:
    return (
        str(record.get("dataset_name", "")),
        str(record.get("heavy_atom_bin", "unknown")),
        str(record.get("hetero_atom_bin", "unknown")),
        str(record.get("estimated_flexibility_bin", "unknown")),
        str(record.get("contains_halogen", False)),
        str(record.get("contains_phosphorus_or_sulfur", False)),
        str(record.get("geometry_source", "unknown")),
    )


def deterministic_jitter(record: dict[str, Any], seed: int) -> float:
    digest = hashlib.sha256(f"{seed}|{stable_key(record)}".encode()).hexdigest()
    return int(digest[:16], 16) / float(0xFFFFFFFFFFFFFFFF)


def estimate_flexibility_bin(_record: dict[str, Any]) -> str:
    return "unknown"


def enrich_record(record: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    try:
        molecule = parse_xyz(str(record.get("xyz", "")))
        properties = inspect_xyz(molecule)
    except XTBParseError as exc:
        return None, failure_record(record, "parse_error", str(exc))

    if int(record.get("charge", 0)) != 0:
        return None, failure_record(record, "domain_error", "charge must be 0")
    if int(record.get("multiplicity", 1)) != 1:
        return None, failure_record(record, "domain_error", "multiplicity must be 1")

    domain_error = check_domain(molecule, properties, XTB_DOMAIN)
    if domain_error is not None:
        return None, failure_record(record, "domain_error", domain_error)

    elements = set(properties["elements"])
    enriched = {
        **record,
        **properties,
        "charge": 0,
        "multiplicity": 1,
        "contains_halogen": bool(elements & {"F", "Cl", "Br"}),
        "contains_phosphorus_or_sulfur": bool(elements & {"P", "S"}),
        "heavy_atom_bin": bin_value(int(properties["heavy_atom_count"]), HEAVY_ATOM_BINS),
        "hetero_atom_bin": bin_value(int(properties["hetero_atom_count"]), HETERO_ATOM_BINS),
        "estimated_flexibility_bin": estimate_flexibility_bin(record),
        "geometry_source": record.get("geometry_source", "unknown"),
    }
    return enriched, None


def failure_record(record: dict[str, Any], failure_type: str, message: str) -> dict[str, Any]:
    return {
        "dataset_name": record.get("dataset_name"),
        "record_id": record.get("record_id"),
        "failure_type": failure_type,
        "message": message,
    }


def sample_records_with_quotas(
    records: list[dict[str, Any]],
    quotas: dict[str, int],
    seed: int,
    quota_note_dataset_names: Iterable[str] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_dataset: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        by_dataset.setdefault(str(record.get("dataset_name")), []).append(record)

    sampled: list[dict[str, Any]] = []
    for dataset_name in sorted(by_dataset):
        dataset_records = sorted(by_dataset[dataset_name], key=output_order_key)
        quota = quotas.get(dataset_name, len(dataset_records))
        selected = stratified_sample(dataset_records, quota, seed)
        sampled.extend(selected)

    quota_notes: list[dict[str, Any]] = []
    quota_note_datasets = set(by_dataset)
    if quota_note_dataset_names is not None:
        quota_note_datasets.update(str(dataset_name) for dataset_name in quota_note_dataset_names)
    for dataset_name in sorted(quota_note_datasets):
        dataset_records = by_dataset.get(dataset_name, [])
        quota = quotas.get(dataset_name, len(dataset_records))
        if quota > 0 and len(dataset_records) < quota:
            quota_notes.append(
                {
                    "dataset_name": dataset_name,
                    "available": len(dataset_records),
                    "quota": quota,
                    "status": "quota_underfilled",
                }
            )
    return sorted(sampled, key=output_order_key), quota_notes


def sample_records(records: list[dict[str, Any]], seed: int, expanded: bool) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    quotas = EXPANDED_LIGHT_QUOTAS if expanded else PILOT_LIGHT_QUOTAS
    return sample_records_with_quotas(records, quotas, seed)


def fit_sample_to_target(
    selected_records: list[dict[str, Any]],
    candidate_records: list[dict[str, Any]],
    target: int | None,
    seed: int,
) -> list[dict[str, Any]]:
    if target is None or len(selected_records) >= target:
        return sorted(selected_records, key=output_order_key)
    selected_by_key = {stable_key(record): record for record in selected_records}
    remaining = [record for record in candidate_records if stable_key(record) not in selected_by_key]
    needed = target - len(selected_by_key)
    for record in stratified_sample(remaining, needed, seed):
        selected_by_key[stable_key(record)] = record
        if len(selected_by_key) >= target:
            break
    return sorted(selected_by_key.values(), key=output_order_key)


def tier_aware_sample_records(
    filtered_records: list[dict[str, Any]],
    seed: int,
    light_quotas: dict[str, int],
    medium_quotas: dict[str, int],
    expensive_quotas: dict[str, int],
    tier_targets: dict[str, int] | None = None,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    filtered_dataset_names = {str(record.get("dataset_name")) for record in filtered_records}
    light_records, light_notes = sample_records_with_quotas(filtered_records, light_quotas, seed)
    medium_candidates = [record for record in filtered_records if int(record.get("carbon_count", 0)) > 0]
    medium_records, medium_notes = sample_records_with_quotas(medium_candidates, medium_quotas, seed, filtered_dataset_names)
    expensive_candidates = [record for record in filtered_records if is_hessian_eligible(record)]
    expensive_records, expensive_notes = sample_records_with_quotas(
        expensive_candidates, expensive_quotas, seed, filtered_dataset_names
    )
    if tier_targets is not None:
        light_records = fit_sample_to_target(light_records, filtered_records, tier_targets.get("light"), seed)
        medium_records = fit_sample_to_target(medium_records, medium_candidates, tier_targets.get("medium"), seed)
        expensive_records = fit_sample_to_target(expensive_records, expensive_candidates, tier_targets.get("expensive"), seed)
    sampled_records = sorted(
        {stable_key(row): row for row in [*light_records, *medium_records, *expensive_records]}.values(),
        key=output_order_key,
    )
    quota_notes = (
        [{"tier": "light", **note} for note in light_notes]
        + [{"tier": "medium", **note} for note in medium_notes]
        + [{"tier": "expensive", **note} for note in expensive_notes]
    )
    return light_records, medium_records, expensive_records, sampled_records, quota_notes


def stratified_sample(records: list[dict[str, Any]], quota: int, seed: int) -> list[dict[str, Any]]:
    if quota >= len(records):
        return records

    strata: dict[tuple[str, ...], list[dict[str, Any]]] = {}
    for record in records:
        strata.setdefault(stratification_key(record), []).append(record)

    for stratum_records in strata.values():
        stratum_records.sort(key=lambda record: (deterministic_jitter(record, seed), stable_key(record)))

    selected: list[dict[str, Any]] = []
    ordered_strata = sorted(strata.items(), key=lambda item: (deterministic_jitter({"dataset_name": "|".join(item[0]), "record_id": ""}, seed), item[0]))
    while ordered_strata and len(selected) < quota:
        next_round: list[tuple[tuple[str, ...], list[dict[str, Any]]]] = []
        for key, stratum_records in ordered_strata:
            if stratum_records and len(selected) < quota:
                selected.append(stratum_records.pop(0))
            if stratum_records:
                next_round.append((key, stratum_records))
        ordered_strata = next_round
    return selected


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def load_source_manifest(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    with path.open() as handle:
        return yaml.safe_load(handle)


def main() -> int:
    args = parse_args()
    mode = mode_name(args)
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    source_manifest = load_source_manifest(args.source_manifest)
    raw_records = load_jsonl(args.input_jsonl)
    filtered_records: list[dict[str, Any]] = []
    rejected_records: list[dict[str, Any]] = []
    for record in raw_records:
        enriched, failure = enrich_record(record)
        if enriched is not None:
            filtered_records.append(enriched)
        if failure is not None:
            rejected_records.append(failure)

    tier_sampled_record_counts: dict[str, int] | None = None
    tier_targets: dict[str, int] | None = None
    if mode in {"intermediate", "expanded"}:
        if mode == "expanded":
            light_quotas = EXPANDED_LIGHT_QUOTAS
            medium_quotas = EXPANDED_MEDIUM_QUOTAS
            expensive_quotas = EXPANDED_EXPENSIVE_QUOTAS
            tier_targets = EXPANDED_TIER_TARGETS
        else:
            light_quotas = INTERMEDIATE_LIGHT_QUOTAS
            medium_quotas = INTERMEDIATE_MEDIUM_QUOTAS
            expensive_quotas = INTERMEDIATE_EXPENSIVE_QUOTAS

        light_records, medium_records, expensive_records, sampled_records, quota_notes = tier_aware_sample_records(
            filtered_records,
            args.seed,
            light_quotas,
            medium_quotas,
            expensive_quotas,
            tier_targets,
        )
        tier_sampled_record_counts = {
            "light": len(light_records),
            "medium": len(medium_records),
            "expensive": len(expensive_records),
        }
        write_jsonl(output_dir / "sampled_records.light.jsonl", light_records)
        write_jsonl(output_dir / "sampled_records.medium.jsonl", medium_records)
        write_jsonl(output_dir / "sampled_records.expensive.jsonl", expensive_records)
    else:
        sampled_records, quota_notes = sample_records(filtered_records, args.seed, args.expanded)

    write_jsonl(output_dir / "filtered_records.jsonl", sorted(filtered_records, key=output_order_key))
    write_jsonl(output_dir / "sampled_records.jsonl", sampled_records)
    manifest = {
        "status": "ok",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "seed": args.seed,
        "mode": mode,
        "source_manifest": str(args.source_manifest),
        "source_manifest_loaded": source_manifest is not None,
        "input_jsonl": [str(path) for path in args.input_jsonl],
        "raw_record_count": len(raw_records),
        "filtered_record_count": len(filtered_records),
        "sampled_record_count": len(sampled_records),
        "rejected_record_count": len(rejected_records),
        "rejections_by_failure_type": dict(Counter(row["failure_type"] for row in rejected_records)),
        "quota_notes": quota_notes,
        "domain": XTB_DOMAIN,
    }
    if tier_targets is not None:
        manifest["tier_targets"] = tier_targets
    if tier_sampled_record_counts is not None:
        manifest["tier_sampled_record_counts"] = tier_sampled_record_counts
    (output_dir / "sample_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
    print(json.dumps({"status": "ok", "output_dir": str(output_dir), "sampled_record_count": len(sampled_records)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
