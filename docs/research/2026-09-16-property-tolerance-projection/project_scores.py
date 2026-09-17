"""Offline tolerance experiment; reuse the production evaluator without YAML writes.

Run from the repository root with PYTHONPATH=src and a Python environment containing
the project, numpy and openpyxl. See the adjacent research report for interpretation.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

from verifier_grounded_benchmark.evaluation.property_calculation import (
    PropertyCalculationEvaluator,
)
from verifier_grounded_benchmark.evaluation.property_calculation.parsing.dispatcher import (
    parse_answer,
)
from verifier_grounded_benchmark.task.loader import load_task_pack
from verifier_grounded_benchmark.task.models import (
    PropertyCalculationTaskSpec,
    TaskPack,
    freeze_mapping,
)

ROOT = Path(__file__).resolve().parents[3]
GROUPS = (
    "gpt_sol_skill_on",
    "gpt_sol_skill_off",
    "qwen_flash_skill_on",
    "qwen_flash_skill_off",
)
SOURCES = {
    "property_calculation_basic": "99d73931db2f439c80453dd9adfaecb0.xlsx",
    "property_calculation_advanced": "f1b6a8d8836e4cbc9f72e5f452feb0bc.xlsx",
}
PENALTIES = {"property_calculation_basic": 0.03, "property_calculation_advanced": 0.003}
SEED = 20260916
BASELINE_INVENTORY = ROOT / "releases/v0.9.2/task-inventory.json"


def baseline_profiles(profile_ids) -> dict:
    inventory = json.loads(BASELINE_INVENTORY.read_text(encoding="utf-8"))
    return {
        key: inventory["scoring_profiles"][key]["definition"] for key in profile_ids
    }


def load_baseline_pack(track: str) -> TaskPack:
    directory = ROOT / "src/verifier_grounded_benchmark/task/packs" / track
    pack = load_task_pack(directory / "tasks.yaml", directory / "verifier_specs.yaml")
    return replace(
        pack,
        version="0.9.2",
        scoring_profiles=freeze_mapping(baseline_profiles(pack.scoring_profiles)),
    )


@dataclass
class Observation:
    task: PropertyCalculationTaskSpec
    answers: list[dict]
    recorded: np.ndarray
    source_row: int


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_observations(path: Path, pack: TaskPack) -> list[Observation]:
    import openpyxl  # Optional dependency used only to read the private workbooks.

    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        if len(workbook.worksheets) != 1:
            raise ValueError("Expected one worksheet per supplied workbook")
        rows = list(workbook.active.values)
    finally:
        workbook.close()
    expected_models = ["gpt-5-6-sol", "gpt-5-6-sol", "qwen3-8-flash", "qwen3-8-flash"]
    columns = [4, 7, 10, 13]
    if [rows[1][j] for j in columns] != expected_models:
        raise ValueError("Unexpected model header/order")
    if [rows[2][j] for j in columns] != ["skill-on", "skill-off"] * 2:
        raise ValueError("Unexpected skill header/order")
    if any(rows[3][j + 2] != "v0.9.2 得分" for j in columns):
        raise ValueError("Expected v0.9.2 baseline scores")
    tasks = {task.task_id: task for task in pack.tasks}
    observations = []
    seen = set()
    for row_number, row in enumerate(rows[4:], 5):
        match = re.match(
            r"(property_calculation_(?:basic|advanced)_\d{3}_\w+)", str(row[0])
        )
        if not match:
            if str(row[0]).startswith("各实验组平均分") or all(v is None for v in row):
                continue
            raise ValueError(f"Unrecognized source row {row_number}")
        task_id = match[1]
        if task_id in seen or task_id not in tasks:
            raise ValueError(f"Duplicate or unknown task: {task_id}")
        seen.add(task_id)
        task = tasks[task_id]
        names = [g["property"] for g in task.raw["gold_answers"]]
        sheet_gold, unknown = parse_answer(json.loads(row[2]), names)
        expected_gold = {
            g["property"]: {k: g[k] for k in ("value", "unit") if k in g}
            for g in task.raw["gold_answers"]
        }
        if unknown or sheet_gold != expected_gold:
            raise ValueError(f"Workbook/config gold mismatch: {task_id}")
        answers = [json.loads(row[j]) if row[j] is not None else {} for j in columns]
        if any(not isinstance(answer, dict) for answer in answers):
            raise ValueError(f"Answer must be a JSON object: {task_id}")
        recorded = np.array([row[j + 2] for j in columns], dtype=float)
        if not np.isfinite(recorded).all():
            raise ValueError(f"Missing/nonfinite recorded score: {task_id}")
        observations.append(Observation(task, answers, recorded, row_number))
    if seen != set(tasks):
        raise ValueError(f"Task coverage mismatch: {set(tasks) - seen}")
    return observations


def profiles_at_scale(
    pack: TaskPack, task: PropertyCalculationTaskSpec, scale: float
) -> dict:
    if not np.isfinite(scale) or scale <= 0:
        raise ValueError("Tolerance scale must be finite and positive")
    profiles = {key: dict(value) for key, value in pack.scoring_profiles.items()}
    for gold in task.raw["gold_answers"]:
        profile = profiles[gold["scoring_profile"]]
        if profile["type"] == "numeric_gold":
            for side in ("lower_tolerance", "upper_tolerance"):
                profile[side] *= scale
    return profiles


def evaluate(
    pack: TaskPack, observation: Observation, scale: float = 1.0
) -> tuple[np.ndarray, np.ndarray]:
    profiles = profiles_at_scale(pack, observation.task, scale)
    results = [
        PropertyCalculationEvaluator().evaluate(
            answer,
            observation.task,
            profiles,
            versions={"scoring": pack.scoring_version},
        )
        for answer in observation.answers
    ]
    numeric = []
    for result in results:
        fields = [
            c["score"]
            for c in result["scores"]["constraint_scores"]
            if c["type"] == "numeric_gold"
        ]
        numeric.append(float(np.mean(fields)) if fields else 0.0)
    return np.array([r["scores"]["score"] for r in results]), np.array(numeric)


def candidate_options(
    pack: TaskPack, observation: Observation, training: tuple = (0, 1, 2, 3)
) -> tuple[str, list]:
    baseline, numeric = evaluate(pack, observation)
    profiles = [
        pack.scoring_profiles[g["scoring_profile"]]
        for g in observation.task.raw["gold_answers"]
    ]
    if not any(p["type"] == "numeric_gold" for p in profiles):
        return "categorical_fixed", [(1.0, baseline)]
    sample = numeric[list(training)]
    category, lower, upper = "mixed", 0.1, 1.0
    if np.max(sample) <= 0.1:
        category, lower, upper = "numeric_floor", 1.0, 10.0
    elif np.min(sample) >= 0.8:
        category, upper = "numeric_ceiling", 0.5
    grid = sorted({float(f"{value:.3g}") for value in np.geomspace(lower, upper, 301)})
    options = []
    for scale in grid:
        score, numeric_score = evaluate(pack, observation, scale)
        if category == "numeric_floor" and np.mean(numeric_score[list(training)]) < 0.2:
            continue
        options.append((scale, score))
    if not options:
        return "floor_unrecoverable_within_bounds", [(1.0, baseline)]
    return category, options


def select_option(
    options: list, penalty: float, training: tuple = (0, 1, 2, 3)
) -> tuple:
    # Model names, target means and signed model differences never enter selection.
    return max(
        options,
        key=lambda option: (
            float(np.var(option[1][list(training)])) - penalty * np.log(option[0]) ** 2
        ),
    )


def mean_ci(values: np.ndarray, indices: np.ndarray) -> list[float]:
    return np.quantile(values[indices].mean(axis=1), [0.025, 0.975]).tolist()


def score_metrics(scores: np.ndarray, indices: np.ndarray) -> dict:
    groups = {}
    for column, name in enumerate(GROUPS):
        values = scores[:, column] * 100
        groups[name] = {
            "n": len(values),
            "mean": float(values.mean()),
            "sd": float(values.std(ddof=1)),
            "median": float(np.median(values)),
            "q25": float(np.quantile(values, 0.25)),
            "q75": float(np.quantile(values, 0.75)),
            "zero_rate": float(np.mean(values <= 1e-12)),
            "low_rate": float(np.mean(values <= 10)),
            "high_rate": float(np.mean(values >= 90)),
            "full_rate": float(np.mean(values >= 100 - 1e-10)),
            "mean_ci95": mean_ci(values, indices),
        }
    pairs = {}
    for name, difference in {
        "skill_on": (scores[:, 0] - scores[:, 2]) * 100,
        "skill_off": (scores[:, 1] - scores[:, 3]) * 100,
        "model_average": (scores[:, :2].mean(axis=1) - scores[:, 2:].mean(axis=1))
        * 100,
    }.items():
        pairs[name] = {
            "mean_gap_gpt_minus_qwen": float(difference.mean()),
            "mean_absolute_gap": float(np.abs(difference).mean()),
            "ci95": mean_ci(difference, indices),
            "gpt_wins": int(np.sum(difference > 1e-8)),
            "ties": int(np.sum(np.abs(difference) <= 1e-8)),
            "qwen_wins": int(np.sum(difference < -1e-8)),
        }
    return {
        "groups": groups,
        "pairs": pairs,
        "overall_mean": float(scores.mean() * 100),
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
        "all_zero_tasks": int(np.sum(np.max(scores, axis=1) <= 1e-12)),
        "all_high_tasks": int(np.sum(np.min(scores, axis=1) >= 0.9)),
        "tied_tasks": int(np.sum(np.ptp(scores, axis=1) <= 1e-10)),
        "near_tied_tasks_under_1pt": int(np.sum(np.ptp(scores, axis=1) < 0.01)),
        "zero_rate": float(np.mean(scores <= 1e-12)),
    }


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def run(source_dir: Path, output_dir: Path, bootstrap_samples: int = 10000) -> dict:
    source_hashes = {str(BASELINE_INVENTORY): sha256(BASELINE_INVENTORY)}
    packs = {}
    observations_by_track = {}
    for track, filename in SOURCES.items():
        pack_dir = ROOT / "src/verifier_grounded_benchmark/task/packs" / track
        inputs = [
            source_dir / filename,
            *[
                pack_dir / name
                for name in ("tasks.yaml", "scoring.yaml", "verifier_specs.yaml")
            ],
        ]
        for path in inputs:
            source_hashes[str(path)] = sha256(path)
        pack = load_baseline_pack(track)
        packs[track] = pack
        observations_by_track[track] = read_observations(source_dir / filename, pack)
    summary = {
        "seed": SEED,
        "bootstrap_samples": bootstrap_samples,
        "source_sha256": source_hashes,
        "tracks": {},
    }
    parameters, task_rows, group_rows, sensitivity_rows = [], [], [], []
    for track, pack in packs.items():
        observations = observations_by_track[track]
        baseline = np.array([evaluate(pack, item)[0] for item in observations])
        recorded = np.array([item.recorded for item in observations])
        mismatch = float(np.max(np.abs(recorded - baseline)))
        if mismatch > 5.1e-7:
            raise ValueError(f"Baseline reproduction failed for {track}: {mismatch}")
        options = [candidate_options(pack, item) for item in observations]
        chosen = [select_option(choices, PENALTIES[track]) for _, choices in options]
        candidate = np.array([choice[1] for choice in chosen])
        rng = np.random.default_rng(SEED)
        indices = rng.integers(
            0, len(observations), size=(bootstrap_samples, len(observations))
        )
        baseline_metrics = score_metrics(baseline, indices)
        candidate_metrics = score_metrics(candidate, indices)
        sd_delta = (candidate.std(axis=1) - baseline.std(axis=1)) * 100
        track_summary = {
            "source_file": SOURCES[track],
            "source_sheet": "结果汇总" if "basic" in track else "工作表 1",
            "baseline_max_absolute_error_0_to_1": mismatch,
            "missing_answers": int(
                sum(not a for item in observations for a in item.answers)
            ),
            "penalty": PENALTIES[track],
            "baseline": baseline_metrics,
            "candidate": candidate_metrics,
            "within_task_sd_gain_ci95": mean_ci(sd_delta, indices),
            "tasks_with_sd_gain_over_1pt": int(np.sum(sd_delta > 1)),
            "tasks_with_sd_loss_over_1pt": int(np.sum(sd_delta < -1)),
            "holdout": {},
        }
        for variant, metrics in (
            ("baseline", baseline_metrics),
            ("candidate", candidate_metrics),
        ):
            for group in GROUPS:
                row = {
                    "track": track,
                    "variant": variant,
                    "group": group,
                    **metrics["groups"][group],
                }
                row["ci95_lower"], row["ci95_upper"] = row.pop("mean_ci95")
                group_rows.append(row)
        for penalty in (0.0, 0.003, 0.01, 0.03, 0.1):
            matrix = np.array(
                [select_option(choices, penalty)[1] for _, choices in options]
            )
            sensitivity_rows.append(
                {
                    "track": track,
                    "experiment": "selection_penalty",
                    "value": penalty,
                    **{
                        group: float(matrix[:, col].mean() * 100)
                        for col, group in enumerate(GROUPS)
                    },
                    "within_task_sd": float(matrix.std(axis=1).mean() * 100),
                    "model_gap": float(
                        (matrix[:, :2].mean() - matrix[:, 2:].mean()) * 100
                    ),
                }
            )
        for multiplier in (0.8, 1.0, 1.2):
            matrix = np.array(
                [
                    evaluate(
                        pack,
                        item,
                        choice[0] * multiplier
                        if category != "categorical_fixed"
                        else 1,
                    )[0]
                    for item, choice, (category, _) in zip(
                        observations, chosen, options, strict=True
                    )
                ]
            )
            sensitivity_rows.append(
                {
                    "track": track,
                    "experiment": "frozen_width_multiplier",
                    "value": multiplier,
                    **{
                        group: float(matrix[:, col].mean() * 100)
                        for col, group in enumerate(GROUPS)
                    },
                    "within_task_sd": float(matrix.std(axis=1).mean() * 100),
                    "model_gap": float(
                        (matrix[:, :2].mean() - matrix[:, 2:].mean()) * 100
                    ),
                }
            )
        for training, heldout, label in (
            ((0, 2), (1, 3), "fit_on_evaluate_off"),
            ((1, 3), (0, 2), "fit_off_evaluate_on"),
        ):
            heldout_scores = np.array(
                [
                    select_option(
                        candidate_options(pack, item, training)[1],
                        PENALTIES[track],
                        training,
                    )[1]
                    for item in observations
                ]
            )[:, list(heldout)]
            original_gap = (
                np.abs(baseline[:, heldout[0]] - baseline[:, heldout[1]]) * 100
            )
            new_gap = np.abs(heldout_scores[:, 0] - heldout_scores[:, 1]) * 100
            track_summary["holdout"][label] = {
                "baseline_absolute_gap": float(original_gap.mean()),
                "candidate_absolute_gap": float(new_gap.mean()),
                "absolute_gap_gain_ci95": mean_ci(new_gap - original_gap, indices),
                "gpt_mean": float(heldout_scores[:, 0].mean() * 100),
                "qwen_mean": float(heldout_scores[:, 1].mean() * 100),
                "signed_gap_ci95": mean_ci(
                    (heldout_scores[:, 0] - heldout_scores[:, 1]) * 100, indices
                ),
            }
        for index, (item, (category, _), (scale, _)) in enumerate(
            zip(observations, options, chosen, strict=True)
        ):
            row = {
                "track": track,
                "task_id": item.task.task_id,
                "source_row": item.source_row,
                "category": category,
                "tolerance_multiplier": scale,
            }
            for col, group in enumerate(GROUPS):
                row[f"baseline_{group}"] = float(baseline[index, col] * 100)
                row[f"candidate_{group}"] = float(candidate[index, col] * 100)
            row.update(
                {
                    "baseline_sd": float(baseline[index].std() * 100),
                    "candidate_sd": float(candidate[index].std() * 100),
                    "sd_gain": float(sd_delta[index]),
                }
            )
            task_rows.append(row)
            for gold in item.task.raw["gold_answers"]:
                profile = pack.scoring_profiles[gold["scoring_profile"]]
                numeric = profile["type"] == "numeric_gold"
                parameters.append(
                    {
                        "track": track,
                        "task_id": item.task.task_id,
                        "property": gold["property"],
                        "profile_id": gold["scoring_profile"],
                        "gold": gold["value"],
                        "unit": gold.get("unit", ""),
                        "value_transform": profile.get("value_transform", "identity")
                        if numeric
                        else "categorical",
                        "category": category,
                        "tolerance_multiplier": scale if numeric else 1.0,
                        "old_lower_tolerance": profile.get("lower_tolerance", ""),
                        "old_upper_tolerance": profile.get("upper_tolerance", ""),
                        "new_lower_tolerance": profile["lower_tolerance"] * scale
                        if numeric
                        else "",
                        "new_upper_tolerance": profile["upper_tolerance"] * scale
                        if numeric
                        else "",
                    }
                )
        summary["tracks"][track] = track_summary
    # Fail before writing any experimental outputs if an input was modified.
    if any(sha256(Path(path)) != digest for path, digest in source_hashes.items()):
        raise RuntimeError("An input changed during the projection")
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, rows in (
        ("candidate_tolerances.csv", parameters),
        ("task_scores.csv", task_rows),
        ("group_statistics.csv", group_rows),
        ("sensitivity.csv", sensitivity_rows),
    ):
        write_csv(output_dir / name, rows)
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-dir", type=Path, default=ROOT / "review_system/data/shared-files"
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path(__file__).resolve().parent
    )
    args = parser.parse_args()
    summary = run(args.source_dir, args.output_dir)
    for track, result in summary["tracks"].items():
        print(
            track,
            json.dumps(
                {
                    "means": {
                        g: v["mean"] for g, v in result["candidate"]["groups"].items()
                    },
                    "sd": result["candidate"]["mean_within_task_sd"],
                    "holdout": result["holdout"],
                }
            ),
        )


if __name__ == "__main__":
    main()
