# xTB 进阶化学性质题目设计方案

## 背景

现有 xTB-XYZ track 已经支持模型直接输出单个小分子的 XYZ 几何，并用本地 xTB CLI 计算三类性质：HOMO-LUMO gap、molecular dipole moment 和 relaxation energy。第二版任务已将 `relaxation_energy` 从独立目标调整为通用几何质量门槛，避免粗糙坐标被 xTB 优化“修好”后仍获得高分。

下一批题目应继续保持 direct-XYZ 的核心能力测试：模型必须自己给出三维结构，verifier 不从 SMILES 生成 conformer。新增性质应优先满足三个条件：

- xTB CLI 能稳定计算，并能通过 stdout 或 JSON/输出文件保守解析。
- 该性质有明确化学意义，不能只是现有 gap/dipole 的同义变体。
- 对通用大模型形成新的难点：除结构常识外，还要求电子结构、局部反应性、溶剂效应或热力学推理。

## 事实依据

官方 xTB 文档和已有 inverse-design 文献支持继续扩展以下性质族：

- xTB properties 文档列出 GFN2-xTB 输出中的 orbital energies、HOMO-LUMO gap、atomic partial charges、atomic C6 coefficients、atomic polarizabilities、molecular C6/C8、Wiberg/Mayer bond orders、dipole moment 和 quadrupole moment。
- xTB singlepoint 文档支持 vertical IP/EA、IPEA 模型、global electrophilicity index、Fukui indices、DIPRO、ESP 等计算。
- xTB solvation 文档支持 ALPB/GBSA implicit solvent，并输出 solvation free energy `Gsolv`。
- xTB hessian 文档支持 vibrational frequencies、IR/Raman intensities 和 298.15 K thermochemical properties，包括 zero-point energy、entropy、heat capacity、enthalpy 和 Gibbs free energy。
- Tartarus inverse molecular design benchmark 使用 CREST 和 GFN2-xTB 计算 HOMO、LUMO、gap、dipole 等性质，并将 LUMO 等电子结构量用于 OPV 目标。
- Hiener 和 Hutchison 的有机介电材料搜索使用 GFN2-xTB 同时优化 polarizability 和 dipole moment。
- GAELLE 等反应性工作流使用 xTB 的 conformer、electrophilicity、Fukui 和 implicit-solvent 能量来分析反应性。

参考资料：

- xTB properties: https://xtb-docs.readthedocs.io/en/latest/properties.html
- xTB singlepoint runtypes: https://xtb-docs.readthedocs.io/en/latest/sp.html
- xTB command line: https://xtb-docs.readthedocs.io/en/latest/commandline.html
- xTB ALPB/GBSA solvation: https://xtb-docs.readthedocs.io/en/latest/gbsa.html
- xTB hessian and thermochemistry: https://xtb-docs.readthedocs.io/en/latest/hessian.html
- Tartarus benchmark: https://papers.neurips.cc/paper_files/paper/2023/file/09f8b2469a3d1089a7c60d9ef1983271-Paper-Datasets_and_Benchmarks.pdf
- Dipole/polarizability GA optimization: https://pubs.acs.org/doi/10.1021/acs.jpca.2c01266
- GAELLE reactivity workflow: https://www.mdpi.com/3042-6723/1/1/1
- QMugs xTB quantum-mechanical descriptors: https://www.nature.com/articles/s41597-022-01390-7

## 设计目标

新增一批进阶 xTB direct-XYZ 任务：

```yaml
object_type: small_molecule_3d
formal_track: true
capability_tags:
  - open_generation
  - property_satisfaction
  - property_optimization
  - multi_objective
  - geometry_quality
  - three_dimensional_geometry
  - xyz
  - xtb
  - quantum_chemistry
```

目标能力覆盖：

- 电子受体/供体能力：LUMO、vertical IP/EA、global electrophilicity。
- 分子响应性：polarizability 与 dipole 的协同优化。
- 溶液相行为：implicit-solvent solvation free energy 和溶剂选择性。
- 局部反应性：Fukui indices 和位点选择性。
- 热力学与真实极小点：hessian 频率、虚频数、ZPE、entropy/Gibbs free energy。

## 非目标

以下内容不纳入本批设计：

