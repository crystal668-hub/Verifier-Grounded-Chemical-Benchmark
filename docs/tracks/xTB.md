# xTB 题目设计与实现同步

更新日期：2026-07-21

## 1. 设计来源

xTB 题目来自以下本地设计与计划文档：

- `docs/superpowers/specs/2026-06-05-xtb-direct-xyz-verifier-design.md`：定义 direct-XYZ 题型，要求模型直接输出分子三维坐标，而不是由 verifier 从 SMILES 生成构象。
- `docs/superpowers/plans/2026-06-08-xtb-direct-xyz-implementation.md`：实现 `xtb_xyz` task pack、XYZ answer extraction、property-level xTB verifier scripts 和 shared local CLI backend。
- `docs/superpowers/plans/2026-06-09-xtb-xyz-quality-gate-redesign.md`：将 `relaxation_energy` 重新定位为所有 xTB direct-XYZ 题目的通用几何质量门。
- `~/.agents/skills/xtb-cli-verifier/SKILL.md`：记录当前 xTB CLI verifier 的运行、解析和 failure mapping 规则。

当前真实实现已按如下边界落地：

```text
task constraint/property -> verifier_id -> verification_script -> shared local xTB CLI backend
```

## 2. 题目类型

当前 xTB 题目是 `small_molecule_3d` 的 open-generation property-satisfaction / property-optimization 任务。模型需要直接提交一个 fenced XYZ block：

````text
FINAL ANSWER:
```xyz
<XYZ content>
```
````

统一设计约束：

- 只接受一个 neutral closed-shell small molecule。
- 输入是 explicit-hydrogen molecular XYZ。
- 不从 SMILES 生成构象；提交的 3D 坐标本身就是答案的一部分。
- allowed elements：H、C、N、O、F、P、S、Cl、Br。
- base atom count：3 到 80。
- base heavy atom count：1 到 40。
- 候选必须是单连通分子，坐标单位为 Angstrom。
- 每道题还叠加 task-level structural domain，例如最小 heavy atom count、最小 carbon/hetero atom count、formula denylist 和 heavy-element diversity。

这使 xTB track 与 RDKit track 有本质区别：RDKit 只验证 2D/topological SMILES descriptor；xTB track 还评价模型是否能提交一个几何上合理的 3D 分子结构。

## 3. 当前题目数量

当前 task pack：`tasks/xtb_xyz/`

- 题目数量：18。
- verifier specs：13。
- 所有题目均为 `formal_track: true`。
- 原有 13 题包含 `relaxation_energy` quality gate；014-018 严格按专家题面约束，不额外引入该 gate。

