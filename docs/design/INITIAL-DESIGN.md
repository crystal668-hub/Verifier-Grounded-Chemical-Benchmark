# Verifier-Grounded 化学 Benchmark 初始设计方案

日期：2026-05-26
更新：2026-05-27 补充近两年化学 LLM/agent benchmark 调研与设计规范提炼。
更新：2026-06-02 明确最终 verifier 以单一 Docker 镜像发布，并将正式题目收紧到可计算化学性质。
更新：2026-07-02 对照当前 repo 实现状态，明确 RDKit 与 xTB 两类题目已形成可复用雏形；AtomisticSkills MCP prototype 已移除，材料方向后续以 native Python 后端重新设计。

## 1. 项目动机

本项目希望构造一类新的化学 benchmark，用来评估大模型或化学智能体在真实科研式任务中的问题解决能力。当前已有化学 benchmark 的评价方式主要集中在两类：

1. 验证最终答案是否与标准答案一致，例如数值、选项、短文本或结构化答案匹配。
2. 根据回答是否覆盖指定知识点、步骤或 rubric 条目打分。

这两类评价方式适合考试题、知识问答、推导题或固定答案任务，但很难覆盖真实化学研究中常见的问题形态。实际科研任务经常不是“回答某个唯一答案”，而是“提出一个满足若干性质约束的化学对象”，例如：

- 给出一个具有指定药物样性质、溶解度和安全性约束的小分子。
- 设计一个 band gap 落在目标窗口且稳定性较好的材料。
- 提出一个满足特定低成本量子性质约束的分子候选。

这类任务天然允许多个有效答案，也不适合仅靠文本覆盖度判断回答质量。模型输出的关键不是解释是否听起来合理，而是候选对象本身是否真的满足目标性质。因此，本项目引入 verifier-grounded 的评价机制：由封装在官方 verifier Docker 镜像中的独立化学工具、固定模型和计算脚本重新验证候选对象性质，并基于性质偏差给出分数。

## 2. Benchmark 核心定位

本 benchmark 的核心形态是：

> Open-generation chemical property satisfaction benchmark。

也就是说，每道题给出一个具有真实化学研究价值的目标或约束，要求模型生成一个或多个候选化学对象。模型的最终答案应包含可被程序解析的候选对象标识，而不是只输出一个数值结论。

候选对象可以包括但不限于：

- 小分子：SMILES、InChI 或可规范化的化学名称。
- 材料：composition、CIF、pymatgen Structure 或其他可转换结构表示。
- 量子化学分子：SMILES 加可生成的 3D 构象，或明确的结构文件。
- 后续扩展中的反应或催化候选：reaction SMILES、催化剂结构、slab+adsorbate 表示等。

题目设计应围绕“有研究者实际关心并训练模型预测或用专业软件计算的性质”展开。如果某一性质在化学研究中经常被预测、筛选或优化，并且可以由稳定 verifier 自动计算或预测，就可以作为本 benchmark 的候选目标性质。正式题目应避免选择那类只要查询 PubChem、Materials Project、ChEMBL、TDC、Matbench 或类似数据库/数据集字段就能直接得到的性质；数据库可用于审校、构造 fixtures、参考 entries、novelty 检查或离线校准，但不应成为正式性质分数的 oracle。

## 3. 当前硬约束

初版 benchmark 只考虑 open-generation 题型，不引入 Candidate-selection track。

Candidate-selection 形式虽然工程上更容易控制，但如果候选项已经有限且固定，所有候选项性质可以预先计算，最终只需要程序判断选项是否正确。此时 verifier 的设计价值会显著降低，因为评价问题退化为传统的选择或排序任务。本项目要评估的是模型能否在开放空间中提出化学对象，并使该对象通过独立性质验证。

初版题目还应避免“数据库查值型 open generation”。如果候选对象的目标性质可以通过公开数据库字段、冻结 benchmark 标签或数据集查表直接得到，那么任务更接近 retrieval benchmark，而不是本项目关注的科研式可计算性质满足问题。正式评分应要求 verifier 对候选对象执行计算、模拟、结构处理或固定模型推断。

本 benchmark 的设计目标也不以区分 skills-on 和 skills-off 为核心。skills-on/skills-off 对比可以作为未来实验分支，但它不是 benchmark 题型、评价机制或题目选择的设计出发点。初版设计更关注如何解决现有化学 benchmark 难以评价真实开放生成科研任务的问题。

