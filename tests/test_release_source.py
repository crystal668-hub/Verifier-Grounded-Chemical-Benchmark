from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

import verifier_grounded_benchmark as vgb
from scripts.release.build_release import _require_formal_inventory, task_inventory

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_TASK_IDS = {
    "open_generation_rdkit": [
        "rdkit_001_qed_max",
        "rdkit_002_sa_min",
        "rdkit_003_logp_window",
        "rdkit_004_tpsa_window",
        "rdkit_005_hba_window",
        "rdkit_006_hbd_window",
        "rdkit_007_fsp3_max",
        "rdkit_008_qed_sa",
        "rdkit_009_logp_tpsa",
        "rdkit_010_hba_hbd",
        "rdkit_011_logp_target",
        "rdkit_012_sa_logp_target",
        "rdkit_013_chain_end_to_end_max",
        "rdkit_014_caffeine_similarity_max",
    ],
    "open_generation_xtb": [
        "xtb_001_gap_window",
        "xtb_002_dipole_window",
        "xtb_003_gap_max",
        "xtb_004_gap_min",
        "xtb_005_dipole_max",
        "xtb_006_low_gap_high_dipole_opt",
        "xtb_007_gap_dipole_window",
        "xtb_008_lumo_min",
        "xtb_009_polarizability_dipole_opt",
        "xtb_010_solvation_selectivity_alpb",
        "xtb_011_electrophilicity_max",
        "xtb_012_fukui_carbon_site",
        "xtb_013_hessian_thermo_stability",
        "xtb_014_formula_dipole_min",
        "xtb_015_two_fluorine_gap_min",
        "xtb_016_c10_f2_gap_min",
        "xtb_017_roy_singlepoint_energy_min",
        "xtb_018_ritonavir_optimized_energy_min",
        "xtb_019_odd_element_counts_gap_max",
        "xtb_020_pyrene_substituent_energy_min",
    ],
    "property_calculation_advanced": [
        "property_calculation_advanced_001_free_energy",
        "property_calculation_advanced_002_crystal_phase",
        "property_calculation_advanced_003_hbond_count",
        "property_calculation_advanced_004_ir_top2_frequencies",
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
    ],
    "property_calculation_basic": [
        "property_calculation_basic_001_toluene_aqueous_solvation_free_energy",
        "property_calculation_basic_002_ethanol_aqueous_solvation_free_energy",
        "property_calculation_basic_003_diethyl_ether_aqueous_solvation_free_energy",
        "property_calculation_basic_004_anisole_aqueous_solvation_free_energy",
        "property_calculation_basic_005_nitrobenzene_reduction_potential",
        "property_calculation_basic_006_tetracyanoethylene_reduction_potential",
        "property_calculation_basic_007_dimethylaniline_oxidation_potential",
        "property_calculation_basic_008_triphenylamine_oxidation_potential",
        "property_calculation_basic_009_thianthrene_oxidation_potential",
        "property_calculation_basic_010_water_dimer_binding_energy",
        "property_calculation_basic_011_ammonia_dimer_binding_energy",
        "property_calculation_basic_012_benzene_t_dimer_binding_energy",
        "property_calculation_basic_013_adenine_thymine_wc_pair_binding_energy",
        "property_calculation_basic_014_water_methanol_complex_binding_energy",
        "property_calculation_basic_015_ethene_ethyne_t_complex_binding_energy",
        "property_calculation_basic_016_thiophene_polarizability",
        "property_calculation_basic_017_benzene_polarizability",
        "property_calculation_basic_018_octatetraene_polarizability",
        "property_calculation_basic_019_dimethyl_sulfoxide_water_dipole_moment",
        "property_calculation_basic_020_cis_dichloroethene_dipole_moment",
        "property_calculation_basic_021_acetonitrile_dipole_moment",
        "property_calculation_basic_022_naphthalene_bridge_bond_order",
        "property_calculation_basic_023_dimethyl_sulfone_so_bond_order",
        "property_calculation_basic_024_methyl_nitrate_no_bond_order",
        "property_calculation_basic_025_phenol_surface_esp_minimum",
        "property_calculation_basic_026_nitrobenzene_vdw_surface_area",
        "property_calculation_basic_027_pyrrole_surface_esp_variance",
        "property_calculation_basic_028_urea_crystal_density",
        "property_calculation_basic_029_tnt_crystal_density",
        "property_calculation_basic_030_picric_acid_crystal_density",
        "property_calculation_basic_031_allyl_radical_c1_spin_density",
        "property_calculation_basic_032_benzyl_radical_para_c_spin_density",
        "property_calculation_basic_033_phenoxy_radical_o_spin_density",
        "property_calculation_basic_034_indole_c3_fukui_minus",
        "property_calculation_basic_035_chloronitrobenzene_c_fukui_plus",
        "property_calculation_basic_036_furfural_carbonyl_c_fukui_plus",
        "property_calculation_basic_037_benzene_standard_entropy",
        "property_calculation_basic_038_acetonitrile_standard_entropy",
        "property_calculation_basic_039_neopentane_standard_entropy",
        "property_calculation_basic_040_methane_standard_entropy",
        "property_calculation_basic_041_ammonia_standard_entropy",
        "property_calculation_basic_042_carbon_dioxide_standard_entropy",
        "property_calculation_basic_043_acetic_acid_dimerization_enthalpy",
        "property_calculation_basic_044_caffeine_most_negative_mulliken_atom",
        "property_calculation_basic_045_trifluoroacetic_acid_hydrogen_charge",
        "property_calculation_basic_046_methyl_azide_most_negative_mulliken_atom",
        "property_calculation_basic_047_formaldehyde_s1_vertical_excitation_energy",
        "property_calculation_basic_048_acetaldehyde_s1_vertical_excitation_energy",
        "property_calculation_basic_049_acetone_s1_vertical_excitation_energy",
        "property_calculation_basic_050_pyrazine_s1_vertical_excitation_energy",
        "property_calculation_basic_051_formaldehyde_t1_vertical_excitation_energy",
    ],
}


def test_package_track_versions_and_inventory_are_release_aligned() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    version = project["project"]["version"]
    assert version == "0.10.0"

    inventory = task_inventory(version)
    assert inventory["schema_version"] == 2
    assert inventory["result_schema_version"] == "3"
    assert inventory["scoring_version"] == "linear_goal_v2"
    assert inventory["tracks"]["open_generation_xtb"]["scoring_status"] == "formal"
    assert all("family_policy" not in track for track in inventory["tracks"].values())
    assert inventory["scoring_profiles"]
    for track_name, expected_ids in EXPECTED_TASK_IDS.items():
        track = vgb.load_track(track_name)
        assert track.definition.version == version
        assert [task["task_id"] for task in track.tasks()] == expected_ids
        assert inventory["tracks"][track_name]["count"] == len(expected_ids)
        assert inventory["tracks"][track_name]["task_ids"] == expected_ids


def test_release_inventory_rejects_shadow_scoring_tracks() -> None:
    inventory = task_inventory("0.10.0")
    inventory["tracks"]["open_generation_xtb"]["scoring_status"] = "shadow_pending_research"

    with pytest.raises(RuntimeError, match="open_generation_xtb"):
        _require_formal_inventory(inventory)


def test_package_readme_uses_current_release_version() -> None:
    readme = (ROOT / "src" / "verifier_grounded_benchmark" / "README.md").read_text(
        encoding="utf-8"
    )
    assert "Verifier-Grounded Benchmark (v0.10.0)" in readme
    assert "verifier_grounded_benchmark-0.1.0" not in readme