| task_id | 主目标 | 质量门 |
|---|---|---|
| `xtb_gap_window_001` | HOMO-LUMO gap window `[3.5, 5.5]` eV | relaxation energy <= 0.35 eV |
| `xtb_dipole_window_002` | dipole moment window `[3.0, 5.5]` Debye | relaxation energy <= 0.35 eV |
| `xtb_gap_max_003` | maximize HOMO-LUMO gap, `T=9.749630028571`, `B=1.389963462368` eV | relaxation energy <= 0.35 eV |
| `xtb_gap_min_004` | minimize HOMO-LUMO gap, `T=1.389963462368`, `B=9.749630028571` eV | relaxation energy <= 0.35 eV |
| `xtb_dipole_max_005` | maximize dipole moment, `T=13.374`, `B=3.320` Debye | relaxation energy <= 0.35 eV |
| `xtb_low_gap_high_dipole_opt_006` | minimize gap + maximize dipole | relaxation energy <= 0.35 eV |
| `xtb_gap_dipole_window_007` | gap window `[2.5, 4.2]` eV + dipole window `[3.5, 6.0]` Debye | relaxation energy <= 0.35 eV |
| `xtb_lumo_min_008` | minimize LUMO energy, `T=-10.6883`, `B=-1.94` eV | relaxation energy <= 0.35 eV |
| `xtb_polarizability_dipole_opt_009` | maximize polarizability per heavy atom, `T=9.3430346`, `B=6.4845643`, plus dipole window `[3.0, 8.0]` D | relaxation energy <= 0.35 eV |
| `xtb_solvation_selectivity_alpb_010` | maximize ALPB water-over-hexane selectivity, `T=0.3953163242456749`, `B=-0.17228322475548233` eV | relaxation energy <= 0.35 eV |
| `xtb_electrophilicity_max_011` | maximize global electrophilicity, `T=3.1359`, `B=0.4862` eV | relaxation energy <= 0.35 eV |
| `xtb_fukui_carbon_site_012` | maximize carbon `f+` (`T=0.276`, `B=0.076`) and contrast (`T=0.094`, `B=0`) | relaxation energy <= 0.35 eV |
| `xtb_hessian_thermo_stability_013` | maximize 298 K entropy per heavy atom, `T=76.094775`, `B=40.59789`, with zero imaginary frequencies | relaxation energy <= 0.35 eV |
| `xtb_formula_dipole_min_014` | minimize optimized dipole for exact `C12H16N3O8`, neutral doublet, `T=3.042`, `B=9.328` D | none |
| `xtb_two_fluorine_gap_min_015` | minimize optimized gap with exactly 2 F and at most 10 C, `T=1.242666887976`, `B=12.358052453139` eV | none |
| `xtb_c10_f2_gap_min_016` | same `C10F2` gap profile as task 015 | none |
| `xtb_roy_singlepoint_energy_min_017` | minimize submitted-geometry single-point energy for graph-valid ROY; target/anchor dossier pending | none |
| `xtb_ritonavir_optimized_energy_min_018` | minimize optimized energy while retaining Ritonavir graph and four stereocenters; target/anchor dossier pending | none |

## 4. 涉及的可验证化学性质

| 性质 | 当前用途 | 单位 | 计算方式 |
|---|---|---:|---|
| `homo_lumo_gap` | 主评分目标 | eV | 对提交的 XYZ 做 GFN2-xTB optimization 后，从 xTB 输出解析 HOMO-LUMO gap。 |
| `dipole_moment` | 主评分目标 | Debye | 对提交的 XYZ 做 GFN2-xTB optimization 后，从 xTB molecular dipole 输出解析总偶极矩。 |
| `lumo_energy` | 主评分目标 | eV | 对提交的 XYZ 做 GFN2-xTB optimization 后，从 orbital table 解析 LUMO energy。 |
| `polarizability_per_heavy_atom` | 主评分目标 | atomic units per heavy atom | 对提交的 XYZ 做 GFN2-xTB optimization 后，解析 molecular polarizability 并按 heavy atom count 归一。 |
| `alpb_water_hexane_selectivity` | 主评分目标 | eV | 在优化几何上分别运行 ALPB water 和 hexane solvent calculation，计算 `Gsolv(hexane) - Gsolv(water)`。 |
| `global_electrophilicity` | 主评分目标 | eV | 优化几何后运行 xTB vertical electrophilicity workflow，解析 global electrophilicity。 |
| `max_f_plus_on_carbon` | 主评分目标 | dimensionless | 优化几何后运行 vertical Fukui workflow，解析提交 XYZ atom order 中 carbon atoms 的最大 `f+`。 |
| `f_plus_contrast` | 辅助评分目标 | dimensionless | 从同一 Fukui table 计算最强 carbon `f+` 与其它响应的区分度。 |
| `entropy_298_per_heavy_atom` | 主评分目标 | J mol-1 K-1 per heavy atom | 对优化几何运行 hessian thermochemistry，解析 298.15 K entropy 并按 heavy atom count 归一。 |
| `imaginary_frequency_count` | stability gate | count | 从 hessian thermochemistry 输出统计 imaginary frequencies；正式题要求为 0。 |
| `relaxation_energy` | 几何质量门 | eV | 分别运行 input single-point 与 optimized calculation，计算输入几何到优化几何的能量降低量。 |
| `total_energy` | ROY / Ritonavir 构象主评分目标 | Hartree | ROY 使用提交几何 single-point；Ritonavir 优化后取 total energy，并复查图与立体化学。 |

