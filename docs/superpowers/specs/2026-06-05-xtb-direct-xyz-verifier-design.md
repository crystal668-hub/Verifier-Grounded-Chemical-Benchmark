# xTB 直接 XYZ Verifier 首版设计方案

## 背景

这一轮 xTB verifier 接入应围绕“模型直接输出 XYZ 分子三维结构”设计。模型给出的最终答案不是 SMILES，也不是 CIF/SDF，而是一个带原子坐标的 XYZ block；verifier 直接解析这份 XYZ，做基础几何和化学域检查，然后调用本地 xTB 计算可验证的量子化学性质。

这个方向与现有 RDKit 小分子任务不同。RDKit track 让模型输出 SMILES，verifier 只计算 2D/拓扑 descriptor；xTB-XYZ track 要测试模型能否直接给出合理三维几何。verifier 不应从 SMILES 隐式生成 conformer，否则核心 3D 生成能力会从模型侧转移到 verifier 侧，题目目标会被稀释。

## 事实依据

直接输出 XYZ 是合理且可行的，依据包括工具能力、公开数据集和真实 inverse-design 研究。

- xTB 官方文档支持 XYZ 分子几何输入；xTB 输出中包含 total energy、orbital energies、HOMO-LUMO gap、molecular dipole moment 等性质，并支持标准几何优化流程。
- QM9 包含 133,885 个小有机分子的量子化学结构与性质，数据以 XYZ-like 文件和结构化性质字段呈现，性质包括 dipole moment、HOMO、LUMO、gap 等。
- GEOM 包含约 37 million 个构象，覆盖超过 450,000 个分子，说明“3D 坐标 + 能量/性质”是分子生成和性质预测中的标准对象。
- 已有语言模型研究证明模型可以直接基于 XYZ/CIF/PDB 等文件格式序列生成三维分子、材料和蛋白结合位点。
- Tartarus inverse molecular design benchmark 使用 Open Babel、CREST 和 GFN2-xTB 生成/优化结构，并以 HOMO-LUMO gap、dipole moment、LUMO 等作为真实优化目标；其 OPV 数据集 `hce.csv` 包含 24,953 个样本。
- HOMO-LUMO gap 的最大化和最小化都有研究价值。diamondoid inverse-design 研究在 adamantane 衍生物中搜索到 2.42 到 10.63 eV 的 gap，而未取代 adamantane 的 gap 为 9.45 eV。
- dipole moment 最大化也有研究价值。Hiener 和 Hutchison 的遗传算法研究用 GFN2-xTB 搜索同时具有大 polarizability 和大 dipole moment 的有机介电材料候选。

参考资料：

- xTB geometry input: https://xtb-docs.readthedocs.io/en/latest/geometry.html
- xTB properties: https://xtb-docs.readthedocs.io/en/latest/properties.html
- xTB command-line run types: https://xtb-docs.readthedocs.io/en/latest/commandline.html
- QM9 Scientific Data: https://www.nature.com/articles/sdata201422
- DeepChem QM9 CSV: https://deepchemdata.s3-us-west-1.amazonaws.com/datasets/qm9.csv
- GEOM Scientific Data: https://www.nature.com/articles/s41597-022-01288-4
- Direct 3D language-model generation: https://arxiv.org/abs/2305.05708
- Tartarus tasks: https://tartarus.readthedocs.io/en/latest/tasks.html
- Diamondoid HOMO-LUMO gap inverse design: https://pubs.acs.org/doi/10.1021/acs.jctc.6b01074
- Dipole/polarizability GA optimization: https://pubs.acs.org/doi/10.1021/acs.jpca.2c01266

## 设计范围

首版设计为正式小分子三维结构 track：

```yaml
object_type: small_molecule_3d
formal_track: true
capability_tags:
  - open_generation
  - property_satisfaction
  - property_optimization
  - three_dimensional_geometry
  - xyz
  - xtb
  - quantum_chemistry
```

