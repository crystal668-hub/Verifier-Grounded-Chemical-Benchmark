# Verifier-Grounded 化学 Benchmark：研究定位与设计演进

初稿日期：2026-05-26。现行定位确认：2026-11-03。

本文件保留初始设计的演进背景，并以当前正式题集和实现说明研究主线。
§7、§10 和 §11.1–11.8 是早期选题与调研记录；其余章节按当前
`v1.0.0-rc`（Python `1.0.0rc1`）的定位更新。历史设计版本保存在 Git 中。

## 1. 项目动机与研究主线

通用大模型与支持工具调用、代码执行和任务编排的 agent harness 相结合，为化学问题求解提供了新的系统形态。本项目关注的问题是：**系统能否将化学知识转化为面向具体目标、可验证的求解结果？**

知识问答可以考察化学知识与相关推理，但仅靠知识问答表现不足以衡量目标驱动任务的完成能力。本项目不以“知识题已失去意义”或“现有知识题已经普遍饱和”为前提，也不把已有化学 benchmark 一概归为知识记忆题。

我们将评价重点放在两类互补任务上。第一类是开放生成：给定性质目标和结构约束，要求系统提出候选分子或分子构象。评价器按照固定计算协议重新计算候选的性质，依据其满足目标的程度评分，模型自报的性质值不作为验证证据。第二类是性质计算：给定化学对象与问题条件，要求系统报告目标性质，并依据预先计算或经专家审校后冻结的参考答案评分。两类任务分别覆盖目标约束下的候选构造与给定对象的性质求解。

为降低本地运行评价流程的门槛，开放生成任务的验证主要依托 RDKit、xTB 及必要的 CREST 构象搜索流程；性质计算任务将参考答案的生成与模型评价分离。参考答案可以来自计算成本较高的方法，而评分阶段无需重复这些计算。这使评价流程的运行成本与参考计算的生成成本得以分开。

对可连续度量的数值目标，我们使用预先设定尺度的连续距离评分，刻画候选性质对目标的满足程度，或提交结果对参考值的接近程度。同时保留必要的有效性检查、硬约束和离散答案判定。最终得分反映系统在指定任务、参考协议和评分规则下的完成程度。

## 2. 两类任务的定位

| 题型 | 题面与提交对象 | 评价依据 | 当前正式 tracks |
| --- | --- | --- | --- |
| 开放生成 | 给定目标与约束，提交候选 SMILES 或 XYZ | 对候选执行固定计算协议，重新得到性质 | `open_generation_rdkit`、`open_generation_xtb` |
| 性质计算 | 给定对象与条件，提交数值、标签或多字段答案 | 与预先冻结的 gold 比较 | `property_calculation_basic`、`property_calculation_advanced` |

开放生成无需枚举所有有效候选，同一目标可以允许多个高分答案。性质计算有明确的参考答案，是独立的正式题型。两类任务共同评价最终求解结果，但运行时证据来源不同；“所有题都独立重算”“所有题都不依赖标准答案”均不描述当前套件。

当前开放生成提交单个候选，不以候选新颖性作为通用计分条件。结构域、允许元素、分子身份、电子态等限制按具体任务声明。材料、晶体及激发态相关性质计算题的存在，不等同于已发布材料开放生成 track。

## 3. 答题系统与科学定义

模型与 agent harness 的调用、搜索、工具使用和答案生成由参评方负责。benchmark package 提供任务、解析答案并评分，不接管模型执行，也不检查工具调用轨迹或中间推理。

因此，分数可以比较不同模型与 harness 配置的最终求解表现，但不能单独证明某个答案来自工具使用、参数化知识或特定推理过程。实验应说明模型、harness、工具权限、检索条件和计算预算；归因于某项能力需要相应的实验设计。

题面以化学对象、目标和科学条件为中心。工具中立允许参评系统选择实现方式；当计算层级、状态、单位或其他协议条件定义了所求性质时，仍需明确这些条件。连续容差不能替代科学定义，也不能让不同物理量或未明确的参考协议自动可比。

## 4. 两条评价路径

### 4.1 开放生成：运行时性质验证

开放生成从模型回复中解析候选，应用任务的结构有效性、适用域和身份要求，再按 verifier spec 调度计算。正式入口采用 Python module subprocess；多个性质入口可复用共享后端。xTB/CREST 等外部可执行程序由运行环境提供。

```text
task constraint -> verifier spec/executor -> shared backend
                                              |
                                              v
                                      computed evidence
                                              |
                                              v
                                      constraint scoring
```

Verifier 返回性质、诊断、版本和失败信息，由评价层计算分数。模型自报的性质不能代替重算证据。候选不满足结构域或硬约束可以得到零分；依赖缺失、超时等评价故障单独报告，不当作候选的科学失败。

### 4.2 性质计算：冻结参考答案比较

性质计算解析提交值，按字段定义检查格式、数值域和单位，并与冻结 gold 比较。所需资源为 `tasks.yaml` 和 `scoring.yaml`，不配置或运行性质 verifier。

Gold 的生成与来源审校发生在维护阶段。评价阶段可重复执行同一评分规则，但这不等于独立重算了科学参考值。部分题目的参考值来自专家计算或文献来源；关于输入充分性和参考协议的已知边界应保留在相应 track 和研究记录中。

### 4.3 公共结果契约

两类任务共享结果外层契约：`status: scored | error`、性质/提交答案、分项分数、失败分类与版本信息。开放生成的 `properties` 来自 verifier evidence；性质计算的字段记录提交答案及比较诊断。相同结果字段不意味着执行过相同计算路径。

公共 API、CLI 和错误处理详见[包说明](../../src/verifier_grounded_benchmark/README.md)。

## 5. 连续评分与离散判定

所有可连续评分的数值目标共用 `linear_goal_v2` 内核：定义满分目标或区域，并在其外按配置宽度线性衰减至零。开放生成包括窗口、目标值、最大化和最小化目标；性质计算以 gold 为满分点，按任务声明的数值变换和误差尺度计算接近程度。

连续评分的主要作用是表达接近目标的程度。不同计算协议的差异可以成为选择误差尺度时的考虑因素，但评分宽度是出题效用参数，不自动等于实验不确定度、计算方法误差、置信区间或跨协议误差校准结果。性质计算的 tolerance 表示降到零分的误差宽度，不能写成“容差内一律满分”。

