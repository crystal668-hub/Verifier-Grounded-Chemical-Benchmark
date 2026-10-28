# 2026-10-28 任务退役与连续编号

状态：按用户确认执行；未发布或替换历史 release。

## 退役范围

- property_calculation_advanced_004_ir_top2_frequencies
- rdkit_002_sa_min
- rdkit_005_hba_window
- rdkit_006_hbd_window
- rdkit_007_fsp3_max

## 正式题集

| Track | 题数 | 难度 |
| --- | ---: | --- |
| open_generation_rdkit | 10 | basic 6 / advanced 4 |
| open_generation_xtb | 20 | basic 13 / advanced 7 |
| property_calculation_basic | 51 | basic 51 |
| property_calculation_advanced | 19 | advanced 19 |

合计 100 题。保留任务的内容、gold、评分参数和相对顺序不变，仅更新 ID。

## 备份与共享资源

备份目录：task_backups/2026-10-28-five-tasks/，在 pyproject.toml 中明确排除出 wheel 和 sdist。
manifest.json 记录删除前源码提交、退役 ID、完整迁移映射和专属资源移除清单。
每个退役题保留原题面、评分、使用的 profile，以及适用的 verifier spec 和样例答案。
已移出运行时的 fraction Csp3 专属入口也保留源码备份。
SA、HBA、HBD verifier/profile 仍被保留题目复用，全部保留；只移除 fraction Csp3 专属配置和两个 IR 专属 profile。

## ID 迁移

旧答案必须按完整旧 ID 迁移；不要仅按数字编号匹配。退役 ID 不自动指向新任务。
历史发布物、历史研究数据及既有审核快照保持原状；新的正式清单按当前源码生成。

| 原完整 ID | 新完整 ID |
| --- | --- |
| rdkit_001_qed_max | rdkit_001_qed_max |
| rdkit_003_logp_window | rdkit_002_logp_window |
| rdkit_004_tpsa_window | rdkit_003_tpsa_window |
| rdkit_008_qed_sa | rdkit_004_qed_sa |
| rdkit_009_logp_tpsa | rdkit_005_logp_tpsa |
| rdkit_010_hba_hbd | rdkit_006_hba_hbd |
| rdkit_011_logp_target | rdkit_007_logp_target |
| rdkit_012_sa_logp_target | rdkit_008_sa_logp_target |
| rdkit_013_chain_end_to_end_max | rdkit_009_chain_end_to_end_max |
| rdkit_014_caffeine_similarity_max | rdkit_010_caffeine_similarity_max |
| property_calculation_advanced_001_free_energy | property_calculation_advanced_001_free_energy |
| property_calculation_advanced_002_crystal_phase | property_calculation_advanced_002_crystal_phase |
| property_calculation_advanced_003_hbond_count | property_calculation_advanced_003_hbond_count |
| property_calculation_advanced_005_crystal_density | property_calculation_advanced_004_crystal_density |
| property_calculation_advanced_006_cocrystal_ratio | property_calculation_advanced_005_cocrystal_ratio |
| property_calculation_advanced_007_polymorph_free_energy_crossover | property_calculation_advanced_006_polymorph_free_energy_crossover |
| property_calculation_advanced_008_interaction_binding_energy | property_calculation_advanced_007_interaction_binding_energy |
| property_calculation_advanced_009_homo_lumo_gap | property_calculation_advanced_008_homo_lumo_gap |
| property_calculation_advanced_010_hbond_distances | property_calculation_advanced_009_hbond_distances |
| property_calculation_advanced_011_accessible_pore_volume_ratio | property_calculation_advanced_010_accessible_pore_volume_ratio |
| property_calculation_advanced_012_carboxyl_hydrogen_distance | property_calculation_advanced_011_carboxyl_hydrogen_distance |
| property_calculation_advanced_013_halogen_bond_energy | property_calculation_advanced_012_halogen_bond_energy |
| property_calculation_advanced_014_bay069_pka | property_calculation_advanced_013_bay069_pka |
| property_calculation_advanced_015_formaldehyde_socme | property_calculation_advanced_014_formaldehyde_socme |
| property_calculation_advanced_016_anthracene_isc_rate | property_calculation_advanced_015_anthracene_isc_rate |
| property_calculation_advanced_017_biacetyl_phosphorescence_rate | property_calculation_advanced_016_biacetyl_phosphorescence_rate |
| property_calculation_advanced_018_anthracene_ht_contribution | property_calculation_advanced_017_anthracene_ht_contribution |
| property_calculation_advanced_019_acetophenone_isc_rate | property_calculation_advanced_018_acetophenone_isc_rate |
| property_calculation_advanced_020_azulene_internal_conversion_rate | property_calculation_advanced_019_azulene_internal_conversion_rate |
