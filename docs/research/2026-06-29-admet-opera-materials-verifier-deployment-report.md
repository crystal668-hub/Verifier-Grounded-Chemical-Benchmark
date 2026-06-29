# ADMET-AI、OPERA、CHGNet+pymatgen 与 MatGL 部署使用调研报告

日期：2026-06-29

## 1. 调研结论

本报告面向 `docs/design/INITIAL-DESIGN.md` 中定义的
open-generation chemical property satisfaction benchmark。候选 verifier
必须能在本地或官方 verifier image 中，对模型生成的候选对象重新解析、规范化、计算或预测性质，而不是查询公开数据库标签作为最终 oracle。

本报告排除当前已经形成实现雏形的两类性质：

- RDKit 基础小分子描述符、QED、SA score 等。
- xTB/GFN 系列低成本量子性质，例如 HOMO-LUMO gap、dipole、polarizability、Fukui、thermo 等。

综合官方文档、部署复杂度、性质覆盖、可复现性和与本项目 task schema 的贴合度，推荐顺序如下：

| 推荐级别 | 工具 | 最适合部署的 verifier 方向 | 结论 |
|---|---|---|---|
| P0 | ADMET-AI | 小分子 ADMET 多 endpoint：logS、hERG、AMES、DILI、BBB、Caco-2、CYP、clearance 等 | 最适合作为下一批小分子 verifier。Python/CLI 本地部署简单，项目已在 `pyproject.toml` pin `admet-ai==2.0.1`。 |
| P0/P1 | OPERA | 监管/环境 QSAR：water solubility、Caco-2、FuB、Clint、CATMoS acute toxicity、CERAPP/CoMPARA 等 | 科学和监管语境认可度高，带 applicability domain/accuracy assessment。部署包很重，CLI 入口需要在 Docker 构建时用官方 quick run guide 固化。 |
| P0/P1 | MatGL + pymatgen | 材料 formation energy、band gap、relaxation、energy/forces/stress、hull stability workflow | 推荐作为材料方向主 verifier 后端。MatGL 当前维护更活跃，并包含 CHGNet-PyG、M3GNet、MEGNet、TensorNet/QET 等模型入口；pymatgen 负责相图和 hull 算法层。 |
| P1 | standalone CHGNet + pymatgen | CHGNet static energy/forces/stress/magmom、structure relaxation、CHGNet energy-based stability proxy | 可作为 baseline 或交叉验证。CHGNet README 明确当前实现已迁移到 MatGL，legacy package 不建议作为长期唯一材料 verifier。 |

最终建议：小分子下一批先部署 `ADMET-AI`，再部署 `OPERA`
作为保守 QSAR/AD endpoint 互补。材料方向不要在
`standalone CHGNet` 和 `MatGL` 二选一地孤立部署；推荐的正式形态是
`MatGL model backend + pymatgen PhaseDiagram/structure analysis`，必要时把
MatGL 中的 CHGNet-PyG checkpoint 作为一个具体 model choice。

## 2. 共同 verifier 部署原则

这些工具都应按 property-level verifier script 接入：

```text
task constraint/property -> verification_script -> shared backend/tool environment
```

部署时必须冻结：

- Python/package 版本。
- 模型 checkpoint 名称、来源、hash 或本地缓存路径。
- 输入标准化规则，例如 SMILES canonicalization、CIF/Structure 清洗、元素和尺寸限制。
- 资源上限，例如 timeout、CPU/GPU、最大原子数、最大 heavy atom count。
- 输出单位和 scoring policy。
- failure taxonomy，例如 parse error、domain error、model error、timeout。

对 ML/QSAR verifier，还应额外记录：

- applicability-domain 或 uncertainty 指标。没有官方 AD 时，应至少用训练集近邻距离、结构过滤或 conservative domain gate。
- 对分类 endpoint，明确分数含义是 probability / percentile / hard threshold。
- 对回归 endpoint，明确是否使用 raw prediction、clipped value 或 calibrated value。

## 3. ADMET-AI

### 3.1 官方定位与部署方式

官方 README 将 ADMET-AI 定义为一个 ADMET prediction platform，使用
Chemprop 模型，训练数据来自 Therapeutics Data Commons。官方支持三种使用方式：

- command line。
- Python API。
- web server。

官方安装方式：

