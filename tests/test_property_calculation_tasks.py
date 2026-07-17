from __future__ import annotations

import hashlib
import pytest

from verifier_grounded_benchmark.task import load_task_pack
from verifier_grounded_benchmark.task.resources import package_resource

EXPECTED_CIF = {
    "ETDIAM01": (
        43,
        "83adc2a15c2a055782f584c51b20a0593ef217696379136e8a0b864176cc36fc",
        24,
        "H16 C4 N4",
    ),
    "ETDIAM18": (
        43,
        "b8b9b3c434ec6abda60cba8e7e7706716c33c72960f66390cece8210ca8458e9",
        24,
        "H16 C4 N4",
    ),
    "alpha_CONTCAR": (
        132,
        "aa8c4899bf7d5446194f96a6655ce0da31a3d7f1961d9d53463b8878ad17483a",
        108,
        "H12 C36 I36 N24",
    ),
    "beta_CONTCAR": (
        132,
        "47833b594190b12f126bfddd5ee48ba6f18a482591d527d268ab950e8b6c6f77",
        108,
        "H12 C36 I36 N24",
    ),
}


def load_pack():
    return load_task_pack(
        package_resource("property_calculation", "tasks.yaml"),
        package_resource("property_calculation", "verifier_specs.yaml"),
    )


def load_tasks() -> dict[str, dict]:
    return load_pack().tasks_by_id


def test_property_task_pack_uses_common_envelope_and_answer_schema() -> None:
    tasks = load_tasks()

    assert set(tasks) == {
        "property_calc_free_energy_001",
        "property_calc_crystal_phase_002",
    }
    for task in tasks.values():
        assert task["version"] == 1
        assert task["task_type"] == "property_calculation"
        assert task["object_type"] == "crystal_pair"
        assert task["formal_track"] is True
        assert task["answer_schema"] == {
            "format": "final_answer_line",
            "final_answer_prefix": "FINAL ANSWER:",
            "value_type": "json",
            "cardinality": "one",
        }
        assert "constraints" not in task
        assert task["gold_provenance"] == {
            "disclosure": "withheld_initial_release"
        }
        assert task["scoring"]["aggregation"] == "arithmetic_mean"
        assert "parse_error" in set(task["failure_policy"].values())


def test_all_cif_inputs_are_complete_and_embedded_verbatim_in_prompts() -> None:
    tasks = load_tasks()
    objects = {
        item["object_id"]: (task, item)
        for task in tasks.values()
        for item in task["input_objects"]
    }

    assert set(objects) == set(EXPECTED_CIF)
    for object_id, (task, item) in objects.items():
        expected_lines, expected_hash, _, _ = EXPECTED_CIF[object_id]
        value = item["value"]
        assert item["type"] == "cif"
        assert item["presentation"] == "prompt_inline"
        assert len(value.splitlines()) == expected_lines
        assert hashlib.sha256(value.encode()).hexdigest() == expected_hash
        assert value in task["prompt"]


def test_cif_inputs_parse_to_expected_structures() -> None:
    pymatgen = pytest.importorskip("pymatgen.core")
    tasks = load_tasks()

    for task in tasks.values():
        for item in task["input_objects"]:
            _, _, atom_count, formula = EXPECTED_CIF[item["object_id"]]
            structure = pymatgen.Structure.from_str(item["value"], fmt="cif")
            assert len(structure) == atom_count
            assert structure.composition.formula == formula
            assert structure.volume > 0


def test_task_7_contract_and_gold() -> None:
    pack = load_pack()
    task = pack.tasks_by_id["property_calc_free_energy_001"]

    assert [item["object_id"] for item in task["input_objects"]] == [
        "ETDIAM01",
        "ETDIAM18",
    ]
    assert task["requested_properties"] == [
        {
            "name": "free_energy_difference",
            "value_type": "number",
            "unit": "kJ/mol",
            "comparison_group": "free_energy_difference",
        }
    ]
    assert task["gold_answers"] == [
        {
            "property": "free_energy_difference",
            "value": 0.258031679,
            "unit": "kJ/mol",
            "scoring_profile": "property_calculation_free_energy_difference_numeric_gold_v1",
        }
    ]
    profile = pack.scoring_profiles[task["gold_answers"][0]["scoring_profile"]]
    assert profile["lower_tolerance"] == 0.001
    assert profile["upper_tolerance"] == 0.001
    assert profile["provenance"]["review_status"] == "provisional"
    assert task["scoring"]["comparison_groups"] == [
        {"id": "free_energy_difference", "mode": "all"}
    ]
    assert "300 K" in task["prompt"]
    assert "kJ/mol" in task["prompt"]
    assert "meV" not in task["prompt"]
    assert "0.258031679" not in task["prompt"]


def test_task_8_contract_and_gold() -> None:
    pack = load_pack()
    task = pack.tasks_by_id["property_calc_crystal_phase_002"]

    assert [item["object_id"] for item in task["input_objects"]] == [
        "alpha_CONTCAR",
        "beta_CONTCAR",
    ]
    assert task["requested_properties"] == [
        {
            "name": "potential_energy_difference",
            "value_type": "number",
            "unit": "eV",
            "comparison_group": "potential_energy_difference",
        },
        {
            "name": "ambient_pressure_phase",
            "value_type": "string",
            "comparison_group": "pressure_phase_assignment",
        },
        {
            "name": "high_pressure_phase",
            "value_type": "string",
            "comparison_group": "pressure_phase_assignment",
        },
    ]
    assert task["gold_answers"] == [
        {
            "property": "potential_energy_difference",
            "value": 0.079,
            "unit": "eV",
            "scoring_profile": "property_calculation_potential_energy_difference_numeric_gold_v1",
        },
        {
            "property": "ambient_pressure_phase",
            "value": "alpha",
            "scoring_profile": "property_calculation_ambient_pressure_phase_exact_string_v1",
        },
        {
            "property": "high_pressure_phase",
            "value": "beta",
            "scoring_profile": "property_calculation_high_pressure_phase_exact_string_v1",
        },
    ]
    assert task["scoring"]["comparison_groups"] == [
        {"id": "potential_energy_difference", "mode": "all"},
        {"id": "pressure_phase_assignment", "mode": "all"},
    ]
    assert "0.079" not in task["prompt"]
    assert "alpha is" not in task["prompt"].lower()
    assert "beta is" not in task["prompt"].lower()
    assert "Cambridge Crystallographic Data Centre" not in task["prompt"]
    assert "CCDC" not in task["prompt"]
    assert all("CCDC" not in item["value"] for item in task["input_objects"])


def test_prompts_are_english_tool_neutral_and_have_no_attachment_paths() -> None:
    banned = [
        "/Users/",
        "attachment",
        "upload",
        "pymatgen",
        "xTB",
        "verifier",
        "gold",
        "generation protocol",
    ]
    for task in load_tasks().values():
        prompt = task["prompt"]
        assert prompt.isascii()
        assert all(fragment.lower() not in prompt.lower() for fragment in banned)
        assert prompt.count("```cif") == 2


def test_property_track_has_no_runtime_verifier_specs() -> None:
    assert load_pack().verifier_specs == ()
