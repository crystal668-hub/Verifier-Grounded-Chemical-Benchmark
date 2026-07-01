# RDKit ETKDG + MMFF/UFF baseline 可扩展性质调研

日期：2026-07-01

## 1. 结论摘要

当前 `rdkit_forcefield` backend 已经完成 P0 的最小闭环：单组分 SMILES 经 RDKit ETKDGv3 生成多构象，再按 `MMFF94s -> MMFF94 -> UFF` 优先级做局部优化，并输出构象能量分布、嵌入成功率、优化收敛率和最短非键合距离。

继续沿用这个组合，不新增 OpenMM/OpenFF/GAFF 依赖时，最值得扩展的性质不是“真实热力学能量”，而是三类轻量 verifier 信号：

1. 构象 ensemble 统计：低能构象数、Boltzmann 权重 proxy、RMSD/TFD 多样性、能量分位数。
2. 3D 几何和形状描述符：PMI/NPR、radius of gyration、asphericity、PBF、molecular volume、Labute ASA。
3. 几何质量/strain gate：优化前后 energy drop、力/梯度范数、clash count、扭转角/键长 sanity、提交 3D 构象相对生成 ensemble 的 strain proxy。

不建议把 RDKit MMFF/UFF baseline 扩展成跨分子的绝对稳定性、结合能、溶剂化自由能、反应能垒、MD 动力学或相变性质 verifier。这些需要更明确的物理模型、参数化链和采样方案，应留给 xTB、OpenMM 或专门材料/反应 backend。

## 2. 当前实现核对

当前 backend：`verifiers/backends/rdkit_forcefield.py`

输入和流程：

- 输入：单组分 SMILES。
- 预处理：RDKit sanitize，`Chem.AddHs`。
- 3D 构象：`AllChem.ETKDGv3()`，固定 `random_seed` 与 `prune_rms_thresh`。
- 构象数：默认请求 20 个。
- 力场：优先 `MMFF94s`，其次 `MMFF94`，最后 `UFF`。
- 优化：每个 retained conformer 调用 RDKit force-field minimization，默认 `max_iters=200`。

已经输出的性质：

| property | 当前含义 | 可继续保留的用途 |
|---|---|---|
| `forcefield_name` | 实际使用的 MMFF/UFF variant | provenance 和任务解释 |
| `forcefield_parameterized` | 力场参数覆盖成功时为 1 | domain gate |
| `conformer_count` | ETKDG retained conformer 数 | 构象生成覆盖度 |
| `requested_conformer_count` | 请求构象数 | provenance |
| `embedding_success_rate` | retained / requested | 3D realizability gate |
| `optimization_converged_fraction` | minimization 返回收敛的比例 | geometry quality gate |
| `best_energy_kcal_mol` / `min_energy_kcal_mol` | ensemble 中最低优化后 force-field energy | 同一 workflow 内的相对描述符 |
| `median_energy_kcal_mol` | 优化后能量中位数 | ensemble 统计 |
| `max_energy_kcal_mol` | 优化后最高能量 | ensemble 统计 |
| `energy_range_kcal_mol` | 最高 - 最低优化后能量 | flexibility/strain proxy |
| `min_nonbonded_distance_angstrom` | 第一个 conformer 的最短非键合距离 | clash 辅助指标 |

当前限制：

- `min_nonbonded_distance_angstrom` 只看第一个 conformer，不一定是最低能 conformer。
- 只保留 summary statistics，没有保留每个 conformer 的能量、收敛状态、RMSD 或形状描述符。
- 只接受 SMILES，不接受用户提交的 SDF/mol block/XYZ，因此无法直接验证“候选 3D 构象”的 strain 或 geometry quality。

## 3. 方法依据

RDKit ETKDG、MMFF/UFF 和 3D descriptors 是这个 baseline 的核心依据：