```bash
pip install admet-ai
```

官方 CLI 示例：

```bash
admet_predict \
  --data_path data.csv \
  --save_path preds.csv \
  --smiles_column smiles
```

官方 Python API 示例：

```python
from admet_ai import ADMETModel

model = ADMETModel()
preds = model.predict(smiles="O(c1ccc(cc1)CCOC)CC(O)CNC(C)C")
```

在本项目中，`pyproject.toml` 当前已经包含：

```toml
"admet-ai==2.0.1"
```

因此 verifier image 的推荐部署路径是先使用项目锁定环境：

```bash
uv sync
uv run python -c "from admet_ai import ADMETModel; print(ADMETModel)"
```

如果单独构建 ADMET-AI verifier image，则使用官方 pip 安装，并固定版本：

```bash
python -m pip install "admet-ai==2.0.1"
```

需要注意版本差异：官方 README 说明 GitHub main 为 ADMET-AI v2，而论文和官方 live web server 基于 v1；v2 使用 Chemprop v2，模型从头重训，因此 v1/v2 预测不会完全一致。正式 verifier 必须在 `versions` 中记录 ADMET-AI 版本和模型目录。

### 3.2 可计算/预测性质

ADMET-AI 官方资源 `admet.csv` 包含 52 个输出字段，其中 11 个是 RDKit physicochemical properties，41 个是 ADMET endpoint。当前 benchmark 已经有 RDKit track，因此正式新增 verifier 应优先使用 41 个 ADMET endpoint，而不是重复计分 molecular weight、LogP、QED、TPSA、HBA/HBD 等。

适合本项目的 ADMET-AI endpoint：

| 类别 | endpoint | 输出类型 | 可延伸题目 |
|---|---|---|---|
| Absorption | `Solubility_AqSolDB` aqueous solubility | 回归，log(mol/L) | 生成一个在 drug-like gate 下具有目标 logS 窗口的小分子。 |
| Absorption | `Caco2_Wang` cell effective permeability | 回归，log(10^-6 cm/s) | 生成口服先导分子，要求高 Caco-2 permeability 且水溶性不过低。 |
| Absorption | `PAMPA_NCATS` permeability | 分类概率 | 生成高被动膜通透性候选，同时通过 hERG/AMES safety gate。 |
| Absorption | `Pgp_Broccatelli` P-gp inhibition | 分类概率 | 生成低 P-gp inhibition 风险候选。 |
| Absorption | `Bioavailability_Ma` oral bioavailability | 分类概率 | 生成高口服生物利用度概率候选。 |
| Distribution | `BBB_Martins` BBB penetration | 分类概率 | CNS 题可最大化 BBB penetration；non-CNS 题可最小化 BBB penetration。 |
| Distribution | `PPBR_AZ` plasma protein binding rate | 回归，% | 生成 PPB 落在目标窗口的候选。 |
| Distribution | `VDss_Lombardo` volume of distribution | 回归，L/kg | 生成低/中/高分布体积目标候选。 |
| Metabolism | `CYP1A2/2C19/2C9/2D6/3A4_Veith` CYP inhibition | 分类概率 | 生成低 CYP inhibition 的多目标候选，避免 DDI risk。 |
| Metabolism | `CYP2C9/2D6/3A4_Substrate_CarbonMangels` CYP substrate | 分类概率 | 生成指定 CYP substrate/non-substrate 候选。 |
| Excretion | `Clearance_Hepatocyte_AZ`、`Clearance_Microsome_AZ` | 回归，uL/min/10^6 cells 或 uL/min/mg | 生成低/中/高 clearance 候选。 |
| Excretion | `Half_Life_Obach` | 回归，hr | 生成半衰期落入窗口的候选。 |
| Toxicity | `hERG` | 分类概率 | 生成低 hERG blocking 风险分子。 |
| Toxicity | `AMES` | 分类概率 | 生成低 mutagenicity 风险分子。 |
| Toxicity | `DILI` | 分类概率 | 生成低 drug-induced liver injury 风险分子。 |
| Toxicity | `ClinTox` | 分类概率 | 生成低 clinical toxicity 风险分子。 |
| Toxicity | `LD50_Zhu` | 回归，log(1/(mol/kg)) | 生成低 acute toxicity 风险候选。 |
| Toxicity | Tox21 receptor/stress panel | 分类概率 | 生成低 nuclear receptor / stress response risk 候选。 |