有效性、适用域、分子身份和硬约束保持相应门控；相位标签和原子标识等采用离散匹配或显式部分分。不能把整个评分体系概括为“所有任务都没有二元判断”。

开放生成主目标分数取几何平均，可选 quality gates 取最小值并作为乘子。性质计算默认对字段分数取算术平均；Advanced 002 按 energy 与 phase 两组平均，其中 phase 组要求两个相名均正确。完整且无评价错误的 suite 按任务等权平均，因此当前综合分中开放生成占 30%、性质计算占 70%。论文应分别报告两类任务，明确综合分的构成。

数学定义与架构演进见[统一评分规格](unified-linear-goal-scoring.md)；当前参数以各 track 的 `scoring.yaml` 为准。

## 6. 设计收益与解释边界

两类任务将候选构造与性质求解放在同一个最终结果评价框架中：开放生成支持多解，性质计算扩展固定对象的科学问题覆盖。评价采用预先定义的计算协议或参考答案，减少对自然语言解释风格的依赖。

本地评分通过较轻量的开放生成后端和离线冻结的性质参考值降低运行门槛。答题系统可能自行采用更昂贵的方法；参考答案的生成也可能需要不同的软件与资源。评分端可本地运行不能推出每道题的从头求解都已在个人计算机上验证。

任务、参考值和评分配置的冻结支持结果审计。高分描述既定协议下的完成程度；它不等同于实验最优性、可合成性或完整科研能力。详见[项目限制](Limits.md)和各 [track 文档](../tracks/)。

## 7. 初版推荐覆盖方向

> 本节及后续性质推荐表记录早期选题设想，不是当前正式任务清单或覆盖承诺。当前正式覆盖范围以注册任务清单和各 track 文档为准。

根据目标性质调研报告，初版应优先选择工程可行性高、化学研究价值明确、输入输出规范清晰、可自动验证的性质方向。

### 7.1 小分子确定性与基础药物样性质

推荐作为 P0 方向：

- RDKit QED。
- logP。
- TPSA。
- MW。
- HBD/HBA。
- rotatable bonds。
- SA score。

这些性质适合构造基础 open-generation 任务，例如生成一个满足 drug-likeness、合成可及性和基础理化性质约束的小分子。Verifier 可基于 RDKit 和 RDKit Contrib 实现，工程风险低，结果确定性强。

### 7.2 小分子 ADMET 与安全性质

推荐作为 P0/P1 方向：

- 水溶解度 logS。
- hERG。
- AMES。
- DILI。
- LD50。
- Caco-2、BBB、CYP、PPB、clearance 等 ADME endpoints。

这些性质在药物发现中有明确研究价值，也有大量已有模型。正式 verifier 应优先使用容器内可执行的固定 QSAR/ML 模型或软件，例如 ADMET-AI、SolTranNet、CATMoS 或固定 Chemprop checkpoint；TDC、MoleculeNet、AqSolDB 等公开数据集可用于训练、校准或审校，但不作为题目运行时的性质查表 oracle。

初版应控制 endpoint 数量，优先设计少量多目标任务，例如在 QED、SA、logS 和 hERG 风险之间进行约束组合。

### 7.3 材料性质

推荐作为 P0/P1 方向：

- band gap。
- formation energy。
- energy above hull。
- density。
- dielectric constant 或 refractive index。
- bulk/shear modulus。

这些性质适合构造材料发现任务，例如生成或提出一个稳定性较好且 band gap 位于目标窗口的材料。正式 verifier 应使用容器内可执行的材料计算后端或固定 surrogate，例如 pymatgen PhaseDiagram 加固定 reference entries、CHGNet、MatGL、MACE、MatterSim 或其他 MLIP/DFT proxy workflow。Materials Project、Matbench 等数据源可用于 reference entry 构造、模型校准、审校和 contamination 检查，但不应成为 open-generation 题目的直接性质标签来源。

### 7.4 低成本量子性质

推荐作为 P0/P1 方向：

- HOMO-LUMO gap。
- orbital energies。
- dipole moment。
- polarizability。
- partial charges。
- conformer energy 或 strain。

这些性质可以通过 xTB、xtb-python、RDKit ETKDG/MMFF/UFF、OpenMM 或 cclib 解析量化输出得到。它们适合连接结构生成、3D 构象生成和低成本计算验证。

### 7.5 后续扩展方向

以下方向具有研究价值，但首版不应承诺完整覆盖：

- 催化 adsorption energy、HER/ORR/CO2RR volcano descriptors。
- reaction yield。
- retrosynthesis feasibility。
- reaction-center validity 或 atom mapping confidence。

这些方向输入规范更复杂，verifier 成本和适用域风险更高。初版可以在设计文档中保留为后续扩展，不作为第一批任务的核心交付。

### 7.6 首版推荐优先进入的性质表

下表中的推荐 verifier 已按“成熟、可复现、化学领域内普遍认可”原则收紧：优先选择容器内可执行的确定性工具、固定计算脚本和已有广泛使用记录的开源模型；较新的 foundation model 或研究型模型只作为备选交叉验证，不作为首版唯一 verifier。只通过数据库或数据集标签查值得到的性质不进入正式评分目标。