- charged molecules、radicals 或 open-shell 分子。它们需要新的 charge/spin answer schema 和 domain 规则。
- multi-fragment binding energy、reaction energy、pKa 或 proton affinity。它们需要 multi-XYZ 或 fragment-labeled answer schema。
- conformer ensemble 或 CREST workflow。它们计算成本更高，且需要明确 ensemble 聚合规则。
- DIPRO 二聚体 electronic coupling。它需要二聚体/片段标注，适合作为后续独立设计。

## 统一候选结构域

除 hessian 任务另有限制外，本批任务继续沿用 xTB-XYZ 当前 domain：

```yaml
domain:
  format: xyz
  charge: 0
  multiplicity: 1
  allowed_elements: [H, C, N, O, F, P, S, Cl, Br]
  atom_count: [3, 80]
  heavy_atom_count: [1, 40]
  coordinate_units: angstrom
  max_absolute_coordinate: 30.0
  min_interatomic_distance: 0.45
  inferred_components: 1
  require_explicit_hydrogens: true
```

所有任务默认增加几何质量门槛：

```yaml
- type: minimize_bounded
  property: relaxation_energy
  verifier_id: xtb_relaxation_energy_gfn2_v1
  role: quality_gate
  lower: 0.0
  upper: 0.35
```

`relaxation_energy` 的定义保持不变：

```text
relaxation_energy_eV = max(0.0, (E_input_singlepoint_Eh - E_optimized_Eh) * 27.211386245988)
```

## Answer Schema

本批任务继续使用单个 fenced XYZ final-answer block：

````yaml
answer_schema: &xyz_answer_schema
  format: final_answer_block
  final_answer_prefix: "FINAL ANSWER:"
  value_type: xyz
  fence_language: xyz
  cardinality: one
  example: |
    FINAL ANSWER:
    ```xyz
    3
    water
    O 0.000000 0.000000 0.000000
    H 0.758602 0.000000 0.504284
    H -0.758602 0.000000 0.504284
    ```
````

## 候选任务总览

| 优先级 | 任务 ID | 主性质 | 推荐难度 | 主要能力 |
| --- | --- | --- | --- | --- |
| 1 | `xtb_lumo_min_008` | optimized-geometry LUMO energy | intermediate | 电子受体设计 |
| 2 | `xtb_polarizability_dipole_opt_009` | polarizability per heavy atom + dipole | advanced | 分子响应性和介电材料 proxy |
| 3 | `xtb_solvation_selectivity_alpb_010` | ALPB solvent selectivity | advanced | 溶液相稳定化和极性设计 |
| 4 | `xtb_electrophilicity_max_011` | global electrophilicity index | advanced | IP/EA 组合电子结构 |
| 5 | `xtb_fukui_carbon_site_012` | carbon-site Fukui index selectivity | expert | 局部反应位点控制 |
| 6 | `xtb_hessian_thermo_stability_013` | imaginary modes + entropy/ZPE/frequency | expert | 真正极小点和热化学性质 |

## 任务 1：LUMO 最小化

### 化学性质

`lumo_energy` 是 xTB 优化后结构的最低未占据分子轨道能量，单位 eV。任务目标是让 LUMO 尽可能低，同时继续要求提交几何接近 xTB 低能结构。

### 化学价值

低 LUMO 分子通常更容易接受电子，常作为电子受体、n 型有机半导体、还原电位 proxy 和 OPV acceptor 设计中的关键指标。与 HOMO-LUMO gap 相比，LUMO 单独约束能把目标从“能级差”转向“绝对受电子能力”，因此对电子结构控制更具体。

### 对通用大模型的难度

通用大模型可能知道硝基、氰基、羰基、含氟取代和共轭骨架会降低 LUMO，但很难同时满足：

- 中性闭壳层和 allowed-elements 约束。
- 合理三维几何和低 relaxation energy。
- 避免只堆极端吸电子小基团而导致 domain 或优化失败。
- 命中 xTB orbital energy 数值，而不是依赖定性常识。

### 推荐 verifier 形式

```yaml
verifier_id: xtb_lumo_gfn2_v1
property_name: lumo_energy
backend:
  type: local_xtb
  executable: xtb
  method: GFN2-xTB
  charge: 0
  uhf: 0
  optimize_before_property: true
property:
  source: xTB GFN2-xTB optimized geometry orbital energy printout
  units: eV
  notes: Parse the LUMO orbital energy, not the HOMO-LUMO gap.
```

