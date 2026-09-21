"""Project a frozen property-family policy without fitting to submitted answers."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
import sys
import tempfile
from copy import deepcopy
from decimal import Decimal
from pathlib import Path

import numpy as np
import yaml

from verifier_grounded_benchmark.task.loader import load_task_pack

ROOT = Path(__file__).resolve().parents[3]
DIRECTORY = Path(__file__).resolve().parent
POLICY = DIRECTORY / "family_policy.yaml"
PREVIOUS = DIRECTORY.parent / "2026-09-16-property-tolerance-projection"

# Reuse the validated workbook reader and evaluator adapter, not the optimizer.
spec = importlib.util.spec_from_file_location(
    "original_projection", PREVIOUS / "project_scores.py"
)
original = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = original
spec.loader.exec_module(original)


def baseline_scoring(track: str) -> dict:
    """Keep v0.9.2 widths and the R2 domain fixes independent of later releases."""
    directory = ROOT / "src/verifier_grounded_benchmark/task/packs" / track
    source = yaml.safe_load((directory / "scoring.yaml").read_text(encoding="utf-8"))
    snapshot = yaml.safe_load(
        (DIRECTORY / f"{track}.scoring.yaml").read_text(encoding="utf-8")
    )
    source["scoring_config"].update(task_pack_version="0.9.2", scoring_status="formal")
    source["tasks"] = deepcopy(snapshot["tasks"])
    source["scoring_profiles"] = original.baseline_profiles(source["scoring_profiles"])
    for profile_id, profile in source["scoring_profiles"].items():
        frozen = snapshot["scoring_profiles"][profile_id]
        for key in ("minimum_value", "value_transform"):
            if key in frozen:
                profile[key] = frozen[key]
            else:
                profile.pop(key, None)
        if "semantic_decision_record" in frozen["provenance"]:
            profile["provenance"]["semantic_decision_record"] = frozen["provenance"][
                "semantic_decision_record"
            ]
    return source


def index_rules(policy: dict) -> dict:
    indexed = {}
    for family, rule in policy["families"].items():
        if rule["mode"] not in {"absolute", "relative", "log10"}:
            raise ValueError(f"Unsupported error mode: {family}")
        for parameter in (
            rule["parameter"],
            rule.get("upper_parameter", rule["parameter"]),
        ):
            if isinstance(parameter, bool) or not isinstance(parameter, (int, float)):
                raise ValueError(f"Invalid tolerance parameter: {family}")
            if not math.isfinite(parameter) or parameter <= 0:
                raise ValueError(f"Invalid tolerance parameter: {family}")
        for property_name in rule["properties"]:
            for unit in rule["units"]:
                key = (property_name, unit)
                if key in indexed:
                    raise ValueError(f"Overlapping family selectors: {key}")
                indexed[key] = (family, rule)
    return indexed


def candidate_scoring(source: dict, policy: dict) -> dict:
    """Resolve widths from property definitions and gold, with no answer input."""
    result = deepcopy(source)
    result["scoring_config"]["scoring_status"] = "shadow_pending_research"
    rules = index_rules(policy)
    assigned = {}
    for task in result["tasks"]:
        for gold in task["gold_answers"]:
            profile_id = gold["scoring_profile"]
            profile = result["scoring_profiles"][profile_id]
            if profile["type"] != "numeric_gold":
                continue
            key = (gold["property"], gold["unit"])
            if key not in rules:
                raise ValueError(f"No family rule for {key}")
            family, rule = rules[key]
            transform = profile.get("value_transform", "identity")
            if (rule["mode"] == "log10") != (transform == "log10"):
                raise ValueError(f"Family/transform mismatch: {key}")
            scale = (
                abs(Decimal(str(gold["value"])))
                if rule["mode"] == "relative"
                else Decimal(1)
            )
            if scale == 0:
                raise ValueError(f"Relative scoring requires a nonzero gold: {key}")
            lower = float(Decimal(str(rule["parameter"])) * scale)
            upper = float(
                Decimal(str(rule.get("upper_parameter", rule["parameter"]))) * scale
            )
            widths = (lower, upper)
            if profile_id in assigned and assigned[profile_id] != widths:
                raise ValueError(
                    f"Shared profile has incompatible gold scales: {profile_id}"
                )
            assigned[profile_id] = widths
            profile.update(lower_tolerance=lower, upper_tolerance=upper)
            profile.pop("error_mode", None)
            profile.pop("error_parameter", None)
            profile.pop("upper_error_parameter", None)
            profile["provenance"].update(
                decay_source="predeclared_property_family_score_anchors",
                decision_record=policy["decision_record"],
                review_status=rule.get("status", policy["status"]),
                review_date="2026-09-17",
                tolerance_family=family,
                tolerance_policy=policy["policy_id"],
            )
    return result


def parameter_rows(track: str, source: dict, candidate: dict) -> list[dict]:
    with (PREVIOUS / "candidate_tolerances.csv").open(
        encoding="utf-8-sig", newline=""
    ) as handle:
        previous = {
            (row["task_id"], row["property"]): row for row in csv.DictReader(handle)
        }
    rows = []
    for task in candidate["tasks"]:
        for gold in task["gold_answers"]:
            profile = candidate["scoring_profiles"][gold["scoring_profile"]]
            old = source["scoring_profiles"][gold["scoring_profile"]]
            fitted = previous[(task["task_id"], gold["property"])]
            numeric = profile["type"] == "numeric_gold"
            row = {
                "track": track,
                "task_id": task["task_id"],
                "property": gold["property"],
                "family": profile["provenance"].get(
                    "tolerance_family", "categorical_unchanged"
                ),
                "gold": gold["value"],
                "unit": gold.get("unit", ""),
                "value_transform": profile.get("value_transform", "identity")
                if numeric
                else "categorical",
                "minimum_value": profile.get("minimum_value", ""),
                "error_mode": profile.get("error_mode", ""),
                "error_parameter": profile.get("error_parameter", ""),
                "status": profile["provenance"]["review_status"],
            }
            for side in ("lower", "upper"):
                width = profile.get(f"{side}_tolerance", "")
                row[f"original_{side}_tolerance"] = old.get(f"{side}_tolerance", "")
                row[f"fitted_{side}_tolerance"] = fitted[f"new_{side}_tolerance"]
                row[f"new_{side}_tolerance"] = width
                row[f"score_90_{side}_error"] = (
                    float(Decimal(str(width)) / 10) if numeric else ""
                )
                row[f"score_50_{side}_error"] = (
                    float(Decimal(str(width)) / 2) if numeric else ""
                )
            rows.append(row)
    return rows


def metrics(scores: np.ndarray) -> dict:
    return {
        "group_means": dict(
            zip(original.GROUPS, (scores.mean(axis=0) * 100).tolist(), strict=True)
        ),
        "mean_within_task_sd": float(scores.std(axis=1).mean() * 100),
        "mean_pairwise_absolute_gap": float(
            np.mean(
                [
                    np.abs(scores[:, i] - scores[:, j])
                    for i in range(4)
                    for j in range(i + 1, 4)
                ]
            )
            * 100
        ),
        "all_groups_at_least_90_count": int(np.sum(np.all(scores >= 0.9, axis=1))),
        "all_groups_zero_count": int(np.sum(np.all(scores <= 1e-12, axis=1))),
        "individual_zero_rate": float(np.mean(scores <= 1e-12)),
    }


def run(source_dir: Path | None, output_dir: Path, policy_path: Path = POLICY) -> dict:
    policy = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    inputs = [
        policy_path,
        Path(__file__),
        PREVIOUS / "project_scores.py",
        PREVIOUS / "candidate_tolerances.csv",
        PREVIOUS / "task_scores.csv",
        original.BASELINE_INVENTORY,
    ]
    inputs.extend(
        ROOT / "src/verifier_grounded_benchmark" / name
        for name in (
            "evaluation/property_calculation/scoring/numeric_gold.py",
            "task/schema/common.py",
            "task/schema/property_calculation.py",
        )
    )
    sources, candidates, directories = {}, {}, {}
    # Freeze every family's widths before opening any answer workbook.
    for track in original.SOURCES:
        directory = ROOT / "src/verifier_grounded_benchmark/task/packs" / track
        directories[track] = directory
        inputs.extend(
            directory / name
            for name in ("tasks.yaml", "scoring.yaml")
        )
        inputs.append(DIRECTORY / f"{track}.scoring.yaml")
        source = baseline_scoring(track)
        sources[track] = source
        candidates[track] = candidate_scoring(source, policy)
    if source_dir is not None:
        inputs.extend(source_dir / name for name in original.SOURCES.values())
    hashes = {str(path): original.sha256(path) for path in inputs}
    with (PREVIOUS / "task_scores.csv").open(
        encoding="utf-8-sig", newline=""
    ) as handle:
        previous = {row["task_id"]: row for row in csv.DictReader(handle)}
    summary = {
        "policy_id": policy["policy_id"],
        "status": policy["status"],
        "parameters_fit_to_answers": False,
        "source_sha256": hashes,
        "tracks": {},
    }
    parameters, task_rows, configs = [], [], {}
    with tempfile.TemporaryDirectory() as temporary:
        for track, candidate in candidates.items():
            directory = directories[track]
            config = yaml.safe_dump(candidate, sort_keys=False, allow_unicode=True)
            configs[track] = config
            config_path = Path(temporary) / f"{track}.scoring.yaml"
            config_path.write_text(config, encoding="utf-8")
            pack = load_task_pack(
                directory / "tasks.yaml", None, config_path
            )
            parameters.extend(parameter_rows(track, sources[track], candidate))
            if source_dir is None:
                continue
            observations = original.read_observations(
                source_dir / original.SOURCES[track], pack
            )
            scores = np.array(
                [original.evaluate(pack, item)[0] for item in observations]
            )
            recorded = np.array([item.recorded for item in observations])
            baseline_path = Path(temporary) / f"{track}.baseline.scoring.yaml"
            baseline_path.write_text(yaml.safe_dump(sources[track]), encoding="utf-8")
            current_pack = load_task_pack(
                directory / "tasks.yaml",
                None,
                baseline_path,
            )
            corrected = np.array(
                [original.evaluate(current_pack, item)[0] for item in observations]
            )
            fitted = np.array(
                [
                    [
                        float(previous[item.task.task_id][f"candidate_{group}"]) / 100
                        for group in original.GROUPS
                    ]
                    for item in observations
                ]
            )
            summary["tracks"][track] = {
                "tasks": len(observations),
                "recorded_v0_9_2": metrics(recorded),
                "semantic_corrections_only": metrics(corrected),
                "previous_fitted_projection": metrics(fitted),
                "family_policy": metrics(scores),
            }
            for i, item in enumerate(observations):
                row = {"track": track, "task_id": item.task.task_id}
                for j, group in enumerate(original.GROUPS):
                    row[f"recorded_{group}"] = float(recorded[i, j] * 100)
                    row[f"semantic_corrections_{group}"] = float(corrected[i, j] * 100)
                    row[f"fitted_{group}"] = float(fitted[i, j] * 100)
                    row[f"family_{group}"] = float(scores[i, j] * 100)
                task_rows.append(row)
    if any(original.sha256(Path(path)) != digest for path, digest in hashes.items()):
        raise RuntimeError("An input changed during the projection")
    output_dir.mkdir(parents=True, exist_ok=True)
    original.write_csv(output_dir / "candidate_tolerances.csv", parameters)
    if task_rows:
        original.write_csv(output_dir / "task_scores.csv", task_rows)
    for track, config in configs.items():
        (output_dir / f"{track}.scoring.yaml").write_text(config, encoding="utf-8")
    summary_name = "summary.json" if source_dir is not None else "policy_manifest.json"
    (output_dir / summary_name).write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-dir",
        type=Path,
        help="Optional private workbook directory; omit to export policy only",
    )
    parser.add_argument("--output-dir", type=Path, default=DIRECTORY)
    args = parser.parse_args()
    summary = run(args.source_dir, args.output_dir)
    print(
        json.dumps(
            {"policy_id": summary["policy_id"], "tracks": summary["tracks"]}, indent=2
        )
    )


if __name__ == "__main__":
    main()
