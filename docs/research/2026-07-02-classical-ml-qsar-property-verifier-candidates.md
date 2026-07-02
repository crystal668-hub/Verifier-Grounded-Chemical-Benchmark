# 经典 QSAR/QSPR 与早期机器学习性质预测 verifier 候选清单

日期：2026-07-02

## 1. 调研口径

本文件补充 `2026-06-30-end-to-end-property-ml-model-candidates.md`。前一份清单
已经覆盖了大量近年深度学习、图网络、foundation model 和材料 MLIP 候选；本文件
刻意把检索视线放到更早期、更传统、在监管或药物化学工作流中使用率较高的
QSAR/QSPR、read-across、片段贡献、随机森林、SVM、kNN、PLS、朴素贝叶斯、
专家规则和早期神经网络模型。

纳入候选的共同条件：

1. 输入可以是 SMILES、SDF/MOL、CAS+结构、3D 结构、composition 或其他明确化学表示。
2. 输出是化学/材料性质、ADMET、毒性、环境归趋、代谢位点、靶点概率或类似可评分
   预测结果。
3. 有明确项目地址、文档、软件下载页、API、CLI、Web 服务或商业部署路径。
4. 在领域内有相对较高使用率，证据包括监管引用、长期维护、商业/工业使用、论文影响力、
   常用教学/工作流或模型库生态。
5. 适合被包装为 property-level verifier script，至少能在固定版本、固定输入规范和固定
   scoring policy 下复现预测。

排除或降级原则：

- 只返回数据库已有实验标签的系统不能作为正式 verifier oracle；它们只能用于审校、校准、
  novelty 检查或训练集污染分析。
- 只计算结构描述符而没有 endpoint 语义的工具不单独计入性质预测模型；但 logP、logS、pKa、
  vapor pressure、BCF、Cramer class 这类由结构到性质的模型可计入。
- Web-only 服务如果没有官方本地包或稳定 API，先列为 P2 研究储备，不建议首版 verifier
  直接依赖公网。
- 商业工具可以列入候选，但必须在风险中标出许可、CI/容器化和版本锁定问题。

## 2. 对 verifier 设计的含义

这批候选与当前 RDKit/xTB/材料计算软件类 backend 的区别是：它们通常不做从头计算，
而是把候选结构端到端送入一个固定 QSAR/QSPR 模型或专家规则系统，直接输出目标性质。
这很适合构造低成本、多 endpoint 的小分子任务，例如：

- 生成一个低 Ames / 低 hERG / 高水溶解度的小分子。
- 生成一个低 BCF / 易降解 / 低水生毒性的环境化学品候选。
- 生成一个 pKa、logD、Caco-2、BBB 或 plasma protein binding 落入目标窗口的候选。
- 生成一个满足 Cramer class、TTC 或结构警示约束的食品接触/香料/杂质候选。

正式进入 verifier image 前，每个候选仍要固定：

- 软件/模型版本、安装包来源、许可证和可再分发性。
- endpoint id、单位、分类阈值、概率含义和适用域字段。
- 输入标准化规则，例如盐处理、tautomer、isotope、mixture、charge、SMILES canonicalization。
- 模型失败时的 failure taxonomy，例如 parse error、out of domain、tool error、timeout。
- 是否会联网、是否会查数据库标签、是否包含候选结构的实验值泄漏。

## 3. 候选清单

优先级含义：

- P0：最值得优先验证或已经与当前设计高度贴合。
- P1：科学价值高，但部署、许可或 endpoint 选择需要进一步收敛。
- P2：可作为研究储备、交叉验证、Web-only 参考或特定窄域任务候选。