| 优先级 | 性质类别 | 选择理由 | 研究价值 | 推荐 verifier |
|---|---|---|---|---|
| P0-1 | RDKit QED/logP/TPSA/MW + SA score 多约束小分子设计 | 最稳定、成本最低、可本地确定性验证；可作为所有小分子任务的基础 sanity layer，并快速暴露无效 SMILES、过大分子或不可合成结构。 | 覆盖药物化学早期过滤指标和合成可及性约束，适合评估模型是否能生成基础 drug-like 且可合成的小分子。 | RDKit QED、Crippen、Descriptors；RDKit Contrib `SA_Score`。 |
| P0-2 | 水溶解度 logS | ADMET 价值高，输出连续，适合 open generation；应优先使用成熟开源 QSAR 工具或固定训练 checkpoint。 | 水溶解度直接影响 oral exposure、formulation 和 screening success，是 ADMET/QSPR 中常见的关键连续性质。 | 首选：SolTranNet、ADMET-AI 或固定 Chemprop checkpoint；公开数据集仅用于训练/校准/审校。 |
| P0-3 | hERG/AMES/DILI 等 safety endpoint | 药物发现中真实重要，适合作为 hard safety constraint，而不是单独优化目标；正式评分应来自固定 endpoint 模型。 | hERG、mutagenicity、DILI、acute toxicity 是早期 safety triage 的关键 endpoint，可提升任务的真实药物发现约束强度。 | 首选：CATMoS、ADMET-AI 或固定 Chemprop/QSAR checkpoint；TDC/MoleculeNet 只作训练、校准或审校来源。 |
| P0-4 | 材料 band gap | 材料 ML 最成熟性质之一，结构或成分输入清晰；正式题目应要求容器内模型或计算 workflow 对候选重新预测。 | band gap 是光伏、半导体、透明导体、光催化、绝缘材料设计的核心性质。 | 首选：MEGNet / MatGL 等固定 band-gap 模型；必要时使用小规模固定计算 workflow 作校准或交叉检查。 |
| P0-5 | formation energy / energy above hull | 是材料生成的基础 feasibility gate；没有稳定性评分，open-generation 材料题容易退化为无意义结构生成。 | formation energy 和 E above hull 是 computational materials discovery 中衡量热力学稳定性和可实现性的基础目标。 | 首选：CHGNet / M3GNet / MatGL / MACE relaxation 与 energy proxy；pymatgen PhaseDiagram 可使用固定 reference entries 计算 hull 距离。 |
| P0-6 | HOMO-LUMO gap | xTB 可本地运行，连续数值，成本低于 DFT；适合小分子开放生成，并能区分是否会调用工具。 | HOMO-LUMO gap 是光电、有机电子、反应性和稳定性 proxy 的常见量子性质。 | 首选：xTB/GFN2-xTB 固定版本 + RDKit ETKDG 构象生成 + cclib 或固定 parser。 |
| P0-7 | dipole / polarizability / partial-charge 指标 | xTB 和 cclib 可验证，能引导 agent 做结构层面的物理性质优化，而不只是查数据库；适合作为 secondary objective 或 physical descriptor task。 | dipole、polarizability 和 partial charges 影响 solvation、crystal packing、dielectric response、binding 与 force-field interaction modeling。 | 首选：xTB/GFN2-xTB 固定版本；cclib 解析 `atomcharges`、`moments`、`polarizabilities`。备选：OpenFF/RDKit charge models 仅用于低成本 charge sanity，不与 xTB charge 混合评分。 |
| P1-8 | ADME multi-endpoint：Caco-2/BBB/CYP/PPB/clearance | 真实药化价值高，但 endpoint 定义和模型适用域比 logS/hERG 更复杂；首版适合作为少量 multi-objective 题，不宜全面铺开。 | ADME 决定 exposure、drug-drug interaction、CNS penetration、oral absorption，是 lead optimization 的真实多目标核心。 | 首选：ADMET-AI 或固定 ADMET checkpoint；公开 ADMET 数据只用于训练/校准/审校。 |
| P1-9 | 靶点活性 / binding affinity proxy | 最接近真实 drug discovery 目标，但 leakage 和 assay heterogeneity 高；首版只适合窄 target family 的固定预测模型或 docking proxy。 | 真实药物发现通常需要同时优化 target potency/selectivity 与 ADMET，而不只是生成 drug-like 分子。 | 首选：DeepDTA/DeepPurpose 等固定窄域 surrogate、固定受体与参数的 docking workflow；ChEMBL/BindingDB 不作为直接标签 oracle。 |
| P1-10 | adsorption energy / HER descriptor | 催化方向代表性质；输入复杂，但可通过固定 slab templates 和固定计算协议降低难度。 | adsorption energy 是 heterogeneous catalysis descriptor 核心；HER 等任务常用 ΔG_H 等吸附自由能构建 volcano relationship。 | 首选：ASE + pymatgen 固定 slab/adsorbate 构建、FairChem / GemNet-OC / EquiformerV2 固定 checkpoint 或小规模固定计算 workflow。 |
| P1-11 | reaction yield / retrosynthesis feasibility / RXNMapper validity | 反应和合成方向需要进入首版但应窄域；可分别用低成本 reaction validity、合成可达性和 family-specific fixed model 控制风险。 | reaction yield 是反应优化直接目标；retrosynthesis feasibility 防止奖励不可合成候选；atom mapping 和 reaction-center validity 可过滤不守恒或不合理 reaction SMILES。 | 首选：RDKit reaction parsing / mass balance；RXNMapper confidence；AiZynthFinder + fixed stock/policy；`rxn_yields` / Yield-BERT 仅限固定反应家族和冻结 checkpoint。 |

### 7.7 按 verifier 难度划分的首版性质表

这里的难度指 verifier 的计算与工程难度，而不是性质本身的科研价值。划分标准如下：

- 简单：RDKit 或同类确定性 cheminformatics 工具可直接计算或校验，适合先作为 runner 和答案解析的 smoke test。
- 中等：需要运行计算化学脚本，但单个候选通常可较快完成，例如 RDKit 构象生成加 xTB 单点或优化。
- 困难：从头计算通常很慢、难以稳定自动化，或需要固定 QSAR/ML 模型、ML interatomic potential、retrosynthesis planner、reaction yield surrogate、reference entries 或严格资源上限。

