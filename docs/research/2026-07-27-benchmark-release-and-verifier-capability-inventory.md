# v0.4.2 Benchmark 发行版与 Verifier 能力清单

更新日期：2026-07-28

本文把两个范围分开记录：

1. `v0.4.2` 发行版实际包含的正式 benchmark tracks 和题目。
2. 当前仓库源码已经实现的 verifier backend 能力，包括尚未注册为正式 track 的后端。

因此，“源码中可以计算”不等于“已经进入正式发行版”。

## 1. 核对口径

- 发行版以 `releases/v0.4.2/manifest.json`、`task-inventory.json` 和
  `scoring-profiles.json` 为准。
- `v0.4.2` 的 canonical source commit 是 `c3cad26`，三个发行 track 的
  task pack version 都是 `0.4.2`，统一使用 `linear_goal_v2`。
- 正式 track 以 `src/verifier_grounded_benchmark/task/registry.py` 中的
  builtin registry 和发行版 inventory 中的 `scoring_status: formal` 为准。
- backend 能力以
  `src/verifier_grounded_benchmark/evaluation/open_generation/verifiers/`
  下的 backend、property-level script 和对应 capability 文档为准。

## 2. v0.4.2 正式发行内容

发行版共有 **36 道题**。这里按 task ID 计数；例如
`property_calc_crystal_phase_002` 虽然要求回答三个属性，仍计为一道题。

```text
track                    题目数  输入/题型                                      主要考察方向
rdkit                    14      单组分 SMILES；open-generation                  2D 描述符、多目标优化、构象代理、分子相似性
xtb                      20      显式氢 XYZ（19 道）或 SMILES-to-conformer（1 道）  3D 几何、GFN-xTB 电子结构/反应性/热化学、构象和身份约束
property_calculation     2       完整 CIF；fixed-input property calculation     分子晶体自由能差、势能差和压力相判定
合计                     36
```

三个 track 都是正式 track，task pack 版本均为 `0.4.2`。发行 manifest 中的
OpenClaw 数据集计数也分别是 `14`、`20` 和 `2`。

### 2.1 RDKit：14 道

14 道题全部是单组分小分子 SMILES 的 open-generation 题。能力方向可以分成：

- **单目标描述符约束（001-007）**：QED 最大化、SA score 最小化、LogP
  窗口、TPSA 窗口、HBA 窗口、HBD 窗口和 fraction Csp3 最大化。
- **多目标约束（008-010）**：QED + SA、LogP + TPSA、HBA + HBD。
- **目标距离和硬约束（011-012）**：LogP 靠近 3；以及 SA 硬门下的
  LogP 目标。
- **构象/结构协议（013）**：固定六碳链、ETKDGv3 + UFF 有限构象工作流，
  最大化端到端距离。
- **分子相似性（014）**：在 LogP、SA、QED 硬门下最大化候选与 caffeine
  reference 的 Morgan fingerprint Tanimoto 相似度。

源码标签中的 difficulty 分布是 `simple: 11`、`expert: 3`；这里的
“001-014”分组描述的是考察方向，不把 task 的 difficulty 标签重新解释为
另一套等级。

### 2.2 xTB：20 道

20 道题全部是 open-generation。001-019 提交显式氢 XYZ；020 提交 SMILES，
由 verifier 生成初始几何并运行 CREST/xTB。difficulty 分布为
`basic: 2`、`intermediate: 6`、`advanced: 7`、`expert: 5`。

主要方向如下：

- **电子结构与偶极（001-007）**：HOMO-LUMO gap、dipole 的窗口/最大化/最小化，
  以及 gap + dipole 多目标组合。
- **受体、极化和溶剂化（008-010）**：LUMO energy、按重原子归一化的
  polarizability、dipole，以及 ALPB water/hexane solvation selectivity。
- **反应性和热化学（011-013）**：global electrophilicity、碳位点的 Fukui
  `f+` 响应（最大碳位点值和 contrast），以及 Hessian 计算得到的
  298 K entropy per heavy atom；任务 013 还要求零 imaginary frequency。
- **固定组成/电子态约束（014-016、019）**：中性 doublet、带电闭壳层、
  `C10F2` 组成，以及各元素计数为奇数等结构域约束。
- **分子身份和能量（017-018、020）**：ROY submitted-geometry single-point
  energy、Ritonavir 优化后 total energy，以及保持 pyrene 三取代图身份的
  CREST ensemble + xTB total energy。