| # | 候选模型/工具 | 优先级 | 方法时代/模型家族 | 输入 | 可预测内容 | 部署与使用路径 | Verifier 适配价值 | 主要风险 |
|---:|---|---|---|---|---|---|---|---|
| 1 | [US EPA TEST](https://www.epa.gov/comptox-tools/toxicity-estimation-software-tool-test) | P0/P1 | 2000s-2010s QSAR；hierarchical clustering、FDA、nearest-neighbor、consensus 等 | 结构文件、SMILES/绘图、批量 SDF | Rat oral LD50、Ames、developmental toxicity、fathead minnow LC50、Daphnia、Tetrahymena、BCF、物化性质等 | EPA 免费下载；v5.1.2 页面提供安装包；v4.2.1 仍有 Windows/Mac/Linux zip；GUI/批量模式，需确认 headless 调度 | 经典、监管语境强、endpoint 明确，适合作为毒性与物化性质固定模型 verifier | 现代版本 headless/CLI 能力需实测；训练集包含公开化合物，需 novelty gate；EPA 明示仅估算且无适用性保证 |
| 2 | [VEGA QSAR](https://www.vegahub.eu/portfolio-types/in-silico-models/) | P0/P1 | 2000s-2010s CAESAR/IRFMN/KNN/read-across/CORAL/OPERA 等 QSAR 集成 | SMILES、SDF 等 | Mutagenicity、carcinogenicity、skin sensitization、BCF、fish/Daphnia/algae toxicity、persistence、logP、WS、KOC、Henry、KOA、PPB 等 | VEGAHUB 免费 standalone/online；Java 应用；OECD Toolbox 也有 VEGA plugin | 模型多、适用域和 reliability 输出丰富，适合保守 toxicology/ecotox verifier | 单个模型版本、QMRF、插件 id 和输出列必须逐项冻结；批量无 GUI 调度需实测 |
| 3 | [OECD QSAR Toolbox](https://qsartoolbox.org/) | P1/P2 | 2008 起的监管 read-across/QSAR 平台；v4.8 含 254 (Q)SAR 模型 | 结构、IUCLID/批量导入 | 物化、环境归趋、生态毒理、人类健康 hazard；skin sensitisation、Ames、aquatic tox 等 | 免费 standalone；有 API/WebAPI/Server 手册和 repository plugins | 很适合做监管风格 read-across/QSAR 对照和报告生成 | 容易退化为查询实验数据库或 read-across 专家流程；正式 verifier 只能选择固定 external QSAR/data-gap workflow |
| 4 | [EPI Suite KOWWIN](https://www.epa.gov/tsca-screening-tools/epi-suitetm-estimation-program-interface) | P0/P1 | 1990s-2000s atom/fragment contribution QSPR | SMILES、CAS/name+结构 | log octanol-water partition coefficient, logKow | Windows EPI Suite v4.11 或 EPA web beta；单输入运行全套模型 | 经典 logP/logKow verifier，速度低、解释性强，可和 RDKit Crippen/OPERA 交叉 | Windows-only 官方桌面版；web beta 不宜作为冻结 oracle；CAS lookup 模式不能用于正式评分 |
| 5 | [EPI Suite WSKOWWIN/WATERNT](https://www.epa.gov/tsca-screening-tools/epi-suitetm-estimation-program-interface) | P0/P1 | Fragment/fragment-constant water-solubility QSPR | SMILES、CAS/name+结构 | Water solubility；WSKOWWIN 通过 logKow 和修正因子，WATERNT 直接 fragment method | 随 EPI Suite 安装或 web beta | 可作为传统 logS/water solubility verifier，与 OPERA/ADMET-AI/SolTranNet 形成模型多样性 | 同 EPI Suite 部署风险；不同 solubility 定义和单位需固定 |
| 6 | [EPI Suite MPBPWIN](https://www.epa.gov/tsca-screening-tools/epi-suitetm-estimation-program-interface) | P1 | Group contribution / QSPR | SMILES、CAS/name+结构 | Melting point、boiling point、vapor pressure、subcooled liquid vapor pressure | 随 EPI Suite 安装或 web beta | 可构造挥发性、物化窗口类开放生成题 | MP/BP 预测误差和结构域风险较高；单位与温度条件要写清 |
| 7 | [EPI Suite HENRYWIN](https://www.epa.gov/tsca-screening-tools/epi-suitetm-estimation-program-interface) | P1 | Group/bond contribution QSPR | SMILES、CAS/name+结构 | Henry's law constant / air-water partition | 随 EPI Suite 安装或 web beta | 适合环境归趋、挥发迁移类 verifier | 离子化、水反应性和温度条件需要 domain gate |
| 8 | [EPI Suite AOPWIN](https://www.epa.gov/tsca-screening-tools/epi-suitetm-estimation-program-interface) | P1 | Atmospheric oxidation SAR/QSPR | SMILES、CAS/name+结构 | OH radical reaction rate、ozone reaction rate、atmospheric half-life | 随 EPI Suite 安装或 web beta | 可做低大气持久性候选设计 | 只适合挥发性有机物和特定反应类别；环境浓度假设需固定 |
| 9 | [EPI Suite BIOWIN/BioHCwin](https://www.epa.gov/tsca-screening-tools/epi-suitetm-estimation-program-interface) | P0/P1 | Rule/linear/nonlinear biodegradation models | SMILES、CAS/name+结构 | Aerobic/anaerobic biodegradability、ready biodegradation probability、hydrocarbon biodegradation half-life | 随 EPI Suite 安装或 web beta | 适合可降解/低持久性任务，是环境化学端到端性质预测强候选 | endpoint 是 screening-level 概率/分类；需避免把结果解释成实验半衰期 |
| 10 | [EPI Suite KOCWIN](https://www.epa.gov/tsca-screening-tools/epi-suitetm-estimation-program-interface) | P1 | Molecular connectivity + logKow-based QSPR | SMILES、CAS/name+结构 | Soil/sediment organic carbon sorption coefficient Koc | 随 EPI Suite 安装或 web beta | 可做土壤迁移性/吸附性目标 | 离子化、有机盐和表面活性剂适用域需限制 |
| 11 | [EPI Suite BCFBAF](https://www.epa.gov/tsca-screening-tools/epi-suitetm-estimation-program-interface) | P0/P1 | Regression + Arnot-Gobas bioaccumulation model | SMILES、CAS/name+结构 | Fish BCF/BAF、metabolism half-life、trophic level bioaccumulation | 随 EPI Suite 安装或 web beta | 环境 bioaccumulation verifier 价值高，可设低 BCF/BAF 约束 | 对 ionized/surfactant/metal-containing 化合物不稳；输出多模型需选定 |
| 12 | [EPI Suite HYDROWIN](https://www.epa.gov/tsca-screening-tools/epi-suitetm-estimation-program-interface) | P1 | Hydrolysis class-specific SAR | SMILES、CAS/name+结构 | Aqueous hydrolysis rate constants and half-lives | 随 EPI Suite 安装或 web beta | 可做水解稳定性或易降解性约束 | 只覆盖特定可水解官能团；pH/温度条件必须固定 |
| 13 | [EPI Suite KOAWIN](https://www.epa.gov/tsca-screening-tools/epi-suitetm-estimation-program-interface) | P1 | Partition-coefficient QSPR | SMILES、CAS/name+结构 | Octanol-air partition coefficient KOA | 随 EPI Suite 安装或 web beta | 可补 POPs/环境分配任务 | 依赖 logKow/Henry 估算链，误差传播要记录 |
| 14 | [EPI Suite AEROWIN/WVOLWIN](https://www.epa.gov/tsca-screening-tools/epi-suitetm-estimation-program-interface) | P2 | Aerosol sorption and water volatilization screening models | SMILES、CAS/name+结构 | Airborne particulate sorption、volatilization from rivers/lakes | 随 EPI Suite 安装或 web beta | 可做环境迁移模型储备 | 更像场景模型，不是单纯分子性质；场景参数要冻结 |
| 15 | [EPI Suite STPWIN](https://www.epa.gov/tsca-screening-tools/epi-suitetm-estimation-program-interface) | P2 | Sewage treatment fate model | SMILES、CAS/name+结构 | Activated sludge removal、biodegradation/sorption/air stripping fractions | 随 EPI Suite 安装或 web beta | 可做污水处理去除率任务储备 | 场景假设强；不宜作为首版普适分子性质 oracle |
| 16 | [EPI Suite LEV3EPI](https://www.epa.gov/tsca-screening-tools/epi-suitetm-estimation-program-interface) | P2 | Level III fugacity multimedia fate model | SMILES、CAS/name+结构 | Air/water/soil/sediment steady-state partitioning | 随 EPI Suite 安装或 web beta | 可做环境归趋 multi-compartment 任务储备 | 环境模型参数比结构模型更关键；不宜无场景说明直接评分 |
| 17 | [US EPA ECOSAR](https://www.epa.gov/tsca-screening-tools/ecological-structure-activity-relationships-ecosar-predictive-model) | P0/P1 | Class-based aquatic ecotoxicity QSAR | SMILES、CAS/name+结构 | Acute/chronic aquatic toxicity for fish, daphnids, algae and other classes | EPI Suite 内置，也可单独下载；Windows/software path | 水生毒性 endpoint 明确，适合低生态毒性候选约束 | 化学类别识别和 logKow 依赖强；需固定 class selection 和 endpoint |
| 18 | [Toxtree Cramer/TTC](https://toxtree.sourceforge.net/) | P0/P1 | 1978 Cramer decision tree + extensions/revised tree | SMILES、SDF、MOL、绘图 | Cramer class I/II/III、TTC hazard class | Java standalone；open-source；Toxtree 3.1.0/2.6.x | 很适合快速 toxicity gate，输出离散、可解释、可本地固定 | 是 hazard class 不是实验毒性值；金属、聚合物、混合物等应排除 |
| 19 | [Toxtree Benigni-Bossa](https://toxtree.sourceforge.net/carc.html) | P0/P1 | Structural alerts + QSAR/discriminant analysis | SMILES、SDF、MOL | Mutagenicity/carcinogenicity alerts and classes | Toxtree plugin | 可作为 genotox structural-alert verifier，与 Ames ML 模型互补 | 告警不是定量概率；false positive/negative 需与任务阈值谨慎绑定 |
| 20 | [Toxtree Verhaar / Modified Verhaar](https://toxtree.sourceforge.net/) | P1 | Aquatic toxicity mode-of-action decision tree | SMILES、SDF、MOL | Aquatic toxicity mode of action class | Toxtree plugin | 可辅助 ECOSAR/TEST aquatic tox 适用域和 MOA gate | 输出是 MOA 分类，不直接给 LC50；适合辅助 verifier |
| 21 | [Toxtree skin/eye/protein/DNA alerts](https://toxtree.sourceforge.net/) | P1/P2 | Structural alerts and decision trees | SMILES、SDF、MOL | Skin/eye irritation, skin sensitisation reactivity domains, protein/DNA binding alerts | Toxtree plugins | 可做反应性和结构警示 gate | 多为 alert/profiler，不能当作高精度实验 endpoint |
| 22 | [SMARTCyp](https://toxtree.sourceforge.net/) | P1/P2 | Semi-empirical/fragment/ML-like site-of-metabolism scoring | SMILES、SDF/MOL | CYP-mediated site-of-metabolism ranking, often CYP3A4/2D6/2C9 | Java tool；Toxtree 也集成 SMARTCyp/metabolite prediction plugin | 可构造代谢软点规避或 site-of-metabolism 任务 | per-atom ranking 不等于 clearance；需要固定 CYP isoform 和评分输出 |
| 23 | [lazar](https://pmc.ncbi.nlm.nih.gov/articles/PMC3669891/) | P1 | Lazy structure-activity relationships；local QSAR/read-across | SMILES/structure | Mutagenicity、carcinogenicity、acute toxicity、NOAEL/LOAEL、BBB 等可用模型 | Web/REST/OpenRiskNet 记录；source linked in QMRF/OpenTox ecosystem | 早期可解释 local QSAR，带 applicability domain 和近邻依据 | 活跃部署状态需复核；某些服务需要登录；正式使用应自托管固定模型 |
| 24 | [AMBIT / OpenTox models](https://ambit.sourceforge.net/) | P1/P2 | OpenTox QSAR service framework; descriptor/ML/model wrappers | SMILES、SDF、REST chemical representation | Toxicity、physchem、read-across/QSAR endpoints depending installed models | Open-source server/REST API；可接 Toxtree、model services、datasets | 技术上适合做本地 QSAR service backend | 不是单一固定模型；必须选择具体 model id 和训练数据，避免查表 |
| 25 | [OCHEM](https://ochem.eu/) | P2 | Online Chemical Database and Modeling Environment; RF/SVM/kNN/ANN 等 | SMILES/SDF/Web input | logP/logS、toxicity、ADMET、environmental endpoints and user models | Web platform；有模型发布和预测界面 | 可作为发现传统 QSAR 模型和交叉验证来源 | Web-only/账号/模型可用性变化；不建议首版 runtime 依赖公网 |
| 26 | [ALOGPS 2.1](https://vcclab.org/lab/alogps/) | P1/P2 | Early associative neural networks + E-state indices | SMILES/MOL via web/app interface | logP、water solubility logS、pKa/logD 辅助比较 | VCCLAB online applet/non-Java interface；历史 standalone 需复核 | 经典 logP/logS 预测，论文和性能指标清楚 | 老 Java/Web 形态不利于容器化；需确认可离线运行或重实现许可 |
| 27 | [XLOGP3](https://www.sioc-ccbg.ac.cn/software/xlogp3/) | P2 | Atom-additive + correction factors logP model | SMILES/MOL depending implementation | logP / lipophilicity | Academic web/software page；多工具集成 | 可作为 logP consensus 成员或比较模型 | 部署和许可需复核；单 endpoint，且已有 RDKit/EPI/ChemAxon 重叠 |
| 28 | [Molinspiration](https://www.molinspiration.com/) | P2 | Fragment/QSAR-style property and bioactivity scoring | SMILES/Web input | miLogP、TPSA、drug-likeness、bioactivity scores for GPCR/kinase/ion channel/nuclear receptor etc. | Public web calculators and commercial services | 可作为早期 web QSAR 对照，bioactivity score 可做弱 surrogate | 主要 Web-only；模型细节和本地部署有限，不适合首版正式 oracle |
| 29 | [DataWarrior / OSIRIS-style property explorer](https://openmolecules.org/datawarrior/) | P1/P2 | Fragment/rule/QSPR and cheminformatics predictors | SMILES/SDF/table | cLogP、cLogS、TPSA、druglikeness、toxicity risk, mutagenic/tumorigenic/reproductive/irritant flags | Desktop Java app；supports macros and batch table workflows | 免费、常用、可批量，适合低成本 drug-likeness/tox-risk gate | 部分预测是 heuristic/risk flags；headless automation 要实测 |
| 30 | [PASS Online](https://www.way2drug.com/passonline/) | P2 | Activity spectrum prediction from structure; Bayesian/nearest-neighbor style family | Structure/SMILES via web | Biological activity probabilities Pa/Pi, mechanisms, pharmacological/toxic effects | Way2Drug web; commercial/academic ecosystem | 可做“候选可能具备某生物活性”弱 verifier | 输出不是直接实验 potency；Web-only 且 activity definitions 很宽 |
| 31 | [GUSAR](https://www.way2drug.com/gusar/) | P2 | QSAR ensemble/self-consistent regression style models | Structure/SMILES via web | Acute rat toxicity LD50 for routes/species, environmental/toxicity-related endpoints depending server | Way2Drug web/server | 适合 acute toxicity 交叉验证候选 | Web-only；正式部署、license 和 batch API 需确认 |
| 32 | [ProTox-II](https://tox-new.charite.de/protox_II/) | P2 | Similarity, fragment propensities, ML classifiers | SMILES/Web input | LD50, toxicity class, organ toxicity, Tox21 nuclear receptor/stress response, pathways, targets | Web server | 易用、引用多，适合研究参考或离线复现 target | Web-only；模型和数据版本随服务变化 |
| 33 | [pkCSM](https://biosig.lab.uq.edu.au/pkcsm/) | P2 | Graph-based signatures with classical ML | SMILES/Web input | Absorption, distribution, metabolism, excretion, toxicity endpoints | Web server | 覆盖 ADMET 多 endpoint，典型 2015 前后轻量 ML | 无官方本地部署；服务稳定性和版本冻结不足 |
| 34 | [admetSAR](http://lmmd.ecust.edu.cn/admetsar2/) | P2 | QSAR/ML ADMET classifiers/regressors | SMILES/Web input | ADMET-associated properties, toxicity, metabolism/transport endpoints | Web server; admetSAR 2.0/3.0 ecosystem | 多 endpoint，适合候选发现和结果对照 | Web-only；endpoint definitions 和 model version 需锁定 |
| 35 | [PreADMET](https://preadmet.webservice.bmdrc.org/) | P2 | Classical QSAR ADME/Tox web models | SMILES/Web input | HIA, Caco-2, BBB, PPB, CYP, Ames, carcinogenicity and drug-likeness-like endpoints | Web server | 老牌 ADME/Tox web predictor，适合对照 | Web-only；本地部署和许可不清 |
| 36 | [SwissADME](http://www.swissadme.ch/) | P2 | Rule/QSPR/BOILED-Egg and drug-likeness models | SMILES/Web input | Physchem, lipophilicity consensus, water solubility, GI absorption, BBB, P-gp, CYP inhibition, drug-likeness, SA | Web batch input | 非常常用，输出结构化，适合作为人类可读参考 | Web-only；部分 endpoint 是规则/consensus，不是实验标签式 ML |
| 37 | [SwissTargetPrediction](http://www.swisstargetprediction.ch/) | P2 | 2D/3D similarity-based target prediction | SMILES/Web input | Probable protein targets/classes | Web server | 可做 target-likelihood surrogate 或 activity-side constraint | 目标概率不是 binding affinity；Web-only；training leakage 与 known drugs 相似性强 |
| 38 | [MetaPrint2D](https://www-metaprint2d.ch.cam.ac.uk/) | P2 | Data-mined metabolite transformation/site likelihood | SMILES/Web input | Sites of metabolism and metabolite likelihood maps | Web server | 可用于 metabolism soft-spot gate | Web-only；不是 clearance 或 metabolite abundance |
| 39 | [BioTransformer](https://github.com/djoumbou/biotransformer) | P1/P2 | Rule-based + ML metabolism prediction | SMILES/SDF, CLI | Human/environmental microbial/CYP phase metabolism products, enzymes, transformations | Java command-line/open-source GitHub | 可本地容器化，适合代谢产物生成和 reactive metabolite prefilter | 输出是 predicted products/pathways，不是单一数值性质；评分需定义清楚 |
| 40 | [Meteor Nexus](https://www.lhasalimited.org/products/meteor-nexus.htm) | P1/P2 | Expert rule/knowledge-based metabolism prediction | Structure input through Nexus/Lhasa suite | Metabolic fate, likely metabolites, biotransformations | Commercial Lhasa Nexus platform | 工业使用率高，可做 metabolism verifier if licensed | 商业许可；API/CLI 和 redistributable container 需供应商确认 |
| 41 | [Derek Nexus](https://www.lhasalimited.org/blog/10-frequently-asked-questions-about-derek-nexus-answered/) | P1 | Expert structural-alert toxicology system | Structure input through Nexus/StarDrop module | Mutagenicity, carcinogenicity, chromosome damage, skin sensitisation, teratogenicity, respiratory sensitisation, organ toxicity, neurotoxicity, reproductive toxicity, hepatotoxicity 等 | Commercial Lhasa Nexus; also available in Optibrium StarDrop module | 监管/ICH M7 语境强，适合 genotox/safety hard gate | 商业许可；输出 likelihood levels 不是概率；版本更新可能改变分类 |
| 42 | [Sarah Nexus](https://www.lhasalimited.org/solutions/in-silico-mutagenicity-assessment/) | P1 | Statistical QSAR; SOHN fragment hypotheses | Structure input through Nexus/Lhasa suite | Bacterial mutagenicity; newer versions include chromosome damage | Commercial Lhasa Nexus | 与 Derek 互补，符合 ICH M7 “统计 + expert rule” 双模型思路 | 商业许可；仅窄 genotox endpoint；需固定 confidence/domain interpretation |
| 43 | [CASE Ultra / MultiCASE](https://www.multicase.com/) | P1 | 1980s-2010s CASE fragments/statistical SAR | SMILES/SDF/structure | Mutagenicity, carcinogenicity, developmental/reproductive tox, skin sensitization, aquatic tox and custom models depending modules | Commercial desktop/server/batch software | ICH M7 和监管 tox 传统工具，适合商业可接受时接入 | 许可和模型包费用；具体 endpoint 模型需单独登记 |
| 44 | [Leadscope Model Applier](https://www.instem.com/solutions/in-silico-toxicology/) | P1 | Statistical QSAR with structural alerts/descriptors | SMILES/SDF/structure | Mutagenicity, carcinogenicity, ICH M7 impurity, DART, skin sensitization and other tox models | Commercial Instem/Leadscope software | 工业/监管使用率高，适合 genotox 和 tox endpoint verifier | 商业许可；模型版本和 batch automation 需供应商文档确认 |
| 45 | [ACD/Labs Percepta PhysChem Suite](https://www.acdlabs.com/products/percepta-platform/) | P1 | Fragment/QSPR + curated experimental databases | SMILES/SDF/structure | pKa, logP, logD, aqueous solubility, BP/VP and related physicochemical properties | Commercial desktop/browser/enterprise; batch deployment and KNIME/Pipeline Pilot integrations | pKa/logD/logS 价值高，适合 drug-like multi-objective tasks | 商业许可；算法 proprietary；confidence/reliability index 需解析 |
| 46 | [ACD/Labs Percepta ADME Suite](https://www.acdlabs.com/products/percepta-platform/) | P1 | QSAR/QSPR ADME models, trainable with in-house data | SMILES/SDF/structure | BBB, passive absorption, oral bioavailability, CYP inhibitors/substrates, P-gp, distribution, MRDD, regioselectivity | Commercial Percepta platform | 多 ADME endpoint，适合工业风格 verifier if license available | 许可；endpoint units/probability definitions and trainable custom state need freezing |
| 47 | [ACD/Labs Tox Suite](https://www.acdlabs.com/products/percepta-platform/tox-suite/) | P1 | Structure-based toxicity QSAR modules | SMILES/SDF/structure | Acute toxicity, aquatic toxicity, endocrine disruption, mutagenicity, hERG, irritation, organ adverse effects | Commercial Percepta platform | 毒性覆盖强，可与 Derek/Sarah/CASE/Leadscope 形成商业 consensus | 许可；部分模块可训练，必须固定模型 library 和 reliability policy |
| 48 | [ChemAxon cxcalc / Calculator Plugins](https://docs.chemaxon.com/latest/calculators_cxcalc-command-line-tool.html) | P0/P1 | Fragment/empirical QSPR calculators | SMILES, SDF, MOL, command-line input | pKa, logP, logD, logS/solubility, charge, polarizability-like descriptors depending license | `cxcalc` CLI; Marvin/JChem tools; Linux/macOS/Windows; commercial/free-academic terms vary | CLI 清晰、易容器化，适合 pKa/logD/logS property scripts | 商业许可和 plugin availability；tautomer/pH/electrolyte settings must be frozen |
| 49 | [Simulations Plus ADMET Predictor](https://www.simulations-plus.com/software/admetpredictor/) | P1 | Classical and modern ML ADMET/QSPR platform | SMILES/SDF/structure | 175+ ADMET/PK/tox properties: solubility vs pH, logD, pKa, CYP/UGT, Ames, DILI, hERG, PK endpoints | Commercial desktop/enterprise; CLI, REST API, Python/wrappers, KNIME/Pipeline Pilot integrations | Endpoint 覆盖极强，automation 明确，适合商业可接受的 ADMET verifier | 许可/容器部署；模型 proprietary；需要 export raw predictions/confidence/domain |
| 50 | [BIOVIA TOPKAT / Discovery Studio Predictive Toxicology](https://www.3ds.com/products/biovia/discovery-studio/qsar-admet-predictive-toxicology) | P1 | TOPKAT/BIOVIA QSAR toxicology, Bayesian/PLS/GFA/forest 等平台模型 | SMILES/SDF/Discovery Studio ligand input | Human toxicity/ecotoxicity, Ames, carcinogenicity, biodegradability and distributed ADME/Tox models depending package | Commercial BIOVIA Discovery Studio / Pipeline Pilot ecosystem | 经典 TOPKAT 在文献和监管讨论中常见，适合商业 tox verifier | 许可；TOPKAT model/version/export automation 需明确 |
| 51 | [BIOVIA Discovery Studio ADMET models](https://www.3ds.com/products/biovia/discovery-studio/qsar-admet-predictive-toxicology) | P1/P2 | QSAR/QSPR descriptors and distributed ADME models | Structure libraries | Solubility, BBB, CYP2D6, hepatotoxicity-like ADME descriptors depending module | Commercial Discovery Studio/Pipeline Pilot | 可作为 ADME endpoint 补充，尤其已有 BIOVIA 环境时 | 与 TOPKAT 边界需拆清；proprietary model details |
| 52 | [Schrodinger QikProp](https://www.schrodinger.com/platform/products/qikprop/) | P1 | William Jorgensen ADME/QSPR property models | 3D ligand structures, Maestro/structure files | QPlogS, QPlogPo/w, QPlogBB, Caco-2/MDCK permeability, human oral absorption, skin permeability, Rule-of-5 flags and descriptors | Commercial Schrodinger suite; Maestro GUI and command-line mode documented in manuals | 药物化学使用率高，CLI/batch 清楚，适合 ADME physchem verifier | 商业许可；需要 3D preparation policy；部分 descriptors are rule flags |
| 53 | [Optibrium StarDrop ADME QSAR](https://optibrium.com/products/stardrop/modules/adme-qsar/) | P1 | QSAR models with confidence and chemical-space estimates | Structure input / StarDrop tables | pKa, logP, logD7.4, aqueous/PBS solubility, CYP affinities, HLM Clint, PPB, hERG, BBB, Caco-2, HIA, P-gp, Ames | Commercial StarDrop optional module; integration with informatics platforms | ADME endpoint selection close to benchmark needs；uncertainty/domain reporting useful | 许可；headless/API path must be confirmed for verifier image |
| 54 | [Optibrium StarDrop Auto-Modeller](https://optibrium.com/products/stardrop/modules/auto-modeller/) | P1/P2 | RF, Gaussian processes, RBF, PLS, decision trees with built-in descriptors | Structure tables + endpoint labels | User-trained QSAR/QSPR for potency, solubility, BBB, project endpoints | Commercial StarDrop module | 可用于训练和冻结自有 classical QSAR checkpoint | 不是 off-the-shelf endpoint unless model is trained/frozen；requires model artifact governance |
| 55 | [Danish QSAR Database / DTU QSAR models](https://qsar.food.dtu.dk/) | P2 | Ensemble QSAR predictions for many endpoints | Chemical identifiers/structures, database access | Mutagenicity, carcinogenicity, endocrine, developmental/reproductive, ecotox and other endpoints depending model | Public database/interface; some model documentation/QMRF | 监管筛查价值高，可用于候选 discovery and contamination checks | 主要是预计算/数据库形态；正式 verifier 不能直接查表作为 oracle unless local models are provided |
| 56 | [QsarDB model packages](https://qsardb.org/) | P2 | Repository of published QSAR models, descriptors and QMRF metadata | Depends on package; often descriptors/structure | Published endpoint-specific QSARs: BCF, toxicity, physchem, environmental endpoints | Download model packages; some include descriptor/model metadata | 是寻找可复现传统 QSAR 的模型仓库 | 每个 package 可执行性差异大；需要逐模型复现 descriptor pipeline |
| 57 | [AFLOW-ML](https://aflow.org/aflow-ml/) | P1/P2 | 2010s materials ML from composition/crystal-derived descriptors | Composition or material representation via REST/API | Formation enthalpy, band gap, energy/volume-related material properties depending endpoint | AFLOW-ML web/API; potential local reproduction via AFLOW ecosystem unclear | 早期材料端到端 property predictor，补小分子 QSAR 之外的材料候选 | API/web dependency and model version freezing；may be database-adjacent and needs leakage review |
| 58 | [Magpie materials ML](https://bitbucket.org/wolverton/magpie) | P2 | Composition descriptors + classical ML for materials | Composition formulas | Formation energy, band gap, volume, elastic/thermal-like properties depending trained model | Java code / published models/examples; often used through Magpie/matminer lineage | 经典 composition-only materials ML，适合 formula-only baseline verifier | 通常需要自训/freeze checkpoint；composition-only cannot validate structure feasibility |

## 4. 首批最值得验证的候选

### 4.1 开源或免费、较可能本地固定的 P0/P1

1. `EPA TEST`：优先验证是否能在 Linux container 中 headless batch 运行，首选 Ames、LD50、
   aquatic toxicity、BCF 或 water solubility 等 endpoint。
2. `VEGA QSAR`：优先挑 Ames consensus、BCF、fish/Daphnia/algae acute toxicity、
   water solubility、KOC、Henry 或 PPB 等单 endpoint，确认 batch/export。
3. `Toxtree`：优先接 Cramer/TTC、Benigni-Bossa、Verhaar、skin sensitisation/reactivity
   alerts；Java 部署成本最低。
4. `EPI Suite / ECOSAR`：科学价值高，但官方 Windows 桌面限制明显。若 verifier image
   可以接受 Wine/Windows runner 或以后改 Linux-compatible wrapper，可作为环境归趋 P0。
5. `BioTransformer`：Java CLI、本地可控，适合代谢产物和代谢软点类 task。
6. `lazar / AMBIT`：如果能自托管 OpenTox/REST 服务并冻结模型，可作为可解释 local QSAR
   verifier。

### 4.2 商业但高价值的 P1

1. `ChemAxon cxcalc`：最适合 pKa/logD/logS CLI property verifier。
2. `ACD/Labs Percepta`：physchem、ADME 和 tox 模块覆盖广，reliability index 对 domain
   gate 有用。
3. `ADMET Predictor`：覆盖面最大，且有 CLI/REST/Python/KNIME 等自动化路径。
4. `Derek Nexus + Sarah Nexus`：适合 ICH M7/杂质 mutagenicity 和 genotox 双模型 verifier。
5. `CASE Ultra / Leadscope / TOPKAT / QikProp / StarDrop`：工业使用率高，但进入官方镜像
   的前提是许可允许 batch automation 和可再分发部署。

### 4.3 Web-only 或数据库邻近的 P2

`SwissADME`、`pkCSM`、`admetSAR`、`PreADMET`、`ProTox-II`、`PASS`、`GUSAR`、
`MetaPrint2D`、`OCHEM`、`Danish QSAR Database`、`AFLOW-ML` 等适合继续调研、
做人工参考或离线校准，但首版正式 verifier 不应依赖公网服务，也不应查询已经预计算的
候选性质标签作为评分。

## 5. 与现有深度学习候选的互补关系

现有清单中的 `ADMET-AI`、`Chemprop`、`SolTranNet`、`MatGL`、`CHGNet` 等更像现代
训练框架或深度模型。本文候选的优势是：

- 很多 endpoint 已经有长期监管或工业使用经验。
- 输入输出简单，适合 property-level verifier script。
- 多数小分子模型运行成本低，适合批量评分。
- 许多工具提供 applicability domain、confidence、nearest-neighbor 或 alert rationale。

主要不足是：

- 许可和部署经常比开源 Python 模型复杂。
- Web-only 服务和数据库型平台不能直接作为正式 runtime oracle。
- 传统 QSAR 对新颖 scaffold、离子化/盐/混合物、organometallics、聚合物和大分子适用域有限。
- 许多输出是 hazard/risk class 或 structural alert，不应过度解释为精确实验性质。

## 6. 推荐下一步

1. 先为 `Toxtree`、`BioTransformer`、`ChemAxon cxcalc`、`EPA TEST`、`VEGA` 分别做
   environment smoke plan，确认 headless/batch 输出。
2. 对 EPI Suite/ECOSAR 做 Windows/Wine/Docker feasibility spike；如果不能稳定自动化，
   暂时只保留为研究候选。
3. 对商业工具只建立 metadata registry，不写 runtime wrapper，除非确认许可证和部署方式。
4. 对 Web-only 工具建立 `research_reference_only` 标记，避免未来误接入正式 scoring path。
5. 每个进入 verifier 的 endpoint 都要有小型 calibration set，检查输出单位、分类方向、
   out-of-domain 行为和已知结构的稳定性。

## 7. 主要来源

- EPA TEST: <https://www.epa.gov/comptox-tools/toxicity-estimation-software-tool-test>
- EPA TEST v4.2 guide: <https://www.epa.gov/sites/default/files/2016-05/documents/600r16058.pdf>
- EPA EPI Suite: <https://www.epa.gov/tsca-screening-tools/epi-suitetm-estimation-program-interface>
- EPA EPI Suite v4.11 download: <https://www.epa.gov/tsca-screening-tools/download-epi-suitetm-estimation-program-interface-v411>
- VEGAHUB in silico models: <https://www.vegahub.eu/portfolio-types/in-silico-models/>
- OECD QSAR Toolbox: <https://qsartoolbox.org/>
- OECD QSAR Toolbox (Q)SARs: <https://qsartoolbox.org/resources/qsars/>
- Toxtree: <https://toxtree.sourceforge.net/>
- Toxtree Benigni-Bossa: <https://toxtree.sourceforge.net/carc.html>
- lazar framework paper: <https://pmc.ncbi.nlm.nih.gov/articles/PMC3669891/>
- OpenRiskNet Lazar service record: <https://openrisknet.org/e-infrastructure/services/110/>
- ALOGPS 2.1: <https://vcclab.org/lab/alogps/>
- ChemAxon cxcalc docs: <https://docs.chemaxon.com/latest/calculators_cxcalc-command-line-tool.html>
- ChemAxon logD docs: <https://docs.chemaxon.com/latest/calculators_logd-plugin.html>
- ACD/Labs Percepta: <https://www.acdlabs.com/products/percepta-platform/>
- ACD/Labs Tox Suite: <https://www.acdlabs.com/products/percepta-platform/tox-suite/>
- Simulations Plus ADMET Predictor: <https://www.simulations-plus.com/software/admetpredictor/>
- ADMET Predictor Toxicity Module: <https://www.simulations-plus.com/software/admetpredictor/toxicity/>
- Lhasa Derek Nexus FAQ: <https://www.lhasalimited.org/blog/10-frequently-asked-questions-about-derek-nexus-answered/>
- Lhasa Sarah/Derek mutagenicity assessment: <https://www.lhasalimited.org/solutions/in-silico-mutagenicity-assessment/>
- BIOVIA QSAR/ADMET/Predictive Toxicology: <https://www.3ds.com/products/biovia/discovery-studio/qsar-admet-predictive-toxicology>
- Optibrium StarDrop ADME QSAR: <https://optibrium.com/products/stardrop/modules/adme-qsar/>
- Optibrium StarDrop Auto-Modeller: <https://optibrium.com/products/stardrop/modules/auto-modeller/>
- SwissADME: <http://www.swissadme.ch/>
- pkCSM: <https://biosig.lab.uq.edu.au/pkcsm/>
- admetSAR 2.0: <http://lmmd.ecust.edu.cn/admetsar2/>
- ProTox-II: <https://tox-new.charite.de/protox_II/>
- BioTransformer: <https://github.com/djoumbou/biotransformer>
- AFLOW-ML: <https://aflow.org/aflow-ml/>
- Magpie: <https://bitbucket.org/wolverton/magpie>

## 8. 按预测性质所属化学子领域分类

本节把上面的经典 QSAR/QSPR、专家规则和商业模型候选按预测性质所属的化学子领域汇总。
平台型工具通常横跨多个 endpoint，因此会被重复列入多个子领域。后续如果转成机器可读
registry，应允许一个候选拥有多个 `property_domain` 标签。

| 化学子领域 | 主要候选 | 预测性质或 endpoint | Verifier 使用重点 |
|---|---|---|---|
| 小分子物理化学与药物样基础性质 | `EPI Suite KOWWIN`、`EPI Suite WSKOWWIN/WATERNT`、`EPI Suite MPBPWIN`、`ALOGPS 2.1`、`XLOGP3`、`Molinspiration`、`DataWarrior/OSIRIS-style property explorer`、`ACD/Labs Percepta PhysChem Suite`、`ChemAxon cxcalc`、`Schrodinger QikProp`、`SwissADME`、`OCHEM`、`QsarDB model packages` | logP/logKow、logS/water solubility、pKa、logD、melting/boiling point、vapor pressure、TPSA、drug-likeness、Rule-of-5 flags | 最适合构造低成本、端到端的小分子物化窗口任务；要固定 pH、温度、tautomer/ionization policy 和单位，避免与 RDKit 基础描述符重复计分。 |
| 小分子 ADME 与药代相关性质 | `ACD/Labs Percepta ADME Suite`、`Simulations Plus ADMET Predictor`、`BIOVIA Discovery Studio ADMET models`、`Schrodinger QikProp`、`Optibrium StarDrop ADME QSAR`、`pkCSM`、`admetSAR`、`PreADMET`、`SwissADME`、`VEGA QSAR`、`OECD QSAR Toolbox`、`OCHEM` | Caco-2、MDCK、HIA/GI absorption、BBB、P-gp、CYP inhibition/substrate、clearance、PPB/FuB、VDss、bioavailability、skin permeability | 适合药物发现 multi-objective verifier；进入正式评分时必须明确 endpoint 是概率、分类、回归值还是规则判断，并记录 applicability-domain/confidence。 |
| 毒理学、安全性、结构警示与监管 hazard | `US EPA TEST`、`VEGA QSAR`、`OECD QSAR Toolbox`、`Toxtree Cramer/TTC`、`Toxtree Benigni-Bossa`、`Toxtree skin/eye/protein/DNA alerts`、`lazar`、`AMBIT/OpenTox`、`GUSAR`、`ProTox-II`、`Derek Nexus`、`Sarah Nexus`、`CASE Ultra/MultiCASE`、`Leadscope Model Applier`、`ACD/Labs Tox Suite`、`Simulations Plus ADMET Predictor`、`BIOVIA TOPKAT`、`Danish QSAR Database`、`QsarDB model packages` | Ames/mutagenicity、carcinogenicity、LD50/acute toxicity、DILI、hERG、developmental/reproductive toxicity、skin sensitisation、irritation、organ toxicity、endocrine disruption、TTC/Cramer class、structural alerts | 是传统 QSAR 最成熟的应用区；很多输出是 hazard class、alert 或 expert likelihood，不应等同精确实验概率。ICH M7 类任务可用 Derek/Sarah/CASE/Leadscope consensus 思路。 |
| 环境化学、生态毒理与环境归趋 | `EPI Suite HENRYWIN`、`EPI Suite AOPWIN`、`EPI Suite BIOWIN/BioHCwin`、`EPI Suite KOCWIN`、`EPI Suite BCFBAF`、`EPI Suite HYDROWIN`、`EPI Suite KOAWIN`、`EPI Suite AEROWIN/WVOLWIN`、`EPI Suite STPWIN`、`EPI Suite LEV3EPI`、`US EPA ECOSAR`、`US EPA TEST`、`VEGA QSAR`、`OECD QSAR Toolbox`、`Toxtree Verhaar/Modified Verhaar`、`ACD/Labs Tox Suite`、`BIOVIA TOPKAT`、`Danish QSAR Database`、`QsarDB model packages` | Aquatic acute/chronic toxicity、fish/Daphnia/algae endpoints、BCF/BAF、biodegradation、persistence、Koc、Henry constant、KOA、hydrolysis half-life、atmospheric oxidation half-life、sewage-treatment removal、multimedia fate | 适合建立区别于药物 ADMET 的环境化学 verifier；EPI/ECOSAR 类模型要固定环境场景参数，不能把场景模拟结果误写成纯分子性质。 |
| 代谢、site-of-metabolism 与生物转化 | `SMARTCyp`、`MetaPrint2D`、`BioTransformer`、`Meteor Nexus`、`ACD/Labs Percepta ADME Suite`、`Simulations Plus ADMET Predictor`、`pkCSM`、`admetSAR`、`PreADMET`、`Optibrium StarDrop ADME QSAR` | CYP site-of-metabolism、metabolic soft spots、predicted metabolites、biotransformations、CYP substrate/inhibition、UGT/metabolism-related endpoints | 适合作为代谢软点规避或代谢产物 plausibility verifier；per-atom ranking 和 predicted metabolite 不等于 clearance，评分函数需单独设计。 |
| 生物活性、靶点倾向与药理作用谱 | `PASS Online`、`Molinspiration`、`SwissTargetPrediction`、`ProTox-II`、`OCHEM`、`QsarDB model packages`、`Optibrium StarDrop Auto-Modeller` | Biological activity spectra、target class probability、GPCR/kinase/ion-channel/nuclear-receptor bioactivity score、pathway/target toxicity associations、user-trained potency/property models | 可作为窄域 target-likelihood 或 project-specific QSAR 储备；Web-only 和 similarity-heavy 模型容易泄漏 known-drug 信息，不适合作为首版唯一 potency oracle。 |
| QSAR 平台、模型仓库与可复现模型基础设施 | `OECD QSAR Toolbox`、`AMBIT/OpenTox`、`OCHEM`、`Danish QSAR Database`、`QsarDB model packages`、`Optibrium StarDrop Auto-Modeller`、`lazar` | 取决于具体模型包或 workflow：toxicity、ADME、physchem、environmental endpoints、custom QSAR | 这些更像模型/工作流容器，而不是单一 endpoint；正式接入时必须拆成具体模型 id、训练数据、descriptor pipeline 和 fixed prediction command。 |
| 材料化学与无机材料性质 | `AFLOW-ML`、`Magpie materials ML` | Formation enthalpy/energy、band gap、volume、elastic/thermal-like composition or crystal-derived properties | 作为经典/早期材料 ML 补充现代 MatGL/CHGNet/MACE；composition-only 模型只能作为 formula-level baseline，需要结构与稳定性 gate。 |

从子领域覆盖看，本文候选对“小分子物化、ADME、毒理、安全性、环境归趋”最强，
对材料和靶点活性只提供少量早期或平台型补充。首批工程验证建议优先从
`Toxtree`、`ChemAxon cxcalc`、`BioTransformer`、`EPA TEST`、`VEGA`、`EPI Suite/ECOSAR`
中各挑 1-2 个 endpoint 做 smoke 和输出解析，形成跨子领域的最小经典 QSAR verifier 集。
