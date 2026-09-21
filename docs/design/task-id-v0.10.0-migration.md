# v0.10.0 task ID migration

RDKit and xTB task IDs now use the track name and a three-digit original number.
Task order, task content, verifier IDs, and scoring profile IDs are unchanged.
Update the `task_id` field in existing answer records before scoring with v0.10.0.
Property Calculation task IDs are unchanged. Historical release and research records
retain the IDs used when they were produced.

| Previous ID | v0.10.0 ID |
| --- | --- |
| `rdkit_qed_max_001` | `rdkit_001` |
| `rdkit_sa_min_002` | `rdkit_002` |
| `rdkit_logp_window_003` | `rdkit_003` |
| `rdkit_tpsa_window_004` | `rdkit_004` |
| `rdkit_hba_window_005` | `rdkit_005` |
| `rdkit_hbd_window_006` | `rdkit_006` |
| `rdkit_fsp3_max_007` | `rdkit_007` |
| `rdkit_qed_sa_008` | `rdkit_008` |
| `rdkit_logp_tpsa_009` | `rdkit_009` |
| `rdkit_hba_hbd_010` | `rdkit_010` |
| `rdkit_logp_target_011` | `rdkit_011` |
| `rdkit_sa_logp_target_012` | `rdkit_012` |
| `rdkit_chain_end_to_end_max_013` | `rdkit_013` |
| `rdkit_caffeine_similarity_max_014` | `rdkit_014` |
| `xtb_gap_window_001` | `xtb_001` |
| `xtb_dipole_window_002` | `xtb_002` |
| `xtb_gap_max_003` | `xtb_003` |
| `xtb_gap_min_004` | `xtb_004` |
| `xtb_dipole_max_005` | `xtb_005` |
| `xtb_low_gap_high_dipole_opt_006` | `xtb_006` |
| `xtb_gap_dipole_window_007` | `xtb_007` |
| `xtb_lumo_min_008` | `xtb_008` |
| `xtb_polarizability_dipole_opt_009` | `xtb_009` |
| `xtb_solvation_selectivity_alpb_010` | `xtb_010` |
| `xtb_electrophilicity_max_011` | `xtb_011` |
| `xtb_fukui_carbon_site_012` | `xtb_012` |
| `xtb_hessian_thermo_stability_013` | `xtb_013` |
| `xtb_formula_dipole_min_014` | `xtb_014` |
| `xtb_two_fluorine_gap_min_015` | `xtb_015` |
| `xtb_c10_f2_gap_min_016` | `xtb_016` |
| `xtb_roy_singlepoint_energy_min_017` | `xtb_017` |
| `xtb_ritonavir_optimized_energy_min_018` | `xtb_018` |
| `xtb_odd_element_counts_gap_max_019` | `xtb_019` |
| `xtb_pyrene_substituent_energy_min_020` | `xtb_020` |