| 难度 | 性质类别 | 对应首版性质 | 划分依据 | 最推荐 verifier | 使用方法链接 |
|---|---|---|---|---|---|
| 简单 | 小分子基础药物样性质与 SA score | P0-1 RDKit QED/logP/TPSA/MW + SA score | SMILES 解析后即可用 RDKit descriptor 或 RDKit Contrib 直接计算，速度快、确定性强。 | RDKit QED/Descriptors；RDKit Contrib `SA_Score` | [RDKit QED docs](https://www.rdkit.org/docs/source/rdkit.Chem.QED.html)<br>[RDKit SA_Score](https://github.com/rdkit/rdkit/tree/master/Contrib/SA_Score) |
| 简单 | Reaction SMILES 解析、基础质量守恒与 schema validity | P1-11 中的 reaction validity 子任务 | 只做 reaction SMILES 可解析性、分子合法性、原子/元素守恒、字段 schema 校验时，不需要 ML 或昂贵计算。 | RDKit `rdChemReactions`；Open Reaction Database schema validation | [RDKit reaction docs](https://www.rdkit.org/docs/source/rdkit.Chem.rdChemReactions.html)<br>[ORD schema docs](https://docs.open-reaction-database.org/en/stable/schema.html) |
| 中等 | HOMO-LUMO gap / orbital energies | P0-6 HOMO-LUMO gap | 需要从 SMILES 生成 3D 构象并运行 xTB/GFN2-xTB；对中小 neutral organic molecules 通常可批量运行，但比 RDKit descriptor 慢。 | xTB/GFN2-xTB；cclib parser | [xTB properties docs](https://xtb-docs.readthedocs.io/en/latest/properties.html)<br>[cclib parsed data](https://cclib.github.io/data.html) |
| 中等 | dipole / polarizability / partial charges | P0-7 dipole、polarizability、partial-charge 指标 | 同样依赖 3D 构象和 xTB 输出；比纯 descriptor 更重，但仍可作为低成本量子性质 verifier。 | xTB/GFN2-xTB；cclib parser | [xTB properties docs](https://xtb-docs.readthedocs.io/en/latest/properties.html)<br>[cclib parsed data](https://cclib.github.io/data.html) |
| 困难 | 水溶解度 logS | P0-2 水溶解度 logS | 真实 logS 不能由 RDKit 公式可靠给出；首版应依赖成熟 QSAR 工具或固定训练 checkpoint。 | SolTranNet；ADMET-AI；固定 Chemprop/QSAR checkpoint | [ADMET-AI GitHub](https://github.com/swansonk14/admet_ai) |
| 困难 | hERG / AMES / DILI 等 safety endpoint | P0-3 hERG/AMES/DILI 等 safety endpoint | 安全 endpoint 是实验标签上的 QSAR/ML 预测问题；正式评分需要固定模型版本和 applicability-domain 规则。 | CATMoS；ADMET-AI；固定 Chemprop/QSAR checkpoint | [ADMET-AI GitHub](https://github.com/swansonk14/admet_ai) |
| 困难 | ADME multi-endpoint：Caco-2 / BBB / CYP / PPB / clearance | P1-8 ADME multi-endpoint | endpoint 定义、实验协议和适用域复杂，通常需要固定 QSAR/ML 模型。 | ADMET-AI；固定 ADMET checkpoint | [ADMET-AI GitHub](https://github.com/swansonk14/admet_ai) |
| 困难 | 材料 band gap | P0-4 材料 band gap | 从头计算 band gap 通常需要 DFT；首版应使用固定 ML surrogate 或受限计算 workflow 对候选重新预测。 | MEGNet / MatGL fixed band-gap model；受限 DFT/MLIP proxy workflow | [MatGL docs](https://matgl.ai/)<br>[CHGNet GitHub](https://github.com/CederGroupHub/chgnet) |
| 困难 | formation energy / energy above hull | P0-5 formation energy / energy above hull | 可靠 E_hull 依赖一致 reference entries 和 candidate energy；新结构通常要 relaxation 和 energy model，因此比快速脚本更难。 | CHGNet / M3GNet / MatGL / MACE energy proxy；pymatgen PhaseDiagram with fixed reference entries | [pymatgen usage docs](https://pymatgen.org/usage.html)<br>[CHGNet GitHub](https://github.com/CederGroupHub/chgnet) |
| 困难 | 靶点活性 / binding affinity proxy | P1-9 靶点活性 / binding affinity proxy | 活性数据受 assay heterogeneity 和 leakage 影响；首版应只做窄域 fixed model 或固定 docking protocol。 | DeepDTA/DeepPurpose fixed checkpoint；AutoDock Vina fixed receptor/box/protocol | [DeepPurpose GitHub](https://github.com/kexinhuang12345/DeepPurpose)<br>[AutoDock Vina docs](https://autodock-vina.readthedocs.io/) |
| 困难 | adsorption energy / HER descriptor | P1-10 adsorption energy / HER descriptor | 从头 DFT relaxation 很慢；首版应限制 slab/adsorbate template，并使用固定 MLIP/OC 模型或受限计算 workflow。 | ASE fixed slab/adsorbate workflow；FairChem / GemNet-OC / EquiformerV2 fixed checkpoints | [ASE surface docs](https://ase-lib.org/ase/build/surface.html)<br>[FAIR-Chem docs](https://fair-chem.github.io/) |
| 困难 | atom mapping confidence / reaction-center validity | P1-11 中的 RXNMapper validity 子任务 | 如果只做 RDKit 解析是简单问题；若要求 atom mapping confidence 或 reaction center plausibility，则需要 RXNMapper 这类 ML mapper。 | RXNMapper；RDKit reaction validation | [RXNMapper GitHub](https://github.com/rxn4chemistry/rxnmapper)<br>[RDKit reaction docs](https://www.rdkit.org/docs/source/rdkit.Chem.rdChemReactions.html) |
| 困难 | retrosynthesis feasibility | P1-11 中的 retrosynthesis feasibility 子任务 | 需要 retrosynthesis planner、模板/策略模型和 fixed stock；结果高度依赖 stock 与 policy checkpoint。 | AiZynthFinder；fixed purchasable stock and policy | [AiZynthFinder docs](https://molecularai.github.io/aizynthfinder/)<br>[AiZynthFinder GitHub](https://github.com/MolecularAI/aizynthfinder) |
| 困难 | reaction yield | P1-11 中的 reaction yield 子任务 | 通用 yield prediction 不稳定；首版只能在固定 reaction family 和 fixed checkpoint 下使用。 | `rxn_yields` / Yield-BERT fixed checkpoint；family-specific fixed yield model | [rxn_yields GitHub](https://github.com/rxn4chemistry/rxn_yields) |

## 8. 当前交付与发布边界

当前 RC 交付是本地 wheel/sdist、release 材料和 Git tag。Python API/CLI 接收调用方提供的答案；RDKit 随包依赖安装，xTB 6.7.1 与任务 020 所需的 CREST 2.12 单独提供。正式 verifier 使用 `executor.type: python_module`。Spec 中保留的 `verifier_image` 字段不代表单一官方镜像已构建或发布。

四个正式 track 不提供公开 sample answers；开发回归答案不进入 wheel/sdist。性质计算 gold 和 scoring 配置仍随发行包提供，用于离线评分与审计；普通任务视图不自动返回 gold，显式接口为 `track.task(task_id, include_gold=True)`。移除样例答案不构成隐藏测试集或防污染机制。

当前正式开放生成只使用 RDKit 与 xTB/CREST。源码中的其他可选后端不能直接计作正式任务覆盖。早期单镜像构想和公开 dev/mini/hidden test 划分不作为当前已交付事实。发行详情见 [RC 说明](../research/2026-10-28-v1.0.0-rc-release-notes.md)。

## 9. 科研能力声明的范围

本 benchmark 评价给定对象、目标、结构域、参考协议和评分规则下的求解结果。它不直接评价独立提出研究问题、选择研究方向、设计合成路线或执行实验的完整能力。

开放生成 verifier 得分不直接证明实验性质；性质计算参考答案比较不证明答题者执行过某个计算流程。评分端的工程回归、参考值的科学来源验证、数值重复性与模型表现是不同层次的证据，论文应分别说明。

## 10. 早期相关 Benchmark 调研

> 本节保留截至 2026-05-27 的调研记录。写作时需另外核实相关工作，不能把本节当作当前完整文献综述。

### 10.1 调研口径

本节调研 2024 年 5 月至 2026 年 5 月之间，用于评估大模型或智能体化学能力的代表性 benchmark。覆盖范围包括：

- 化学知识问答与考试型推理。
- 分子结构理解、SMILES/IUPAC/图像/图结构之间的转换、编辑和生成。
- 定量化学计算、谱图解析、反应机理和多步推理。
- 多模态化学与材料任务，包括谱图、晶体结构、实验装置和反应图。
- 化学安全、材料合成方案、分子工作流代码生成等更接近实践或 agent 使用场景的任务。

本节不把 MoleculeNet、TDC、Matbench 这类传统性质预测 benchmark 作为主要对象；它们更适合作为模型训练、校准、审校或 contamination 分析来源，而不是本项目正式运行时的性质查表 oracle。ChemLLMBench、ChemLLM ChemBench 等更早工作可作为背景参考，但本节重点放在近两年更明确面向 LLM、MLLM 或 agent 能力诊断的新 benchmark。

### 10.2 代表性 Benchmark 对比

| Benchmark | 时间与来源 | 主要评估能力 | 任务与数据设计 | 评价方式 | 对本项目的启发 |
|---|---:|---|---|---|---|
| [ChemBench](https://arxiv.org/abs/2404.01475) | 2024/2025，arXiv/Nature Chemistry | 化学知识、推理、计算、直觉和安全 | 2,788 个问答对，覆盖普通化学、无机、分析、材料、安全等主题；同时标注 topic、skill、difficulty；提供 ChemBench-Mini 子集 | 面向黑盒 text completion 的自动评测；严格判对；引入化学专家人类基线；支持工具增强系统 | benchmark 应有能力 taxonomy、难度层级、人工专家校验、可重复 runner、小型代表性子集和人类基线；不能只看总分 |
| [ChemBench 设计博客](https://www.chembench.org/blog/chembench) | 2024 | benchmark 工程规范 | 明确提出 end-to-end automation、expert validation、支持分子/方程特殊标记、支持黑盒系统、超越 MCQ、多主题覆盖 | 通过统一 pipeline 查询模型、人类子集和 leaderboard | 我们应把 evaluator 做成可重复运行的工程系统；题目和答案需保留化学语义标记；不能依赖 raw logits |
| [CACTUS](https://arxiv.org/abs/2405.00972) | 2024 | 化学工具增强 agent 能力 | LLM agent 集成 cheminformatics 工具，在数千个化学问题上评估；任务涉及分子性质、相似性搜索、drug-likeness 等 | 比较 open-source LLM 基线与工具增强 agent 的准确率 | agent benchmark 应明确工具集合、工具调用协议、硬件/模型配置和工具失败处理；工具增强分数不能与纯 LLM 分数混报 |
| [ChemSafetyBench](https://arxiv.org/abs/2411.16736) | 2024 | 化学安全、准确性、拒答边界、越狱鲁棒性 | 超过 30K 样本；三类任务：化学性质查询、用途合法性判断、合成方法描述；包含手写模板和 jailbreaking 场景 | 自动评估 safety、accuracy、appropriateness | 化学 benchmark 必须显式处理 dual-use 与安全拒答；危险合成、受控物质和误导性安全建议不应只按“答得完整”奖励 |
| [MaCBench](https://arxiv.org/abs/2411.16955) | 2024/2025 | 化学与材料多模态科学助手能力 | 真实化学/材料任务，覆盖数据抽取、实验理解、结果解释；包含谱图、实验装置、材料图像等视觉输入 | 系统评估 VLM 在感知、跨模态综合、多步推理上的失败模式 | 若引入图像或实验资料，应把“看懂图”和“化学推理”拆开诊断；真实科研图像比玩具图更能暴露能力边界 |
| [MolPuzzle](https://papers.nips.cc/paper_files/paper/2024/hash/f2b9e8e7a36d43ddfd3d55113d56b1e0-Abstract-Datasets_and_Benchmarks_Track.html) | 2024，NeurIPS Datasets and Benchmarks | 分子结构解析、谱图解释、多步假设检验 | 217 个结构解析实例，拆成超过 23,000 个 sequential QA；三个子任务：molecule understanding、spectrum interpretation、molecule construction | exact match 与分阶段评估；与人类表现对比 | 复杂化学任务应拆成可诊断子任务；最终答案低分时，需要知道失败来自结构理解、谱图解析还是构造候选 |
| [AlchemyBench](https://arxiv.org/abs/2502.16457) | 2025 | 材料合成实践任务 | 基于 17K+ 专家验证的材料合成 recipe；任务包括原料/设备预测、合成步骤生成、表征结果预测 | LLM-as-a-judge，并报告与专家评估的一致性 | 对开放过程类任务可使用 judge，但必须校准到专家评估；合成步骤类任务要保存 recipe provenance 和可复核评价维度 |
| [ChemIQ](https://pubs.acs.org/doi/full/10.1021/acs.jcim.5c02145) | 2025，JCIM | 有机分子结构理解与化学推理 | 816 个短答题；算法生成，覆盖 SMILES 理解、原子/路径计数、IUPAC、NMR 结构解析、Free-Wilson 分析等；使用 canonical/randomized SMILES | 短答自动判分；OPSIN 等工具解析 IUPAC；多次重复评估随机性 | 问题应尽量可程序生成和刷新以降低泄漏；短答优于 MCQ；必须处理同义 IUPAC、随机 SMILES 等等价表示 |
| [ChemCoTBench](https://arxiv.org/abs/2505.21318) | 2025 | 分子操作式逐步推理 | 1,495 个 benchmark 样本，22 类任务；把化学推理形式化为 SMILES 上的添加、删除、替换、优化、反应预测等模块化操作；另有 22K CoT 数据 | LLM 与 13 位化学专家混合验证；按任务类型和步骤诊断 | 对结构生成或优化任务，应把“可验证的化学操作”定义清楚；不必强制评估隐藏 CoT，但可以评估中间产物、编辑操作和最终结构 |
| [MolLangBench](https://arxiv.org/abs/2505.15054) | 2025/2026 | 语言提示下的分子识别、编辑、生成 | 识别任务由 cheminformatics 工具自动构造；编辑/生成任务由专家标注和验证；支持线性字符串、分子图像、分子图 | 确定性输出与专家校验结合；按 recognition/editing/generation 分项 | 开放生成前应先定义分子表示、等价性、编辑约束和可解析输出；生成任务比识别/编辑更需要 verifier |
| [QCBench](https://arxiv.org/abs/2508.01670) | 2025 | 定量化学计算与数学推理 | 350 个计算化学题，覆盖 7 个化学子领域；三档难度；每题源于真实化学场景，设计上避免启发式 shortcut | 数值答案评估，并按子领域与难度分析 | 数值类题必须记录单位、容差、有效数字和中间公式；应按难度和知识域报告，而非只报平均准确率 |
| [MOLERR2FIX](https://aclanthology.org/2025.emnlp-main.977.pdf) | 2025，EMNLP | 化学可信性、自检、错误定位与修正 | 1,193 个细粒度错误实例；每例包含 error type、span location、explanation、correction 四元标注 | 四阶段链式评估：detect、localize、explain、revise | 可信化学助手不能只会生成；benchmark 应包含“识别错误、定位错误、解释原因、修复输出”的诊断轨道或错误案例 |
| [SUPERChem](https://arxiv.org/abs/2512.01274) | 2025 | 专家级多步、多模态化学推理 | 500 个专家策划的高难题，覆盖多子领域；同时提供 multimodal 和 text-only 格式；原创题与迭代校验用于降低污染 | final-answer accuracy + Reasoning Path Fidelity；40.3% 人类基线 | 对高难推理，应同时记录最终答案和专家解题路径；如果评估过程质量，需把评分规则与专家路径显式化 |
| [ChemVTS-Bench](https://arxiv.org/abs/2511.17909) | 2025 | 视觉-文本-符号融合推理 | 覆盖有机分子、无机材料、3D 晶体结构；每题有 visual-only、visual-text hybrid、SMILES symbolic 三种输入模式 | 自动 agent workflow 标准化推理、答案验证、失败诊断 | 多模态题应设计平行输入形态，用来区分视觉瓶颈、符号推理瓶颈和跨模态融合瓶颈 |
| [ReactBench](https://arxiv.org/abs/2604.15994) | 2026 | 化学反应图中的拓扑推理 | 1,618 个专家标注 QA，来自真实反应图；覆盖线性、分支、汇合、循环等结构；四个层级任务维度 | 比较局部锚点任务与整体结构推理任务 | 对反应流程或合成路线图，不应只问局部元素识别；必须评估全局拓扑、分支依赖和路径一致性 |
| [MolViBench](https://arxiv.org/abs/2605.02351) | 2026 | 分子工作流代码生成与 agent-like 实践能力 | 358 个任务，5 个认知层级，12 类真实药物发现工作流；要求生成可执行分子程序 | 多层评估：可执行性、type-aware 输出比较、AST API semantic fallback、化学正确性 | 对 agent/tool-use 能力，最好评估可执行产物而不是自然语言解释；固定工具环境、依赖、输入输出 schema 和失败日志 |
| [ChemPro](https://arxiv.org/abs/2602.03108) | 2026 | 渐进式通用化学知识与考试能力 | 4,100 个自然语言问答对，四个难度段；MCQ 与数值题，覆盖生化、无机、有机、物化 | 大规模模型对比；按难度和问题类型分析 | 即使不是科研生成任务，也提示 benchmark 需要难度梯度；基础题可以作为 sanity check，但不应主导本项目初版 |

补充说明：2025 年的 oMeBench 曾提出有机反应机理 benchmark，但截至 2026-05-27，其 arXiv 页面显示该稿件已撤回，因此本设计不把它作为主要依据。反应机理方向仍可参考其“逐步中间体、步骤类型、相似性评分”的思想，但需要等待更稳定的数据与评价方案。

## 11. 从早期 Benchmark 调研提炼的设计规范

> §11.1–11.8 保留早期建议，包含尚未实现的能力、字段、数据划分和报告维度；不代表当前发布承诺。现行约定见 §11.9。

### 11.1 Benchmark 层面的规范

一个化学 LLM/agent benchmark 至少应明确以下 benchmark card：

- 评估目标：区分知识记忆、定量推理、结构理解、开放生成、工具使用、实验/合成规划、安全拒答等能力，不用一个总分笼统代表“化学能力”。
- 适用对象：纯文本 LLM、多模态模型、工具增强 agent、代码生成 agent 是否都可参加；若支持多个系统类型，输入输出协议必须一致。
- 工具政策：明确 tools-off、tools-on、retrieval-on、code-execution-on 等模式；同一 leaderboard 中不能混合不可比设置。
- 题目来源：人工原创、专家改写、算法生成、数据库抽样、文献抽取、真实实验记录等来源要逐项记录。
- 数据版本：每次发布需有版本号、发布日期、题目集版本、verifier image tag、辅助资产版本、隐藏测试集策略和变更记录。
- 安全政策：涉及受控物质、危险合成、毒性增强、规避监管等内容时，公开题面、标准答案和模型输出要经过双用途风险审查。
- 报告维度：必须按任务类型、化学子领域、难度、输入模态、对象类型和失败模式分项报告；总分只能作为附加摘要。

### 11.2 Task 层面的规范

每道题应有可机器读取的 task card，建议包含：

- `task_id`、`version`、`source_type`、`license`、`curator`、`reviewer`。
- `capability_tags`：例如 `structure_understanding`、`property_satisfaction`、`quantitative_reasoning`、`reaction_planning`、`safety_refusal`、`tool_use`。
- `chemistry_domain`：小分子、材料、反应、催化、光谱、量子化学、ADMET、实验操作等。
- `object_type` 与 `input_representation`：SMILES、InChI、IUPAC、CIF、composition、reaction SMILES、谱图、图像、表格、自然语言实验记录等。
- `prompt` 与 `allowed_context`：题面、允许使用的工具、是否允许联网、是否允许数据库检索辅助、是否允许多候选。
- `answer_schema`：模型最终答案必须满足的结构化格式，例如 JSON 字段、候选 SMILES 列表、候选 CIF、数值加单位、反应步骤数组。
- `verifier_spec`：评分依赖的 `verifier_image`、`verification_script`、固定模型或计算 workflow、资源上限、适用域和 failure policy。只有非 property-satisfaction 的辅助题型才可记录传统 `oracle` 或专家 rubric。
- `scoring`：二元正确、连续分数、窗口约束、步骤分、partial credit、refusal score、novelty score 等规则。
- `failure_policy`：无效结构、无法解析、单位缺失、多个互相矛盾答案、unsafe over-answer、超时、工具失败的处理方式。

### 11.3 数据构造与审校规范

- 至少两层质量控制：题目创建者之外，应有独立化学背景 reviewer 检查题面、答案、单位、边界条件和评分脚本。
- 自动生成题不能免除人工抽检；人工题也应尽量配套脚本验证标准答案。
- 对于 SMILES、IUPAC、CIF、reaction SMILES 等化学表示，答案库必须记录 canonicalization 规则和等价判定方式。
- 对多解问题，不应试图枚举所有正确答案；应定义 verifier、约束和评分函数。
- 题目创建阶段应显式检查目标性质是否能由公开数据库或数据集直接查值；如果可以直接查值，应改写为计算型性质、改用模型/计算 workflow 重新预测，或移出正式 property-satisfaction track。
- 数据集应包含容易题、中等题、困难题和少量 adversarial/edge cases，例如随机 SMILES、同分异构、盐、混合物、单位陷阱、不可合成结构、越狱式安全题。
- 应保留一个小型公开 dev 集、一个公开示例集、一个冻结公开 test 集，以及一个可周期更新或隐藏的 contamination-resistant test 集。
- 公开 release 应包含题目统计：领域分布、能力分布、难度分布、对象类型分布、数据来源分布、安全风险分布。

### 11.4 答案格式与解析规范

- 首选结构化输出，不把长篇自然语言解释作为唯一可评分对象。
- 数值题必须要求单位，并定义单位换算、容差、有效数字、四舍五入和区间答案规则。
- 分子与材料生成题必须要求候选对象的机器可读表示；模型自报的性质值只能作为辅助信息，不能作为评分依据。
- 若允许多个候选，应定义 `best-of-k`、平均分、去重、重复惩罚和 invalid candidate 的计分方式。
- 不应强制模型暴露隐藏推理轨迹作为主评分对象；如果需要过程质量，应评分可验证的中间产物、操作序列、路线图、代码执行结果或专家定义的 solution path fidelity。
- 对开放文本答案，只有在无法用程序 verifier 覆盖时才使用 LLM judge 或人工 rubric；且 judge 必须有专家一致性或抽样复核报告。

### 11.5 评分与 Verifier 规范

现有 benchmark 的共同趋势是从“答案字符串匹配”转向“可验证对象或可验证过程”。本项目的 verifier-grounded 设计应更严格地执行以下规范：

- Verifier 优先级：确定性工具/计算脚本 > 固定 ML 或 MLIP surrogate > 固定 workflow + 辅助 reference assets > 专家 rubric > LLM-as-a-judge。数据库查表不作为正式性质 verifier。
- 每个 verifier 必须固定 image tag、property-level 脚本入口、依赖、随机种子、输入预处理、输出单位、适用域规则和失败处理。
- 每个 task card 应能通过 constraints 追溯到一组 `verification_script`；runner 对单题和批量测试都按同一脚本契约执行，批量测试只是在调度层循环多道题，多目标任务只是在单题内部循环多个约束脚本。
- 对分子任务，至少执行 validity、canonicalization、duplicate、salt/mixture、charge、stereochemistry、heavy atom count 和 forbidden element 检查。
- 对材料任务，至少执行 composition validity、structure parsing、charge/oxidation sanity、cell/volume sanity、duplicate structure 和稳定性相关 gate。
- 对反应任务，至少执行 reaction parsing、atom mapping/mass balance、反应物/产物合法性和条件字段规范化。
- 对代码或 agent 任务，应同时评分 executability、chemical correctness、resource usage、runtime failure、unsafe action 和 reproducibility。
- 连续性质评分应避免硬二元阈值过多；推荐 hard validity gates + smooth property score + explicit penalty。
- 如果 verifier 是 ML surrogate，应报告训练数据来源、适用域、校准质量、已知 failure mode 和是否可能被 benchmark 题目污染，但运行时仍必须对候选对象执行固定模型推断，而不是查训练集或公开 benchmark 标签。

### 11.6 过程级与失败诊断规范

近两年的 benchmark 越来越强调“为什么错”而不是只记录“错了”。本项目应把失败诊断纳入 runner 输出：

- `parse_error`：无法解析结构、JSON、单位或文件。
- `validity_error`：化学对象无效、价态不合理、结构缺失、反应不守恒。
- `domain_error`：对象超出 verifier 适用域。
- `constraint_error`：候选有效但不满足目标性质约束。
- `reasoning_error`：中间产物或步骤与目标不一致，仅在任务提供可验证步骤时使用。
- `safety_error`：对危险请求过度配合，或在安全任务中拒答不足。
- `tool_error`：工具调用、代码执行或依赖失败。
- `verifier_timeout`：验证脚本超过题目或 spec 中定义的 timeout。
- `verifier_environment_error`：verifier image、脚本、模型 checkpoint 或辅助资产缺失。

最终 leaderboard 应能显示每个模型在哪类错误上失分，而不是只显示平均分。

### 11.7 多模态与实践任务规范

如果后续加入谱图、分子图像、晶体结构图、实验装置、反应路线图或论文图表，应遵守：

- 同一化学问题尽量设计 visual-only、visual-text、symbolic 三种输入，隔离感知、语义融合和符号推理能力。
- 图像数据应使用真实科研 artifact 或专家生成 artifact，并记录分辨率、裁剪、标注、OCR 文本泄漏和渲染方式。
- 结构图、反应图和谱图应保留可程序验证的底层结构或标签，用于自动判分和错误定位。
- 对实验/合成方案类任务，应区分“步骤文本合理”“原料设备完整”“条件可执行”“安全合规”“预期表征合理”等维度。
- 实践能力不要只靠自然语言评审；能执行的部分应执行，能被容器内工具、固定模型或计算 workflow 验证的部分应验证。

### 11.8 安全与双用途规范

化学 benchmark 必须把安全作为一等公民，而不是附属说明：

- 涉及危险化学品、受控物质、高毒物质、爆炸物、化学武器相关物质时，应定义允许回答、应拒答、应给安全替代信息的边界。
- 对安全任务的评分不能简单奖励信息量；应同时评分准确性、合规性、拒答质量和是否提供可操作危险步骤。
- 公开数据不应泄露可直接执行的危险合成细节；必要时使用 redacted answer、受控访问或只公开 meta-evaluation。
- 对 open-generation 任务，应加入 forbidden chemical space 或 safety gate，防止模型通过生成高风险候选获得高性质分。

### 11.9 现行设计约定

1. 开放生成与性质计算是两类互补的正式题型，分别使用运行时重算和冻结 gold 比较。
2. 所有任务有机器可解析的答案契约；评分面向最终结果，不以中间推理或工具调用轨迹为依据。
3. 工具中立与科学定义分开处理；影响目标含义的计算条件应明确，不能以容差代替定义。
4. 可连续度量的数值目标采用连续距离评分，结构/硬约束和离散字段保留显式判定。
5. 轻量化描述评分端的设计取舍；参考计算与参评系统求解成本分别报告。
6. 当前正式覆盖由 registry 与 task packs 定义，不根据可选 backend 清单推断。
7. 论文区分工程验收、参考值来源与模型实验结论；按任务类型报告结果，并说明综合分权重和实验配置。

## 12. 当前仓库实现对照

截至 2026-11-03，正式版本为 `1.0.0rc1`，对应 `v1.0.0-rc`，包含四个 track、100 道任务：

| Track | 题数 | basic / advanced | 回答与评价 |
| --- | ---: | --- | --- |
| `open_generation_rdkit` | 10 | 6 / 4 | 单个 SMILES；RDKit descriptor 或固定构象流程重算 |
| `open_generation_xtb` | 20 | 13 / 7 | 19 题 XYZ、1 题 SMILES；xTB/CREST 重算 |
| `property_calculation_basic` | 51 | 51 / 0 | 固定对象的数值或原子标识；gold 比较 |
| `property_calculation_advanced` | 19 | 0 / 19 | 固定对象的数值、标签或多字段答案；gold 比较 |

数据来自[正式 registry](../../src/verifier_grounded_benchmark/task/registry.py)及各 task pack；逐题信息见[注册任务清单](../benchmark_registered_tasks.md)。`basic`/`advanced` 是任务元数据，不自动对应模型成功率；定义见[难度标准](task-difficulty-levels.md)。

### 12.1 评价架构

唯一正式实现包为 `src/verifier_grounded_benchmark/`，`src/vgb/` 提供别名。

- `task/`：schema、registry、任务资源与加载。
- `evaluation/open_generation/`：候选解析、verifier 执行、性质证据与候选评分。
- `evaluation/property_calculation/`：答案解析、gold 比较与字段/分组评分。
- `evaluation/common/` 与 `evaluation/reporting/`：公共评分内核、失败/结果契约及覆盖率报告。
- `Track`/`Suite` 与 `vgb-score`：公开调用入口；模型执行由调用方负责。

### 12.2 正式运行时与配置

RDKit track 有 13 个 verifier specs，xTB track 有 15 个。xTB 001–013 使用 relaxation-energy quality gate；014–020 按各题声明处理，不自动加上该乘子。任务 020 接收 SMILES，由冻结 CREST/xTB 流程生成并搜索构象。

任务定义与评分配置分离：所有 track 有 `tasks.yaml` 和 `scoring.yaml`，仅开放生成提供 `verifier_specs.yaml`。当前 task schema 为 2、结果 schema 为 3、连续评分版本为 `linear_goal_v2`。详细协议见 [RDKit](../tracks/RDKit.md)、[xTB](../tracks/xTB.md)、[Basic](../tracks/PropertyCalculationBasic.md)和 [Advanced](../tracks/PropertyCalculationAdvanced.md)。

### 12.3 已记录的验证范围

[RC 验收记录](../../releases/v1.0.0-rc/VALIDATION.md)报告了核心测试、安装、资源一致性和评分边界检查。70 道性质计算的 gold round trips 验证评分器与配置的一致性，不是独立科学重算；该次 live xTB/CREST 回归使用 9 道输入，不代表覆盖全部 20 道题。重复 CREST 稳定性与跨平台数值等价性仍需对应的实验证据。

## 13. 后续论文材料与证据

研究主线已按 §1 确认。后续写作以当前题集与已执行证据为基础，分别处理：

- **实验解释**：记录模型与 harness 配置、工具/检索权限、预算和重复运行设置，分别报告两类任务及失败情况；不能从最终分数直接归因工具使用。
- **参考答案依据**：整理 gold 来源、科学协议与输入充分性。已知边界见[专家题转换记录](../research/2026-08-20-task14-25-property-calculation-conversion-plan.md)，不能把参考值冻结解释为所有题面都足以唯一重建参考值。
- **评分依据**：解释连续距离尺度、硬约束和离散规则，区分评分效用、数值重复性和方法间差异。
- **计算成本**：分别报告评分端、参考值生成和答题端成本；“适合个人计算机”的具体运行结论需说明实测环境与任务范围。
- **数据与相关工作**：说明 gold 可访问性和污染控制边界，并在写作时更新 §10 的历史文献调研；隐藏题库、新后端或新任务均需另外定义范围。