### 推荐 task card

```yaml
task_id: xtb_lumo_min_008
version: 1
object_type: small_molecule_3d
difficulty: intermediate
formal_track: true
capability_tags: [open_generation, property_optimization, geometry_quality, three_dimensional_geometry, xyz, xtb, lumo_energy, electron_acceptor]
constraints:
  - type: minimize_bounded
    property: lumo_energy
    verifier_id: xtb_lumo_gfn2_v1
    lower: -4.0
    upper: 1.0
  - type: minimize_bounded
    property: relaxation_energy
    verifier_id: xtb_relaxation_energy_gfn2_v1
    role: quality_gate
    lower: 0.0
    upper: 0.35
structural_domain:
  heavy_atom_count: [8, 40]
  carbon_count_min: 4
  hetero_atom_count_min: 2
  formula_denylist: [HCN, CH2O, CH3NO2]
scoring:
  aggregation: geometric_mean
```

### 校准事项

`lower: -4.0` 和 `upper: 1.0` 是首轮建议值。实现前应在 QM9/QMugs 或本仓库 sample pack 上跑 GFN2-xTB 分布校准，确认简单分子不会饱和，典型强受体能获得高分。

## 任务 2：高极化率 + 偶极矩协同优化

### 化学性质

主性质建议使用 `polarizability_per_heavy_atom`：

```text
polarizability_per_heavy_atom = molecular_alpha_0 / heavy_atom_count
```

其中 `molecular_alpha_0` 来自 GFN2-xTB 的 molecular polarizability printout。任务同时加入 dipole moment 约束，避免模型只靠增大分子尺寸获得高 polarizability。

### 化学价值

极化率描述电子云在外电场下变形的能力；偶极矩描述分子永久电荷分离。二者共同约束可作为有机介电材料、分子响应材料和高介电常数候选的 proxy。单独最大化 polarizability 会偏向更大、更重、更软的分子；归一化后再叠加 dipole，可把目标转向单位结构复杂度上的响应性。

### 对通用大模型的难度

该任务比 dipole 最大化更难：

- 高极化率偏向大共轭体系、重原子和软电子云，但分子大小受限。
- 高 dipole 要求不对称极性取代，与高度共轭/高极化结构并非总是同向。
- 分子必须保持可优化、低 relaxation energy 和闭壳层。
- `polarizability_per_heavy_atom` 不是常见教科书直觉，模型很难直接估数。

### 推荐 verifier 形式

```yaml
verifier_id: xtb_polarizability_gfn2_v1
property_name: polarizability_per_heavy_atom
backend:
  type: local_xtb
  executable: xtb
  method: GFN2-xTB
  charge: 0
  uhf: 0
  optimize_before_property: true
property:
  source: xTB GFN2-xTB optimized geometry molecular polarizability printout
  units: atomic_units_per_heavy_atom
  notes: Parse molecular alpha(0), then divide by submitted heavy atom count.
```

### 推荐 task card

```yaml
task_id: xtb_polarizability_dipole_opt_009
version: 1
object_type: small_molecule_3d
difficulty: advanced
formal_track: true
capability_tags: [open_generation, property_optimization, multi_objective, geometry_quality, three_dimensional_geometry, xyz, xtb, polarizability, dipole_moment]
constraints:
  - type: maximize_bounded
    property: polarizability_per_heavy_atom
    verifier_id: xtb_polarizability_gfn2_v1
    lower: 4.0
    upper: 12.0
  - type: window
    property: dipole_moment
    verifier_id: xtb_dipole_gfn2_v1
    min: 3.0
    max: 8.0
    sigma: 1.0
  - type: minimize_bounded
    property: relaxation_energy
    verifier_id: xtb_relaxation_energy_gfn2_v1
    role: quality_gate
    lower: 0.0
    upper: 0.35
structural_domain:
  heavy_atom_count: [8, 40]
  carbon_count_min: 4
  hetero_atom_count_min: 2
  heavy_element_diversity_min: 2
scoring:
  aggregation: geometric_mean
```

### 校准事项

`polarizability_per_heavy_atom` 的单位和数量级必须用本地 xTB 版本确认。若不同 xTB 版本输出字段不稳定，优先使用 `--json` 或 xTB 产生的 structured output 文件。