主目标性质在 task constraints 中的覆盖次数为：HOMO-LUMO gap `8`、dipole
`6`、total energy `3`，LUMO、polarizability、ALPB selectivity、global
electrophilicity、Fukui 两个指标和 entropy 各 `1`。另外，001-013 都有
`relaxation_energy` 几何质量 gate，共 `13` 次；它不是独立的题目数。

### 2.3 Property calculation：2 道

这是固定输入、模型报告数值的正式 track，不运行 RDKit、xTB 或其他性质
verifier：

- `property_calc_free_energy_001`：给定两套分子晶体 CIF，报告 300 K 的
  absolute free-energy difference，单位 `kJ/mol`。
- `property_calc_crystal_phase_002`：给定 alpha/beta 两套晶体 CIF，报告
  absolute potential-energy difference，单位 `eV`，并判断 ambient-pressure
  phase 和 high-pressure phase。

该 track 使用 numeric-gold 和 exact-string 比较组；它评估模型能否根据题面
固定结构报告正确结果，不应被计入“已实现的性质计算 backend”数量。

## 3. 已实现的正式发行 backend

### 3.1 RDKit descriptor 与 force field

这是正式 `rdkit` track 的共享计算层：

- **工具**：RDKit `2026.3.2`；SA score 使用 RDKit Contrib scorer。
- **2D/拓扑性质**：QED、Crippen LogP、TPSA、分子量（MW）、H-bond donor
  count（HBD）、H-bond acceptor count（HBA）、fraction Csp3、SA score。
- **相似性**：Morgan bit fingerprint（radius `2`、`2048` bit、不含 chirality、
  使用 bond types）与冻结 caffeine reference 的 Tanimoto 相似度。
- **3D/经典力场**：RDKit ETKDG 构象生成、MMFF94/MMFF94s/UFF 参数化和优化；
  正式任务 013 固定使用 ETKDGv3 + UFF，并计算六碳链端到端距离。共享
  force-field backend 还会产生构象数、收敛比例、能量范围和最小非键距离等
  中间证据。

`rdkit_descriptors/backend.py` 的通用 descriptor 表还注册了
`rotatable_bonds` 和 `ring_count`，但它们当前没有对应的正式 task/property
profile。`mw` 虽可由 backend 和 script 计算，也不是当前 14 道题的主目标。

### 3.2 xTB 与 CREST

- **工具/版本**：本地 `xtb` executable，正式 spec 固定 xTB `6.7.1`；主流程
  以 GFN2-xTB 为主。global electrophilicity 使用 GFN1-xTB/IPEA 的
  `--vomega`，Fukui 使用 GFN1-xTB 的 `--vfukui`。
- **几何和电子态**：XYZ 解析、连通性/原子距离/显式氢/组成域检查，charge、
  UHF 和电子数奇偶校验；部分题目还检查 graph、stereochemistry 和优化后
  identity。
- **可以计算的性质**：
  - `homo_lumo_gap`（eV）和 `lumo_energy`（eV）；
  - `dipole_moment`（Debye）；
  - `total_energy`（Hartree）和输入几何到优化几何的
    `relaxation_energy`（eV）；
  - `polarizability_per_heavy_atom`（atomic units per heavy atom）；
  - `alpb_water_hexane_selectivity`（eV），即
    `Gsolv(hexane) - Gsolv(water)`；
  - `global_electrophilicity`（eV）；
  - `max_f_plus_on_carbon` 与 `f_plus_contrast`（dimensionless），并保留最大
    碳位点的 atom index/symbol；
  - `entropy_298_per_heavy_atom`（J mol-1 K-1 per heavy atom）和
    `imaginary_frequency_count`。
- **CREST 扩展**：任务 020 使用 CREST `2.12`、GFN2-xTB 和 xTB `6.7.1`，
  对满足 pyrene 三取代 identity 的候选做 `-mquick` conformer search，再对
  最低 ensemble member 做 xTB single-point energy。

这里的 gap、轨道能级、偶极、solvation、反应性和 total energy 都是冻结方法
下的 surrogate/protocol property；total energy 只应在相同组成、charge、
电子态和计算协议内比较。

## 4. 源码已实现但尚未进入正式发行的 backend

以下后端有共享 backend、property script 或环境检查脚本，但没有进入
`builtin registry`，也不在 `v0.4.2/task-inventory.json` 的正式三条 track 中。

- `admet_ai`
  - 工具/模型：`admet-ai==2.0.1` native `ADMETModel`，同时记录 Chemprop 和 RDKit 版本。
  - 输入：单组分 SMILES。
  - 性质：`AMES`、`BBB_Martins`、`Caco2_Wang`、`hERG`、`Solubility_AqSolDB`。