- RDKit `rdDistGeom` 提供 `EmbedMultipleConfs`、ETKDG/ETKDGv2/ETKDGv3 等 3D distance-geometry 构象生成入口。ETKDG 系列来自 Riniker 和 Landrum 的 knowledge-based distance geometry conformer generation 方法。
- RDKit `rdForceFieldHelpers` 提供 `MMFFHasAllMoleculeParams`、`MMFFGetMoleculeForceField`、`MMFFOptimizeMolecule`、`UFFHasAllMoleculeParams`、`UFFGetMoleculeForceField`、`UFFOptimizeMolecule` 等 API。MMFF94 是 Halgren 的 Merck molecular force field；UFF 是 Rappe、Casewit、Colwell、Goddard 和 Skiff 提出的全周期表通用力场。
- RDKit `Descriptors3D` 和 `rdMolDescriptors` 提供 PMI/NPR、radius of gyration、asphericity、eccentricity、spherocity、PBF、MORSE、RDF、WHIM、GETAWAY、Labute ASA 等 3D/准 3D 描述符。
- RDKit `ChemicalFeatures`/`rdMolChemicalFeatures` 可基于 feature definition 识别 donor、acceptor、aromatic、hydrophobe、charged 等 pharmacophore feature，并可在 conformer 上取 3D feature positions。
- RDKit `TorsionFingerprints` 可计算 conformer 之间的 torsion fingerprint deviation，用于补充 RMSD 无法表达的扭转构象差异。

## 4. 可直接扩展的性质候选

这些性质只需要当前 RDKit 依赖和当前 SMILES -> ETKDG -> MMFF/UFF workflow，适合 P0 后续小步添加。

### 4.1 构象 ensemble 能量统计

| 候选 property | 计算方式 | verifier 用途 | 风险 |
|---|---|---|---|
| `energy_p10_kcal_mol` / `energy_p90_kcal_mol` | retained conformer 优化后能量分位数 | 比 min/max 更稳健的 energy spread | 构象数少时分位数噪声大 |
| `energy_iqr_kcal_mol` | P75 - P25 | flexibility proxy | 仍依赖 ETKDG retained set |
| `low_energy_conformer_count_1kcal` | `energy <= min + 1` 的 conformer 数 | 判断低能盆数量 | duplicate conformers 会影响计数 |
| `low_energy_conformer_fraction_3kcal` | `energy <= min + 3` 的比例 | 构象可及性 proxy | 不是真实热力学 population |
| `boltzmann_weight_top1_298k_proxy` | 用相对 MMFF/UFF energy 在 298 K 下归一化 | 低能构象集中度 proxy | 不应叫真实平衡分布 |
| `effective_conformer_count_298k_proxy` | `1 / sum(weight^2)` | ensemble degeneracy proxy | 受构象采样和去重影响 |

推荐优先级：高。

原因：当前 backend 已经有每个 conformer 的 energy list，只是没有输出更丰富的 summary。实现成本低，能直接支撑“柔性/刚性/低能构象多样性”类任务。

命名建议：所有 Boltzmann 相关字段加 `proxy` 或在文档中明确为 fixed-workflow surrogate，避免被解释成实验构象分布。

### 4.2 构象几何多样性

| 候选 property | 计算方式 | verifier 用途 | 风险 |
|---|---|---|---|
| `conformer_rmsd_median_angstrom` | 优化后 conformers 两两 heavy-atom RMSD 的中位数 | 3D shape diversity | 对对称分子和 alignment 设置敏感 |
| `conformer_rmsd_max_angstrom` | 两两 RMSD 最大值 | 构象覆盖度 | outlier 敏感 |
| `low_energy_rmsd_median_angstrom` | 只在 `min + 3 kcal/mol` 内计算 RMSD | 低能构象多样性 | 低能 conformer 数太少时不可用 |
| `tfd_median` | RDKit TorsionFingerprints 的 TFD matrix 中位数 | 扭转构象多样性 | 对刚性/少扭转分子信息少 |
| `tfd_max` | TFD 最大值 | 扭转覆盖度 | outlier 敏感 |

推荐优先级：高。

原因：RMSD/TFD 是 conformer ensemble verifier 的自然补充。它能把“能量范围大”拆成两种情况：真构象多样性，或几何异常导致的高能 outlier。

实现注意：

- RMSD 统计建议默认只看 heavy atoms，避免氢原子方向主导结果。
- 对 `conformer_count < 2` 的分子返回 `0.0` 或显式 `null` 需要与 result schema 约定；当前 property schema 更偏数值，首批可返回 `0.0` 并记录 `conformer_pair_count`。
- TFD 更适合柔性有机分子，不能替代 RMSD。

### 4.3 3D 形状和尺寸描述符