首版保持保守：

- 只接受 molecular XYZ，不接受 SDF、CIF、PDB 或周期结构。
- 只接受中性闭壳层分子：charge 0，singlet multiplicity。
- 固定使用 GFN2-xTB。
- HOMO-LUMO gap 和 dipole moment 都在 xTB 优化后结构上评分。
- relaxation energy 定义为输入几何单点能与优化后能量之差，用于评价模型直接输出的几何是否接近低能结构。
- 暂不纳入振动频率、虚频数、vertical IP/EA、partial charges、溶剂化、反应路径、构象 ensemble。

## 候选结构域

模型提示词暴露的硬约束必须与 verifier 域检查一致。首版使用以下 domain：

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

`inferred_components` 用 covalent radius 图从 XYZ 坐标推断连通性，并拒绝断开的几何。这个图只作为 validity gate，不作为性质来源；正式性质仍由 xTB 计算。

首版不从 XYZ 自动推断 charge、spin 或 bond order。后续如果需要 charged molecules、radicals 或 SDF bond order，需要单独设计 answer schema。

## Answer Schema

任务使用 fenced final-answer block：

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

extractor 返回现有 verifier-ready shape：

```python
{
    "task_id": task_id,
    "candidates": [{"xyz": extracted_xyz}],
    "raw_answer": original_response,
    "extracted_answer": extracted_xyz,
}
```

XYZ 内容要求：

- 第一行是 atom count。
- 第二行是 comment line，可以为空但必须存在。
- 后续每行是元素符号和三个有限浮点坐标，单位 Angstrom。
- atom count 必须与坐标行数一致。

## Verifier 架构

沿用当前仓库的 constraint-level routing 边界：

```text
task constraint/property -> verifier_id -> verification_script -> shared backend/tool environment
```

不要创建 task-level verifier script。每个 xTB 性质有一个 property-level script，所有脚本调用共享 backend：

```text
verifiers/xtb/xtb_gap.py
verifiers/xtb/xtb_dipole.py
verifiers/xtb/xtb_relaxation_energy.py
verifiers/backends/xtb_properties.py
```

共享 backend 负责：

- XYZ 解析和 domain check。
- 临时工作目录。
- xTB 命令构造。
- 输入几何单点计算和几何优化。
- xTB 输出解析。
- failure type 映射。
- xTB 版本和 parser 版本 metadata。

property-level script 只检查 `verifier_spec.property_name` 与脚本性质是否一致，然后调用 shared backend。

## Verifier Specs

首版定义三个 verifier spec：

