# v0.4.2 Benchmark 发行版与 Verifier 能力清单

更新日期：2026-07-27

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

| track | 题目数 | 输入/题型 | 主要考察方向 |
| --- | ---: | --- | --- |
| `rdkit` | 14 | 单组分分子 SMILES；open-generation | 2D 分子描述符约束、多目标性质优化、简单构象代理和分子相似性 |
| `xtb` | 20 | 19 道显式氢 XYZ，1 道 SMILES-to-conformer；open-generation | 3D 几何生成、GFN-xTB 电子结构/反应性/热化学性质、构象和分子身份约束 |
| `property_calculation` | 2 | 题面内嵌完整 CIF；fixed-input property calculation | 分子晶体自由能差、势能差和压力相判定 |
| **合计** | **36** |  |  |

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

| backend | 工具/模型与运行方式 | 输入 | 当前可以计算的性质 |
| --- | --- | --- | --- |
| `admet_ai` | `admet-ai==2.0.1` 的 native `ADMETModel`；backend 同时记录 Chemprop 和 RDKit 版本 | 单组分 SMILES | `AMES`、`BBB_Martins`、`Caco2_Wang`、`hERG`、`Solubility_AqSolDB` 五个 ADMET endpoint |
| `soltrannet` | Ersilia Docker image `ersiliaos/eos6oli:v1.0.0`，也可连接外部 HTTP service | 单组分 SMILES | `soltrannet_log_s`，由服务返回的 `solubility` 映射而来，作为 logS-style aqueous solubility 标量 |
| `molgpka` | Docker image `ghcr.io/quanted/cts-molgpka:dev-acafcb3fb93dbf8dcf6c952cbf3b12161e7f468d`，默认 linux/amd64 | 单组分 SMILES | 原始 `molgpka_pka_values`、预测 pKa 数量 `molgpka_pka_count`、最小 pKa 和最大 pKa |
| `matgl` | native MatGL；默认模型 `MEGNet-Eform-MP-2018.6.1`，可配置 band-gap fidelity/state attribute | CIF | formation energy（`eV/atom`）、band gap（`eV`） |
| `mace_mp` | native MACE-MP ASE calculator；默认 `small`、CPU、`float32` | CIF，经 pymatgen 转 ASE Atoms | total potential energy（eV）、energy per atom（eV/atom）、max force（eV/Angstrom）、stress norm（eV/Angstrom^3） |
| `torchani` | native TorchANI `ANI2x`，默认 CPU | XYZ，经 ASE 读取 | total energy（Hartree）、energy per atom（Hartree/atom）、max force（Hartree/Angstrom） |
| `openmm` | OpenMM core；OpenFF/SMIRNOFF 默认 `openff-2.2.1.offxml` + AM1-BCC；GAFF 走显式配置和环境 probe | 固定 fixture，或单组分 SMILES ligand | fixed-system initial/minimized potential energy、energy drop、final max force；OpenFF ligand path 还计算参数化后的 minimization energy/force。当前 GAFF 路径主要是 GAFF template-generator 可用性 smoke，不是完整的正式 ligand 性质 task |

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