| 候选 property | RDKit API / 计算方式 | verifier 用途 | 风险 |
|---|---|---|---|
| `radius_of_gyration_angstrom` | `Descriptors3D.RadiusOfGyration` 或 `rdMolDescriptors.CalcRadiusOfGyration` | 分子紧凑程度 | conformer 依赖 |
| `pmi1` / `pmi2` / `pmi3` | principal moments of inertia | 形状和尺寸 | 与原子质量/坐标有关 |
| `npr1` / `npr2` | normalized principal moments | rod/disk/sphere 形状分类 | 小分子边界值需校准 |
| `asphericity` | RDKit 3D descriptor | 球形偏离程度 | 单一 conformer 代表性 |
| `eccentricity` | RDKit 3D descriptor | elongated shape proxy | 同上 |
| `spherocity_index` | RDKit 3D descriptor | 球形程度 | 同上 |
| `pbf` | plane of best fit descriptor | 平面性/三维性 | aromatic 平面分子会集中在低值 |
| `mol_volume_angstrom3` | `AllChem.ComputeMolVolume` | 体积/packing proxy | grid spacing 会影响速度和数值 |
| `labute_asa_angstrom2` | `rdMolDescriptors.CalcLabuteASA` | 近似表面积 | 原子半径模型近似 |

推荐优先级：高到中。

最稳健的首批组合：

- `radius_of_gyration_angstrom`
- `npr1`
- `npr2`
- `pbf`
- `asphericity`
- `mol_volume_angstrom3`

这些性质适合做“分子 3D shape envelope”或“compact/non-planar molecule”任务，也可作为 RDKit 2D descriptor track 的 3D 补充。

实现注意：

- 默认应在最低能 conformer 上计算，并输出 `shape_conformer_rank=0` 或类似 provenance。
- 如果后续做 ensemble shape，可输出 `radius_of_gyration_min/median/max`、`pbf_min/median/max`，但首批不要一次性扩太多字段。
- `MORSE`、`RDF`、`WHIM`、`GETAWAY` 维度较高，不适合一开始直接暴露为任务 property；可在后续 ML 特征研究中使用。

### 4.4 几何质量和 clash 指标

| 候选 property | 计算方式 | verifier 用途 | 风险 |
|---|---|---|---|
| `min_nonbonded_distance_best_angstrom` | 最低能 conformer 的最短非键合距离 | 替代当前 first conformer clash 指标 | 仍是粗略 gate |
| `nonbonded_clash_count` | 非键合距离低于元素半径阈值的 pair 数 | 结构质量 gate | 阈值需要校准 |
| `min_heavy_atom_distance_angstrom` | heavy atom pair 最短距离 | 原子重叠 gate | 需排除键合/1-3 pair |
| `max_gradient_norm` | force field `CalcGrad()` 后按原子聚合 | 优化后残余力 proxy | RDKit force unit/provenance 需写清 |
| `mean_gradient_norm` | 梯度范数平均值 | convergence 质量补充 | 同上 |
| `optimization_failure_count` | minimization 非 0 返回码数量 | 当前收敛率的 count 版本 | 已可由 fraction 推出 |
| `embedding_failure_count` | requested - retained | 当前嵌入率的 count 版本 | 已可由 rate 推出 |

推荐优先级：中到高。

原因：它们更像 verifier 的 quality gate，而不是目标优化性质。对于防止模型提交不可嵌入、严重重叠、局部优化失败的分子很有价值。

实现注意：

- 当前 `min_nonbonded_distance_angstrom` 应优先迁移为最低能 conformer 上的指标，或新增字段避免改变现有语义。
- clash count 要定义 pair 排除规则：至少排除 1-2 键合 pair，建议也考虑排除 1-3 pair 或使用缩放阈值。
- `CalcGrad()` 返回的是扁平梯度数组，可转换成每原子三维向量范数；字段名不要写成严格物理力，建议叫 `gradient_norm`。

### 4.5 3D pharmacophore 和相互作用 proxy

| 候选 property | 计算方式 | verifier 用途 | 风险 |
|---|---|---|---|
| `pharmacophore_feature_count` | RDKit BaseFeatures feature factory | 3D feature richness | 与 2D 功能团计数相关 |
| `hbd_hba_min_distance_angstrom` | donor/acceptor feature positions 的最短距离 | intramolecular interaction proxy | feature 定义影响大 |
| `aromatic_centroid_distance_max_angstrom` | aromatic features/ ring centroids 距离 | shape/pharmacophore span | 多芳环分子更有意义 |
| `charged_feature_distance_min_angstrom` | positive/negative ionizable features 距离 | salt bridge/zwitterion proxy | 当前 formal charge domain 较窄 |
| `pharmacophore_span_angstrom` | selected features pairwise max distance | 3D pharmacophore envelope | 对 feature 少的分子不可用 |