```yaml
verifiers:
  - verifier_id: xtb_gap_gfn2_v1
    name: xTB GFN2 HOMO-LUMO Gap Verifier
    version: 1
    formal_track: true
    verifier_image: verifier-grounded:dev
    verification_script: verifiers/xtb/xtb_gap.py
    timeout_seconds: 240
    property_name: homo_lumo_gap
    resources: &xtb_resources
      cpu: 2
      memory_mb: 2048
    backend: &xtb_backend
      type: local_xtb
      executable: xtb
      method: GFN2-xTB
      charge: 0
      uhf: 0
      optimize_before_property: true
    package_versions: &xtb_package_versions
      xtb: external
      rdkit: "2026.3.2"
    domain: &xtb_xyz_domain
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
    property:
      source: xTB GFN2-xTB optimized geometry property printout
      units: eV
      notes: 固定 xTB 输出中的 HOMO-LUMO orbital-energy gap，不等同于实验 optical gap。
    scoring: &xtb_scoring
      supported_modes:
        - window
        - maximize_bounded
        - minimize_bounded
      bounded_modes:
        good_at_or_baseline: forbidden
      final_score_range: [0.0, 1.0]
    failure_policy: &xtb_failure_policy
      parse_error: missing fenced XYZ block or unparseable XYZ content
      validity_error: atom overlap, disconnected geometry, or invalid coordinate values
      domain_error: outside element, atom-count, charge, spin, or coordinate domain
      verifier_environment_error: xTB executable missing or unusable
      verifier_tool_error: xTB calculation failed, optimization did not converge, or output property was missing
      verifier_timeout: xTB calculation exceeded timeout

  - verifier_id: xtb_dipole_gfn2_v1
    name: xTB GFN2 Dipole Moment Verifier
    version: 1
    formal_track: true
    verifier_image: verifier-grounded:dev
    verification_script: verifiers/xtb/xtb_dipole.py
    timeout_seconds: 240
    property_name: dipole_moment
    resources: *xtb_resources
    backend: *xtb_backend
    package_versions: *xtb_package_versions
    domain: *xtb_xyz_domain
    property:
      source: xTB GFN2-xTB optimized geometry molecular dipole printout
      units: debye
      notes: 总偶极矩模长，方向无关。
    scoring: *xtb_scoring
    failure_policy: *xtb_failure_policy

  - verifier_id: xtb_relaxation_energy_gfn2_v1
    name: xTB GFN2 Relaxation Energy Verifier
    version: 1
    formal_track: true
    verifier_image: verifier-grounded:dev
    verification_script: verifiers/xtb/xtb_relaxation_energy.py
    timeout_seconds: 300
    property_name: relaxation_energy
    resources: *xtb_resources
    backend:
      <<: *xtb_backend
      input_singlepoint_before_optimization: true
      optimize_before_property: true
    package_versions: *xtb_package_versions
    domain: *xtb_xyz_domain
    property:
      source: xTB GFN2-xTB input single-point energy minus optimized total energy
      units: eV
      notes: 衡量模型提交的 XYZ 是否已经接近 xTB 势能面局部低能结构。
    scoring: *xtb_scoring
    failure_policy: *xtb_failure_policy
```

`relaxation_energy` 计算方式：

```text
relaxation_energy_eV = max(0.0, (E_input_singlepoint_Eh - E_optimized_Eh) * 27.211386245988)
```

`max(0.0, ...)` 用于避免数值噪声或优化器输出导致负 relaxation energy。

## 题目集合

首版同时包含窗口题和优化题。窗口题验证模型能否命中特定性质区间；优化题验证模型能否把有研究意义的性质推向目标方向。所有 max/min 优化题都使用固定上下界线性映射，不按参赛答案动态排序。

