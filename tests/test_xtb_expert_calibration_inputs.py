from __future__ import annotations

import json
from importlib.resources import files

import yaml

from verifier_grounded_benchmark.evaluation.open_generation.parsing.dispatcher import normalize_answer_record
from verifier_grounded_benchmark.task.loader import (
    load_task_pack,
)
from verifier_grounded_benchmark.evaluation.open_generation.verifiers.xtb.backend import inspect_xyz, parse_xyz


CALIBRATION_DIR = files("verifier_grounded_benchmark.task.calibration.xtb")
TASKS_PATH = CALIBRATION_DIR.joinpath("tasks.yaml")
SPECS_PATH = CALIBRATION_DIR.joinpath("verifier_specs.yaml")
ANSWERS_PATH = CALIBRATION_DIR.joinpath("answers.jsonl")
MANIFEST_PATH = CALIBRATION_DIR.joinpath("manifest.yaml")
TASK_IDS = {
    "xtb_formula_dipole_min_014",
    "xtb_two_fluorine_gap_min_015",
    "xtb_c10_f2_gap_min_016",
    "xtb_roy_singlepoint_energy_min_017",
    "xtb_ritonavir_optimized_energy_min_018",
}


def load_answers() -> list[dict]:
    with ANSWERS_PATH.open() as handle:
        return [json.loads(line) for line in handle if line.strip()]


def load_calibration_pack():
    return load_task_pack(TASKS_PATH, SPECS_PATH)


def test_expert_candidate_pack_is_complete_but_not_formal() -> None:
    pack = load_calibration_pack()
    tasks = pack.tasks_by_id
    specs = pack.verifier_specs_by_id

    assert set(tasks) == TASK_IDS
    assert len(specs) == 4
    for task in tasks.values():
        assert task["formal_track"] is False
        assert task["object_type"] == "small_molecule_3d"
        assert task["answer_schema"]["format"] == "final_answer_block"
        assert task["answer_schema"]["value_type"] == "xyz"
        assert task["answer_schema"]["fence_language"] == "xyz"
        assert task["scoring"]["aggregation"] == "geometric_mean"
        assert len(task["constraints"]) == 1
        assert "calibration_pending" not in task["constraints"][0]
        assert all(
            constraint.get("role") != "quality_gate"
            and constraint["property"] != "relaxation_energy"
            for constraint in task["constraints"]
        )


def test_expert_candidate_pack_uses_frozen_bounds_and_timeouts() -> None:
    pack = load_calibration_pack()
    tasks = pack.tasks_by_id
    specs = pack.verifier_specs_by_id
    expected = {
        "xtb_formula_dipole_min_014": (3.042, 9.328, 240),
        "xtb_two_fluorine_gap_min_015": (1.242666887976, 12.358052453139, 240),
        "xtb_c10_f2_gap_min_016": (1.242666887976, 12.358052453139, 240),
        "xtb_roy_singlepoint_energy_min_017": (-50.30, -50.25, 300),
        "xtb_ritonavir_optimized_energy_min_018": (-148.20, -148.15, 600),
    }

    for task_id, (lower, upper, timeout) in expected.items():
        constraint = tasks[task_id]["constraints"][0]
        spec = specs[constraint["verifier_id"]]
        profile = pack.scoring_profiles[constraint["scoring_profile"]]
        assert profile["full_score_target"] == lower
        assert profile["zero_score_anchor"] == upper
        assert spec["executor"]["timeout_seconds"] == timeout


def test_task_2_uses_exact_formula_and_neutral_doublet() -> None:
    pack = load_calibration_pack()
    tasks = pack.tasks_by_id
    specs = pack.verifier_specs_by_id
    task = tasks["xtb_formula_dipole_min_014"]
    spec = specs[task["constraints"][0]["verifier_id"]]

    assert task["structural_domain"] == {"formula": "C12H16N3O8"}
    assert spec["property_name"] == "dipole_moment"
    assert spec["backend"]["charge"] == 0
    assert spec["backend"]["uhf"] == 1
    assert spec["backend"]["validate_electron_parity"] is True
    assert "C12H16N3O8" in task["prompt"]
    assert "neutral doublet" in task["prompt"]