## 任务 3：ALPB 水/非极性溶剂选择性

### 化学性质

推荐主性质为 `alpb_water_hexane_selectivity`：

```text
alpb_water_hexane_selectivity = Gsolv_hexane - Gsolv_water
```

单位 eV。数值越大，说明水相溶剂化比非极性溶剂更稳定。相比只最小化 `Gsolv_water`，该差值更能避免模型单纯生成大而强极性的分子，因为目标强调相对溶剂选择性。

### 化学价值

溶剂化自由能是极性、氢键能力、分子表面积和电荷分布的综合结果。水/非极性溶剂选择性可作为水溶性、环境响应、极性官能团布局和溶液相稳定性的 proxy。它比 gas-phase dipole 更接近真实应用场景。

### 对通用大模型的难度

模型通常知道羟基、羰基、腈基、胺、酰胺等提高水相稳定性，但难点在于：

- 本 track 不允许离子和显式盐，不能靠铵盐/羧酸盐作弊。
- 过多极性基团可能导致不合理几何、强内氢键或优化失败。
- 选择性是两个溶剂模型输出的差值，不是单一极性大小。
- ALPB 数值受分子形状和表面积影响，定性判断不够。

### 推荐 verifier 形式

```yaml
verifier_id: xtb_solvation_selectivity_alpb_v1
property_name: alpb_water_hexane_selectivity
backend:
  type: local_xtb
  executable: xtb
  method: GFN2-xTB
  charge: 0
  uhf: 0
  optimize_before_property: true
  solvent_runs:
    - model: alpb
      solvent: water
    - model: alpb
      solvent: hexane
property:
  source: xTB GFN2-xTB ALPB Gsolv printout on optimized geometry
  units: eV
  notes: Compute Gsolv(hexane) - Gsolv(water); higher means stronger water-selective stabilization.
```

### 推荐 task card

```yaml
task_id: xtb_solvation_selectivity_alpb_010
version: 1
object_type: small_molecule_3d
difficulty: advanced
formal_track: true
capability_tags: [open_generation, property_optimization, geometry_quality, three_dimensional_geometry, xyz, xtb, solvation, alpb]
constraints:
  - type: maximize_bounded
    property: alpb_water_hexane_selectivity
    verifier_id: xtb_solvation_selectivity_alpb_v1
    lower: 0.0
    upper: 1.5
  - type: minimize_bounded
    property: relaxation_energy
    verifier_id: xtb_relaxation_energy_gfn2_v1
    role: quality_gate
    lower: 0.0
    upper: 0.35
structural_domain:
  heavy_atom_count: [8, 36]
  carbon_count_min: 3
  hetero_atom_count_min: 3
  formula_denylist: [H2O, NH3, HCN, CH2O, CH3OH, CH3CN]
scoring:
  aggregation: geometric_mean
```

### 校准事项

该任务每个候选至少需要 gas/optimized geometry 加两个 solvent single-point 或 solvent runs，成本高于 gap/dipole。应设置更长 timeout，并先确认本地 xTB 支持 `hexane` 溶剂名；如果版本不支持，改用文档和本地版本都支持的非极性溶剂。

## 任务 4：全局亲电性最大化

### 化学性质

`global_electrophilicity` 使用 xTB `--vomega` 直接计算。文档中其定义为：

```text
GEI = (IP + EA)^2 / (8 * (IP - EA))
```

其中 IP 和 EA 来自 vertical ionization potential 与 vertical electron affinity。该任务建议使用 GFN1-IPEA 模型，而不是 GFN2 默认 orbital energy proxy。

### 化学价值

全局亲电性比 LUMO 更综合：它同时考虑分子的失电子难度和得电子能力，反映整体接受电子密度的倾向。它适合评价亲核攻击敏感性、Lewis 酸性、共价反应片段和电子受体设计。

### 对通用大模型的难度

该任务难度高于 LUMO 最小化：

- GEI 是 IP/EA 组合性质，不等同于低 LUMO 或小 gap。
- IPEA 模型的数值分布不如常见 gap/dipole 容易从常识估计。
- 过强吸电子结构可能导致优化失败、异常小 gap 或不稳定几何。
- 模型必须在中性闭壳层限制下制造高亲电性。