````yaml
tasks:
  - task_id: xtb_gap_window_001
    version: 1
    object_type: small_molecule_3d
    difficulty: basic
    formal_track: true
    capability_tags: [open_generation, property_satisfaction, three_dimensional_geometry, xyz, xtb, homo_lumo_gap]
    prompt: |
      Propose one neutral closed-shell small molecule as an XYZ geometry.

      The molecule must satisfy these requirements:
      - The XYZ must contain exactly one connected molecule with all hydrogens explicit.
      - Allowed elements: H, C, N, O, F, P, S, Cl, Br.
      - Atom count must be between 3 and 80 inclusive.
      - Heavy atom count must be between 1 and 40 inclusive.
      - Coordinates must be in Angstrom and suitable for local xTB optimization.
      - After GFN2-xTB optimization, have a HOMO-LUMO gap between 4.0 and 6.0 eV.

      Your final answer must appear exactly in this format:
      FINAL ANSWER:
      ```xyz
      <XYZ content>
      ```
    answer_schema: *xyz_answer_schema
    constraints:
      - type: window
        property: homo_lumo_gap
        verifier_id: xtb_gap_gfn2_v1
        min: 4.0
        max: 6.0
        sigma: 0.75
    scoring:
      aggregation: geometric_mean
    failure_policy: &xtb_task_failure_policy
      malformed_final_answer: parse_error
      invalid_xyz: parse_error
      invalid_coordinates: validity_error
      disconnected_geometry: validity_error
      atom_overlap: validity_error
      outside_domain: domain_error
      missing_xtb: verifier_environment_error
      backend_failure: verifier_tool_error
      timeout: verifier_timeout

  - task_id: xtb_dipole_window_002
    version: 1
    object_type: small_molecule_3d
    difficulty: basic
    formal_track: true
    capability_tags: [open_generation, property_satisfaction, three_dimensional_geometry, xyz, xtb, dipole_moment]
    prompt: |
      Propose one neutral closed-shell small molecule as an XYZ geometry.

      The molecule must satisfy these requirements:
      - The XYZ must contain exactly one connected molecule with all hydrogens explicit.
      - Allowed elements: H, C, N, O, F, P, S, Cl, Br.
      - Atom count must be between 3 and 80 inclusive.
      - Heavy atom count must be between 1 and 40 inclusive.
      - Coordinates must be in Angstrom and suitable for local xTB optimization.
      - After GFN2-xTB optimization, have a molecular dipole moment between 1.5 and 4.0 Debye.

      Your final answer must appear exactly in this format:
      FINAL ANSWER:
      ```xyz
      <XYZ content>
      ```
    answer_schema: *xyz_answer_schema
    constraints:
      - type: window
        property: dipole_moment
        verifier_id: xtb_dipole_gfn2_v1
        min: 1.5
        max: 4.0
        sigma: 1.0
    scoring:
      aggregation: geometric_mean
    failure_policy: *xtb_task_failure_policy

  - task_id: xtb_gap_max_003
    version: 1
    object_type: small_molecule_3d
    difficulty: intermediate
    formal_track: true
    capability_tags: [open_generation, property_optimization, three_dimensional_geometry, xyz, xtb, homo_lumo_gap]
    prompt: |
      Propose one neutral closed-shell small molecule as an XYZ geometry.

      The molecule must satisfy these requirements:
      - The XYZ must contain exactly one connected molecule with all hydrogens explicit.
      - Allowed elements: H, C, N, O, F, P, S, Cl, Br.
      - Atom count must be between 3 and 80 inclusive.
      - Heavy atom count must be between 1 and 40 inclusive.
      - Coordinates must be in Angstrom and suitable for local xTB optimization.
      - Maximize the GFN2-xTB optimized-geometry HOMO-LUMO gap.

      Your final answer must appear exactly in this format:
      FINAL ANSWER:
      ```xyz
      <XYZ content>
      ```
    answer_schema: *xyz_answer_schema
    constraints:
      - type: maximize_bounded
        property: homo_lumo_gap
        verifier_id: xtb_gap_gfn2_v1
        lower: 0.0
        upper: 12.0
    scoring:
      aggregation: geometric_mean
    failure_policy: *xtb_task_failure_policy

  - task_id: xtb_gap_min_004
    version: 1
    object_type: small_molecule_3d
    difficulty: intermediate
    formal_track: true
    capability_tags: [open_generation, property_optimization, three_dimensional_geometry, xyz, xtb, homo_lumo_gap]
    prompt: |
      Propose one neutral closed-shell small molecule as an XYZ geometry.

      The molecule must satisfy these requirements:
      - The XYZ must contain exactly one connected molecule with all hydrogens explicit.
      - Allowed elements: H, C, N, O, F, P, S, Cl, Br.
      - Atom count must be between 3 and 80 inclusive.
      - Heavy atom count must be between 1 and 40 inclusive.
      - Coordinates must be in Angstrom and suitable for local xTB optimization.
      - Minimize the GFN2-xTB optimized-geometry HOMO-LUMO gap.

      Your final answer must appear exactly in this format:
      FINAL ANSWER:
      ```xyz
      <XYZ content>
      ```
    answer_schema: *xyz_answer_schema
    constraints:
      - type: minimize_bounded
        property: homo_lumo_gap
        verifier_id: xtb_gap_gfn2_v1
        lower: 0.0
        upper: 8.0
    scoring:
      aggregation: geometric_mean
    failure_policy: *xtb_task_failure_policy

  - task_id: xtb_dipole_max_005
    version: 1
    object_type: small_molecule_3d
    difficulty: intermediate
    formal_track: true
    capability_tags: [open_generation, property_optimization, three_dimensional_geometry, xyz, xtb, dipole_moment]
    prompt: |
      Propose one neutral closed-shell small molecule as an XYZ geometry.

      The molecule must satisfy these requirements:
      - The XYZ must contain exactly one connected molecule with all hydrogens explicit.
      - Allowed elements: H, C, N, O, F, P, S, Cl, Br.
      - Atom count must be between 3 and 80 inclusive.
      - Heavy atom count must be between 1 and 40 inclusive.
      - Coordinates must be in Angstrom and suitable for local xTB optimization.
      - Maximize the GFN2-xTB optimized-geometry molecular dipole moment.

      Your final answer must appear exactly in this format:
      FINAL ANSWER:
      ```xyz
      <XYZ content>
      ```
    answer_schema: *xyz_answer_schema
    constraints:
      - type: maximize_bounded
        property: dipole_moment
        verifier_id: xtb_dipole_gfn2_v1
        lower: 0.0
        upper: 10.0
    scoring:
      aggregation: geometric_mean
    failure_policy: *xtb_task_failure_policy

  - task_id: xtb_relaxation_energy_min_006
    version: 1
    object_type: small_molecule_3d
    difficulty: intermediate
    formal_track: true
    capability_tags: [open_generation, geometry_quality, property_optimization, three_dimensional_geometry, xyz, xtb, relaxation_energy]
    prompt: |
      Propose one neutral closed-shell small molecule as an XYZ geometry.

      The molecule must satisfy these requirements:
      - The XYZ must contain exactly one connected molecule with all hydrogens explicit.
      - Allowed elements: H, C, N, O, F, P, S, Cl, Br.
      - Atom count must be between 3 and 80 inclusive.
      - Heavy atom count must be between 1 and 40 inclusive.
      - Coordinates must be in Angstrom and already close to a low-energy xTB geometry.
      - Minimize the GFN2-xTB relaxation energy from the submitted geometry to the optimized geometry.

      Your final answer must appear exactly in this format:
      FINAL ANSWER:
      ```xyz
      <XYZ content>
      ```
    answer_schema: *xyz_answer_schema
    constraints:
      - type: minimize_bounded
        property: relaxation_energy
        verifier_id: xtb_relaxation_energy_gfn2_v1
        lower: 0.0
        upper: 0.5
    scoring:
      aggregation: geometric_mean
    failure_policy: *xtb_task_failure_policy

  - task_id: xtb_gap_dipole_window_007
    version: 1
    object_type: small_molecule_3d
    difficulty: intermediate
    formal_track: true
    capability_tags: [open_generation, property_satisfaction, multi_objective, three_dimensional_geometry, xyz, xtb, homo_lumo_gap, dipole_moment]
    prompt: |
      Propose one neutral closed-shell small molecule as an XYZ geometry.

      The molecule must satisfy these requirements:
      - The XYZ must contain exactly one connected molecule with all hydrogens explicit.
      - Allowed elements: H, C, N, O, F, P, S, Cl, Br.
      - Atom count must be between 3 and 80 inclusive.
      - Heavy atom count must be between 1 and 40 inclusive.
      - Coordinates must be in Angstrom and suitable for local xTB optimization.
      - After GFN2-xTB optimization, have a HOMO-LUMO gap between 3.0 and 5.0 eV.
      - After GFN2-xTB optimization, have a molecular dipole moment between 2.0 and 5.0 Debye.

      Your final answer must appear exactly in this format:
      FINAL ANSWER:
      ```xyz
      <XYZ content>
      ```
    answer_schema: *xyz_answer_schema
    constraints:
      - type: window
        property: homo_lumo_gap
        verifier_id: xtb_gap_gfn2_v1
        min: 3.0
        max: 5.0
        sigma: 0.75
      - type: window
        property: dipole_moment
        verifier_id: xtb_dipole_gfn2_v1
        min: 2.0
        max: 5.0
        sigma: 1.0
    scoring:
      aggregation: geometric_mean
    failure_policy: *xtb_task_failure_policy
