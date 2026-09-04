from __future__ import annotations

import re

import pytest

import verifier_grounded_benchmark as vgb
from verifier_grounded_benchmark.task.loader import load_task_pack
from verifier_grounded_benchmark.task.resources import package_resource

EXPECTED_GOLD = {
    "property_calculation_basic_001_toluene_aqueous_solvation_free_energy": (-0.82, "kcal/mol"),
    "property_calculation_basic_002_ethanol_aqueous_solvation_free_energy": (-5.42, "kcal/mol"),
    "property_calculation_basic_003_diethyl_ether_aqueous_solvation_free_energy": (-2.11, "kcal/mol"),
    "property_calculation_basic_004_anisole_aqueous_solvation_free_energy": (-1.98, "kcal/mol"),
    "property_calculation_basic_005_nitrobenzene_reduction_potential": (-1.24, "V"),
    "property_calculation_basic_006_tetracyanoethylene_reduction_potential": (0.21, "V"),
    "property_calculation_basic_007_dimethylaniline_oxidation_potential": (0.83, "V"),
    "property_calculation_basic_008_triphenylamine_oxidation_potential": (0.82, "V"),
    "property_calculation_basic_009_thianthrene_oxidation_potential": (1.11, "V"),
    "property_calculation_basic_010_water_dimer_binding_energy": (-4.97, "kcal/mol"),
    "property_calculation_basic_011_ammonia_dimer_binding_energy": (-2.85, "kcal/mol"),
    "property_calculation_basic_012_benzene_t_dimer_binding_energy": (-2.48, "kcal/mol"),
    "property_calculation_basic_013_adenine_thymine_wc_pair_binding_energy": (-16.13, "kcal/mol"),
    "property_calculation_basic_014_water_methanol_complex_binding_energy": (-4.89, "kcal/mol"),
    "property_calculation_basic_015_ethene_ethyne_t_complex_binding_energy": (-1.33, "kcal/mol"),
    "property_calculation_basic_016_thiophene_polarizability": (65.01, "a.u."),
    "property_calculation_basic_017_benzene_polarizability": (67.87, "a.u."),
    "property_calculation_basic_018_octatetraene_polarizability": (95.51, "a.u."),
    "property_calculation_basic_019_dimethyl_sulfoxide_water_dipole_moment": (5.43, "Debye"),
    "property_calculation_basic_020_cis_dichloroethene_dipole_moment": (1.88, "Debye"),
    "property_calculation_basic_021_acetonitrile_dipole_moment": (3.85, "Debye"),
    "property_calculation_basic_022_naphthalene_bridge_bond_order": (1.2522, "dimensionless"),
    "property_calculation_basic_023_dimethyl_sulfone_so_bond_order": (1.6615, "dimensionless"),
    "property_calculation_basic_024_methyl_nitrate_no_bond_order": (0.9292, "dimensionless"),
    "property_calculation_basic_025_phenol_surface_esp_minimum": (-25.95, "kcal/mol"),
    "property_calculation_basic_026_nitrobenzene_vdw_surface_area": (150.3, "angstrom^2"),
    "property_calculation_basic_027_pyrrole_surface_esp_variance": (178.25, "(kcal/mol)^2"),
    "property_calculation_basic_028_urea_crystal_density": (1.333, "g/cm^3"),
    "property_calculation_basic_029_tnt_crystal_density": (1.71, "g/cm^3"),
    "property_calculation_basic_030_picric_acid_crystal_density": (1.831, "g/cm^3"),
    "property_calculation_basic_031_allyl_radical_c1_spin_density": (-0.266, "dimensionless"),
    "property_calculation_basic_032_benzyl_radical_para_c_spin_density": (0.301, "dimensionless"),
    "property_calculation_basic_033_phenoxy_radical_o_spin_density": (0.415, "dimensionless"),
    "property_calculation_basic_034_indole_c3_fukui_minus": (0.076, "dimensionless"),
    "property_calculation_basic_035_chloronitrobenzene_c_fukui_plus": (0.055, "dimensionless"),
    "property_calculation_basic_036_furfural_carbonyl_c_fukui_plus": (0.07, "dimensionless"),
    "property_calculation_basic_037_benzene_standard_entropy": (64.67, "cal/(mol*K)"),
    "property_calculation_basic_038_acetonitrile_standard_entropy": (57.88, "cal/(mol*K)"),
    "property_calculation_basic_039_neopentane_standard_entropy": (73.88, "cal/(mol*K)"),
    "property_calculation_basic_040_methane_standard_entropy": (44.4, "cal/(mol*K)"),
    "property_calculation_basic_041_ammonia_standard_entropy": (45.92, "cal/(mol*K)"),
    "property_calculation_basic_042_carbon_dioxide_standard_entropy": (51.18, "cal/(mol*K)"),
    "property_calculation_basic_043_acetic_acid_dimerization_enthalpy": (-16.04, "kcal/mol"),
    "property_calculation_basic_044_caffeine_most_negative_mulliken_atom": ("11 O", None),
    "property_calculation_basic_045_trifluoroacetic_acid_hydrogen_charge": (0.364, "e"),
    "property_calculation_basic_046_methyl_azide_most_negative_mulliken_atom": ("3 N", None),
    "property_calculation_basic_047_formaldehyde_s1_vertical_excitation_energy": (4.12, "eV"),
    "property_calculation_basic_048_acetaldehyde_s1_vertical_excitation_energy": (4.42, "eV"),
    "property_calculation_basic_049_acetone_s1_vertical_excitation_energy": (4.51, "eV"),
    "property_calculation_basic_050_pyrazine_s1_vertical_excitation_energy": (4.04, "eV"),
    "property_calculation_basic_051_formaldehyde_t1_vertical_excitation_energy": (3.39, "eV"),
}

