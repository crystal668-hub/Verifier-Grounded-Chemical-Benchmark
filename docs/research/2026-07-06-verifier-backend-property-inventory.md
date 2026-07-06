# Verifier Backend Property Inventory

日期：2026-07-06

本文梳理当前已经实现的 verifier backend 中可计算或可预测的化学/材料性质。口径如下：

- “正式 track”指已在内置 registry 注册并通过任务包暴露的 track；当前为 `rdkit` 和 `xtb`。
- “prototype/未注册正式 track”指 backend、脚本入口或测试已经存在，但未纳入内置正式 track。
- “随结果返回/辅助约束”指 backend 会计算并写入 `properties`，可用于诊断、门控或在支持 `additional_property_names` 的 spec 中作为辅助约束。

## 汇总表

| Backend | 状态 | 输入 | 可计算/可预测的性质 | 备注 |
|---|---:|---|---|---|
| RDKit descriptors | 正式 track | SMILES | `qed`, `logp`, `tpsa`, `mw`, `hba`, `hbd`, `sa_score`, `fraction_csp3` | 已在 `rdkit_baseline` verifier specs 暴露。来源：`src/verifiers/backends/rdkit_descriptors.py` 与 `tasks/rdkit_baseline/verifier_specs.yaml`。 |
| RDKit descriptors | backend 支持，未正式暴露 | SMILES | `rotatable_bonds`, `ring_count` | `DESCRIPTOR_FUNCTIONS` 已支持，但当前没有对应正式 task/script spec。 |
| xTB local CLI | 正式 track | XYZ | `homo_lumo_gap`, `dipole_moment`, `relaxation_energy`, `lumo_energy`, `polarizability_per_heavy_atom`, `alpb_water_hexane_selectivity`, `global_electrophilicity`, `max_f_plus_on_carbon`, `entropy_298_per_heavy_atom` | 已在 `xtb_xyz` verifier specs 暴露。 |
| xTB local CLI | 随结果返回/辅助约束 | XYZ | `molecular_polarizability`, `gsolv_water_eV`, `gsolv_hexane_eV`, `f_plus_contrast`, `max_f_plus_atom_index`, `max_f_plus_atom_symbol`, `imaginary_frequency_count`, `entropy_298` | 部分属性已作为 `additional_property_names` 可约束，例如 `f_plus_contrast`、`imaginary_frequency_count`。 |
| xTB structural/domain | 辅助结构属性 | XYZ | `atom_count`, `heavy_atom_count`, `elements`, `formula`, `carbon_count`, `hetero_atom_count`, `heavy_element_diversity`, `max_absolute_coordinate` | 用于结构域检查，也会合并进结果 `properties`。 |
| RDKit forcefield | prototype，未注册正式 track | SMILES | `energy_range_kcal_mol`, `optimization_converged_fraction` | ETKDG conformer generation + MMFF94s/MMFF94/UFF minimization。 |
| RDKit forcefield | 随结果返回 | SMILES | `best_energy_kcal_mol`, `min_energy_kcal_mol`, `median_energy_kcal_mol`, `max_energy_kcal_mol`, `embedding_success_rate`, `min_nonbonded_distance_angstrom`, `conformer_count`, `forcefield_parameterized` | 更像构象/参数化质量与力场能量代理指标。 |
| ADMET-AI | 已实现 backend + 5 个脚本入口，未注册正式 track | SMILES | `Solubility_AqSolDB`, `hERG`, `AMES`, `BBB_Martins`, `Caco2_Wang` | backend 按 `property_name` 读取 ADMET-AI 输出；当前脚本入口实现这 5 个。 |
| OPERA | 已实现通用 backend，未注册正式 track | SMILES | 任意配置的 OPERA 数值 endpoint；当前测试覆盖 `WS` | 会同时读取 `AD_<property>` applicability-domain flag。 |
| MatGL | 已实现 backend，未注册正式 track | CIF | `formation_energy`, `bandgap` | `formation_energy` 单位 eV/atom；`bandgap` 单位 eV，支持 bandgap fidelity/state_attr。 |
| MatGL structure/domain | 辅助材料结构属性 | CIF | `reduced_formula`, `atom_count`, `volume`, `elements` | 从 pymatgen `Structure` 派生，用于材料结构域检查。 |
| OpenMM core | 已实现环境/固定体系 probe，未注册正式 track | 固定 fixture | `initial_energy_kj_mol`, `minimized_energy_kj_mol`, `energy_drop_kj_mol`, `final_max_force_kj_mol_nm` | 固定双粒子 harmonic bond smoke，不依赖候选分子。 |
| OpenMM + OpenFF | 已实现 ligand minimization backend，未注册正式 track | SMILES | `initial_energy_kj_mol`, `minimized_energy_kj_mol`, `energy_drop_kj_mol`, `final_max_force_kj_mol_nm` | OpenFF 分支会参数化候选 ligand 并最小化。 |
| OpenMM + OpenFF | 随结果返回 | SMILES | `parameterization_success`, `system_particle_count`, `charge_method`, `forcefield_family`, `forcefield_name`, `selected_platform` | GAFF 分支目前主要是可用性 smoke，不产生 ligand 能量指标。 |

## 正式暴露情况

当前内置 registry 只注册了两个正式 track：

- `rdkit`：RDKit baseline small-molecule descriptor tasks。
- `xtb`：xTB direct-XYZ small-molecule tasks。

其余 backend 已有实现或测试覆盖，但未进入内置正式 track；其中 `tasks/rdkit_forcefield/verifier_specs.yaml` 标记为 prototype，OpenMM backend 测试也明确不创建正式 task pack。

## 主要来源文件

- `src/verifiers/backends/rdkit_descriptors.py`
- `src/verifiers/backends/xtb_properties.py`
- `src/verifiers/backends/rdkit_forcefield.py`
- `src/verifiers/backends/admet_ai_properties.py`
- `src/verifiers/backends/opera_properties.py`
- `src/verifiers/backends/matgl_properties.py`
- `src/verifiers/backends/openmm_core_properties.py`
- `src/verifiers/backends/openmm_openff_properties.py`
- `src/verifiers/backends/openmm_runtime.py`
- `tasks/rdkit_baseline/verifier_specs.yaml`
- `tasks/xtb_xyz/verifier_specs.yaml`
- `tasks/rdkit_forcefield/verifier_specs.yaml`
