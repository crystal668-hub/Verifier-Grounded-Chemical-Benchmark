from __future__ import annotations

import re

import pytest

import verifier_grounded_benchmark as vgb
from verifier_grounded_benchmark.task.loader import load_task_pack
from verifier_grounded_benchmark.task.resources import package_resource

EXPECTED_GOLD = {
    "property_calc_easy_001_toluene_aqueous_solvation_free_energy": (-0.82, "kcal/mol"),
    "property_calc_easy_002_ethanol_aqueous_solvation_free_energy": (-5.42, "kcal/mol"),
    "property_calc_easy_003_diethyl_ether_aqueous_solvation_free_energy": (-2.11, "kcal/mol"),
    "property_calc_easy_004_anisole_aqueous_solvation_free_energy": (-1.98, "kcal/mol"),
    "property_calc_easy_005_nitrobenzene_reduction_potential": (-1.24, "V"),
    "property_calc_easy_006_tetracyanoethylene_reduction_potential": (0.21, "V"),
    "property_calc_easy_007_dimethylaniline_oxidation_potential": (0.83, "V"),
    "property_calc_easy_008_triphenylamine_oxidation_potential": (0.82, "V"),
    "property_calc_easy_009_thianthrene_oxidation_potential": (1.11, "V"),
    "property_calc_easy_010_water_dimer_binding_energy": (-4.97, "kcal/mol"),
    "property_calc_easy_011_ammonia_dimer_binding_energy": (-2.85, "kcal/mol"),
    "property_calc_easy_012_benzene_t_dimer_binding_energy": (-2.48, "kcal/mol"),
    "property_calc_easy_013_adenine_thymine_wc_pair_binding_energy": (-16.13, "kcal/mol"),
    "property_calc_easy_014_water_methanol_complex_binding_energy": (-4.89, "kcal/mol"),
    "property_calc_easy_015_ethene_ethyne_t_complex_binding_energy": (-1.33, "kcal/mol"),
    "property_calc_easy_016_thiophene_polarizability": (65.01, "a.u."),
    "property_calc_easy_017_benzene_polarizability": (67.87, "a.u."),
    "property_calc_easy_018_octatetraene_polarizability": (95.51, "a.u."),
    "property_calc_easy_019_dimethyl_sulfoxide_water_dipole_moment": (5.43, "Debye"),
    "property_calc_easy_020_cis_dichloroethene_dipole_moment": (1.88, "Debye"),
    "property_calc_easy_021_acetonitrile_dipole_moment": (3.85, "Debye"),
    "property_calc_easy_022_naphthalene_bridge_bond_order": (1.2522, "dimensionless"),
    "property_calc_easy_023_dimethyl_sulfone_so_bond_order": (1.6615, "dimensionless"),
    "property_calc_easy_024_methyl_nitrate_no_bond_order": (0.9292, "dimensionless"),
    "property_calc_easy_025_phenol_surface_esp_minimum": (-25.95, "kcal/mol"),
    "property_calc_easy_026_nitrobenzene_vdw_surface_area": (150.3, "angstrom^2"),
    "property_calc_easy_027_pyrrole_surface_esp_variance": (178.25, "(kcal/mol)^2"),
    "property_calc_easy_028_urea_crystal_density": (1.333, "g/cm^3"),
    "property_calc_easy_029_tnt_crystal_density": (1.71, "g/cm^3"),
    "property_calc_easy_030_picric_acid_crystal_density": (1.831, "g/cm^3"),
    "property_calc_easy_031_allyl_radical_c1_spin_density": (-0.266, "dimensionless"),
    "property_calc_easy_032_benzyl_radical_para_c_spin_density": (0.301, "dimensionless"),
    "property_calc_easy_033_phenoxy_radical_o_spin_density": (0.415, "dimensionless"),
    "property_calc_easy_034_indole_c3_fukui_minus": (0.076, "dimensionless"),
    "property_calc_easy_035_chloronitrobenzene_c_fukui_plus": (0.055, "dimensionless"),
    "property_calc_easy_036_furfural_carbonyl_c_fukui_plus": (0.07, "dimensionless"),
    "property_calc_easy_037_benzene_standard_entropy": (64.67, "cal/(mol*K)"),
    "property_calc_easy_038_acetonitrile_standard_entropy": (57.88, "cal/(mol*K)"),
    "property_calc_easy_039_neopentane_standard_entropy": (73.88, "cal/(mol*K)"),
    "property_calc_easy_040_methane_standard_entropy": (44.4, "cal/(mol*K)"),
    "property_calc_easy_041_ammonia_standard_entropy": (45.92, "cal/(mol*K)"),
    "property_calc_easy_042_carbon_dioxide_standard_entropy": (51.18, "cal/(mol*K)"),
    "property_calc_easy_043_acetic_acid_dimerization_enthalpy": (-16.04, "kcal/mol"),
    "property_calc_easy_044_caffeine_most_negative_mulliken_atom": ("11 O", None),
    "property_calc_easy_045_trifluoroacetic_acid_hydrogen_charge": (0.364, "e"),
    "property_calc_easy_046_methyl_azide_most_negative_mulliken_atom": ("3 N", None),
    "property_calc_easy_047_formaldehyde_s1_vertical_excitation_energy": (4.12, "eV"),
    "property_calc_easy_048_acetaldehyde_s1_vertical_excitation_energy": (4.42, "eV"),
    "property_calc_easy_049_acetone_s1_vertical_excitation_energy": (4.51, "eV"),
    "property_calc_easy_050_pyrazine_s1_vertical_excitation_energy": (4.04, "eV"),
    "property_calc_easy_051_formaldehyde_t1_vertical_excitation_energy": (3.39, "eV"),
}

