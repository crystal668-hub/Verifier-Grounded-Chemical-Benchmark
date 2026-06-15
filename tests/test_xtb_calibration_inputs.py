from __future__ import annotations

import json
from pathlib import Path

import yaml

from benchmark.answer_extraction import normalize_answer_record
from benchmark.evaluate import load_tasks


ROOT = Path(__file__).resolve().parents[1]
TASK_DIR = ROOT / "tasks" / "xtb_xyz"
ANSWERS_PATH = TASK_DIR / "calibration_answers.jsonl"
MANIFEST_PATH = TASK_DIR / "calibration_manifest.yaml"


def _load_answers() -> list[dict]:
    with ANSWERS_PATH.open() as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _load_manifest() -> dict:
    with MANIFEST_PATH.open() as handle:
        return yaml.safe_load(handle)


def test_xtb_calibration_files_exist_and_are_nonempty() -> None:
    assert ANSWERS_PATH.exists()
    assert MANIFEST_PATH.exists()
    assert len(_load_answers()) >= 26
    assert len(_load_manifest()["candidates"]) >= 26


def test_xtb_calibration_answers_have_unique_candidate_ids() -> None:
    answers = _load_answers()
    candidate_ids = [answer["candidate_id"] for answer in answers]
    assert len(candidate_ids) == len(set(candidate_ids))


def test_xtb_calibration_answers_reference_known_tasks_and_extract_xyz() -> None:
    tasks = load_tasks(TASK_DIR / "tasks.yaml")
    answers = _load_answers()
    for answer in answers:
        assert answer["task_id"] in tasks
        assert answer["role"] in {"positive_candidate", "near_miss", "negative_baseline", "stress_case"}
        normalized = normalize_answer_record(answer, tasks[answer["task_id"]])
        assert normalized.ok, answer["candidate_id"]
        candidate = normalized.answer["candidates"][0]
        assert "xyz" in candidate
        xyz_lines = candidate["xyz"].splitlines()
        assert int(xyz_lines[0]) == len(xyz_lines) - 2


def test_xtb_calibration_manifest_matches_answers() -> None:
    answers = _load_answers()
    manifest = _load_manifest()
    manifest_ids = set(manifest["candidates"])
    answer_ids = {answer["candidate_id"] for answer in answers}
    assert answer_ids == manifest_ids
    for answer in answers:
        metadata = manifest["candidates"][answer["candidate_id"]]
        assert metadata["role"] == answer["role"]
        assert answer["task_id"] in metadata["target_tasks"]
        assert answer["task_id"] in metadata["expected_behavior"]


def test_xtb_calibration_covers_every_task_with_positive_and_negative_cases() -> None:
    tasks = load_tasks(TASK_DIR / "tasks.yaml")
    answers = _load_answers()
    for task_id in tasks:
        roles = {answer["role"] for answer in answers if answer["task_id"] == task_id}
        assert "positive_candidate" in roles, task_id
        assert "negative_baseline" in roles, task_id