ORIGINAL_PROPERTY_TASK_IDS = [
    "property_calculation_advanced_001_free_energy",
    "property_calculation_advanced_002_crystal_phase",
    "property_calculation_advanced_003_hbond_count",
    "property_calculation_advanced_004_ir_top3_frequencies",
    "property_calculation_advanced_005_crystal_density",
    "property_calculation_advanced_006_cocrystal_ratio",
    "property_calculation_advanced_007_polymorph_free_energy_crossover",
    "property_calculation_advanced_008_interaction_binding_energy",
    "property_calculation_advanced_009_homo_lumo_gap",
    "property_calculation_advanced_010_hbond_distances",
    "property_calculation_advanced_011_accessible_pore_volume_ratio",
    "property_calculation_advanced_012_carboxyl_hydrogen_distance",
    "property_calculation_advanced_013_halogen_bond_energy",
    "property_calculation_advanced_014_bay069_pka",
    "property_calculation_advanced_015_formaldehyde_socme",
    "property_calculation_advanced_016_anthracene_isc_rate",
    "property_calculation_advanced_017_biacetyl_phosphorescence_rate",
    "property_calculation_advanced_018_anthracene_ht_contribution",
    "property_calculation_advanced_019_acetophenone_isc_rate",
    "property_calculation_advanced_020_azulene_internal_conversion_rate",
]

ABSOLUTE_WIDTHS = {
    **dict.fromkeys((*range(1, 5), *range(10, 16), 43), 3.0),
    **dict.fromkeys(range(5, 10), 0.6),
    **dict.fromkeys(range(47, 52), 1.0),
}

RELATIVE_WIDTHS = {
    **dict.fromkeys(range(16, 19), 0.25),
    **dict.fromkeys(range(19, 22), 0.35),
    **dict.fromkeys(range(22, 25), 0.20),
    25: 0.40,
    26: 0.20,
    27: 0.35,
    **dict.fromkeys(range(28, 31), 0.20),
    **dict.fromkeys(range(31, 34), 0.80),
    **dict.fromkeys(range(34, 37), 1.00),
    **dict.fromkeys(range(37, 43), 0.12),
    45: 0.75,
}


def load_pack(name: str = "property_calculation_basic"):
    return load_task_pack(
        package_resource(name, "tasks.yaml"),
        package_resource(name, "verifier_specs.yaml"),
    )