### 3.3 推荐题目形态

ADMET-AI 最适合构造小分子多目标任务：

| 题目方向 | 示例约束 |
|---|---|
| 高溶解度低心脏毒性 | `Solubility_AqSolDB >= threshold`，`hERG <= threshold`，再用 RDKit domain gate 控制 MW/charge。 |
| CNS 候选设计 | `BBB_Martins >= threshold`，`hERG <= threshold`，`AMES <= threshold`，`Solubility_AqSolDB` 在窗口内。 |
| non-CNS peripheral drug | `BBB_Martins <= threshold`，`Bioavailability_Ma >= threshold`，`CYP3A4_Veith <= threshold`。 |
| 低 DDI 风险候选 | 多个 CYP inhibition endpoint 同时低于阈值。 |
| 毒性规避 | `AMES <= threshold`、`DILI <= threshold`、`ClinTox <= threshold`。 |

### 3.4 verifier 适配建议

推荐先部署一组小而强的 endpoint，而不是一次铺满 41 个：

1. `Solubility_AqSolDB`，连续回归，容易设计窗口/最大化任务。
2. `hERG`，药物安全约束价值高。
3. `AMES` 或 `DILI`，作为第二 safety gate。
4. `BBB_Martins`，用于 CNS/non-CNS 两类题。
5. `Caco2_Wang` 或 `Bioavailability_Ma`，用于 absorption/oral exposure。

工程注意事项：

- ADMET-AI 会过滤无效 SMILES。verifier script 应把无效或被过滤的候选映射为 `validity_gate=0`，不能静默忽略。
- 禁止把 ADMET-AI 输出中的 DrugBank percentile 当作唯一性质值；正式 score 应优先使用 raw endpoint prediction。percentile 可以作为可解释辅助。
- `include_physchem=True` 会额外输出 RDKit 性质。本项目已有 RDKit verifier，ADMET-AI script 应默认 `include_physchem=False` 或忽略这些列，避免重复性质来源不一致。
- 建议在 verifier spec 中记录：`admet_ai_version`、`chemprop_version`、`models_dir_hash`、`endpoint_id`、`task_type`、`units`。

## 4. OPERA

### 4.1 官方定位与部署方式

OPERA 官方 README 将其定义为 free and open-source/open-data QSAR model suite，提供 physicochemical properties、environmental fate、toxicity endpoints，并包含 applicability domain 和 accuracy assessment。

官方 release `v2.9.2` 提供多种安装包：

- `OPERA2.9_UI_mcr`：GUI，Windows/Linux。
- `OPERA2.9_CL_mcr`：command line，Windows/Linux。
- `OPERA2.9_CL_Par`：parallel command line，适合大批量分子。
- `libOPERA2.9_*`：C/C++/Java/Python 嵌入库。

官方 release 说明 command-line 安装包自带依赖和 MATLAB runtime，安装时不需要互联网；安装后模型本地运行，不访问网络。对本项目 verifier image，推荐使用 Linux command-line 包：

```bash
curl -L -o OPERA2.9_CL_mcr.tar.xz \
  https://github.com/NIEHS/OPERA/releases/download/v2.9.2/OPERA2.9_CL_mcr.tar.xz
tar -xJf OPERA2.9_CL_mcr.tar.xz
```

之后按安装包内 `Install_guide.pdf` 运行安装器。安装指南说明命令行使用时先切换到包含输入结构的工作目录，可通过：

```bash
opera -h
```

查看帮助；通用命令形态是：

```text
OPERA <input> <output> <options>
```

本轮 backend 接入时按官方 `run_OPERA.sh` launcher 固化了实际 verifier
调用契约：

```text
run_OPERA.sh <mcr_directory> --SMI <input.smi> --Output <output.csv> --Endpoint <endpoint>
```

因此本地部署除 `OPERA_EXECUTABLE` 外还需要配置 MATLAB Runtime 目录
`OPERA_MCR_DIRECTORY`。macOS arm64 本机未安装 OPERA；当前 verifier
backend 会把未配置 executable 或 MCR 的情况报告为
`verifier_environment_error`，正式验证仍应在 Linux/Docker 环境中完成。