- `soltrannet`
  - 工具/模型：Ersilia Docker image `ersiliaos/eos6oli:v1.0.0`，也可连接外部 HTTP service。
  - 输入：单组分 SMILES。
  - 性质：`soltrannet_log_s`，即服务返回的 logS-style aqueous solubility 标量。
- `molgpka`
  - 工具/模型：Docker image `ghcr.io/quanted/cts-molgpka:dev-acafcb3fb93dbf8dcf6c952cbf3b12161e7f468d`，默认 linux/amd64。
  - 输入：单组分 SMILES。
  - 性质：原始 `molgpka_pka_values`、pKa 数量 `molgpka_pka_count`、最小 pKa 和最大 pKa。
- `matgl`
  - 工具/模型：native MatGL，默认模型 `MEGNet-Eform-MP-2018.6.1`，可配置 band-gap fidelity/state attribute。
  - 输入：CIF。
  - 性质：formation energy（`eV/atom`）、band gap（`eV`）。
- `mace_mp`
  - 工具/模型：native MACE-MP ASE calculator，默认 `small`、CPU、`float32`。
  - 输入：CIF，经 pymatgen 转为 ASE Atoms。
  - 性质：total potential energy（eV）、energy per atom（eV/atom）、max force（eV/Angstrom）、stress norm（eV/Angstrom^3）。
- `torchani`
  - 工具/模型：native TorchANI `ANI2x`，默认 CPU。
  - 输入：XYZ，经 ASE 读取。
  - 性质：total energy（Hartree）、energy per atom（Hartree/atom）、max force（Hartree/Angstrom）。
- `openmm`
  - 工具/模型：OpenMM core；OpenFF/SMIRNOFF 默认 `openff-2.2.1.offxml` + AM1-BCC；GAFF 使用显式配置和环境 probe。
  - 输入：固定 fixture 或单组分 SMILES ligand。
  - 性质：fixed-system initial/minimized potential energy、energy drop、final max force；OpenFF ligand path 还计算参数化后的 minimization energy/force。GAFF 当前主要是 template-generator 可用性 smoke，不是完整正式 ligand 性质 task。

这些后端的运行条件不同：ADMET-AI 是 package 依赖，MatGL/MACE-MP/TorchANI
通过 optional dependency group 安装，SolTranNet/MolGpKa 依赖外部 Docker，
OpenMM/OpenFF 使用独立的可选环境。它们目前缺少正式 track 所需的完整 task
pack、冻结阈值/校准、公开发布边界或统一运行环境，因此不能直接按
`v0.4.2` 正式题目使用。

## 5. 结论与边界

- **发行版覆盖**：36 道正式题，集中在 RDKit 小分子描述符/构象、xTB 低成本
  量子性质，以及固定输入晶体性质计算三个方向。
- **正式 verifier 能力**：主要是 RDKit + xTB/CREST；其中
  `property_calculation` 是 gold-based evaluator，不是第三个 verifier
  backend。
- **仓库储备能力**：ADMET/QSAR、pKa、材料 GNN/MLIP、分子量子 ML、OpenMM
  力场路径已经有代码基础，但仍属于非正式 backend。
- **不应据此声称已经支持**：DFT/ab initio 通用 parser、energy-above-hull/
  PhaseDiagram、长时间 MD/FEP/docking、反应网络或逆合成等能力；当前源码中
  没有这些正式可执行 verifier。

对应的逐 track 细节见：
`docs/tracks/RDKit.md`、`docs/tracks/xTB.md`、
`docs/tracks/PropertyCalculation.md`、`docs/tracks/MolGpKa.md`、
`docs/tracks/SolTranNet.md`、`docs/tracks/MACE-MP.md`、
`docs/tracks/TorchANI.md` 和 `docs/tracks/OpenMM-OpenFF.md`。

## 6. 两次 mixed-datasets run 与三模型横向结果

### 6.1 数据口径

本节整理的是 `/Users/xutao/.openclaw/workspace/state/benchmark-runs/formal/`
下的正式运行结果。比较集合固定为 mixed-datasets 两次 run 共同包含的 13
个 task：RDKit 4 道、xTB 7 道和 property calculation 2 道。

- `gpt-5.6-terra` 和 `gpt-5.6-sol` 直接使用
  `formal/mixed-datasets/` 下各自最新的完整 run。
- `gpt-5.5` 没有 `mixed-datasets` 子目录，因此按三个正式 track 各取该模型
  最近一次完整 run：RDKit 4 道、xTB 7 道、property calculation 2 道，再按
  task ID 拼成同一批 13 道题。