ORIGINAL_PROPERTY_TASK_IDS = [
    "property_calc_001_free_energy",
    "property_calc_002_crystal_phase",
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
]

REFERENCE_PROFILE_TOLERANCES = {
    1: (-1.1, -0.7, 0.29, 0.13),
    2: (-5.6, -4.4, 0.19, 1.03),
    3: (-2.19, -0.99, 0.09, 1.13),
    4: (-3.05, -1.85, 1.08, 0.14),
    5: (-1.15, -1.15, 0.01, 0.1),
    6: (0.24, 0.24, 0.01, 0.04),
    7: (0.81, 0.81, 0.03, 0.01),
    8: (0.92, 0.92, 0.01, 0.11),
    9: (1.23, 1.23, 0.01, 0.13),
    10: (-5.02, -5.02, 0.06, 0.01),
    11: (-3.17, -3.17, 0.33, 0.01),
    12: (-2.77, -2.71, 0.3, 0.01),
    13: (-16.37, -16.37, 0.25, 0.01),
    14: (-5.12, -5.12, 0.24, 0.01),
    15: (-1.53, -1.53, 0.21, 0.01),
    20: (1.9, 1.9, 0.01, 0.03),
    21: (3.92, 3.92, 0.01, 0.08),
    25: (-26.15, -26.15, 0.21, 0.01),
    28: (1.32, 1.32, 0.014, 0.001),
    29: (1.654, 1.654, 0.066, 0.01),
    30: (1.763, 1.763, 0.069, 0.001),
    37: (64.34, 64.34, 0.34, 0.01),
    38: (58.19, 58.19, 0.01, 0.32),
    39: (73.2, 73.2, 0.69, 0.01),
    40: (44.52, 44.52, 0.1, 0.22),
    41: (45.97, 45.97, 0.01, 0.06),
    42: (51.07, 51.07, 0.12, 0.01),
    43: (-15.3, -15.3, 0.01, 0.75),
}


