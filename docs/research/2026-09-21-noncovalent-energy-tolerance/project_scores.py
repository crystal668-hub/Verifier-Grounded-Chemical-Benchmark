"""Re-score the current answer workbooks with a noncovalent-energy override.

This is a research projection. It reads the current formal v0.9.3 task packs,
changes only the named tolerance family in a temporary scoring file, and never
modifies the formal task-pack configuration.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import tempfile
from copy import deepcopy
from pathlib import Path

import numpy as np
import openpyxl
import yaml

from verifier_grounded_benchmark.evaluation.property_calculation import (
    PropertyCalculationEvaluator,
)
from verifier_grounded_benchmark.task.loader import load_task_pack

ROOT = Path(__file__).resolve().parents[3]
GROUPS = (
    "gpt_sol_skill_on",
    "gpt_sol_skill_off",
    "qwen_flash_skill_on",
    "qwen_flash_skill_off",
)
TRACKS = {
    "property_calculation_basic": "516177f8058f43d3a65127b6ba0a147a.xlsx",
    "property_calculation_advanced": "71ba494357c643f69dcb8e6ae28ab299.xlsx",
}
FAMILY = "noncovalent_energy"
OVERRIDE_WIDTH = 2.0


def candidate_scoring(scoring: dict) -> dict:
    candidate = deepcopy(scoring)
    changed = []
    for profile_id, profile in candidate["scoring_profiles"].items():
        if profile.get("provenance", {}).get("tolerance_family") != FAMILY:
            continue
        profile["lower_tolerance"] = OVERRIDE_WIDTH
        profile["upper_tolerance"] = OVERRIDE_WIDTH
        profile["error_parameter"] = OVERRIDE_WIDTH
        changed.append(profile_id)
    if not changed:
        raise ValueError("No noncovalent profiles found")
    return candidate


def _observations(path: Path, task_by_id: dict):
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        rows = list(workbook.active.values)
    finally:
        workbook.close()
    observations = []
    for row_number, row in enumerate(rows[4:], 5):
        match = re.match(
            r"(property_calculation_(?:basic|advanced)_\d{3}_[a-z0-9_]+)",
            str(row[0]),
        )
        if not match:
            continue
        task_id = match.group(1)
        if task_id not in task_by_id:
            raise ValueError(f"Unknown task in workbook row {row_number}: {task_id}")
        answers = [json.loads(row[column]) if row[column] is not None else {}
                   for column in (2, 5, 8, 11)]
        recorded = np.array([row[column] for column in (4, 7, 10, 13)], dtype=float)
        observations.append((task_id, answers, recorded, row_number))
    if set(task_by_id) != {item[0] for item in observations}:
        raise ValueError("Workbook/task coverage mismatch")
    return observations


def _score(pack, task_by_id, task_id, answer):
    versions = {
        "package": "0.9.3",
        "task_pack": pack.version,
        "scoring": pack.scoring_version,
        "verifiers": {},
    }
    return float(
        PropertyCalculationEvaluator()
        .evaluate(answer, task_by_id[task_id], pack.scoring_profiles, versions=versions)["scores"]["score"]
    )


def _metrics(scores: np.ndarray) -> dict:
    return {
        "means": dict(zip(GROUPS, (scores.mean(axis=0) * 100).tolist(), strict=True)),
        "mean_within_task_sd": float(scores.std(axis=1).mean() * 100),
        "mean_pairwise_absolute_gap": float(
            np.mean([np.abs(scores[:, i] - scores[:, j]) for i in range(4) for j in range(i + 1, 4)])
            * 100
        ),
        "all_groups_at_least_90_count": int(np.sum(np.all(scores >= 0.9, axis=1))),
        "all_groups_zero_count": int(np.sum(np.all(scores <= 1e-12, axis=1))),
        "individual_zero_rate": float(np.mean(scores <= 1e-12)),
    }


def run(source_dir: Path, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "status": "formal_r3_projection",
        "formal_scoring_updated": True,
        "family": FAMILY,
        "override_width_kcal_per_mol": OVERRIDE_WIDTH,
        "tracks": {},
    }
    task_rows = []
    with tempfile.TemporaryDirectory() as temporary:
        for track, filename in TRACKS.items():
            directory = ROOT / "src/verifier_grounded_benchmark/task/packs" / track
            scoring = yaml.safe_load((directory / "scoring.yaml").read_text(encoding="utf-8"))
            candidate = candidate_scoring(scoring)
            scoring_path = Path(temporary) / f"{track}.yaml"
            scoring_path.write_text(yaml.safe_dump(candidate, sort_keys=False, allow_unicode=True))
            projected = load_task_pack(directory / "tasks.yaml", directory / "verifier_specs.yaml", scoring_path)
            projected_tasks = {task.task_id: task for task in projected.tasks}
            observations = _observations(source_dir / filename, projected_tasks)
            baseline = np.array([
                recorded for _, _, recorded, _ in observations
            ])
            candidate_scores = np.array([
                [_score(projected, projected_tasks, task_id, answer) for task_id, answers, _, _ in observations for answer in answers]
            ]).reshape(len(observations), 4)
            delta = candidate_scores - baseline
            summary["tracks"][track] = {
                "tasks": len(observations),
                "baseline": _metrics(baseline),
                "candidate": _metrics(candidate_scores),
                "mean_change": dict(zip(GROUPS, (delta.mean(axis=0) * 100).tolist(), strict=True)),
                "affected_task_count": int(np.sum(np.any(np.abs(delta) > 1e-12, axis=1))),
            }
            for index, (task_id, _, _, _) in enumerate(observations):
                task_rows.append({
                    "track": track,
                    "task_id": task_id,
                    **{f"baseline_{group}": float(baseline[index, column] * 100) for column, group in enumerate(GROUPS)},
                    **{f"candidate_{group}": float(candidate_scores[index, column] * 100) for column, group in enumerate(GROUPS)},
                    **{f"change_{group}": float(delta[index, column] * 100) for column, group in enumerate(GROUPS)},
                })
            (output_dir / f"{track}.scoring.override.yaml").write_text(
                yaml.safe_dump(candidate, sort_keys=False, allow_unicode=True), encoding="utf-8"
            )
    with (output_dir / "task_scores.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(task_rows[0]))
        writer.writeheader()
        writer.writerows(task_rows)
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=ROOT / "review_system/data/shared-files")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    print(json.dumps(run(args.source_dir, args.output_dir), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