`relaxation_energy` 不是独立化学优化目标，而是 direct-XYZ 质量乘子。它用于惩罚“坐标很粗糙，但 xTB 优化后性质看起来合格”的答案。

## 5. 对应 verifier

当前 xTB verifier 都通过 `verifiers/xtb/cli.py` 进入共享后端 `verifiers/xtb/backend.py`。

| verifier_id | property_name | verification_script | 后端 |
|---|---|---|---|
| `xtb_gap_gfn2_v1` | `homo_lumo_gap` | `verifiers/xtb/xtb_gap.py` | local `xtb` CLI, GFN2-xTB |
| `xtb_dipole_gfn2_v1` | `dipole_moment` | `verifiers/xtb/xtb_dipole.py` | local `xtb` CLI, GFN2-xTB |
| `xtb_relaxation_energy_gfn2_v1` | `relaxation_energy` | `verifiers/xtb/xtb_relaxation_energy.py` | local `xtb` CLI, GFN2-xTB |
| `xtb_lumo_gfn2_v1` | `lumo_energy` | `verifiers/xtb/xtb_lumo.py` | local `xtb` CLI, GFN2-xTB |
| `xtb_polarizability_gfn2_v1` | `polarizability_per_heavy_atom` | `verifiers/xtb/xtb_polarizability.py` | local `xtb` CLI, GFN2-xTB |
| `xtb_solvation_selectivity_alpb_v1` | `alpb_water_hexane_selectivity` | `verifiers/xtb/xtb_solvation_selectivity.py` | local `xtb` CLI, GFN2-xTB with ALPB water/hexane runs |
| `xtb_electrophilicity_gfn1_ipea_v1` | `global_electrophilicity` | `verifiers/xtb/xtb_electrophilicity.py` | local `xtb` CLI, optimized geometry plus GFN1-xTB/IPEA property run |
| `xtb_fukui_gfn1_v1` | `max_f_plus_on_carbon` | `verifiers/xtb/xtb_fukui.py` | local `xtb` CLI, optimized geometry plus GFN1-xTB Fukui run |
| `xtb_hessian_thermo_gfn2_v1` | `entropy_298_per_heavy_atom` | `verifiers/xtb/xtb_hessian_thermo.py` | local `xtb` CLI, GFN2-xTB hessian thermochemistry |
| `xtb_dipole_doublet_gfn2_v1` | `dipole_moment` | `verifiers/xtb/xtb_dipole.py` | local `xtb` CLI, neutral doublet GFN2-xTB optimization |
| `xtb_gap_charged_closed_shell_gfn2_v1` | `homo_lumo_gap` | `verifiers/xtb/xtb_gap.py` | local `xtb` CLI, comment-declared charge and closed-shell GFN2-xTB optimization |
| `xtb_total_energy_roy_singlepoint_gfn2_v1` | `total_energy` | `verifiers/xtb/xtb_total_energy.py` | local `xtb` CLI, graph-gated submitted-geometry single-point |
| `xtb_total_energy_ritonavir_optimized_gfn2_v1` | `total_energy` | `verifiers/xtb/xtb_total_energy.py` | local `xtb` CLI, pre/post identity-gated optimization |

真实执行流程：

