# v0.10.0 track and task ID migration

The four canonical tracks are `open_generation_rdkit`, `open_generation_xtb`,
`property_calculation_basic`, and `property_calculation_advanced`.
RDKit and xTB's former track names `rdkit` and `xtb` are replaced by the two
`open_generation_*` names in the API, CLI, task-pack directories, and inventory.
Backend module names and executable names remain unchanged.

Task IDs use the backend name, original three-digit number, and original task
description. Task order, task content, verifier IDs, and scoring profile IDs are
unchanged. Update the track selection and `task_id` fields in existing answer
records before scoring with the revised v0.10.0. Property Calculation task IDs
are unchanged. Historical releases and research results retain their original IDs.

| v0.9.4 ID | Superseded short v0.10.0 ID | Revised v0.10.0 ID |
| --- | --- | --- |
| `rdkit_qed_max_001` | `rdkit_001` | `rdkit_001_qed_max` |
| `rdkit_sa_min_002` | `rdkit_002` | `rdkit_002_sa_min` |
| `rdkit_logp_window_003` | `rdkit_003` | `rdkit_003_logp_window` |
| `rdkit_tpsa_window_004` | `rdkit_004` | `rdkit_004_tpsa_window` |
| `rdkit_hba_window_005` | `rdkit_005` | `rdkit_005_hba_window` |
| `rdkit_hbd_window_006` | `rdkit_006` | `rdkit_006_hbd_window` |
| `rdkit_fsp3_max_007` | `rdkit_007` | `rdkit_007_fsp3_max` |
| `rdkit_qed_sa_008` | `rdkit_008` | `rdkit_008_qed_sa` |
| `rdkit_logp_tpsa_009` | `rdkit_009` | `rdkit_009_logp_tpsa` |
| `rdkit_hba_hbd_010` | `rdkit_010` | `rdkit_010_hba_hbd` |
| `rdkit_logp_target_011` | `rdkit_011` | `rdkit_011_logp_target` |
| `rdkit_sa_logp_target_012` | `rdkit_012` | `rdkit_012_sa_logp_target` |
| `rdkit_chain_end_to_end_max_013` | `rdkit_013` | `rdkit_013_chain_end_to_end_max` |
| `rdkit_caffeine_similarity_max_014` | `rdkit_014` | `rdkit_014_caffeine_similarity_max` |
| `xtb_gap_window_001` | `xtb_001` | `xtb_001_gap_window` |
| `xtb_dipole_window_002` | `xtb_002` | `xtb_002_dipole_window` |
| `xtb_gap_max_003` | `xtb_003` | `xtb_003_gap_max` |
| `xtb_gap_min_004` | `xtb_004` | `xtb_004_gap_min` |
| `xtb_dipole_max_005` | `xtb_005` | `xtb_005_dipole_max` |
| `xtb_low_gap_high_dipole_opt_006` | `xtb_006` | `xtb_006_low_gap_high_dipole_opt` |
| `xtb_gap_dipole_window_007` | `xtb_007` | `xtb_007_gap_dipole_window` |
| `xtb_lumo_min_008` | `xtb_008` | `xtb_008_lumo_min` |
| `xtb_polarizability_dipole_opt_009` | `xtb_009` | `xtb_009_polarizability_dipole_opt` |
| `xtb_solvation_selectivity_alpb_010` | `xtb_010` | `xtb_010_solvation_selectivity_alpb` |
| `xtb_electrophilicity_max_011` | `xtb_011` | `xtb_011_electrophilicity_max` |
| `xtb_fukui_carbon_site_012` | `xtb_012` | `xtb_012_fukui_carbon_site` |
| `xtb_hessian_thermo_stability_013` | `xtb_013` | `xtb_013_hessian_thermo_stability` |
| `xtb_formula_dipole_min_014` | `xtb_014` | `xtb_014_formula_dipole_min` |
| `xtb_two_fluorine_gap_min_015` | `xtb_015` | `xtb_015_two_fluorine_gap_min` |
| `xtb_c10_f2_gap_min_016` | `xtb_016` | `xtb_016_c10_f2_gap_min` |
| `xtb_roy_singlepoint_energy_min_017` | `xtb_017` | `xtb_017_roy_singlepoint_energy_min` |
| `xtb_ritonavir_optimized_energy_min_018` | `xtb_018` | `xtb_018_ritonavir_optimized_energy_min` |
| `xtb_odd_element_counts_gap_max_019` | `xtb_019` | `xtb_019_odd_element_counts_gap_max` |
| `xtb_pyrene_substituent_energy_min_020` | `xtb_020` | `xtb_020_pyrene_substituent_energy_min` |