### 推荐 verifier 形式

```yaml
verifier_id: xtb_electrophilicity_gfn1_ipea_v1
property_name: global_electrophilicity
backend:
  type: local_xtb
  executable: xtb
  method: GFN1-xTB/IPEA
  charge: 0
  uhf: 0
  optimize_before_property: true
  property_command: --vomega
property:
  source: xTB vertical electrophilicity printout
  units: eV
  notes: Use xTB --vomega on optimized geometry; parse GEI directly when available.
```

### 推荐 task card

```yaml
task_id: xtb_electrophilicity_max_011
version: 1
object_type: small_molecule_3d
difficulty: advanced
formal_track: true
capability_tags: [open_generation, property_optimization, geometry_quality, three_dimensional_geometry, xyz, xtb, electrophilicity, ipea]
constraints:
  - type: maximize_bounded
    property: global_electrophilicity
    verifier_id: xtb_electrophilicity_gfn1_ipea_v1
    lower: 0.5
    upper: 4.0
  - type: minimize_bounded
    property: relaxation_energy
    verifier_id: xtb_relaxation_energy_gfn2_v1
    role: quality_gate
    lower: 0.0
    upper: 0.35
structural_domain:
  heavy_atom_count: [8, 40]
  carbon_count_min: 4
  hetero_atom_count_min: 2
  formula_denylist: [HCN, CH2O, CH3NO2]
scoring:
  aggregation: geometric_mean
```

### 校准事项

几何优化仍可使用 GFN2-xTB，但 `--vomega` 性质计算使用 IPEA run type。实现时必须在 result metadata 中记录 optimization method 与 property method，避免把 GFN2 orbital proxy 和 IPEA vertical property 混淆。

## 任务 5：Fukui 碳位点选择性

### 化学性质

推荐主性质为 `max_f_plus_on_carbon`，并增加选择性指标 `f_plus_contrast`：

```text
max_f_plus_on_carbon = max(f_plus[i] for atom i where element == C)
f_plus_contrast = max_f_plus_on_carbon - second_largest_f_plus
```

`f+` 通常对应亲核攻击敏感性，即该原子接受电子密度的倾向。任务要求最强反应位点落在碳原子上，并且与其他原子拉开差距。

### 化学价值

Fukui index 是局部反应性描述符。与 global electrophilicity 相比，它不只问“这个分子是否亲电”，还问“哪个原子最亲电”。这类任务可以测试模型对官能团、共轭、取代效应和 regioselectivity 的综合控制。

### 对通用大模型的难度

这是本批最能区分通用大模型和化学推理模型的任务之一：

- 模型必须控制局部电子结构，而不是只控制全分子性质。
- XYZ 中原子顺序会参与解析，prompt 和 verifier 必须避免让模型通过注释作弊。
- 很多强吸电子分子最强 Fukui 位点可能在杂原子而非碳上。
- 局部位点选择性需要结构、官能团、共轭和空间构型共同配合。

### 推荐 verifier 形式

```yaml
verifier_id: xtb_fukui_gfn1_v1
property_name: max_f_plus_on_carbon
backend:
  type: local_xtb
  executable: xtb
  method: GFN1-xTB
  charge: 0
  uhf: 0
  optimize_before_property: true
  property_command: --vfukui
property:
  source: xTB vertical Fukui indices printout
  units: dimensionless
  notes: Parse atom-indexed f+ values and map them back to submitted XYZ element order.
```

### 推荐 task card

```yaml
task_id: xtb_fukui_carbon_site_012
version: 1
object_type: small_molecule_3d
difficulty: expert
formal_track: true
capability_tags: [open_generation, property_optimization, geometry_quality, three_dimensional_geometry, xyz, xtb, fukui, local_reactivity]
constraints:
  - type: maximize_bounded
    property: max_f_plus_on_carbon
    verifier_id: xtb_fukui_gfn1_v1
    lower: 0.05
    upper: 0.35
  - type: maximize_bounded
    property: f_plus_contrast
    verifier_id: xtb_fukui_gfn1_v1
    lower: 0.00
    upper: 0.15
  - type: minimize_bounded
    property: relaxation_energy
    verifier_id: xtb_relaxation_energy_gfn2_v1
    role: quality_gate
    lower: 0.0
    upper: 0.35
structural_domain:
  heavy_atom_count: [8, 32]
  carbon_count_min: 5
  hetero_atom_count_min: 2
  formula_denylist: [HCN, CH2O, CH3NO2]
scoring:
  aggregation: geometric_mean
```

