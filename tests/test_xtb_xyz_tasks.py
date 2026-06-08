from __future__ import annotations

from pathlib import Path

import yaml

from benchmark.answer_extraction import normalize_answer_record
from benchmark.evaluate import load_answers_jsonl, load_tasks, load_verifier_specs


ROOT = Path(__file__).resolve().parents[1]
TASK_DIR = ROOT / "tasks" / "xtb_xyz"


def test_xtb_xyz_tasks_define_first_batch_properties() -> None:
    tasks = load_tasks(TASK_DIR / "tasks.yaml")
    specs = load_verifier_specs(TASK_DIR / "verifier_specs.yaml")

    assert set(tasks) == {
        "xtb_gap_window_001",
        "xtb_dipole_window_002",
        "xtb_gap_max_003",
        "xtb_gap_min_004",
        "xtb_dipole_max_005",
        "xtb_relaxation_energy_min_006",
        "xtb_gap_dipole_window_007",
    }
    assert set(specs) == {
        "xtb_gap_gfn2_v1",
        "xtb_dipole_gfn2_v1",
        "xtb_relaxation_energy_gfn2_v1",
    }
    assert specs["xtb_gap_gfn2_v1"]["verification_script"] == "verifiers/xtb/xtb_gap.py"
    assert specs["xtb_dipole_gfn2_v1"]["verification_script"] == "verifiers/xtb/xtb_dipole.py"
    assert specs["xtb_relaxation_energy_gfn2_v1"]["verification_script"] == "verifiers/xtb/xtb_relaxation_energy.py"
    assert specs["xtb_gap_gfn2_v1"]["property_name"] == "homo_lumo_gap"
    assert specs["xtb_dipole_gfn2_v1"]["property_name"] == "dipole_moment"
    assert specs["xtb_relaxation_energy_gfn2_v1"]["property_name"] == "relaxation_energy"
    assert specs["xtb_gap_gfn2_v1"]["backend"]["type"] == "local_xtb"
    assert specs["xtb_gap_gfn2_v1"]["backend"]["executable"] == "xtb"
    assert specs["xtb_gap_gfn2_v1"]["backend"]["method"] == "GFN2-xTB"

    for task in tasks.values():
        assert task["answer_schema"]["format"] == "final_answer_block"
        assert task["answer_schema"]["value_type"] == "xyz"
        assert task["answer_schema"]["fence_language"] == "xyz"
        assert task["formal_track"] is True
        assert "small_molecule_3d" == task["object_type"]
        assert task["scoring"]["aggregation"] == "geometric_mean"
        for constraint in task["constraints"]:
            assert constraint["verifier_id"] in specs

    relaxation = tasks["xtb_relaxation_energy_min_006"]["constraints"][0]
    assert relaxation["type"] == "minimize_bounded"
    assert relaxation["property"] == "relaxation_energy"
    assert relaxation["upper"] == 0.5


def test_xtb_xyz_prompts_expose_domain_without_verifier_internals() -> None:
    tasks = load_tasks(TASK_DIR / "tasks.yaml")

    required = [
        "Allowed elements: H, C, N, O, F, P, S, Cl, Br.",
        "Atom count must be between 3 and 80 inclusive.",
        "Heavy atom count must be between 1 and 40 inclusive.",
        "all hydrogens explicit",
        "FINAL ANSWER:",
        "```xyz",
    ]
    forbidden = ["verifier_id", "verifiers/", "sigma", "geometric_mean", "xtb_gap_gfn2_v1"]
    for task in tasks.values():
        prompt = task["prompt"]
        for phrase in required:
            assert phrase in prompt
        for phrase in forbidden:
            assert phrase not in prompt


def test_xtb_xyz_sample_answers_use_fenced_xyz() -> None:
    tasks = load_tasks(TASK_DIR / "tasks.yaml")
    answers = load_answers_jsonl(TASK_DIR / "sample_answers.jsonl")

    assert len(answers) == 7
    for answer in answers:
        normalized = normalize_answer_record(answer, tasks[answer["task_id"]])
        assert normalized.ok
        assert normalized.answer is not None
        candidate = normalized.answer["candidates"][0]
        assert "xyz" in candidate
        lines = candidate["xyz"].splitlines()
        assert int(lines[0]) == len(lines) - 2


def test_xtb_verifier_specs_are_yaml_loadable() -> None:
    with (TASK_DIR / "verifier_specs.yaml").open() as handle:
        payload = yaml.safe_load(handle)

    assert len(payload["verifiers"]) == 3
    assert payload["verifiers"][0]["domain"]["allowed_elements"] == ["H", "C", "N", "O", "F", "P", "S", "Cl", "Br"]