推荐优先级：中。

原因：这些性质能让 RDKit forcefield backend 从“构象能量”扩到“3D pharmacophore geometry”。它们仍然很轻量，但任务设计需要更谨慎，避免把简单功能团计数伪装成高精度生物活性预测。

实现注意：

- 应固定 RDKit feature definition 文件，例如 `BaseFeatures.fdef`，并在 versions/provenance 中记录。
- feature 少于 2 个时要定义返回值策略。
- 首批更适合做 quality gate 或辅助属性，不建议作为唯一主目标。

## 5. 需要小幅输入扩展后才有意义的性质

这些性质仍然可以用 RDKit + MMFF/UFF 计算，但需要候选答案允许提交 3D 坐标，例如 SDF/mol block/XYZ，或者任务给定 reference molecule + candidate conformer。

| 候选 property | 需要的新输入 | 计算方式 | 用途 |
|---|---|---|---|
| `submitted_energy_kcal_mol` | SDF/mol block conformer | 对提交坐标直接建 force field 并 `CalcEnergy()` | 3D 构象质量 |
| `relaxed_energy_kcal_mol` | SDF/mol block conformer | 复制提交 conformer 后 minimization | 局部低能程度 |
| `relaxation_energy_drop_kcal_mol` | SDF/mol block conformer | submitted - relaxed | strain/clash gate |
| `strain_proxy_kcal_mol` | SDF/mol block + generated ensemble | submitted energy - generated ensemble min | 提交构象相对低能 ensemble 的 strain |
| `rmsd_to_relaxed_angstrom` | SDF/mol block conformer | 提交构象和优化后构象 RMSD | 构象稳定性 |
| `torsion_shift_to_relaxed_deg` | SDF/mol block conformer | rotatable torsion angle 变化 | 扭转稳定性 |
| `template_conformer_rmsd_angstrom` | reference conformer fixture | candidate 和 reference alignment RMSD | 构象复现/编辑任务 |

推荐优先级：中。

这些性质对“3D 分子生成/构象生成”任务价值很高，但它们不是纯 SMILES backend 能表达的。建议等当前 SMILES baseline 稳定后，再设计 `rdkit_forcefield_conformer_input` 或复用 xTB XYZ track 的输入/质量门模式。

## 6. 不建议由该 baseline 声明的性质

| 不建议 property | 原因 | 更合适 backend |
|---|---|---|
| 跨分子绝对稳定性排名 | MMFF/UFF energy 零点和组成依赖强，不适合不同分子直接比较 | xTB/DFT/校准数据集 |
| 生成焓、Gibbs 自由能、热容、熵 | RDKit MMFF/UFF baseline 没有频率/热化学校准流程 | xTB Hessian/量化 backend |
| 溶剂化自由能、logS、logP 的 3D 物理预测 | 需要溶剂模型或经验/ML 模型 | OPERA/ADMET-AI/xTB solvation |
| 结合能、docking score、蛋白-配体相互作用 | 缺受体、采样和打分函数 | docking/OpenMM/FEP backend |
| 反应能、活化能、过渡态 | MMFF/UFF 不适合断键成键反应路径 | xTB/DFT/反应网络 backend |
| MD 扩散系数、RDF、粘度、相变 | ETKDG + minimization 不是动力学模拟 | OpenMM/GROMACS/LAMMPS |
| 晶体/材料弹性、声子、缺陷能 | 小分子 RDKit 力场不覆盖周期体系 | ASE/MatGL/MACE/DFT |

## 7. 推荐实施路线

### P0.1：补全 ensemble summary

优先字段：

- `energy_iqr_kcal_mol`
- `energy_p10_kcal_mol`
- `energy_p90_kcal_mol`
- `low_energy_conformer_count_1kcal`
- `low_energy_conformer_count_3kcal`
- `low_energy_conformer_fraction_3kcal`
- `boltzmann_weight_top1_298k_proxy`
- `effective_conformer_count_298k_proxy`

理由：直接复用现有 energy list，风险最低。

### P0.2：补全最低能 conformer 的 3D shape

优先字段：

- `radius_of_gyration_angstrom`
- `npr1`
- `npr2`
- `pbf`
- `asphericity`
- `mol_volume_angstrom3`
- `labute_asa_angstrom2`

理由：RDKit 官方 descriptors 覆盖好，任务可解释性强。

### P0.3：补全构象多样性和质量 gate

优先字段：