### 校准事项

Fukui values 是相对指标，不宜跨完全不同体系解释为绝对物理量。benchmark 可以把它作为 scoring property 使用，但 prompt 和 notes 应明确它是 xTB-defined local reactivity descriptor。实现时需要测试 atom-index 映射和输出格式稳定性。

## 任务 6：Hessian 热化学与稳定极小点

### 化学性质

该任务把 hessian 结果拆成两个层次：

- gate：`imaginary_frequency_count == 0`，确保优化结构是 xTB 势能面上的局部极小点，而不是鞍点。
- 主目标：选择一个热化学/振动目标，例如 `entropy_298_per_heavy_atom`、`zpe_per_heavy_atom` 或 `lowest_real_frequency` 窗口。

推荐第一版主目标为 `entropy_298_per_heavy_atom` 最大化：

```text
entropy_298_per_heavy_atom = S_298 / heavy_atom_count
```

### 化学价值

hessian 任务把 benchmark 从“优化后能算一个电子性质”推进到“分子几何是一个真正稳定的局部极小点”。虚频数直接反映结构是否处于 minimum；熵和低频模式反映分子柔性、振动自由度和热力学贡献。该任务对 direct-XYZ 生成能力非常敏感。

### 对通用大模型的难度

该任务是本批计算与建模难度最高的单分子任务：

- 需要提交接近极小点的三维几何，否则 hessian 容易出现虚频。
- 低频振动和 entropy 与三维构型、柔性、扭转自由度相关，难以靠二维官能团直觉判断。
- hessian 计算成本高，atom count 必须更小。
- 模型可能生成柔性但几何粗糙的结构，最终被 relaxation gate 或 imaginary-frequency gate 拒绝。

### 推荐 verifier 形式

```yaml
verifier_id: xtb_hessian_thermo_gfn2_v1
property_name: entropy_298_per_heavy_atom
backend:
  type: local_xtb
  executable: xtb
  method: GFN2-xTB
  charge: 0
  uhf: 0
  optimize_before_property: true
  property_command: --ohess
property:
  source: xTB optimized hessian thermochemistry printout
  units: J mol-1 K-1 per heavy atom
  notes: Parse imaginary frequencies and 298.15 K entropy; restrict molecule size for runtime.
```

### 推荐 task card

```yaml
task_id: xtb_hessian_thermo_stability_013
version: 1
object_type: small_molecule_3d
difficulty: expert
formal_track: true
capability_tags: [open_generation, property_optimization, geometry_quality, three_dimensional_geometry, xyz, xtb, hessian, thermochemistry]
constraints:
  - type: window
    property: imaginary_frequency_count
    verifier_id: xtb_hessian_thermo_gfn2_v1
    min: 0
    max: 0
    sigma: 1.0
    role: stability_gate
  - type: maximize_bounded
    property: entropy_298_per_heavy_atom
    verifier_id: xtb_hessian_thermo_gfn2_v1
    lower: 5.0
    upper: 18.0
  - type: minimize_bounded
    property: relaxation_energy
    verifier_id: xtb_relaxation_energy_gfn2_v1
    role: quality_gate
    lower: 0.0
    upper: 0.35
structural_domain:
  atom_count: [6, 48]
  heavy_atom_count: [4, 18]
  carbon_count_min: 2
  hetero_atom_count_min: 1
scoring:
  aggregation: geometric_mean
timeout_seconds: 600
```

### 校准事项

hessian 输出和 thermochemistry 单位必须在 xTB 6.7.x 环境下用真实样本校准。若 entropy 解析不稳定，第一版可退化为更稳健的 `imaginary_frequency_count` gate 加 `lowest_real_frequency` window。

## Verifier 架构扩展

本批不改变 task-level routing 模式。新增 verifier 仍应是 property-level script，调用共享 xTB backend：

```text
verifiers/xtb/xtb_lumo.py
verifiers/xtb/xtb_polarizability.py
verifiers/xtb/xtb_solvation_selectivity.py
verifiers/xtb/xtb_electrophilicity.py
verifiers/xtb/xtb_fukui.py
verifiers/xtb/xtb_hessian_thermo.py
verifiers/backends/xtb_properties.py
```