## 4. Verifier-Grounded 评价机制

每个正式评分约束应绑定一个可复现的验证脚本。验证脚本是某一化学性质或 descriptor 的计算入口：它读取模型给出的候选对象、task card 中的单个 constraint 和对应 verifier spec，在官方 verifier Docker 镜像内调用对应的计算后端，独立计算或预测该性质，然后根据候选对象与该约束之间的距离打分。

这里的“绑定验证脚本”应按所计算的化学性质或 descriptor 分类，而不是按 task id 复制或包装一套 verifier。对用户和 runner 来说，每个评分 constraint 必须能追溯到唯一、明确、可独立执行的 `verification_script`；当多道题或多目标题计算同一种性质时，它们应调用同一个脚本，并使用相同输入输出契约。对工程实现来说，这个脚本内部可以复用共享后端库或工具环境，例如 RDKit descriptor backend、xTB workflow、ADMET 模型、native MatGL backend 或未来 native MACE backend。也就是说，分层应是：

```text
task constraint/property -> verification_script -> shared backend/tool environment
```

runner 不应再维护“某类 verifier 到 Python 函数”的代码分发表；分发信息应来自 task/spec 中的脚本路径。共享后端只负责提供可复用计算能力，不能替代 property-level 验证脚本成为用户需要理解或选择的验证入口。

Verifier 不信任模型自报的性质值。即使模型在回答中声称某个分子 QED 为 0.82、logS 为 -2.1，评价时也只把候选对象本身作为输入，由 verifier 重新计算或预测这些性质。

最终发布形态应是一个单一官方 verifier image。用户测评模型时只需要拉取该镜像、构建运行容器，并把题目、答案和 verifier spec 传给 runner。单题测试和批量测试使用同一套评分逻辑：runner 只是在调度层逐题、逐约束执行对应验证脚本，多目标任务由 runner 聚合多个脚本返回的 constraint scores；脚本的执行后端全部来自容器内预装环境。需要注意的是，打包和发布这个官方镜像属于上线前的交付工作，不是当前设计与早期开发阶段必须完成的工程任务；当前阶段只需要把 task schema、verifier spec、脚本 I/O 和后端边界设计成能够自然迁移到该镜像形态，避免后续上线时重复重构。

一个完整的 verifier 评价流程包括：

1. 解析候选对象：检查 SMILES、CIF、reaction SMILES 或结构文件是否可解析。
2. 规范化候选对象：进行 canonicalization、去盐、选择主组分、结构合法性检查或材料结构标准化。
3. 适用域检查：确认候选对象属于 verifier 支持的化学空间。
4. 性质验证：运行容器内确定性工具、固定 ML 模型、计算化学脚本或材料模拟/MLIP workflow。
5. 距离打分：根据性质值与目标窗口、阈值或目标值之间的偏差计算分数。

验证脚本的 I/O 契约应保持稳定。输入是一个 JSON payload，至少包含：

- `task`：题目记录中的必要元信息，例如 `task_id`、版本和对象类型。
- `constraint`：当前验证脚本负责评分的单个性质约束，包括 `property`、约束类型、阈值或窗口参数，以及绑定的 verifier id。
- `verifier_spec`：verifier image、验证脚本路径、依赖版本、资源上限、后端参数、适用域和 scoring 参数。
- `candidate`：解析后的候选对象，例如 canonical SMILES、CIF/structure 文件路径、reaction SMILES 或结构化 JSON。

输出是一个 JSON result，至少包含：

- `status`：`ok` 或 `error`。
- `failure_type`：无错误时为 `null`；失败时使用统一 failure taxonomy。
- `properties`：verifier 计算出的性质值、单位和必要中间指标。
- `scores`：`validity_gate`、`domain_gate`、`constraint_scores`、`property_score` 和最终 `score`。
- `versions`：verifier image tag、脚本版本、工具版本、模型 checkpoint 或计算后端版本。
- `artifacts`：可选字段，用于记录构象、弛豫结构、日志、原始计算输出或诊断文件。

推荐的通用评分框架是：

```text
score = validity_gate
      * domain_gate
      * property_score
```

其中：