def load_pack(name: str = "property_calculation_easy"):
    return load_task_pack(
        package_resource(name, "tasks.yaml"),
        package_resource(name, "verifier_specs.yaml"),
    )


def test_easy_pack_has_frozen_ids_and_common_property_envelope() -> None:
    pack = load_pack()

    assert pack.pack_id == "property_calculation_easy"
    assert list(pack.tasks_by_id) == list(EXPECTED_GOLD)
    for number, task in enumerate(pack.tasks_by_id.values(), start=1):
        assert re.fullmatch(
            rf"property_calc_easy_{number:03d}_[a-z0-9_]+", task["task_id"]
        )
        assert task["version"] == 1
        assert task["task_type"] == "property_calculation"
        assert task["difficulty"] == "basic"
        assert task["formal_track"] is True
        assert task["answer_schema"] == {
            "format": "final_answer_line",
            "final_answer_prefix": "FINAL ANSWER:",
            "value_type": "json",
            "cardinality": "one",
        }
        assert task["gold_provenance"]["disclosure"] == "withheld_initial_release"
        assert task["gold_provenance"]["source"]
        assert task["scoring"] == {
            "aggregation": "arithmetic_mean",
            "comparison_groups": [
                {"id": task["requested_properties"][0]["name"], "mode": "all"}
            ],
            "version": "linear_goal_v2",
        }
        assert "parse_error" in set(task["failure_policy"].values())


def test_easy_pack_gold_is_frozen_and_samples_are_removed() -> None:
    pack = load_pack()
    assert not package_resource("property_calculation_easy", "sample_answers.jsonl").is_file()
    for task_id, (expected_value, expected_unit) in EXPECTED_GOLD.items():
        task = pack.tasks_by_id[task_id]
        gold = task["gold_answers"][0]
        assert gold["value"] == expected_value
        assert gold.get("unit") == expected_unit


def test_easy_profiles_without_references_keep_reported_precision() -> None:
    profiles = load_pack().scoring_profiles

    expected_tolerances = {
        "property_calculation_easy_wiberg_bond_order_numeric_gold_v2": 0.0001,
        "property_calculation_easy_fukui_function_numeric_gold_v2": 0.001,
        "property_calculation_easy_fukui_function_2dp_numeric_gold_v2": 0.01,
        "property_calculation_easy_vdw_surface_area_numeric_gold_v2": 0.1,
    }
    for profile_id, tolerance in expected_tolerances.items():
        profile = profiles[profile_id]
        assert profile["lower_tolerance"] == tolerance
        assert profile["upper_tolerance"] == tolerance
        assert profile["provenance"]["review_status"] == "approved"


def test_easy_reference_profiles_define_scoreable_asymmetric_ranges() -> None:
    pack = load_pack()
    tasks = list(pack.tasks_by_id.values())

    assert len(REFERENCE_PROFILE_TOLERANCES) == 28
    for number, (
        reference_lower,
        reference_upper,
        lower_tolerance,
        upper_tolerance,
    ) in REFERENCE_PROFILE_TOLERANCES.items():
        task = pack.tasks_by_id[tasks[number - 1]["task_id"]]
        profile_id = task["gold_answers"][0]["scoring_profile"]
        profile = pack.scoring_profiles[profile_id]
        assert profile_id.startswith(
            task["task_id"].replace(
                "property_calc_easy_", "property_calculation_easy_", 1
            )
        )
        assert profile["lower_tolerance"] == pytest.approx(lower_tolerance)
        assert profile["upper_tolerance"] == pytest.approx(upper_tolerance)
        assert profile["provenance"]["decay_source"] == (
            "expert_reference_value_range"
        )
        assert profile["provenance"]["reference_lower"] == reference_lower
        assert profile["provenance"]["reference_upper"] == reference_upper