共享 backend 需要从“单一 optimize 输出解析器”扩展为“property run plan”：

```python
@dataclass(frozen=True)
class XTBPropertyRun:
    mode: str
    method: str
    flags: list[str]
    parse_targets: list[str]
```

每个 property verifier 定义自己的 run plan：

- LUMO/polarizability：GFN2 optimize output。
- solvation：GFN2 optimize 后，对同一 optimized geometry 运行 ALPB solvent single-point。
- electrophilicity：GFN2 optimize 后，GFN1-IPEA `--vomega` property run。
- Fukui：GFN2 optimize 后，GFN1/GFN2 `--vfukui` property run，按本地 xTB 支持情况固定版本。
- hessian：限制分子大小后运行 `--ohess` 或 optimize 后 `--hess`。

## 统一失败映射

新增任务沿用当前 failure policy，并增加 property-specific tool errors：

```yaml
failure_policy:
  malformed_final_answer: parse_error
  invalid_xyz: parse_error
  invalid_coordinates: validity_error
  disconnected_geometry: validity_error
  atom_overlap: validity_error
  outside_domain: domain_error
  unsupported_charge_or_spin: domain_error
  missing_xtb: verifier_environment_error
  xtb_nonzero_exit: verifier_tool_error
  xtb_optimization_not_converged: verifier_tool_error
  xtb_missing_property: verifier_tool_error
  xtb_property_run_unsupported: verifier_tool_error
  xtb_hessian_imaginary_modes_missing: verifier_tool_error
  timeout: verifier_timeout
```

## Scoring 规则

所有任务遵守当前 xTB-XYZ scoring 原则：

```text
final_score = property_score * geometry_quality_score
```

多属性任务使用主属性分数的几何平均：

```text
property_score = geometric_mean(main_constraint_scores)
```

`relaxation_energy` 不纳入主属性几何平均，只作为 quality gate。`imaginary_frequency_count` 也应作为 hessian 任务的 stability gate；若虚频数不为 0，应显著降低或归零最终分数。

## 测试策略

实现时应先写 fake-runner 单元测试，再做真实 xTB smoke test：

1. Parser tests：每个新增性质至少覆盖一种 xTB 6.7.x 样例输出。
2. Run-plan tests：确认 CLI flags、method、charge、UHF 和 solvent 参数正确。
3. Failure mapping tests：missing property、unsupported solvent、nonzero exit、timeout、unconverged optimization。
4. Task schema tests：task IDs、verifier IDs、answer schema、domain、quality gate、prompt 不泄露 verifier internals。
5. Regression baseline tests：常见小分子和简单极性分子不能在进阶任务上拿高分。
6. Optional live smoke tests：本地安装 xTB 时运行少量校准 XYZ；未安装时返回 `verifier_environment_error`，不视为 verifier bug。

## 实施顺序建议

推荐按风险递增实施：

| 顺序 | 任务 | 原因 |
| --- | --- | --- |
| 1 | `xtb_lumo_min_008` | 与现有 gap parser 最接近，工程风险最低。 |
| 2 | `xtb_polarizability_dipole_opt_009` | GFN2 输出已有 polarizability，与现有 dipole 组合自然。 |
| 3 | `xtb_solvation_selectivity_alpb_010` | 化学价值高，输出字段明确，但需要多 solvent run。 |
| 4 | `xtb_electrophilicity_max_011` | 引入 IPEA run type，需要清楚记录 method provenance。 |
| 5 | `xtb_fukui_carbon_site_012` | 局部位点解析和 scoring 难度高，需要谨慎校准。 |
| 6 | `xtb_hessian_thermo_stability_013` | 计算最贵，对 runtime 和输出解析要求最高。 |

## 自检

- Placeholder scan：未发现占位符或未完成条目。
- Scope check：本文只定义下一批 xTB direct-XYZ 题目，不实现代码、不改变现有 task pack。
- Consistency check：所有任务都保留单 XYZ、中性闭壳层、显式氢、allowed-elements 和 relaxation-energy quality gate。
- Ambiguity check：需要实测校准的阈值已明确标记为建议值，不作为最终物理常数。