````

## 优化题打分规则

max/min 优化题使用固定上下界线性评分。上下界是公开、固定、可复现的评分标尺，不从本次参赛答案动态估计。

```text
maximize_bounded:
score = clamp((value - lower) / (upper - lower), 0.0, 1.0)

minimize_bounded:
score = clamp((upper - value) / (upper - lower), 0.0, 1.0)
```

其中 `value` 是 xTB verifier 计算出的性质值。候选结构必须先通过 parse、validity、domain、xTB optimization 等 gate；任何 gate 失败都返回 error/0 分，不进入线性评分。

首版优化题标尺：

| 题目 | 性质 | 方向 | lower | upper | 单位 |
| --- | --- | --- | ---: | ---: | --- |
| `xtb_gap_max_003` | `homo_lumo_gap` | maximize | 0.0 | 12.0 | eV |
| `xtb_gap_min_004` | `homo_lumo_gap` | minimize | 0.0 | 8.0 | eV |
| `xtb_dipole_max_005` | `dipole_moment` | maximize | 0.0 | 10.0 | Debye |
| `xtb_relaxation_energy_min_006` | `relaxation_energy` | minimize | 0.0 | 0.5 | eV |

支持的优化方向：

- `homo_lumo_gap`：最大化和最小化都保留。高 gap 与稳定/绝缘性质相关，低 gap 与 donor-acceptor、窄 gap 分子和有机电子材料设计相关。
- `dipole_moment`：首版只做最大化。最大偶极矩与介电材料、极性分子设计有明确研究动机；最小化更像对称性控制题，暂不放入首版。
- `relaxation_energy`：只做最小化。最大化 relaxation energy 会奖励坏几何或高应变输入，不符合可靠化学生成目标。