- `validity_gate` 判断候选对象是否有效、可解析、可规范化。
- `domain_gate` 判断候选对象是否落在 verifier 的适用范围内。
- `property_score` 衡量候选对象满足目标性质约束的程度。

性质打分可以采用不同形式：

- 窗口约束：性质落入 `[L, U]` 得满分，超出窗口按距离衰减。
- 目标值约束：使用 `exp(-abs(y - target) / sigma)` 之类的连续惩罚。
- 最大化或最小化目标：使用 clipped linear、logistic desirability 或排序型 desirability。
- 多目标约束：优先采用 hard constraints + soft objective；多个 soft score 可用几何平均或加权 desirability 合成。

## 5. 与常规 Benchmark 的差异

Verifier-grounded benchmark 与常规化学问答 benchmark 的关键区别在于评价对象不同。

常规 benchmark 通常评价：

- 最终答案是否等于标准答案。
- 回答是否覆盖参考解法中的关键点。
- LLM judge 是否认为回答合理。

本 benchmark 评价：

- 模型提出的候选化学对象是否有效。
- 候选对象是否属于题目要求的化学空间。
- 独立 verifier 计算出的性质是否满足目标约束。
- 候选对象与目标性质之间的偏差有多小。

因此，同一道题可以有多个满分或高分答案。评价不依赖某个唯一标准答案，也不要求模型复述某条固定推理路径。模型可以通过文献知识、结构类比、局部修改、性质预测、计算脚本或搜索优化得到候选对象；只要最终候选对象经 verifier 验证满足目标，就应获得相应分数。数据库检索可以是参评系统寻找候选的策略之一，但 benchmark 的正式性质评分不应退化为查表。

## 6. 设计收益

### 6.1 更贴近真实科研任务

真实化学研究经常是目标驱动的候选发现过程，而不是固定答案问答。Verifier-grounded 设计可以把“请提出一个满足性质约束的候选物质”转化为可自动评价的 benchmark 任务。

### 6.2 支持开放多解

传统标准答案评价很难处理多解问题。Verifier-grounded 设计不需要事先列出所有正确答案，只需要定义候选对象表示、目标性质和验证方式。

### 6.3 减少文本评分主观性

LLM judge 和 rubric 覆盖评分容易受到表达方式、答案长度和论证风格影响。Verifier-grounded 机制把评价重心转移到候选对象的可验证性质，减少纯文本判断带来的不稳定性。

### 6.4 允许连续分数

对于性质优化任务，二元正确/错误往往过于粗糙。候选对象即使没有完全满足目标，也可能接近目标窗口。距离型评分可以区分“完全无效”“方向正确但略偏”“基本满足”和“完全满足”等不同质量层级。

### 6.5 强化可复现性

每个 verifier 都应固定 verifier image tag、工具版本、模型 checkpoint、计算参数、输入规范和评分函数。这样 benchmark 分数可以在不同运行环境中复现，并能明确说明分数代表的是“满足该 verifier 定义下的性质目标”，而不是笼统证明实验上最优。若使用参考数据或数据库快照，它们只能作为计算 workflow 的辅助资产，例如相图 reference entries、去重集合、novelty 背景库或离线校准集，而不是直接返回目标性质分数的 oracle。

## 7. 初版推荐覆盖方向

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