- 主比较统一使用 `single_llm_skills_on`，即启用 benchmark skills allowlist、
  关闭 web search 的单一 LLM 组。三组主比较均为 13/13 evaluable、13/13
  scored，表中分数是 verifier 返回的 `normalized_score`，范围为 `[0, 1]`；
  分数越高越好。`passed` 字段在这些连续评分结果中没有作为二值指标使用。

两个 mixed run 使用 package/task pack `0.4.2` 和 `linear_goal_v2`。gpt-5.5
的 RDKit、xTB 结果文件中仍同时存在 `0.4.1` 记录和少数 `0.4.2` 记录（RDKit
任务 013、xTB 任务 020 为 `0.4.2`），因此这里按共同 task ID 和统一评分字段
进行横向比较，不把它表述为同一 release 的严格重放。

```text
模型          结果来源                                      生成时间                 组别                  题数  版本口径
gpt-5.5       三个正式 track 的最新 gpt-5.5 run               2026-07-26 至 2026-07-27  single_llm_skills_on  13   RDKit/xTB 含 0.4.1/0.4.2；property 为 0.4.2
gpt-5.6-terra mixed-datasets-gpt-5-6-terra-20260727-191610  2026-07-27               single_llm_skills_on  13   0.4.2
gpt-5.6-sol   mixed-datasets-gpt-5-6-sol-20260727-231050    2026-07-28               single_llm_skills_on  13   0.4.2
```

对应的完整结果路径为：

```text
/Users/xutao/.openclaw/workspace/state/benchmark-runs/formal/mixed-datasets/gpt-5-6-terra/mixed-datasets-gpt-5-6-terra-20260727-191610/results.json
/Users/xutao/.openclaw/workspace/state/benchmark-runs/formal/mixed-datasets/gpt-5-6-sol/mixed-datasets-gpt-5-6-sol-20260727-231050/results.json
/Users/xutao/.openclaw/workspace/state/benchmark-runs/formal/verifier-grounded-rdkit/gpt-5-5/verifier-grounded-rdkit-gpt-5-5-20260726-164725/results.json
/Users/xutao/.openclaw/workspace/state/benchmark-runs/formal/verifier-grounded-xtb-xyz/gpt-5-5/verifier-grounded-xtb-xyz-gpt-5-5-20260726-123119/results.json
/Users/xutao/.openclaw/workspace/state/benchmark-runs/formal/verifier-grounded-property-calculation/gpt-5-5/verifier-grounded-property-calculation-gpt-5-5-20260727-163207/results.json
```

### 6.2 三模型总览

```text
模型          13-task 总均分  RDKit（4）  xTB（7）  property calculation（2）  13/13 scored
gpt-5.5       0.7870          0.8970      0.8708    0.2735                    是
gpt-5.6-terra 0.8756          0.9108      0.9900    0.4047                    是
gpt-5.6-sol   0.8854          0.9216      1.0000    0.4121                    是
```

按 13 道题的简单算术平均汇总，`gpt-5.6-sol` 最高，较 `gpt-5.5` 高
0.0984；`gpt-5.6-terra` 较 `gpt-5.5` 高 0.0886。三模型的差异主要来自
xTB 和 property calculation，RDKit 的差距相对较小。

### 6.3 13-task 横向对比

```text
task                                      track                 gpt-5.5  terra    sol
rdkit_logp_target_011                    RDKit                 0.99480  0.98433  0.99887
rdkit_sa_logp_target_012                 RDKit                 0.99997  0.99223  0.99997
rdkit_chain_end_to_end_max_013           RDKit                 0.94617  1.00000  1.00000
rdkit_caffeine_similarity_max_014        RDKit                 0.64706  0.66667  0.68750
xtb_formula_dipole_min_014               xTB                   1.00000  1.00000  1.00000
xtb_two_fluorine_gap_min_015             xTB                   1.00000  1.00000  1.00000
xtb_c10_f2_gap_min_016                   xTB                   0.93778  0.98655  1.00000
xtb_roy_singlepoint_energy_min_017       xTB                   1.00000  1.00000  1.00000
xtb_ritonavir_optimized_energy_min_018   xTB                   1.00000  1.00000  1.00000
xtb_odd_element_counts_gap_max_019       xTB                   0.15802  0.94360  1.00000
xtb_pyrene_substituent_energy_min_020    xTB                   1.00000  1.00000  1.00000
property_calc_free_energy_001             property calculation   0.04706  0.30945  0.32424
property_calc_crystal_phase_002           property calculation   0.50000  0.50000  0.50000
```