def test_tasks_3_and_4_use_comment_charge_and_only_source_constraints() -> None:
    pack = load_calibration_pack()
    tasks = pack.tasks_by_id
    specs = pack.verifier_specs_by_id
    task_3 = tasks["xtb_two_fluorine_gap_min_015"]
    task_4 = tasks["xtb_c10_f2_gap_min_016"]
    spec = specs[task_3["constraints"][0]["verifier_id"]]

    assert task_3["constraints"][0]["verifier_id"] == task_4["constraints"][0]["verifier_id"]
    assert task_3["structural_domain"] == {
        "allowed_elements": ["H", "C", "O", "N", "S", "F", "Cl"],
        "atom_count": [1, 40],
        "element_count_exact": {"F": 2},
        "element_count_max": {"C": 10},
    }
    assert task_4["structural_domain"] == {
        "allowed_elements": ["H", "C", "O", "N", "S", "F", "Cl"],
        "atom_count": [1, 40],
        "element_count_exact": {"C": 10, "F": 2},
    }
    assert spec["backend"]["charge_source"] == "xyz_comment"
    assert spec["backend"]["uhf"] == 0
    assert spec["backend"]["validate_electron_parity"] is True
    for task in (task_3, task_4):
        assert "charge=<integer>" in task["prompt"]
        assert "closed-shell" in task["prompt"]
        assert "neutral" not in task["prompt"].lower()
        assert "formula_denylist" not in task["structural_domain"]
        assert "heavy_atom_count" not in task["structural_domain"]


def test_roy_and_ritonavir_use_required_identity_and_energy_modes() -> None:
    pack = load_calibration_pack()
    tasks = pack.tasks_by_id
    specs = pack.verifier_specs_by_id
    roy = tasks["xtb_roy_singlepoint_energy_min_017"]
    ritonavir = tasks["xtb_ritonavir_optimized_energy_min_018"]
    roy_spec = specs[roy["constraints"][0]["verifier_id"]]
    ritonavir_spec = specs[ritonavir["constraints"][0]["verifier_id"]]

    assert roy["structural_domain"]["formula"] == "C12H9N3O2S"
    assert roy_spec["backend"]["calculation_mode"] == "submitted_singlepoint"
    assert roy["structure_identity"]["require_stereochemistry"] is False
    assert roy["structure_identity"].get("recheck_after_optimization") is not True

    assert ritonavir["structural_domain"]["formula"] == "C37H48N6O5S2"
    assert ritonavir_spec["backend"]["calculation_mode"] == "optimized"
    assert ritonavir["structure_identity"]["require_stereochemistry"] is True
    assert ritonavir["structure_identity"]["recheck_after_optimization"] is True
    assert "Ritonavir" in ritonavir["prompt"]
    assert ritonavir["structure_identity"]["reference_smiles"] in ritonavir["prompt"]


def test_calibration_answers_and_manifest_cover_valid_conformers_and_controls() -> None:
    tasks = load_calibration_pack().tasks_by_id
    answers = load_answers()
    with MANIFEST_PATH.open() as handle:
        manifest = yaml.safe_load(handle)

    assert len(answers) >= 15
    assert {answer["candidate_id"] for answer in answers} == set(manifest["candidates"])
    for task_id in TASK_IDS:
        task_answers = [answer for answer in answers if answer["task_id"] == task_id]
        roles = {answer["role"] for answer in task_answers}
        assert {"positive_candidate", "negative_baseline"}.issubset(roles)
        assert sum(answer["role"] == "positive_candidate" for answer in task_answers) >= 2

    for answer in answers:
        normalized = normalize_answer_record(answer, tasks[answer["task_id"]])
        assert normalized.ok, answer["candidate_id"]
        xyz = normalized.answer["candidates"][0]["xyz"]
        properties = inspect_xyz(parse_xyz(xyz))
        assert properties["atom_count"] == len(xyz.splitlines()) - 2


def test_positive_candidate_formulas_and_charge_comments() -> None:
    tasks = load_calibration_pack().tasks_by_id
    expected_formulas = {
        "xtb_formula_dipole_min_014": "C12H16N3O8",
        "xtb_roy_singlepoint_energy_min_017": "C12H9N3O2S",
        "xtb_ritonavir_optimized_energy_min_018": "C37H48N6O5S2",
    }
    for answer in load_answers():
        if answer["role"] != "positive_candidate":
            continue
        normalized = normalize_answer_record(answer, tasks[answer["task_id"]])
        molecule = parse_xyz(normalized.answer["candidates"][0]["xyz"])
        properties = inspect_xyz(molecule)
        expected_formula = expected_formulas.get(answer["task_id"])
        if expected_formula:
            assert properties["formula"] == expected_formula
        if answer["task_id"] in {
            "xtb_two_fluorine_gap_min_015",
            "xtb_c10_f2_gap_min_016",
        }:
            assert molecule.comment == "charge=0"
            assert properties["element_counts"].get("F") == 2


def test_expert_calibration_pack_is_not_registered() -> None:
    from verifier_grounded_benchmark import list_tracks

    assert "expert_calibration" not in {track.name for track in list_tracks(status=None)}