安装指南还说明 accepted input files 包括 QSAR-ready `.smi`、`.sdf/.mol`，以及 command-line only 的 descriptor `.csv`。正式 verifier 应优先接受结构输入文件，不使用 `.txt` chemical ID 查找模式。

不建议正式 verifier 依赖 GUI 或在线服务。`OPERA2.9_CL_Par` 只在批量校准或大规模候选筛选时使用；单候选评分优先普通 CL 包，减少并发不确定性。

### 4.2 可计算/预测性质

OPERA README 列出的模型包括：

| 类别 | OPERA endpoint | 输出/含义 | 可延伸题目 |
|---|---|---|---|
| ADME | Caco-2 permeability | logPapp | 生成高通透性候选。 |
| ADME | FuB, plasma fraction unbound | human fraction | 生成目标 unbound fraction 候选。 |
| ADME | Clint, hepatic intrinsic clearance | human uL/min/10^6 cells | 生成低/中/高清除率候选。 |
| Ionization/partition | pKa, LogD | acid dissociation, distribution constant | 生成指定电离/分布性质候选。 |
| Toxicity | CATMoS | acute oral toxicity, LD50, GHS/EPA categories | 生成低急性毒性候选。 |
| Endocrine activity | CERAPP | estrogen receptor binding/agonist/antagonist | 生成低 ER activity 风险候选。 |
| Endocrine activity | CoMPARA | androgen receptor binding/agonist/antagonist | 生成低 AR activity 风险候选。 |
| Physicochemical | MP, BP, VP, WS, LogP, HL, KOA, Koc, BCF | 物化与环境分配性质 | 生成目标水溶性、蒸气压、土壤吸附、鱼体富集等候选。 |
| Environmental fate | OH, biodeg, ready biodeg, Km | 大气/生物降解/鱼体代谢 | 生成更易降解或低持久性候选。 |
| Structural properties | MolWeight、nbAtoms、rotatable bonds、TPSA 等 | 结构描述符 | 只建议作为 OPERA workflow 内部辅助，不应重复当前 RDKit verifier。 |

### 4.3 推荐题目形态

OPERA 比 ADMET-AI 更适合“保守 QSAR + applicability domain”题：

| 题目方向 | 示例约束 |
|---|---|
| 环境友好小分子 | 高 ready biodegradability，低 BCF，合理 WS。 |
| 低急性毒性候选 | CATMoS low toxicity 或 LD50 风险门槛。 |
| formulation/solubility | WS 落在目标窗口，同时 OPERA applicability domain pass。 |
| exposure tuning | Caco-2、FuB、Clint 组合，模拟 early ADME triage。 |
| endocrine safety | CERAPP/CoMPARA activity 概率低于阈值。 |

### 4.4 verifier 适配建议

OPERA 适合作为 ADMET-AI 的互补 verifier，而不是替代：

- ADMET-AI 部署轻，Python API 直接，适合快速多 endpoint 任务。
- OPERA 更重，但官方强调 QSAR-ready 标准化、applicability domain 和 accuracy assessment，适合做更保守的 safety/environment verifier。

推荐首批 OPERA endpoint：

1. `WS`，与 ADMET-AI `Solubility_AqSolDB` 形成交叉验证。
2. `Caco-2`，ADME 价值高。
3. `FuB` 和 `Clint`，早期药代性质。
4. `CATMoS`，毒性风险。
5. `BCF` 或 `Ready_biodeg`，扩展环境化学题。

工程风险：

- 安装包约 2 GB，包含 MATLAB runtime，Docker 镜像体积会显著增加。
- CLI 输出格式需要在部署前固定 parser，并纳入 smoke test fixture。
- OPERA 的 applicability-domain 字段应成为 `domain_gate` 的一部分。
- 如果输入可以是 CASRN/DTXSID 等 identifier，正式 benchmark 应禁用 identifier 查库模式，只接受候选 SMILES/InChI，避免性质评分退化为查表。

## 5. standalone CHGNet + pymatgen

### 5.1 官方定位与部署方式

CHGNet 是 charge-informed graph neural network potential。官方 README 说明它预训练在 Materials Project GGA/GGA+U static 和 relaxation trajectories 上，覆盖超过 1.5 million structures 和 146k compounds，并可预测 energy、forces、stress、site-wise magnetic moments。

