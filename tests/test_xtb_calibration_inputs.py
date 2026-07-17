from __future__ import annotations

import json
from importlib.resources import files

import yaml

from verifier_grounded_benchmark.evaluation.open_generation.parsing.dispatcher import normalize_answer_record
from verifier_grounded_benchmark.task.loader import load_tasks_file as load_tasks
from verifier_grounded_benchmark.task.resources import package_resource


CALIBRATION_DIR = files("verifier_grounded_benchmark.task.calibration.xtb")
ANSWERS_PATH = CALIBRATION_DIR.joinpath("legacy_answers.jsonl")
MANIFEST_PATH = CALIBRATION_DIR.joinpath("legacy_manifest.yaml")
EXPERT_ANSWERS_PATH = CALIBRATION_DIR.joinpath("answers.jsonl")
ADVANCED_TASK_IDS = {
    "xtb_lumo_min_008",
    "xtb_polarizability_dipole_opt_009",
    "xtb_solvation_selectivity_alpb_010",
    "xtb_electrophilicity_max_011",
    "xtb_fukui_carbon_site_012",
    "xtb_hessian_thermo_stability_013",
}


def _load_answers() -> list[dict]:
    with ANSWERS_PATH.open() as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _load_expert_answers() -> list[dict]:
    with EXPERT_ANSWERS_PATH.open() as handle:
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
    tasks = load_tasks(package_resource("xtb", "tasks.yaml"))
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
    tasks = load_tasks(package_resource("xtb", "tasks.yaml"))
    answers = _load_answers() + _load_expert_answers()
    for task_id in tasks:
        roles = {answer["role"] for answer in answers if answer["task_id"] == task_id}
        assert "positive_candidate" in roles, task_id
        assert "negative_baseline" in roles, task_id


def test_xtb_advanced_tasks_have_at_least_three_calibration_roles() -> None:
    answers = _load_answers()
    for task_id in ADVANCED_TASK_IDS:
        roles = {answer["role"] for answer in answers if answer["task_id"] == task_id}
        assert {"positive_candidate", "near_miss", "negative_baseline"}.issubset(roles), task_id


def test_xtb_advanced_calibration_manifest_records_curated_controls() -> None:
    answers = _load_answers()
    manifest = _load_manifest()

    for task_id in ADVANCED_TASK_IDS:
        task_answers = [answer for answer in answers if answer["task_id"] == task_id]
        roles = {answer["role"] for answer in task_answers}
        assert {"positive_candidate", "near_miss", "negative_baseline"}.issubset(roles), task_id

        positive_ids = [answer["candidate_id"] for answer in task_answers if answer["role"] == "positive_candidate"]
        assert len(positive_ids) >= 1, task_id
        for candidate_id in positive_ids:
            metadata = manifest["candidates"][candidate_id]
            assert metadata["expected_behavior"][task_id] in {"high_score", "medium_or_high_score"}
            assert metadata["source"]
            assert metadata["molecule_family"]

    curated_ids = {
        answer["candidate_id"]
        for answer in answers
        if answer["task_id"] in ADVANCED_TASK_IDS and answer["role"] in {"positive_candidate", "near_miss"}
    }
    assert any("qm9" in manifest["candidates"][candidate_id]["source"].lower() for candidate_id in curated_ids)