1. `benchmark/answer_extraction.py` 从 raw response 抽取 fenced `xyz` block。
2. `benchmark/evaluate.py` 按 task constraint 的 `verifier_id` 找到 spec。
3. `benchmark/verifier_scripts.py` 构造 JSON payload 并子进程执行 `verification_script`。
4. xTB backend 解析 XYZ、做元素/坐标/连通性/domain gate、写入临时 `candidate.xyz`。
5. `XTBRunner` 调用本地 `xtb` executable：
   - legacy gap / dipole：`xtb candidate.xyz --gfn 2 --chrg 0 --uhf 0 --opt`
   - expert dipole：固定 neutral doublet (`--chrg 0 --uhf 1`) 后优化。
   - expert gap：从严格的 XYZ comment `charge=<integer>` 解析 charge，固定 `--uhf 0` 并验证电子奇偶性。
   - ROY energy：验证分子图后对提交几何做 single-point，不优化。
   - Ritonavir energy：优化前后验证分子图和四个指定立体中心。
   - relaxation：一次 single-point 加一次 `--opt`
   - LUMO / polarizability：GFN2 optimization 后从 property printout 解析。
   - ALPB selectivity：优化几何后分别运行 water 和 hexane ALPB solvent calculation。
   - electrophilicity / Fukui：优化几何后运行对应 vertical property command。
   - hessian thermo：优化几何后运行 hessian thermochemistry。
6. backend 解析 total energy、HOMO-LUMO gap、dipole moment 和 optimization convergence 文本，并返回标准 result JSON。

缺失 `xtb` 可执行文件映射为 `verifier_environment_error`，不视为候选分子本身错误。

## 6. 数据角色与公开边界

xTB track 当前有三类数据，角色不同，不能混用：

1. `tasks/xtb_xyz/sample_answers.jsonl` 是 public showcase examples。它只展示 answer schema、fenced XYZ 格式和 pipeline 跑通方式，数量少，不覆盖全部 18 个 formal tasks，也不代表 benchmark 分布或校准集分布。
2. calibration corpora 是维护者私有校准数据，用于阈值、正负控制和可靠性检查。它不是 participant examples，不属于公开 benchmark artifact，也不应作为用户可参考样例发布。
3. public tests 只验证 schema、format、routing 和 pipeline contract。真实校准应由 private calibration job 或私有 artifact 处理，避免把校准答案误发布为公开参考答案。

发行包必须包含 formal task definitions、verifier specs 和 public showcase samples；不得包含 xTB private calibration answers 或 calibration manifest。

## 7. 打分计算方式

xTB 主性质沿用 RDKit backend 的统一 `score_constraint`。

### 7.1 Window constraint

性质落在 `[min, max]` 内得 1.0。落在窗口外时按距离指数衰减：

```text
score = exp(-distance_to_window / sigma)
```

### 7.2 Maximize bounded

```text
score = clamp((value - lower) / (upper - lower), 0.0, 1.0)
```

### 7.3 Minimize bounded

```text
score = clamp((upper - value) / (upper - lower), 0.0, 1.0)
```

### 7.4 Relaxation energy

当前实现定义：

```text
relaxation_energy_eV = max(0.0, (E_input_singlepoint_Eh - E_optimized_Eh) * 27.211386245988)
```

原有 001-013 tasks 使用同一个质量门：

```yaml
type: minimize_bounded
property: relaxation_energy
role: quality_gate
lower: 0.0
upper: 0.35
```

因此：

```text
geometry_quality_score = clamp((0.35 - relaxation_energy_eV) / 0.35, 0.0, 1.0)
```

### 7.5 多目标聚合

runner 将主性质和质量门分开聚合：

```text
property_score = geometric_mean(main_constraint_scores)
geometry_quality_score = min(quality_gate_scores)
final_score = property_score * geometry_quality_score
```

对 001-013，这意味着几何很差的 XYZ 可以把最终分数乘到 0，即使优化后 gap 或 dipole 达标。专家题 014-018 只有各自经校准的主性质约束，不使用该乘子。

## 8. 实际化学意义

xTB track 的核心不是简单计算量子性质，而是评估模型能否直接生成一个可被低成本量子化学工具验证的三维分子候选：