官方安装：

```bash
pip install chgnet
```

或安装 main：

```bash
pip install git+https://github.com/CederGroupHub/chgnet
```

官方 static prediction 示例核心流程：

```python
from chgnet.model.model import CHGNet
from pymatgen.core import Structure

chgnet = CHGNet.load()
structure = Structure.from_file("candidate.cif")
prediction = chgnet.predict_structure(structure)

energy = prediction["e"]   # eV/atom
forces = prediction["f"]   # eV/A
stress = prediction["s"]   # GPa
magmom = prediction["m"]   # mu_B
```

官方 structure optimization 示例：

```python
from chgnet.model import StructOptimizer

relaxer = StructOptimizer()
result = relaxer.relax(structure)
relaxed_structure = result["final_structure"]
relaxed_total_energy = result["trajectory"].energies[-1]
```

pymatgen 官方定位是 robust open-source Python library for materials analysis，并提供 phase diagrams、reaction analysis、surfaces、defects、elasticity、electronic structure analysis 等能力。安装：

```bash
pip install pymatgen
```

本项目当前已经 pin：

```toml
"pymatgen==2026.5.4"
```

### 5.2 可计算/预测性质

standalone CHGNet 可作为 MLIP 后端直接给出：

| 性质 | 单位 | verifier 用法 |
|---|---|---|
| energy | eV/atom 或 total eV，视 API 输出字段 | 单点能、relaxed energy、relative stability proxy。 |
| forces | eV/A | relaxation convergence、max force gate。 |
| stress | GPa | relaxation convergence、cell stress gate。 |
| magnetic moments | mu_B | magnetic material 题、charge/magmom sanity。 |
| relaxed structure | pymatgen Structure | 后续 band gap/formation energy/hull workflow 的输入。 |
| MD trajectory | ASE trajectory | P1/P2 才建议，用于高成本动力学性质。 |

pymatgen 在这里不是 ML model，而是材料标准算法层：

| pymatgen 能力 | verifier 用法 |
|---|---|
| `Structure.from_file/from_str` | CIF/structure parsing。 |
| symmetry/structure analysis | domain gate，例如原子数、元素、晶胞、距离、空间群。 |
| `PhaseDiagram` | 用固定 reference entries 计算 convex hull。 |
| `get_e_above_hull` / decomposition | energy above hull、decomposition products。 |
| `ComputedEntry` / compatibility machinery | 管理候选和 reference phase energy。 |

### 5.3 可延伸题目

| 题目方向 | 示例约束 |
|---|---|
| 低 relaxed energy 材料 | 生成 CIF，CHGNet relaxation 成功，final max force 低于阈值，relaxed energy 低于阈值。 |
| 近 hull 稳定材料 | 用 CHGNet 对候选和固定 reference phases 同协议计算能量，再用 pymatgen PhaseDiagram 计算 `E_hull <= 0.1 eV/atom`。 |
| 磁性材料 | 生成含过渡金属结构，要求 predicted site magmom 或 total magmom 在窗口内。 |
| 结构合理性 | relaxation 后体积变化、最短原子距、max force、stress 作为 validity/domain gates。 |

### 5.4 verifier 适配风险

CHGNet + pymatgen 最大价值在于材料稳定性 workflow，但不能直接把 CHGNet energy 混入 Materials Project DFT hull 而不做校准。正式 verifier 应使用以下两种之一：

1. 固定 CHGNet reference phase set：对 reference phases 和候选结构都使用同一个 CHGNet checkpoint、同一 relaxation protocol、同一元素体系，pymatgen 只负责 PhaseDiagram 算法。
2. 固定 DFT/MP reference entries + calibrated CHGNet correction：需要明确校准方法、元素 reference、compatibility scheme 和误差。

推荐采用第 1 种，工程上更可复现，也符合 verifier-grounded 的本地重算原则。

更重要的是，CHGNet README 的 development section 明确说明当前 CHGNet implementation 已迁移到 MatGL，包含更准确的 checkpoints，legacy repo 后续只限 critical bugs。因此 standalone CHGNet 不适合作为长期唯一材料 verifier。

## 6. MatGL

### 6.1 官方定位与部署方式