## 分数阈值依据

阈值来自三类证据：公开 QM9 分布、真实 inverse-design 论文结果、构象/优化能量文献尺度。QM9 分布使用 DeepChem 公开 `qm9.csv` 重新计算，样本数 133,885；`gap` 字段按 Hartree 转 eV，`mu` 字段按 Debye 使用。

### HOMO-LUMO Gap

QM9 gap 分布如下：

| 统计量 | gap eV |
| --- | ---: |
| min | 0.67 |
| p1 | 4.06 |
| p10 | 5.20 |
| p25 | 5.89 |
| median | 6.79 |
| p75 | 7.84 |
| p90 | 8.60 |
| p95 | 8.89 |
| p99 | 9.36 |
| p99.9 | 10.19 |
| max | 16.93 |

`xtb_gap_window_001` 使用 4.0 到 6.0 eV，是一个偏低到中等 gap 的窗口：4.0 eV 约接近 QM9 p1，6.0 eV 约略高于 p25。这能测试模型能否命中非极端但明确偏低的 gap 区间。

`xtb_gap_dipole_window_007` 使用 3.0 到 5.0 eV，是更偏低 gap 的 multi-objective 窗口。QM9 中 5.0 eV 约低于 p10，说明它不是普通中位数目标，而是有意要求模型生成更窄 gap 的结构。