- HOMO-LUMO gap 是光电、有机电子、反应性和稳定性 proxy。窗口、最大化和最小化题分别测试模型是否能定向提出中等 gap、高 gap 或低 gap 分子。
- LUMO energy 是 electron acceptor / reduction tendency proxy，低 LUMO 题测试模型是否能提出更强受电子结构。
- Dipole moment 影响 solvation、crystal packing、dielectric response、binding 和极性材料性质。窗口和最大化题测试模型能否通过结构与官能团布置控制分子极性。
- Polarizability 与 dipole 多目标题模拟极化响应和分子极性的共同优化。
- ALPB water-over-hexane selectivity 让模型针对隐式溶剂稳定化差异提出结构，而不是只优化真空几何性质。
- Global electrophilicity 和 carbon-site Fukui response 把反应性 proxy 纳入 direct-XYZ track。
- Hessian thermochemistry task 同时要求零 imaginary frequencies 和较高 entropy，强调稳定局部极小点和热化学输出的可解析性。
- ROY 与 Ritonavir 题把固定分子内的 conformer energy optimization 纳入 track；绝对 total energy 不跨分子或跨题比较。
- Low-gap + high-dipole 多目标题模拟更接近材料/分子设计的 trade-off，而不是单一性质优化。
- Relaxation energy 使 direct-XYZ 题真正评价 submitted geometry。xTB optimization 只用于标准化测量；如果输入坐标离局部低能结构太远，模型应被扣分。
- 结构域约束和 formula denylist 防止 water、methane、HCN、benzene 等简单/common molecules 在优化题中成为无意义高分答案。

GFN2-xTB 的计算成本低于 DFT，适合 benchmark runner 中重复调用；但文档明确当前性质是 fixed xTB surrogate，不等同实验 optical gap、实验偶极矩或高精度 ab initio 结果。

## 9. 文献与资料支撑

- xTB 官方文档说明该程序面向 GFNn-xTB semiempirical quantum mechanical methods，并支持几何输入、命令行运行与性质输出：https://xtb-docs.readthedocs.io/
- xTB properties 文档展示 HOMO-LUMO gap、Fermi-level 和 molecular dipole moment 输出，其中 dipole 总量以 Debye 给出：https://xtb-docs.readthedocs.io/en/latest/properties.html
- Bannwarth, Ehlert and Grimme, "GFN2-xTB-An Accurate and Broadly Parametrized Self-Consistent Tight-Binding Quantum Chemical Method", JCTC 2019；支撑使用 GFN2-xTB 作为快速结构/相互作用/性质计算方法：https://pubmed.ncbi.nlm.nih.gov/30741547/
- QM9 数据集包含小有机分子的 quantum chemistry structures and properties，包括 dipole moment、HOMO、LUMO 和 gap 等性质，是 3D 量子性质 benchmark 的经典依据：https://www.nature.com/articles/sdata201422
- GEOM 数据集包含 45 万余分子、3700 万构象，说明 3D conformer + energy/property 是分子生成和性质预测中的重要对象：https://www.nature.com/articles/s41597-022-01288-4
- Flam-Shepherd and Aspuru-Guzik 证明语言模型可以直接用 XYZ、CIF、PDB 等文件格式生成 3D 分子、材料和 binding sites，支撑 direct-XYZ answer schema 的可行性：https://arxiv.org/abs/2305.05708
- TARTARUS inverse molecular design benchmark 使用 GFN2-xTB 得到 HOMO/LUMO、HOMO-LUMO gap 和 molecular dipole moment，支撑把这些性质作为 inverse design 任务目标：https://papers.neurips.cc/paper_files/paper/2023/file/09f8b2469a3d1089a7c60d9ef1983271-Paper-Datasets_and_Benchmarks.pdf
- Diamondoid inverse-design 研究展示 HOMO-LUMO gap 可被系统调控，adamantane derivatives gap 范围可从 2.42 到 10.63 eV：https://pubs.acs.org/doi/abs/10.1021/acs.jctc.6b01074
- Hiener and Hutchison 使用 genetic algorithm 与 approximate density functional tight-binding 搜索同时具有大 polarizability 和大 dipole moment 的 conjugated hexamers，支撑 dipole/polarizability 优化的材料设计意义：https://pubs.acs.org/doi/10.1021/acs.jpca.2c01266