def test_easy_reference_boundaries_receive_score_but_outer_boundaries_do_not() -> None:
    track = vgb.load_track("property_calculation_easy")
    pack = load_pack()
    tasks = track.tasks()

    for number, (reference_lower, reference_upper, _, _) in (
        REFERENCE_PROFILE_TOLERANCES.items()
    ):
        task = tasks[number - 1]
        scored_task = pack.tasks_by_id[task["task_id"]]
        gold = scored_task["gold_answers"][0]
        profile = pack.scoring_profiles[gold["scoring_profile"]]
        for reference in {reference_lower, reference_upper}:
            result = track.evaluate_one(
                {"task_id": task["task_id"], "answer": reference, "unit": gold["unit"]}
            )
            assert result["scores"]["score"] > 0.0

        for outer_boundary in (
            gold["value"] - profile["lower_tolerance"],
            gold["value"] + profile["upper_tolerance"],
        ):
            result = track.evaluate_one(
                {
                    "task_id": task["task_id"],
                    "answer": outer_boundary,
                    "unit": gold["unit"],
                }
            )
            assert result["scores"]["score"] == pytest.approx(0.0, abs=1e-12)


def test_easy_prompts_are_self_contained_and_exclude_source_commands() -> None:
    banned = (
        "/Users/",
        "XTB_EXE",
        "QCB_WORK",
        "solvation.py",
        "redox.py",
        "binding.py",
        "density.py",
        "excited.py",
        "attached",
        "upload",
        "verifier",
        "gold",
    )
    for task in load_pack().tasks_by_id.values():
        prompt = task["prompt"]
        assert prompt.isascii()
        assert all(fragment.lower() not in prompt.lower() for fragment in banned)
        for item in task["input_objects"]:
            assert item["presentation"] == "prompt_inline"
            assert prompt.count(item["value"]) == 1


def test_easy_atom_and_condition_contracts_are_explicit() -> None:
    tasks = load_pack().tasks_by_id

    assert "in water" in tasks[
        "property_calc_easy_019_dimethyl_sulfoxide_water_dipole_moment"
    ]["prompt"]
    assert "relative to SCE" in tasks[
        "property_calc_easy_005_nitrobenzene_reduction_potential"
    ]["prompt"]
    assert "zero-based atom indices 3 and 8" in tasks[
        "property_calc_easy_022_naphthalene_bridge_bond_order"
    ]["prompt"]
    assert "zero-based atom index 7" in tasks[
        "property_calc_easy_045_trifluoroacetic_acid_hydrogen_charge"
    ]["prompt"]
    for task_id in (
        "property_calc_easy_044_caffeine_most_negative_mulliken_atom",
        "property_calc_easy_046_methyl_azide_most_negative_mulliken_atom",
    ):
        assert "zero-based" in tasks[task_id]["prompt"]
        assert "index followed by the element symbol" in tasks[task_id]["prompt"]


def test_easy_prompts_preserve_gfn2_xtb_method_and_density_protocol() -> None:
    tasks = load_pack().tasks_by_id

    for task in tasks.values():
        if "GFN2" in task["capability_tags"]:
            assert "GFN2-xTB" in task["prompt"]

    for task_id in (
        "property_calc_easy_028_urea_crystal_density",
        "property_calc_easy_029_tnt_crystal_density",
        "property_calc_easy_030_picric_acid_crystal_density",
    ):
        prompt = tasks[task_id]["prompt"]
        assert "rho = M/V(0.001)" in prompt
        assert "0.001 a.u. electron-density isosurface" in prompt
        assert "B3LYP/6-31G**" in prompt
        assert "GFN2-xTB geometry optimization" in prompt
        assert "Do not apply a crystal packing factor" in prompt
        assert "only for molecular crystals" in prompt


def test_original_property_calculation_track_is_unchanged() -> None:
    assert list(load_pack("property_calculation").tasks_by_id) == ORIGINAL_PROPERTY_TASK_IDS


def test_easy_track_has_no_runtime_verifier_specs() -> None:
    assert load_pack().verifier_specs == ()