def test_easy_pack_has_frozen_ids_and_common_property_envelope() -> None:
    pack = load_pack()

    assert pack.pack_id == "property_calculation_basic"
    assert list(pack.tasks_by_id) == list(EXPECTED_GOLD)
    for number, task in enumerate(pack.tasks_by_id.values(), start=1):
        assert re.fullmatch(
            rf"property_calculation_basic_{number:03d}_[a-z0-9_]+", task["task_id"]
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
    assert not package_resource("property_calculation_basic", "sample_answers.jsonl").is_file()
    for task_id, (expected_value, expected_unit) in EXPECTED_GOLD.items():
        task = pack.tasks_by_id[task_id]
        gold = task["gold_answers"][0]
        assert gold["value"] == expected_value
        assert gold.get("unit") == expected_unit


def test_easy_numeric_profiles_use_reviewed_symmetric_widths() -> None:
    pack = load_pack()
    assert len(ABSOLUTE_WIDTHS) == 21
    assert len(RELATIVE_WIDTHS) == 28

    for number, task in enumerate(pack.tasks_by_id.values(), start=1):
        if number in {44, 46}:
            continue
        profile_id = task["gold_answers"][0]["scoring_profile"]
        profile = pack.scoring_profiles[profile_id]
        gold = float(task["gold_answers"][0]["value"])
        if number in ABSOLUTE_WIDTHS:
            mode, parameter, width = "absolute", ABSOLUTE_WIDTHS[number], ABSOLUTE_WIDTHS[number]
        else:
            mode, parameter = "relative", RELATIVE_WIDTHS[number]
            width = abs(gold) * parameter
        assert profile["lower_tolerance"] == pytest.approx(width)
        assert profile["upper_tolerance"] == pytest.approx(width)
        assert profile["error_mode"] == mode
        assert profile["error_parameter"] == parameter
        assert profile["provenance"]["decay_source"] == "attachment_final_scoring_standard"


def test_easy_numeric_profiles_score_gold_midpoints_and_boundaries() -> None:
    track = vgb.load_track("property_calculation_basic")
    pack = load_pack()
    for number, task in enumerate(track.tasks(), start=1):
        if number in {44, 46}:
            continue
        gold = pack.tasks_by_id[task["task_id"]]["gold_answers"][0]
        profile = pack.scoring_profiles[gold["scoring_profile"]]
        width = profile["lower_tolerance"]
        for offset, expected in ((0.0, 1.0), (-width / 2, 0.5), (width / 2, 0.5), (-width, 0.0), (width, 0.0)):
            result = track.evaluate_one(
                {
                    "task_id": task["task_id"],
                    "answer": gold["value"] + offset,
                    "unit": gold["unit"],
                }
            )
            assert result["scores"]["score"] == pytest.approx(expected, abs=1e-12)


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
        "property_calculation_basic_019_dimethyl_sulfoxide_water_dipole_moment"
    ]["prompt"]
    assert "relative to SCE" in tasks[
        "property_calculation_basic_005_nitrobenzene_reduction_potential"
    ]["prompt"]
    assert "bridgehead C-C bond" in tasks[
        "property_calculation_basic_022_naphthalene_bridge_bond_order"
    ]["prompt"]
    assert "carboxylic hydrogen atom" in tasks[
        "property_calculation_basic_045_trifluoroacetic_acid_hydrogen_charge"
    ]["prompt"]
    for task_id in (
        "property_calculation_basic_022_naphthalene_bridge_bond_order",
        "property_calculation_basic_023_dimethyl_sulfone_so_bond_order",
        "property_calculation_basic_024_methyl_nitrate_no_bond_order",
        "property_calculation_basic_031_allyl_radical_c1_spin_density",
        "property_calculation_basic_032_benzyl_radical_para_c_spin_density",
        "property_calculation_basic_033_phenoxy_radical_o_spin_density",
        "property_calculation_basic_034_indole_c3_fukui_minus",
        "property_calculation_basic_035_chloronitrobenzene_c_fukui_plus",
        "property_calculation_basic_036_furfural_carbonyl_c_fukui_plus",
        "property_calculation_basic_045_trifluoroacetic_acid_hydrogen_charge",
    ):
        assert "zero-based atom index" not in tasks[task_id]["prompt"]
    for task_id in (
        "property_calculation_basic_044_caffeine_most_negative_mulliken_atom",
        "property_calculation_basic_046_methyl_azide_most_negative_mulliken_atom",
    ):
        assert "zero-based" in tasks[task_id]["prompt"]
        assert "index followed by the element symbol" in tasks[task_id]["prompt"]


def test_easy_prompts_preserve_gfn2_xtb_method_and_density_protocol() -> None:
    tasks = load_pack().tasks_by_id

    for task in tasks.values():
        if "GFN2" in task["capability_tags"]:
            assert "GFN2-xTB" in task["prompt"]

    for task_id in (
        "property_calculation_basic_028_urea_crystal_density",
        "property_calculation_basic_029_tnt_crystal_density",
        "property_calculation_basic_030_picric_acid_crystal_density",
    ):
        prompt = tasks[task_id]["prompt"]
        assert "rho = M/V(0.001)" in prompt
        assert "0.001 a.u. electron-density isosurface" in prompt
        assert "B3LYP/6-31G**" in prompt
        assert "GFN2-xTB geometry optimization" in prompt
        assert "Do not apply a crystal packing factor" in prompt
        assert "only for molecular crystals" in prompt


def test_original_property_calculation_track_is_unchanged() -> None:
    assert list(load_pack("property_calculation_advanced").tasks_by_id) == ORIGINAL_PROPERTY_TASK_IDS


def test_easy_track_has_no_runtime_verifier_specs() -> None:
    assert load_pack().verifier_specs == ()