这些性质在药物发现中有明确研究价值，也有大量已有模型。正式 verifier 应优先使用容器内可执行的固定 QSAR/ML 模型或软件，例如 ADMET-AI、OPERA、SolTranNet 或固定 Chemprop checkpoint；TDC、MoleculeNet、AqSolDB 等公开数据集可用于训练、校准或审校，但不作为题目运行时的性质查表 oracle。

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
| P0-2 | 水溶解度 logS | ADMET 价值高，输出连续，适合 open generation；应优先使用成熟开源 QSAR 工具或固定训练 checkpoint。 | 水溶解度直接影响 oral exposure、formulation 和 screening success，是 ADMET/QSPR 中常见的关键连续性质。 | 首选：OPERA WS、SolTranNet、ADMET-AI 或固定 Chemprop checkpoint；公开数据集仅用于训练/校准/审校。 |
| P0-3 | hERG/AMES/DILI 等 safety endpoint | 药物发现中真实重要，适合作为 hard safety constraint，而不是单独优化目标；正式评分应来自固定 endpoint 模型。 | hERG、mutagenicity、DILI、acute toxicity 是早期 safety triage 的关键 endpoint，可提升任务的真实药物发现约束强度。 | 首选：OPERA/CATMoS、ADMET-AI 或固定 Chemprop/QSAR checkpoint；TDC/MoleculeNet 只作训练、校准或审校来源。 |
| P0-4 | 材料 band gap | 材料 ML 最成熟性质之一，结构或成分输入清晰；正式题目应要求容器内模型或计算 workflow 对候选重新预测。 | band gap 是光伏、半导体、透明导体、光催化、绝缘材料设计的核心性质。 | 首选：MEGNet / MatGL 等固定 band-gap 模型；必要时使用小规模固定计算 workflow 作校准或交叉检查。 |
| P0-5 | formation energy / energy above hull | 是材料生成的基础 feasibility gate；没有稳定性评分，open-generation 材料题容易退化为无意义结构生成。 | formation energy 和 E above hull 是 computational materials discovery 中衡量热力学稳定性和可实现性的基础目标。 | 首选：CHGNet / M3GNet / MatGL / MACE relaxation 与 energy proxy；pymatgen PhaseDiagram 可使用固定 reference entries 计算 hull 距离。 |
| P0-6 | HOMO-LUMO gap | xTB 可本地运行，连续数值，成本低于 DFT；适合小分子开放生成，并能区分是否会调用工具。 | HOMO-LUMO gap 是光电、有机电子、反应性和稳定性 proxy 的常见量子性质。 | 首选：xTB/GFN2-xTB 固定版本 + RDKit ETKDG 构象生成 + cclib 或固定 parser。 |
| P0-7 | dipole / polarizability / partial-charge 指标 | xTB 和 cclib 可验证，能引导 agent 做结构层面的物理性质优化，而不只是查数据库；适合作为 secondary objective 或 physical descriptor task。 | dipole、polarizability 和 partial charges 影响 solvation、crystal packing、dielectric response、binding 与 force-field interaction modeling。 | 首选：xTB/GFN2-xTB 固定版本；cclib 解析 `atomcharges`、`moments`、`polarizabilities`。备选：OpenFF/RDKit charge models 仅用于低成本 charge sanity，不与 xTB charge 混合评分。 |
| P1-8 | ADME multi-endpoint：Caco-2/BBB/CYP/PPB/clearance | 真实药化价值高，但 endpoint 定义和模型适用域比 logS/hERG 更复杂；首版适合作为少量 multi-objective 题，不宜全面铺开。 | ADME 决定 exposure、drug-drug interaction、CNS penetration、oral absorption，是 lead optimization 的真实多目标核心。 | 首选：OPERA Caco-2、FuB、Clint、ADMET-AI 或固定 ADMET checkpoint；公开 ADMET 数据只用于训练/校准/审校。 |
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
| 困难 | 水溶解度 logS | P0-2 水溶解度 logS | 真实 logS 不能由 RDKit 公式可靠给出；首版应依赖成熟 QSAR 工具或固定训练 checkpoint。 | OPERA WS；SolTranNet；ADMET-AI；固定 Chemprop/QSAR checkpoint | [OPERA GitHub](https://github.com/NIEHS/OPERA)<br>[ADMET-AI GitHub](https://github.com/swansonk14/admet_ai) |
| 困难 | hERG / AMES / DILI 等 safety endpoint | P0-3 hERG/AMES/DILI 等 safety endpoint | 安全 endpoint 是实验标签上的 QSAR/ML 预测问题；正式评分需要固定模型版本和 applicability-domain 规则。 | OPERA/CATMoS；ADMET-AI；固定 Chemprop/QSAR checkpoint | [OPERA GitHub](https://github.com/NIEHS/OPERA)<br>[ADMET-AI GitHub](https://github.com/swansonk14/admet_ai) |
| 困难 | ADME multi-endpoint：Caco-2 / BBB / CYP / PPB / clearance | P1-8 ADME multi-endpoint | endpoint 定义、实验协议和适用域复杂，通常需要固定 QSAR/ML 模型。 | OPERA ADME models；ADMET-AI；固定 ADMET checkpoint | [OPERA GitHub](https://github.com/NIEHS/OPERA)<br>[ADMET-AI GitHub](https://github.com/swansonk14/admet_ai) |
| 困难 | 材料 band gap | P0-4 材料 band gap | 从头计算 band gap 通常需要 DFT；首版应使用固定 ML surrogate 或受限计算 workflow 对候选重新预测。 | MEGNet / MatGL fixed band-gap model；受限 DFT/MLIP proxy workflow | [MatGL docs](https://matgl.ai/)<br>[CHGNet GitHub](https://github.com/CederGroupHub/chgnet) |
| 困难 | formation energy / energy above hull | P0-5 formation energy / energy above hull | 可靠 E_hull 依赖一致 reference entries 和 candidate energy；新结构通常要 relaxation 和 energy model，因此比快速脚本更难。 | CHGNet / M3GNet / MatGL / MACE energy proxy；pymatgen PhaseDiagram with fixed reference entries | [pymatgen usage docs](https://pymatgen.org/usage.html)<br>[CHGNet GitHub](https://github.com/CederGroupHub/chgnet) |
| 困难 | 靶点活性 / binding affinity proxy | P1-9 靶点活性 / binding affinity proxy | 活性数据受 assay heterogeneity 和 leakage 影响；首版应只做窄域 fixed model 或固定 docking protocol。 | DeepDTA/DeepPurpose fixed checkpoint；AutoDock Vina fixed receptor/box/protocol | [DeepPurpose GitHub](https://github.com/kexinhuang12345/DeepPurpose)<br>[AutoDock Vina docs](https://autodock-vina.readthedocs.io/) |
| 困难 | adsorption energy / HER descriptor | P1-10 adsorption energy / HER descriptor | 从头 DFT relaxation 很慢；首版应限制 slab/adsorbate template，并使用固定 MLIP/OC 模型或受限计算 workflow。 | ASE fixed slab/adsorbate workflow；FairChem / GemNet-OC / EquiformerV2 fixed checkpoints | [ASE surface docs](https://ase-lib.org/ase/build/surface.html)<br>[FAIR-Chem docs](https://fair-chem.github.io/) |
| 困难 | atom mapping confidence / reaction-center validity | P1-11 中的 RXNMapper validity 子任务 | 如果只做 RDKit 解析是简单问题；若要求 atom mapping confidence 或 reaction center plausibility，则需要 RXNMapper 这类 ML mapper。 | RXNMapper；RDKit reaction validation | [RXNMapper GitHub](https://github.com/rxn4chemistry/rxnmapper)<br>[RDKit reaction docs](https://www.rdkit.org/docs/source/rdkit.Chem.rdChemReactions.html) |
| 困难 | retrosynthesis feasibility | P1-11 中的 retrosynthesis feasibility 子任务 | 需要 retrosynthesis planner、模板/策略模型和 fixed stock；结果高度依赖 stock 与 policy checkpoint。 | AiZynthFinder；fixed purchasable stock and policy | [AiZynthFinder docs](https://molecularai.github.io/aizynthfinder/)<br>[AiZynthFinder GitHub](https://github.com/MolecularAI/aizynthfinder) |
| 困难 | reaction yield | P1-11 中的 reaction yield 子任务 | 通用 yield prediction 不稳定；首版只能在固定 reaction family 和 fixed checkpoint 下使用。 | `rxn_yields` / Yield-BERT fixed checkpoint；family-specific fixed yield model | [rxn_yields GitHub](https://github.com/rxn4chemistry/rxn_yields) |

## 8. Verifier 的存在形态

正式 verifier 的发布形态应是一个单一官方 Docker 镜像，而不是让用户分别安装多个本地环境。镜像中预装首版任务需要的计算后端，例如 RDKit、pymatgen、xTB、OpenMM、ASE、cclib、固定 QSAR/ADMET 模型、固定材料 ML 模型、MLIP calculator 和必要的脚本运行环境。

这一镜像形态是最终交付约束，用于指导当前 schema、脚本边界和后端组织方式；它不要求当前开发阶段立即完成镜像构建、发布或完整环境封装。当前开发可以先在本地 Python 环境中实现脚本契约和共享后端，只要这些入口未来可以直接放入官方镜像中运行。

每道题通过 constraints 中的 verifier id 绑定一组 property-level 验证脚本。单目标任务通常只绑定一个脚本；多目标任务绑定多个脚本，并由 runner 在调度层顺序执行后聚合分数。脚本按所计算的化学性质或 descriptor 分类，而不是按 task id 分类；多个任务只要计算同一种性质，就应复用同一个脚本。多个 property-level 脚本可以共享以下类型的后端能力：

1. 确定性工具：例如 RDKit、pymatgen、xTB、OpenMM、ASE、cclib。
2. 固定 ML 模型：例如 ADMET-AI、Chemprop checkpoint、SolTranNet、OPERA、CHGNet、MACE、MatterSim。
3. 固定计算 workflow：例如 RDKit ETKDG + xTB、MLIP relaxation + energy proxy、pymatgen PhaseDiagram + fixed reference entries、固定受体/参数的 docking workflow。

数据库、数据集和外部 API 不作为正式性质分数的直接 oracle。它们可以作为离线资产进入镜像或发布包，用于 reference entries、fixtures、去重/novelty 背景库、applicability-domain 统计、模型训练/校准或人工审校记录。若某个题目的目标性质只能靠查数据库标签得到，该题不应进入正式 open-generation property satisfaction track。

为了保证 benchmark 可复现，每个 verifier spec 至少需要记录：

- verifier 名称、版本和 `verifier_image` tag。
- 对应性质或 descriptor 的 `verification_script` 路径、脚本版本和入口命令。
- 工具、模型或计算 workflow 来源。
- model checkpoint、reference entries、fixed stock 或其他辅助资产标识。
- 输入格式、candidate schema 和规范化规则。
- 输出性质名称、单位和取值范围。
- 适用域规则。
- 评分函数和参数。
- 资源需求，例如 CPU/GPU、内存、timeout、最大候选数和临时文件限制。
- 失败时的处理规则。

正式评分不依赖在线服务。在线服务可以用于调研、题目审校或离线交叉检查，但不能作为 benchmark 运行时的唯一评价路径，也不能让同一题的性质值随在线数据库更新而漂移。

## 9. 当前不纳入范围

初版明确不纳入以下内容：

- Candidate-selection 题型。
- 把 Candidate-selection 作为 calibration、debug 或 sanity check。
- 把只需数据库字段查值的性质作为正式 open-generation 评分目标。
- 以区分 skills-on 和 skills-off 为 benchmark 设计目标。
- 证明某个候选物实验上最优、催化活性最好或药物开发价值最高。
- 依赖在线服务或数据库查询作为正式运行时 verifier。
- 要求模型输出或暴露真实推理轨迹，并以推理轨迹是否符合某条固定路径为主要评分依据。

本 benchmark 验证的是：在给定 verifier 定义的目标性质下，模型是否能提出满足这些性质的候选化学对象。

## 10. 近两年相关 Benchmark 调研

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

## 11. 从现有 Benchmark 提炼的设计规范

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

### 11.9 对本项目的直接设计约束

基于上述调研，本 verifier-grounded benchmark 初版应采用以下约束：

1. 继续坚持 open-generation，不把 MCQ 或 candidate-selection 作为核心题型。
2. 每道题必须有结构化 answer schema，最终评分只信任候选对象和 verifier，不信任模型自报性质。
3. 正式题目应聚焦可计算化学性质，避免把数据库/数据集字段查值作为目标性质 oracle。
4. 首批题目应先覆盖小分子、材料和低成本量子性质三个可自动验证方向，避免过早进入难以复现的通用实验方案评分。
5. 每个任务都要有能力标签、对象类型、难度标签、verifier 标签、constraint 级 `verification_script` 追踪关系和失败模式标签。
6. 每个 verifier 都要有可复现 spec，记录 `verifier_image`、property-level 脚本入口、固定模型或计算 workflow、资源上限和 failure policy；如果使用 LLM judge，只能作为人工 rubric 的扩展或材料合成类开放过程任务的辅助评价，并需要专家一致性校准。
7. Runner 输出应保存原始回答、解析结果、规范化候选、verifier 输出、分项分数、失败类型、依赖版本和可选 artifacts。
8. Leaderboard 不应只发布总分；至少按 validity、domain pass rate、property satisfaction、novelty、安全 gate、任务类别分别报告。
9. 数据发布要包含公开 dev 集、代表性 mini 集和冻结 test 集；后续若公开 leaderboard，应保留隐藏或周期更新题库以缓解污染。

## 12. 当前 repo 实现对照

截至 2026-06-11，当前 repo 已经从纯设计草案进入早期可运行实现阶段。总体工程形态已经基本对齐本文第 4 节和第 8 节提出的分层原则：

```text
task pack -> constraints/verifier_id -> verifier_specs.yaml -> property-level verification_script -> shared backend/tool environment
```

当前 runner 已不依赖中心化 Python verifier registry，而是从 task/spec 中读取 `verification_script` 路径，构造 JSON payload 后通过子进程执行对应脚本。`benchmark/answer_extraction.py` 负责把 raw model response 归一化为 verifier-ready candidate，`benchmark/verifier_scripts.py` 负责脚本 payload 与执行，`benchmark/evaluate.py` 负责逐约束路由、多目标聚合和摘要输出，`scripts/score_answers.py` 提供命令行批量评分入口。

### 12.1 已形成雏形：RDKit 小分子 descriptor 题

`tasks/rdkit_baseline/` 已经形成首个稳定模板：

- `tasks.yaml` 定义 open-generation 小分子题面、`FINAL ANSWER: <SMILES>` 答案格式、domain 约束、单目标和多目标 constraint。
- `verifier_specs.yaml` 将每个 descriptor 绑定到 property-level 脚本，例如 `verifiers/descriptors/rdkit_qed.py`、`rdkit_logp.py`、`rdkit_tpsa.py`、`rdkit_sa_score.py` 等。
- `verifiers/backends/rdkit_descriptors.py` 复用 RDKit descriptor 计算、SMILES 解析、canonicalization、domain gate 和通用 scoring。
- 测试覆盖了答案抽取、脚本路由、多约束聚合、descriptor 后端和 CLI 批量评分。

这部分已经可以作为后续确定性 small-molecule verifier 的参考模式。后续如果接入更多 RDKit 或类似低成本 descriptor，应优先复用这套组织方式：一个性质一个 property-level 脚本，多个脚本共享后端，题目只通过 constraint 绑定 verifier id。

### 12.2 已形成雏形：xTB direct-XYZ 低成本量子题

`tasks/xtb_xyz/` 已经形成第二个可复用模板：

- 题目要求模型直接输出 fenced `xyz` block，而不是只输出 SMILES 或自报性质。
- 当前包含 13 个 formal tasks，覆盖 HOMO-LUMO gap、dipole moment、LUMO、polarizability/dipole、ALPB solvation selectivity、global electrophilicity、Fukui carbon-site response 和 hessian thermochemistry。
- 当前包含 9 个 verifier specs，包括 gap、dipole、relaxation energy、LUMO、polarizability、ALPB selectivity、electrophilicity、Fukui 和 hessian thermo；每个 spec 绑定对应的 property-level `verifiers/xtb/*.py` 脚本。
- `verifiers/backends/xtb_properties.py` 负责 XYZ 解析、元素和几何 domain 检查、连通性检查、xTB CLI 调用、输出解析、runner failure 映射和 scoring。
- relaxation energy 已作为 direct-XYZ 几何质量 gate 接入聚合逻辑，避免模型提交粗糙或非低能构型只靠优化后性质得分。

这部分代表了“需要外部本地计算工具，但仍可用 property-level script + shared backend 固化”的设计路径。后续接入其他计算化学 verifier 时，应优先参考 xTB 的模式：把候选对象格式、计算前 domain gate、工具失败 taxonomy、资源上限和质量 gate 写入 spec，而不是把这些逻辑散落在题目或 runner 中。

### 12.3 材料类 verifier 的当前边界

AtomisticSkills MCP、MACE MCP 和 MatGL MCP prototype 已从当前 active codebase 中移除。当前正式发布面仍以 RDKit 与 xTB 为主；材料方向不再保留依赖外部 AtomisticSkills checkout、MCP server 或 agent-specific conda environment 的可执行路径。

保留的材料方向基础是 native MatGL Python backend：`verifiers/backends/matgl_properties.py` 与 `verifiers/materials/matgl_*.py`。这部分用于后续正式 MatGL task specs 的实现基础，但当前不作为内置正式 track 发布，也不复用已删除的 Si-only MCP prototype task pack。

MACE 将在 native Python backend、模型版本冻结、候选材料 domain、资源模型和正式 task design 明确后重新接入。后续材料类正式题目应参考 RDKit 与 xTB 已成型的分层结构，重新完成材料 verifier 的题目设计、domain 设计、资源约束和正式 failure policy。

## 13. 后续待讨论项

后续讨论应从“是否采用 verifier-grounded 方案”转向“如何把已验证的 RDKit/xTB 模式推广到更多 verifier，并避免实验性 MCP 工具误入正式题目”。优先级如下。

### 13.1 P0：固化已成型实现为正式规范

- 将当前 task card、answer schema、verifier spec 和 result JSON 的实际字段整理成版本化 schema 文档，明确哪些字段为必填、哪些是实验字段。
- 明确 property-level `verification_script` 的稳定 I/O 契约，包括 payload 字段、标准 result 字段、失败类型、版本字段和 artifacts 字段。
- 把 RDKit 与 xTB 作为首批正式模板写入开发规范：新 verifier 必须说明它参考哪一类模板，或解释为什么需要新增模板。
- 统一 `formal_track`、`experimental_smoke`、`prototype` 等状态标记，避免未来材料类实验题目被误认为已完成正式设计。
- 明确多目标聚合规则、quality gate 规则和 bounded scoring 的边界，特别是 `role: quality_gate` 与普通 property score 的关系。
- 补充公开 dev/sample/test 题集的拆分规则，并说明 sample answers 只用于 smoke/regression，不代表 leaderboard 标准答案集合。

### 13.2 P0：补齐正式发布与可复现运行边界

- 设计单一官方 verifier image 的构建、tag、发布和兼容性策略。
- 明确哪些依赖必须进入镜像，哪些可以是外部可选依赖；xTB、native MatGL、未来 native MACE 这类本地工具需要有清晰的降级和环境错误报告。
- 为每个 verifier spec 固定工具版本、模型 checkpoint、reference assets、资源上限和 timeout 语义。
- 明确 CI 中哪些测试必须完全离线、哪些是环境 smoke test、哪些需要手动或 nightly 运行。
- 形成环境检查脚本的统一命名、输出 JSON 格式和 failure message 规范。

### 13.3 P1：材料类 verifier 的正式设计

- 重新设计 MACE 与 MatGL 正式任务，不沿用已移除的 Si-only MCP prototype。需要确定候选材料空间、结构大小、允许元素、晶胞 sanity、去重规则和 domain gate。
- 明确 MatGL band gap、MatGL formation energy、MACE energy 等性质的科学含义、单位、模型输出 convention、适用域和评分窗口。
- 判断材料题是否需要 relaxation、energy above hull、fixed reference entries 或其他稳定性 gate；如果需要，应明确 reference asset 的冻结方式。

### 13.4 P1：扩展 verifier 接入规则

- 新接入 ADMET、QSAR、材料 MLIP、docking、reaction validity 或 retrosynthesis verifier 时，应先写最小 task pack、verifier spec、property-level script、shared backend 和 fake-runner 测试，再扩大题目数量。
- 每个新 verifier 都必须先回答：候选对象表示是什么、目标性质是否可运行时重新计算、是否存在数据库查值捷径、适用域如何定义、失败如何分类。
- 对 ML surrogate verifier，需要记录训练数据来源、模型 checkpoint、校准质量、已知 failure mode 和 contamination 风险。
- 对反应、催化和合成路线任务，应先完成输入 schema 和安全 policy，再讨论正式评分。

### 13.5 P2：评价协议与 leaderboard

- 明确多候选答案的计分方式，包括 best-of-k、重复候选、invalid candidate、候选顺序和预算限制。
- 设计 novelty、leakage、applicability-domain 统计规则，避免正式分数被数据库记忆或训练集污染主导。
- 定义 leaderboard 报告维度：validity pass rate、domain pass rate、property score、quality gate、tool/environment failure、任务类别和对象类型。
- 明确 benchmark runner 与现有 OpenClaw benchmark 体系的集成方式，包括输入输出文件格式、批量调度、日志和 artifacts 保存。
- 设计隐藏或周期更新题库策略，避免开放生成任务在公开 sample 上过拟合。