MatGL 是 Materials Graph Library，用于材料科学图深度学习模型。官方 README 说明它是 MatML ecosystem 的一部分，并提供 MEGNet、M3GNet、CHGNet、TensorNet、QET 等架构。

官方安装：

```bash
pip install matgl
```

可选加速后端：

```bash
pip install "matgl[ops]"  # NVIDIA Warp kernels, NVIDIA GPU
pip install "matgl[jax]"  # JAX/XLA inference, CPU/CUDA/Apple Silicon
```

MatGL v3.0.0 的重要部署变化：

- DGL support removed。
- PyTorch Geometric 是目标后端。
- pretrained weights 重新发布到 Hugging Face `materialyze` 组织。
- GitHub legacy pretrained model fallback 已移除。

因此 verifier image 应在构建阶段预下载并缓存模型，避免评分时联网：

```python
import matgl

model = matgl.load_model("MEGNet-Eform-MP-2018.6.1")
```

官方 CLI 示例：

```bash
mgl relax --infile Li2O.cif --outfile Li2O_relax.cif
mgl predict --model M3GNet-Eform-MP-2018.6.1 --infile Li2O.cif
mgl clear
```

本轮部署将 `matgl==4.0.2` 放入 `materials` dependency group，并记录了
`lightning` lockfile resolution 从 `2.6.5` 到 `2.6.1` 的变化。当前 native
backend 已接入 pymatgen CIF 解析、MatGL model loading、`formation_energy`
和 `bandgap` 两个 property shell；单元测试通过 fake model 覆盖，不在测试
时下载 Hugging Face model。正式题目化前仍需要为具体 band gap checkpoint
补充 fidelity/state_attr 配置，并在 verifier image build 阶段预缓存模型。

### 6.2 可计算/预测性质

MatGL 官方 README 和 tutorials 中直接展示了以下能力：

| 模型/接口 | 性质 | verifier 用法 |
|---|---|---|
| `MEGNet-Eform-MP-2018.6.1` | formation energy, eV/atom | 材料 formation energy 目标或 hull workflow 输入。 |
| `M3GNet-Eform-MP-2018.6.1` | formation energy, eV/atom | 与 MEGNet Eform 交叉验证或替代。 |
| `MEGNet-BandGap-mfi-MP-2019.4.1` | multi-fidelity band gap | PBE/GLLB-SC/HSE/SCAN band gap 目标窗口。 |
| `M3GNet-PES-MatPES-PBE-2025.2` | energy/forces/stress, relaxation, MD | 结构弛豫、relaxed energy、max force/stress gate。 |
| MatGL CHGNet-PyG checkpoints | energy/forces/stress/magmom | 替代 standalone CHGNet，当前更适合作长期维护路径。 |
| TensorNet/QET potentials | energy/forces/stress, charge-aware/equivariant simulations | 后续高阶材料 verifier 或交叉验证。 |

Band gap multi-fidelity 模型需要指定 fidelity label：

```python
import torch
import matgl

model = matgl.load_model("MEGNet-BandGap-mfi-MP-2019.4.1")

# 0: PBE, 1: GLLB-SC, 2: HSE, 3: SCAN
graph_attrs = torch.tensor([0])
bandgap = model.predict_structure(structure=struct, state_attr=graph_attrs)
```

MatGL tutorial 还强调：对 hypothetical 或 experimental source 的未弛豫结构，推荐先用 universal potential relaxation，再做 formation energy 或 band gap prediction。这个点对 open-generation benchmark 很关键，因为模型输出的 CIF 常常不是 DFT-relaxed structure。

### 6.3 可延伸题目

| 题目方向 | 示例约束 |
|---|---|
| 半导体 band gap 设计 | 生成 CIF，MatGL relaxation 成功，PBE band gap 落入 `[1.0, 2.0] eV`。 |
| 宽带隙绝缘体 | relaxed structure，band gap 大于阈值，formation energy 低于阈值。 |
| 稳定光催化材料 proxy | band gap 窗口 + formation energy/hull gate + allowed elements。 |
| 低 formation energy 材料 | `M3GNet-Eform` 或 `MEGNet-Eform` 预测 formation energy 小于阈值。 |
| near-hull material | MatGL potential/property model 提供候选 energy，pymatgen PhaseDiagram 用固定 reference entries 计算 `E_hull`。 |
| 结构质量 gate | relaxation 收敛、max force、体积变化、最短原子距、stress。 |

