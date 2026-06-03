from __future__ import annotations

from pathlib import Path

import yaml

from benchmark.evaluate import load_answers_jsonl, load_tasks, load_verifier_specs
from benchmark.answer_extraction import normalize_answer_record


ROOT = Path(__file__).resolve().parents[1]
TASK_DIR = ROOT / "tasks" / "matgl_materials"


def test_matgl_material_tasks_define_first_batch_properties() -> None:
    tasks = load_tasks(TASK_DIR / "tasks.yaml")
    specs = load_verifier_specs(TASK_DIR / "verifier_specs.yaml")

    assert set(tasks) == {
        "matgl_bandgap_window_si_001",
        "matgl_eform_window_si_002",
        "matgl_bandgap_eform_si_003",
    }
    assert set(specs) == {"matgl_bandgap_pbe_mcp_v1", "matgl_formation_energy_mcp_v1"}
    assert specs["matgl_bandgap_pbe_mcp_v1"]["verification_script"] == "verifiers/materials/matgl_bandgap.py"
    assert specs["matgl_formation_energy_mcp_v1"]["verification_script"] == "verifiers/materials/matgl_formation_energy.py"
    assert specs["matgl_bandgap_pbe_mcp_v1"]["property_name"] == "bandgap"
    assert specs["matgl_formation_energy_mcp_v1"]["property_name"] == "formation_energy"
    assert all(task["answer_schema"]["format"] == "final_answer_block" for task in tasks.values())
    assert all(task["answer_schema"]["value_type"] == "cif" for task in tasks.values())


def test_matgl_material_sample_answers_use_fenced_inline_cif() -> None:
    tasks = load_tasks(TASK_DIR / "tasks.yaml")
    answers = load_answers_jsonl(TASK_DIR / "sample_answers.jsonl")

    assert len(answers) == 3
    for answer in answers:
        normalized = normalize_answer_record(answer, tasks[answer["task_id"]])
        assert normalized.ok
        assert normalized.answer is not None
        candidate = normalized.answer["candidates"][0]
        assert candidate["cif"].startswith("# generated using pymatgen\ndata_Si")


def test_matgl_verifier_specs_are_yaml_loadable() -> None:
    with (TASK_DIR / "verifier_specs.yaml").open() as handle:
        payload = yaml.safe_load(handle)

    assert len(payload["verifiers"]) == 2
    assert payload["verifiers"][0]["backend"]["server"] == "matgl"