`xtb_gap_max_003` 使用 `upper: 12.0 eV`。这个值高于 QM9 p99.9 的 10.19 eV，也高于 diamondoid inverse-design 论文中 adamantane 衍生物高 gap 搜索结果 10.63 eV，但低于 QM9 极端最大值 16.93 eV。因此 12.0 eV 是“极高但不是纯粹不可达”的满分标尺。如果设为 10.0 eV，QM9 中已有 249 个分子达到或超过，且 diamondoid 高 gap 候选会接近饱和，区分度偏弱；如果设到 14.0 eV，首版任务会过度奖励极端异常结构。

`xtb_gap_min_004` 使用 `upper: 8.0 eV`。QM9 中 gap 小于等于 8.0 eV 的样本约 77.7%，大于等于 8.0 eV 的样本约 22.3%。这使 8.0 eV 成为区分普通/偏低 gap 与高 gap 小分子的合理归零上界。`lower: 0.0 eV` 是物理下限式锚点；真实小分子不要求达到 0 eV。diamondoid 论文中的低 gap 候选 2.42 eV 在该标尺下可得约 0.70 分，属于高分但不满分。

### Dipole Moment

QM9 dipole moment 分布如下：

| 统计量 | dipole Debye |
| --- | ---: |
| min | 0.00 |
| p10 | 1.04 |
| p25 | 1.59 |
| median | 2.50 |
| p75 | 3.64 |
| p90 | 4.66 |
| p95 | 5.30 |
| p99 | 6.74 |
| p99.5 | 7.53 |
| p99.9 | 13.46 |
| max | 29.56 |

`xtb_dipole_window_002` 使用 1.5 到 4.0 Debye，约覆盖 QM9 p25 到 p80 量级，是常见但非零极性的窗口。这个窗口适合首批 basic 题，因为不会把任务变成极端偶极搜索。

`xtb_gap_dipole_window_007` 的 dipole 窗口是 2.0 到 5.0 Debye，约从中位数附近推到 p90 以上，适合作为多目标题中的极性约束。

`xtb_dipole_max_005` 使用 `upper: 10.0 Debye`。QM9 中 dipole 大于等于 10.0 Debye 的样本约 0.21%，位于 p99.5 与 p99.9 之间，代表强偶极极端区间。若设为 5.0 Debye，QM9 中约 7.0% 分子已经达到或超过，最大化题容易饱和；若设为 12.0 Debye，只有约 0.14% 样本达到或超过，对首版模型评测过苛刻。10.0 Debye 是高挑战但仍有数据支撑的满分标尺。

dipole 最大化的研究意义来自有机介电材料设计。Hiener/Hutchison 的 GA 研究明确把 dipole moment 与 polarizability 作为优化目标，并使用 GFN2-xTB 计算候选性质。

### Relaxation Energy

`relaxation_energy` 用于衡量模型直接输出的 XYZ 是否已接近低能几何。它不是绝对总能量，因为绝对总能量强依赖元素组成和原子数；它也不是“越大越好”的性质。

GEOM/CREST 文献给出更接近构象合理性的能量尺度：

- CREST 默认 conformer energy window 为 6.0 kcal/mol。
- 只有约 2.5 kcal/mol 以下的 conformer 在室温有显著 population。
- GEOM 中 CREST geometry 经 DFT 优化平均释放能量为 5.74 kcal/mol，约 0.25 eV。

换算关系：

```text
0.25 eV ≈ 5.8 kcal/mol
0.50 eV ≈ 11.5 kcal/mol
1.00 eV ≈ 23.1 kcal/mol
2.00 eV ≈ 46.1 kcal/mol
```

因此首版将 `xtb_relaxation_energy_min_006` 的 `upper` 从旧设计的 2.0 eV 收紧到 0.5 eV。0.5 eV 约为 11.5 kcal/mol，仍比 CREST 默认 conformer window 宽，但比 2.0 eV 更符合低能构象文献尺度。该设置能避免把明显粗糙或高应变的 XYZ 几何评为可接受。

## Window 题评分

窗口题使用现有 `window` 规则：