### 6.4 verifier 适配建议

MatGL 更适合作为材料方向主后端，原因：

- 覆盖直接 property prediction 和 potential/relaxation 两类需求。
- 目前是 CHGNet 新实现和 checkpoint 的承载路径之一。
- 官方 CLI 和 Python API 都适合容器化。
- 模型分发现在集中到 Hugging Face，可以在 Docker build 阶段固定缓存。
- 同一框架下可切换 MEGNet/M3GNet/CHGNet/TensorNet/QET，方便做 hidden ensemble 或交叉验证。

需要控制的风险：

- MatGL v3.0.0 是破坏性更新，DGL backend 移除，旧模型权重不再数值兼容。必须 pin `matgl` 版本和模型 repo revision/hash。
- Hugging Face 模型下载不能发生在评分运行时。verifier image 必须离线可运行。
- band gap 模型是 surrogate，不是 DFT。题目表述应写成 “MatGL-predicted band gap” 或 “verifier-predicted band gap”，不要宣称实验 band gap。
- formation energy 和 potential energy 不能混用。每个 verifier script 必须明确使用直接 property model 还是 potential + reference entries workflow。

## 7. CHGNet+pymatgen 与 MatGL 对比

| 维度 | standalone CHGNet + pymatgen | MatGL + pymatgen |
|---|---|---|
| 官方维护状态 | CHGNet README 说明实现已迁移到 MatGL，legacy package 后续主要限 critical bugs。 | MatGL 是当前 Materialyze/Materials Virtual Lab 图模型平台，v3 仍在快速演进。 |
| 安装复杂度 | `pip install chgnet pymatgen`，简单。 | `pip install matgl pymatgen`，另需处理 PyG/Hugging Face model cache；可选 extras。 |
| 直接性质预测 | energy/forces/stress/magmom；不直接提供 band gap property model。 | formation energy、multi-fidelity band gap、energy/forces/stress、relaxation、CHGNet-PyG magmom 等。 |
| 稳定性 verifier | 需要 CHGNet energy + fixed reference phase set + pymatgen PhaseDiagram。 | 同样需要 pymatgen PhaseDiagram，但可选 MatGL potential 或 direct Eform model，灵活性更高。 |
| band gap 题 | standalone CHGNet 不适合直接做 band gap。 | 官方 tutorial 提供 `MEGNet-BandGap-mfi-MP-2019.4.1`。 |
| magnetic/charge-aware 题 | CHGNet 强项，site-wise magmom 明确。 | MatGL 中 CHGNet-PyG checkpoint 也支持 energy/forces/stress/magmom，且是新实现路径。 |
| API 稳定性 | legacy package 简洁，但长期演进有限。 | 当前更活跃，但 v3 发生较大 breaking change，必须 pin。 |
| 本项目 verifier 适配 | 适合作 baseline、smoke、交叉验证。 | 更适合作材料方向正式 verifier 主后端。 |

结论：如果只部署一个材料 verifier 后端，推荐 `MatGL + pymatgen`。其中 MatGL 负责结构弛豫、formation energy、band gap 或 potential energy；pymatgen 负责 CIF/Structure 解析、结构分析、reference entries 和 PhaseDiagram/E_hull 计算。standalone CHGNet 只建议保留为基线或备份路径。

## 8. 推荐部署路线

### 8.1 小分子 ADMET verifier

第一批建议实现：

| verifier_id 建议 | backend | property |
|---|---|---|
| `admet_ai_solubility_aqsoldb_v1` | ADMET-AI v2 pinned model | `Solubility_AqSolDB` |
| `admet_ai_herg_v1` | ADMET-AI v2 pinned model | `hERG` |
| `admet_ai_ames_v1` | ADMET-AI v2 pinned model | `AMES` |
| `admet_ai_bbb_v1` | ADMET-AI v2 pinned model | `BBB_Martins` |
| `admet_ai_caco2_v1` | ADMET-AI v2 pinned model | `Caco2_Wang` |

第二批建议实现：