13 个 task 的简要概括如下：

1. `rdkit_logp_target_011`：在元素和原子数约束内，让单组分分子的 LogP 接近 3.0。
2. `rdkit_sa_logp_target_012`：在 SA score 严格小于 5.0 的硬约束下优化 LogP 至 3.0。
3. `rdkit_chain_end_to_end_max_013`：固定六碳非环饱和链，用 ETKDGv3 + UFF 最大化两端碳距离。
4. `rdkit_caffeine_similarity_max_014`：满足 LogP、SA、QED 硬约束，最大化与 caffeine 的 Morgan/Tanimoto 相似度。
5. `xtb_formula_dipole_min_014`：固定 `C12H16N3O8`、中性 doublet，优化后最小化偶极矩。
6. `xtb_two_fluorine_gap_min_015`：闭壳层分子含恰好两个 F，最小化 HOMO-LUMO gap。
7. `xtb_c10_f2_gap_min_016`：固定恰好 10 个 C 和 2 个 F，最小化优化后 HOMO-LUMO gap。
8. `xtb_roy_singlepoint_energy_min_017`：保持 ROY 分子身份，最小化提交几何的 GFN2-xTB single-point energy。
9. `xtb_ritonavir_optimized_energy_min_018`：保持 Ritonavir 图结构和立体化学，优化后最小化 total energy。
10. `xtb_odd_element_counts_gap_max_019`：要求非氢元素计数均为奇数、偶极小于 2 D，再最大化 HOMO-LUMO gap。
11. `xtb_pyrene_substituent_energy_min_020`：保持 pyrene 的硝基、氨基、羧基三取代身份，经 CREST 搜索后最小化 total energy。
12. `property_calc_free_energy_001`：从两套分子晶体 CIF 计算 300 K free-energy absolute difference。
13. `property_calc_crystal_phase_002`：计算 alpha/beta 晶体势能差，并判断 ambient-pressure 和 high-pressure phase。

三模型在 13 个 task 上都成功完成了 verifier 评分，没有出现不可评估记录。xTB
的 014、015、017、018、020 五道题三者均得满分；`gpt-5.5` 的主要短板是
019（0.15802）和 016（0.93778）。property calculation 的 002 中三者都只
得到 0.5，说明相别判断部分可能正确，但数值势能差没有同时达到 gold 评分；
001 则是三模型 property 分项分数的主要差异来源。

### 6.4 mixed run 的 skills on/off 对照

两次 mixed run 还提供了 skills allowlist 的消融组。以下分数同样是 13 个共同
task 的算术平均；`delta` 为 on 减 off。

```text
run           skills 状态  13-task 总均分  RDKit（4）  xTB（7）  property calculation（2）
gpt-5.6-terra on          0.8756          0.9108      0.9900    0.4047
gpt-5.6-terra off         0.8605          0.9217      1.0000    0.2500
gpt-5.6-terra on - off   +0.0151         -0.0109     -0.0100   +0.1547
gpt-5.6-sol   on          0.8854          0.9216      1.0000    0.4121
gpt-5.6-sol   off         0.8606          0.9219      1.0000    0.2500
gpt-5.6-sol   on - off   +0.0249         -0.0003     +0.0000   +0.1621
```

在这两次 run 中，skills 的正向差异主要体现在 property calculation；RDKit
和 xTB 没有表现出一致的提升，terra 的两项反而略低，sol 基本持平。因此不能
仅依据这两次 run 把 skills allowlist 的作用概括成对所有化学 track 的普遍增益。

## 7. 结果解释与限制

- 这是同一 13 个 task 的横向分数比较，不是模型生成分子的物理量直接比较；
  分数已经由各 task 冻结的 `linear_goal_v2` profile 归一化。
- `gpt-5.5` 的 13-task 结果由三个正式 track run 拼接而来，不能解读为一个
  同时运行的 mixed-datasets session；它的总均分用于方便横向展示，track 分数
  和 task 分数更适合作为主要证据。
- 两次 mixed run 的 skills on/off 组使用同一模型和同一题集，但不是同一条模型
  横向比较的额外模型列；gpt-5.5 的主列也只取 skills on，以保持比较组一致。
- property calculation 只有 2 道题，均值方差较大；该 track 是固定 CIF 输入的
  计算/报告任务，不能把它与 open-generation 的分子构造难度直接等同。
- 结果文件中所有 13 条主比较记录均为 completed/evaluable/scored，但这只说明
  verifier 流程成功产生了可评分结果，不等同于模型在每道题都满足全部硬约束。
