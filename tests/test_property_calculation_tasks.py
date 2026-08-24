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
    "DEBXIT06": (
        113,
        "c90454dc1687775fe2185770643d0224ff80cdd84ce7e267b538f374d0155775",
        92,
        "H28 C46 N12 O6",
    ),
    "Radiprodil_FormA": (
        73,
        "a97cef84ea1032da99c1ca8741816814d3e6f8b7875402c7a0537182d697fdca",
        196,
        "H80 C84 N12 O16 F4",
    ),
    "Radiprodil_FormC": (
        73,
        "c3b6cf123c89aa53877083c1e0edf5800ed82fffd5cbb288154615a2e5a911a3",
        196,
        "H80 C84 N12 O16 F4",
    ),
    "NOGCOE": (
        191,
        "92469e31fdb204152ee9ade5463815cc6f47ea51bb06b0cfb2d820c8aff26ea2",
        192,
        "H72 C108 N12",
    ),
}

EXPECTED_TASK_IDS = {
    "property_calc_free_energy_001",
    "property_calc_crystal_phase_002",
    "property_calc_003_hbond_count",
    "property_calc_004_ir_top3_frequencies",
    "property_calc_005_crystal_density",
    "property_calc_006_cocrystal_ratio",
    "property_calc_007_polymorph_free_energy_crossover",
    "property_calc_008_interaction_binding_energy",
    "property_calc_009_homo_lumo_gap",
    "property_calc_010_hbond_distances",
    "property_calc_011_accessible_pore_volume_ratio",
    "property_calc_012_carboxyl_hydrogen_distance",
    "property_calc_013_halogen_bond_energy",
    "property_calc_014_bay069_pka",
    "property_calc_015_formaldehyde_socme",
    "property_calc_016_anthracene_isc_rate",
    "property_calc_017_biacetyl_phosphorescence_rate",
    "property_calc_018_anthracene_ht_contribution",
    "property_calc_019_acetophenone_isc_rate",
    "property_calc_020_azulene_internal_conversion_rate",
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

    assert set(tasks) == EXPECTED_TASK_IDS
    for task in tasks.values():
        assert task["version"] == 1
        assert task["task_type"] == "property_calculation"
        assert task["object_type"]
        assert task["formal_track"] is True
        assert task["answer_schema"] == {
            "format": "final_answer_line",
            "final_answer_prefix": "FINAL ANSWER:",
            "value_type": "json",
            "cardinality": "one",
        }
        assert "constraints" not in task
        assert task["gold_provenance"]["disclosure"] == "withheld_initial_release"
        if task["task_id"].startswith("property_calc_0"):
            assert task["gold_provenance"].get("source")
        assert task["scoring"]["aggregation"] == "arithmetic_mean"
        assert "parse_error" in set(task["failure_policy"].values())


def test_all_cif_inputs_are_complete_and_embedded_verbatim_in_prompts() -> None:
    tasks = load_tasks()
    objects = {
        item["object_id"]: (task, item)
        for task in tasks.values()
        for item in task["input_objects"]
        if item["type"] == "cif"
    }

    assert set(EXPECTED_CIF).issubset(objects)
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
            if item["type"] != "cif":
                continue
            _, _, atom_count, formula = EXPECTED_CIF[item["object_id"]]
            structure = pymatgen.Structure.from_str(item["value"], fmt="cif")
            assert len(structure) == atom_count
            assert structure.composition.formula == formula
            assert structure.volume > 0


def test_every_input_object_is_embedded_exactly_once_in_its_prompt() -> None:
    for task in load_tasks().values():
        for item in task["input_objects"]:
            assert task["prompt"].count(item["value"]) == 1


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
            "scoring_profile": "property_calculation_free_energy_difference_numeric_gold_v2",
        }
    ]
    profile = pack.scoring_profiles[task["gold_answers"][0]["scoring_profile"]]
    assert profile["lower_tolerance"] == 0.258031679
    assert profile["upper_tolerance"] == 0.258031679
    assert profile["provenance"]["review_status"] == "approved"
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
            "scoring_profile": "property_calculation_potential_energy_difference_numeric_gold_v2",
        },
        {
            "property": "ambient_pressure_phase",
            "value": "alpha",
            "scoring_profile": "property_calculation_ambient_pressure_phase_exact_string_v2",
        },
        {
            "property": "high_pressure_phase",
            "value": "beta",
            "scoring_profile": "property_calculation_high_pressure_phase_exact_string_v2",
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


def test_expert_task_special_contracts_are_frozen() -> None:
    tasks = load_tasks()

    task_15 = tasks["property_calc_004_ir_top3_frequencies"]
    assert task_15["scoring"]["comparison_groups"] == [
        {"id": "top_three_frequencies", "mode": "unordered_numeric"}
    ]

    task_19 = tasks["property_calc_008_interaction_binding_energy"]
    assert [item["type"] for item in task_19["input_objects"]] == [
        "molecular_dimer_reference"
    ]
    assert "NC1=CC=C2C=CC(=O)N=C2N1" in task_19["prompt"]

    task_21 = tasks["property_calc_010_hbond_distances"]
    assert [item["type"] for item in task_21["input_objects"]] == ["xyz"]

    for task_id in (
        "property_calc_004_ir_top3_frequencies",
        "property_calc_008_interaction_binding_energy",
        "property_calc_009_homo_lumo_gap",
        "property_calc_010_hbond_distances",
    ):
        task = tasks[task_id]
        assert all(item["type"] != "gaussian_output_excerpt" for item in task["input_objects"])
        assert "gaussian" not in task["prompt"].lower()

    task_24 = tasks["property_calc_013_halogen_bond_energy"]
    assert "FI...NH3" in task_24["prompt"]
    assert "F-I...NH3" not in task_24["prompt"]


def test_excited_state_expert_task_contracts_are_frozen() -> None:
    pack = load_pack()
    expected = {
        "property_calc_015_formaldehyde_socme": (
            "spin_orbit_coupling_matrix_element",
            0.00734,
            "eV",
            "property_calculation_socme_numeric_gold_v2",
            0.0001,
        ),
        "property_calc_016_anthracene_isc_rate": (
            "intersystem_crossing_rate",
            117000000.0,
            "s^-1",
            "property_calculation_anthracene_isc_rate_numeric_gold_v2",
            10000000.0,
        ),
        "property_calc_017_biacetyl_phosphorescence_rate": (
            "phosphorescence_rate",
            98.0,
            "s^-1",
            "property_calculation_phosphorescence_rate_numeric_gold_v2",
            1.0,
        ),
        "property_calc_018_anthracene_ht_contribution": (
            "herzberg_teller_contribution",
            100.0,
            "percent",
            "property_calculation_ht_contribution_numeric_gold_v2",
            1.0,
        ),
        "property_calc_019_acetophenone_isc_rate": (
            "intersystem_crossing_rate",
            28400000000.0,
            "s^-1",
            "property_calculation_acetophenone_isc_rate_numeric_gold_v2",
            100000000.0,
        ),
        "property_calc_020_azulene_internal_conversion_rate": (
            "internal_conversion_rate",
            382000000.0,
            "s^-1",
            "property_calculation_internal_conversion_rate_numeric_gold_v2",
            10000000.0,
        ),
    }

    for task_id, (property_name, value, unit, profile_id, tolerance) in expected.items():
        task = pack.tasks_by_id[task_id]
        assert task["requested_properties"] == [
            {
                "name": property_name,
                "value_type": "number",
                "unit": unit,
                "comparison_group": property_name,
            }
        ]
        assert task["gold_answers"] == [
            {
                "property": property_name,
                "value": value,
                "unit": unit,
                "scoring_profile": profile_id,
            }
        ]
        assert task["scoring"]["comparison_groups"] == [
            {"id": property_name, "mode": "all"}
        ]
        assert [item["type"] for item in task["input_objects"]] == ["smiles"]
        assert all(suffix not in task["prompt"] for suffix in (".out", ".inp", ".hess"))
        assert "ORCA" not in task["prompt"]
        profile = pack.scoring_profiles[profile_id]
        assert profile["lower_tolerance"] == tolerance
        assert profile["upper_tolerance"] == tolerance
        assert profile["provenance"]["review_status"] == "approved"

    acetophenone = pack.tasks_by_id["property_calc_019_acetophenone_isc_rate"]
    assert "-1, 0, and +1 T1 spin sublevels" in acetophenone["prompt"]
    anthracene_ht = pack.tasks_by_id["property_calc_018_anthracene_ht_contribution"]
    assert "0-to-100 scale" in anthracene_ht["prompt"]


def test_prompts_are_english_tool_neutral_and_have_no_attachment_paths() -> None:
    banned = [
        "/Users/",
        "attached",
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
        assert prompt.count("```cif") == sum(
            item["type"] == "cif" for item in task["input_objects"]
        )


def test_property_track_has_no_runtime_verifier_specs() -> None:
    assert load_pack().verifier_specs == ()