| verifier_id 建议 | backend | property |
|---|---|---|
| `opera_ws_v1` | OPERA 2.9 CL | `WS` |
| `opera_catmos_v1` | OPERA 2.9 CL | CATMoS toxicity endpoint |
| `opera_clint_v1` | OPERA 2.9 CL | `Clint` |
| `opera_fub_v1` | OPERA 2.9 CL | `FuB` |
| `opera_ready_biodeg_v1` | OPERA 2.9 CL | `Ready_biodeg` |

### 8.2 材料 verifier

第一批建议正式化：

| verifier_id 建议 | backend | property |
|---|---|---|
| `matgl_bandgap_pbe_v1` | MatGL `MEGNet-BandGap-mfi-MP-2019.4.1`, fidelity PBE | band gap, eV |
| `matgl_bandgap_hse_v1` | 同一模型，fidelity HSE | band gap, eV |
| `matgl_eform_m3gnet_v1` | MatGL `M3GNet-Eform-MP-2018.6.1` | formation energy, eV/atom |
| `matgl_relaxed_energy_v1` | MatGL PES checkpoint + fixed relaxation protocol | relaxed total/per-atom energy |
| `matgl_ehull_proxy_v1` | MatGL energy/eform + fixed reference entries + pymatgen PhaseDiagram | energy above hull, eV/atom |

材料 verifier 的推荐执行流程：

1. 解析 candidate CIF 或 structure JSON。
2. 做 domain gate：元素集合、原子数、晶胞体积、最短距离、charge/disorder 支持范围。
3. 使用固定 MatGL potential 进行 relaxation，记录 fmax、steps、是否收敛、体积变化。
4. 对 relaxed structure 计算 band gap 或 formation energy。
5. 如需 E_hull，读取同一元素体系的固定 reference entries，用 pymatgen PhaseDiagram 计算。
6. 输出 property、domain diagnostics、model/checkpoint versions、artifacts。

## 9. 推荐优先级

最推荐的实际落地顺序：

1. `ADMET-AI`：部署成本最低，能立即补齐 RDKit/xTB 之外的真实药物发现 ADMET/safety 目标。
2. `MatGL band gap + formation energy`：材料方向最贴合当前设计，且项目已有 MatGL 相关 smoke/task 脚手架，可从探索状态推进为正式 verifier。
3. `MatGL + pymatgen E_hull proxy`：比单纯 band gap 更能防止无意义材料生成，但需要固定 reference entries 和校准。
4. `OPERA`：科学和监管价值高，适合作为 ADMET-AI 的保守互补；部署包重，建议等 Python 版 ADMET verifier 稳定后再进入官方 image。
5. `standalone CHGNet`：不建议作为唯一正式路线；可作为 MatGL 方案的对照、fallback 或 CHGNet-PyG 结果校验。

## 10. 官方资料来源

- ADMET-AI GitHub README: <https://github.com/swansonk14/admet_ai>
- ADMET-AI live server help text: <https://admet.ai.greenstonebio.com/>
- ADMET-AI endpoint metadata: <https://github.com/swansonk14/admet_ai/blob/main/admet_ai/resources/data/admet.csv>
- ADMET-AI model/API implementation: <https://github.com/swansonk14/admet_ai/blob/main/admet_ai/admet_model.py>
- OPERA GitHub README: <https://github.com/NIEHS/OPERA>
- OPERA v2.9.2 release: <https://github.com/NIEHS/OPERA/releases/tag/v2.9.2>
- OPERA install guide PDF: <https://github.com/NIEHS/OPERA/blob/master/Install_guide.pdf>
- CHGNet GitHub README: <https://github.com/CederGroupHub/chgnet>
- CHGNet API docs: <https://chgnet.lbl.gov>
- pymatgen GitHub README: <https://github.com/materialsproject/pymatgen>
- pymatgen official docs: <https://pymatgen.org>
- MatGL GitHub README: <https://github.com/materialsvirtuallab/matgl>
- MatGL official docs: <https://matgl.ai>
- MatGL property prediction tutorial: <https://matgl.ai/tutorials/Property%20Predictions%20using%20MEGNet%20or%20M3GNet%20Models.html>
- MatGL relaxation + property workflow tutorial: <https://matgl.ai/tutorials/Combining%20the%20M3GNet%20Universal%20Potential%20with%20Property%20Prediction%20Models.html>
- MatGL CHGNet-PyG tutorial: <https://matgl.ai/tutorials/CHGNet-PyG%20Foundation%20Potential.html>
