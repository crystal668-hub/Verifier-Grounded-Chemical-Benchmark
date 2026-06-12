from __future__ import annotations

from pathlib import Path

import yaml

from benchmark.answer_extraction import normalize_answer_record
from benchmark.evaluate import load_answers_jsonl, load_tasks, load_verifier_specs


ROOT = Path(__file__).resolve().parents[1]
TASK_DIR = ROOT / "tasks" / "mace_materials"


def test_mace_material_tasks_define_energy_property() -> None:
    tasks = load_tasks(TASK_DIR / "tasks.yaml")
    specs = load_verifier_specs(TASK_DIR / "verifier_specs.yaml")

    assert set(tasks) == {"mace_energy_window_si_001"}
    assert set(specs) == {"mace_energy_mcp_v1"}
    assert specs["mace_energy_mcp_v1"]["verification_script"] == "verifiers/materials/mace_energy.py"
    assert specs["mace_energy_mcp_v1"]["property_name"] == "energy"
    assert specs["mace_energy_mcp_v1"]["backend"]["server"] == "mace"
    assert specs["mace_energy_mcp_v1"]["mace"]["device"] == "cpu"
    assert all(task["formal_track"] is False for task in tasks.values())
    assert all(task["track_status"] == "prototype" for task in tasks.values())
    assert all("prototype" in task["capability_tags"] for task in tasks.values())
    assert all(spec["formal_track"] is False for spec in specs.values())
    assert all(spec["track_status"] == "prototype" for spec in specs.values())
    assert all(task["answer_schema"]["format"] == "final_answer_block" for task in tasks.values())
    assert all(task["answer_schema"]["value_type"] == "cif" for task in tasks.values())


def test_mace_material_sample_answers_use_fenced_inline_cif() -> None:
    tasks = load_tasks(TASK_DIR / "tasks.yaml")
    answers = load_answers_jsonl(TASK_DIR / "sample_answers.jsonl")

    assert len(answers) == 1
    normalized = normalize_answer_record(answers[0], tasks[answers[0]["task_id"]])
    assert normalized.ok
    assert normalized.answer is not None
    candidate = normalized.answer["candidates"][0]
    assert candidate["cif"].startswith("# generated using pymatgen\ndata_Si")


def test_mace_verifier_specs_are_yaml_loadable() -> None:
    with (TASK_DIR / "verifier_specs.yaml").open() as handle:
        payload = yaml.safe_load(handle)

    assert len(payload["verifiers"]) == 1
    assert payload["verifiers"][0]["environment"] == "mace-agent"