```text
if min <= value <= max:
    score = 1.0
else:
    distance = min - value if value < min else value - max
    score = clamp(exp(-distance / sigma), 0.0, 1.0)
```

`sigma` 只作为窗口外软惩罚宽度，不写入模型提示词。多约束题继续使用 `geometric_mean` 聚合。

## Failure Policy

verifier 返回确定性的 failure row：

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
  timeout: verifier_timeout
```

映射规则：

- 缺失或 malformed fenced XYZ block 是 extraction-level `parse_error`。
- atom-count 不匹配、atom line malformed、坐标非有限数是 verifier-level `parse_error`。
- 原子重叠、断开的分子几何是 `validity_error`。
- 元素不允许、原子数超域、坐标超域、charge/spin 不支持是 `domain_error`。
- 找不到 xTB executable 是 `verifier_environment_error`。
- xTB 非零退出、优化未收敛、输出缺失目标性质是 `verifier_tool_error`。
- 超时是 `verifier_timeout`。

错误行应保留 `raw_answer` 和 `extracted_answer`，方便审计。

## 测试范围

首版实现时增加五层测试。

1. Answer extraction tests:
   - `final_answer_block` 支持 `value_type: xyz`。
   - 多个 `FINAL ANSWER:` block 时使用最后一个。
   - 缺失 fenced block 返回 `parse_error`。
   - 空 XYZ block 返回 `parse_error`。
   - 已有 `candidates` 的结构化 answer 仍绕过 extraction。

2. Task and verifier spec tests:
   - `tasks/xtb_xyz/tasks.yaml` 可 YAML-load。
   - 每个任务使用 `answer_schema.format: final_answer_block`。
   - 每个 xTB constraint 都有 `verifier_id`。
   - 每个引用的 verifier spec 都存在。
   - 每个 verifier spec 都有非空 `verification_script`。
   - prompt 暴露所有硬 domain gate，但不暴露 verifier ID、脚本路径、`sigma` 或聚合细节。

3. Backend unit tests with fake xTB runner:
   - 合法 XYZ 能解析为 atoms 和 coordinates。
   - atom-count mismatch 返回 `parse_error`。
   - disallowed element 返回 `domain_error`。
   - atom overlap 返回 `validity_error`。
   - disconnected geometry 返回 `validity_error`。
   - fake gap、dipole、energy 输出能解析为 properties。
   - `window`、`maximize_bounded`、`minimize_bounded` 使用现有 scoring 规则。
   - missing executable、nonzero exit、timeout、missing property 映射到预期 failure type。

4. Script runner tests:
   - 每个 property script 对 mismatched `property_name` 返回 `verifier_spec_error`。
   - 每个 property script 调用 shared backend 并返回标准 result shape。
   - gap + dipole 多约束任务能聚合两个 verifier 结果。

5. Optional environment smoke test:
   - `scripts/check_xtb_env.py` 报告检测到的 `xtb --version`。
   - 如果安装了 xTB，用 water XYZ 跑一次优化，并解析 gap、dipole、total energy、optimized energy。
   - CI 不要求安装 xTB；smoke test 应手动运行，或在缺失 xTB 时 skip。

## 实现注意事项

首版 xTB backend 保持独立，不走 AtomisticSkills MCP。xTB-XYZ 是本地小分子量子化学 verifier，直接调用本地 `xtb` executable 更简单、可复现，也更贴近后续 formal benchmark 运行方式。

实现中不要从 SMILES 生成 3D 坐标。sample answers 可以手写或来自已知小分子，但 verifier 的输入契约始终是模型最终输出的 XYZ block。

xTB 输出解析应优先使用稳定机器可读文件；如果当前 xTB 版本只能稳定解析文本输出，则 regex 必须小而明确，并用 fixture output 覆盖。

这些阈值是首版固定评分标尺。正式发布前可以用固定校准集做一次版本化调整；发布后同一 benchmark 版本内不得根据参赛模型结果动态调整上下界。
