from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

import verifier_grounded_benchmark as vgb
from scripts.release.build_release import _require_formal_inventory, task_inventory

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_TASK_IDS = {
    "rdkit": [
        "rdkit_qed_max_001",
        "rdkit_sa_min_002",
        "rdkit_logp_window_003",
        "rdkit_tpsa_window_004",
        "rdkit_hba_window_005",
        "rdkit_hbd_window_006",
        "rdkit_fsp3_max_007",
        "rdkit_qed_sa_008",
        "rdkit_logp_tpsa_009",
        "rdkit_hba_hbd_010",
        "rdkit_logp_target_011",
        "rdkit_sa_logp_target_012",
        "rdkit_chain_end_to_end_max_013",
        "rdkit_caffeine_similarity_max_014",
    ],
    "xtb": [
        "xtb_gap_window_001",
        "xtb_dipole_window_002",
        "xtb_gap_max_003",
        "xtb_gap_min_004",
        "xtb_dipole_max_005",
        "xtb_low_gap_high_dipole_opt_006",
        "xtb_gap_dipole_window_007",
        "xtb_lumo_min_008",
        "xtb_polarizability_dipole_opt_009",
        "xtb_solvation_selectivity_alpb_010",
        "xtb_electrophilicity_max_011",
        "xtb_fukui_carbon_site_012",
        "xtb_hessian_thermo_stability_013",
        "xtb_formula_dipole_min_014",
        "xtb_two_fluorine_gap_min_015",
        "xtb_c10_f2_gap_min_016",
        "xtb_roy_singlepoint_energy_min_017",
        "xtb_ritonavir_optimized_energy_min_018",
        "xtb_odd_element_counts_gap_max_019",
        "xtb_pyrene_substituent_energy_min_020",
    ],
    "property_calculation_advanced": [
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
    ],
    "property_calculation_basic": [
        "property_calc_easy_001_toluene_aqueous_solvation_free_energy",
        "property_calc_easy_002_ethanol_aqueous_solvation_free_energy",
        "property_calc_easy_003_diethyl_ether_aqueous_solvation_free_energy",
        "property_calc_easy_004_anisole_aqueous_solvation_free_energy",
        "property_calc_easy_005_nitrobenzene_reduction_potential",
        "property_calc_easy_006_tetracyanoethylene_reduction_potential",
        "property_calc_easy_007_dimethylaniline_oxidation_potential",
        "property_calc_easy_008_triphenylamine_oxidation_potential",
        "property_calc_easy_009_thianthrene_oxidation_potential",
        "property_calc_easy_010_water_dimer_binding_energy",
        "property_calc_easy_011_ammonia_dimer_binding_energy",
        "property_calc_easy_012_benzene_t_dimer_binding_energy",
        "property_calc_easy_013_adenine_thymine_wc_pair_binding_energy",
        "property_calc_easy_014_water_methanol_complex_binding_energy",
        "property_calc_easy_015_ethene_ethyne_t_complex_binding_energy",
        "property_calc_easy_016_thiophene_polarizability",
        "property_calc_easy_017_benzene_polarizability",
        "property_calc_easy_018_octatetraene_polarizability",
        "property_calc_easy_019_dimethyl_sulfoxide_water_dipole_moment",
        "property_calc_easy_020_cis_dichloroethene_dipole_moment",
        "property_calc_easy_021_acetonitrile_dipole_moment",
        "property_calc_easy_022_naphthalene_bridge_bond_order",
        "property_calc_easy_023_dimethyl_sulfone_so_bond_order",
        "property_calc_easy_024_methyl_nitrate_no_bond_order",
        "property_calc_easy_025_phenol_surface_esp_minimum",
        "property_calc_easy_026_nitrobenzene_vdw_surface_area",
        "property_calc_easy_027_pyrrole_surface_esp_variance",
        "property_calc_easy_028_urea_crystal_density",
        "property_calc_easy_029_tnt_crystal_density",
        "property_calc_easy_030_picric_acid_crystal_density",
        "property_calc_easy_031_allyl_radical_c1_spin_density",
        "property_calc_easy_032_benzyl_radical_para_c_spin_density",
        "property_calc_easy_033_phenoxy_radical_o_spin_density",
        "property_calc_easy_034_indole_c3_fukui_minus",
        "property_calc_easy_035_chloronitrobenzene_c_fukui_plus",
        "property_calc_easy_036_furfural_carbonyl_c_fukui_plus",
        "property_calc_easy_037_benzene_standard_entropy",
        "property_calc_easy_038_acetonitrile_standard_entropy",
        "property_calc_easy_039_neopentane_standard_entropy",
        "property_calc_easy_040_methane_standard_entropy",
        "property_calc_easy_041_ammonia_standard_entropy",
        "property_calc_easy_042_carbon_dioxide_standard_entropy",
        "property_calc_easy_043_acetic_acid_dimerization_enthalpy",
        "property_calc_easy_044_caffeine_most_negative_mulliken_atom",
        "property_calc_easy_045_trifluoroacetic_acid_hydrogen_charge",
        "property_calc_easy_046_methyl_azide_most_negative_mulliken_atom",
        "property_calc_easy_047_formaldehyde_s1_vertical_excitation_energy",
        "property_calc_easy_048_acetaldehyde_s1_vertical_excitation_energy",
        "property_calc_easy_049_acetone_s1_vertical_excitation_energy",
        "property_calc_easy_050_pyrazine_s1_vertical_excitation_energy",
        "property_calc_easy_051_formaldehyde_t1_vertical_excitation_energy",
    ],
}


def test_package_track_versions_and_inventory_are_release_aligned() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    version = project["project"]["version"]
    assert version == "0.9.0"

    inventory = task_inventory(version)
    assert inventory["schema_version"] == 2
    assert inventory["result_schema_version"] == "2"
    assert inventory["scoring_version"] == "linear_goal_v2"
    assert inventory["tracks"]["xtb"]["scoring_status"] == "formal"
    assert inventory["scoring_profiles"]
    for track_name, expected_ids in EXPECTED_TASK_IDS.items():
        track = vgb.load_track(track_name)
        assert track.definition.version == version
        assert [task["task_id"] for task in track.tasks()] == expected_ids
        assert inventory["tracks"][track_name]["count"] == len(expected_ids)
        assert inventory["tracks"][track_name]["task_ids"] == expected_ids


def test_release_inventory_rejects_shadow_scoring_tracks() -> None:
    inventory = task_inventory("0.9.0")
    inventory["tracks"]["xtb"]["scoring_status"] = "shadow_pending_research"

    with pytest.raises(RuntimeError, match="xtb"):
        _require_formal_inventory(inventory)


def test_package_readme_uses_current_release_version() -> None:
    readme = (ROOT / "src" / "verifier_grounded_benchmark" / "README.md").read_text(
        encoding="utf-8"
    )
    assert "Verifier-Grounded Benchmark (v0.9)" in readme
    assert "verifier_grounded_benchmark-0.1.0" not in readme