- `conformer_rmsd_median_angstrom`
- `conformer_rmsd_max_angstrom`
- `tfd_median`
- `min_nonbonded_distance_best_angstrom`
- `nonbonded_clash_count`
- `max_gradient_norm`

理由：让 energy spread 不再孤立，能识别“多样性”和“坏构象 outlier”的差别。

### P1：支持提交 3D 构象

优先字段：

- `submitted_energy_kcal_mol`
- `relaxed_energy_kcal_mol`
- `relaxation_energy_drop_kcal_mol`
- `strain_proxy_kcal_mol`
- `rmsd_to_relaxed_angstrom`

理由：这会把 backend 从“SMILES 生成分子 verifier”扩展成“3D 构象 verifier”，但需要输入 schema、失败类型和测试样例同步设计。

## 8. 任务设计建议

适合新增的题型：

1. `rdkit_forcefield_low_energy_conformer_diversity`
   - 目标：生成一个 MMFF 可参数化的小分子，要求低能构象数在指定范围内，且 RMSD diversity 达到阈值。
   - 主性质：`low_energy_conformer_count_3kcal` 或 `effective_conformer_count_298k_proxy`。
   - 辅助 gate：`optimization_converged_fraction >= 0.8`、`min_nonbonded_distance_best_angstrom >= 1.2`。

2. `rdkit_forcefield_nonplanar_shape`
   - 目标：生成一个非平面、适度紧凑的小分子。
   - 主性质：`pbf` 或 `npr1/npr2` window。
   - 辅助 gate：`forcefield_parameterized == 1`、`embedding_success_rate >= 0.5`。

3. `rdkit_forcefield_compact_3d_envelope`
   - 目标：在分子量和重原子数限制内生成 compact molecule。
   - 主性质：`radius_of_gyration_angstrom` 或 `mol_volume_angstrom3` window。
   - 辅助 gate：`energy_range_kcal_mol` 不过大。

4. `rdkit_forcefield_geometry_quality_gate`
   - 目标：生成可稳定优化、无明显 clash 的小分子。
   - 主性质：`optimization_converged_fraction` maximize 或 `nonbonded_clash_count` minimize。
   - 辅助 gate：`min_nonbonded_distance_best_angstrom` window。

不建议新增的题型：

- “生成最低 MMFF 能量的不同分子”：跨分子绝对 energy 不可比。
- “预测真实构象 population”：ETKDG retained set 不是充分采样。
- “模拟室温稳定性/动力学稳定性”：没有 MD。

## 9. 参考资料

- RDKit `rdDistGeom` documentation: https://www.rdkit.org/docs/source/rdkit.Chem.rdDistGeom.html
- RDKit `rdForceFieldHelpers` documentation: https://www.rdkit.org/docs/source/rdkit.Chem.rdForceFieldHelpers.html
- RDKit `Descriptors3D` documentation: https://www.rdkit.org/docs/source/rdkit.Chem.Descriptors3D.html
- RDKit `rdMolDescriptors` documentation: https://www.rdkit.org/docs/source/rdkit.Chem.rdMolDescriptors.html
- RDKit `rdMolTransforms` documentation: https://www.rdkit.org/docs/source/rdkit.Chem.rdMolTransforms.html
- RDKit `rdMolChemicalFeatures` documentation: https://www.rdkit.org/docs/source/rdkit.Chem.rdMolChemicalFeatures.html
- RDKit `TorsionFingerprints` documentation: https://www.rdkit.org/docs/source/rdkit.Chem.TorsionFingerprints.html
- RDKit `AllChem` API reference, including `ComputeMolVolume` and conformer RMS helpers: https://www.rdkit.org/docs/source/rdkit.Chem.AllChem.html
- S. Riniker and G. A. Landrum, "Better Informed Distance Geometry: Using What We Know To Improve Conformation Generation", Journal of Chemical Information and Modeling, 2015.
- T. A. Halgren, "Merck molecular force field. I. Basis, form, scope, parameterization, and performance of MMFF94", Journal of Computational Chemistry, 1996.
- A. K. Rappe, C. J. Casewit, K. S. Colwell, W. A. Goddard III, W. M. Skiff, "UFF, a full periodic table force field for molecular mechanics and molecular dynamics simulations", Journal of the American Chemical Society, 1992.
- T. Schulz-Gasch, C. Scharfer, W. Guba, and G. Rarey, "TFD: Torsion Fingerprint Deviation as a measure to compare small molecule conformations", Journal of Chemical Information and Modeling, 2012.
