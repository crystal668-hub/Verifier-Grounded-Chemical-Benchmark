# AtomisticSkills MCP/Script 工具与 Benchmark Verifier 适配性分析

日期：2026-06-02

## 1. 范围与来源

本次整理面向 arXiv:2605.24002《Harnessing AtomisticSkills for Agentic Atomistic Research》中公开的 AtomisticSkills 工具体系，并对照 `doc/INITIAL-DESIGN.md` 判断每类工具的可部署形态和 verifier 适配性。

核对来源：

- 论文页：<https://arxiv.org/abs/2605.24002>。论文说明 AtomisticSkills 提供 100+ skills，并通过 MCP tools、scripts、MLIP/DFT/数据库/模拟引擎支持材料、化学和药物发现任务。
- 论文源码 `main.tex`。其中明确说明 tools 是严格结构化 Python 函数、运行在独立 MCP server 环境中；同时还有辅助 script 环境支持不适合长期暴露为 MCP 的 skill-specific scripts。
- 开源仓库：<https://github.com/learningmatter-mit/AtomisticSkills>。本地核对 commit：`23d101d10ee416c6bb9c24ad40ce66038a841d5c`。
- 本项目设计文档：`doc/INITIAL-DESIGN.md`。

开源仓库当前核对结果：

- MCP server 文件：10 个。
- `@mcp.tool()` 暴露函数：49 个。
- `SKILL.md`：121 个。
- 含 `scripts/` 文件的 skill 包：108 个。
- script 文件：191 个。
- conda 环境目录：19 个，其中 10 个在 `mcp_config.json` 中配置为 MCP server 环境，其他主要是 script-only 或辅助计算环境。

说明：论文文字称 “more than 10 tool servers and 50 MCP tools”。按当前公开 `main` 分支源码逐项解析，实际可见的是 10 个 MCP server、49 个 `@mcp.tool()` 函数；差异可能来自论文统计口径把辅助 script 环境或私有/案例工具也计入。

## 2. 对照 `INITIAL-DESIGN.md` 的判断准则

本项目的正式 verifier 需要满足：

- 只信任候选对象本身，不信任模型自报性质。
- 能解析、规范化、做适用域检查、独立计算或查证性质，并输出可复现分数。
- 优先级为：确定性本地工具 > 冻结数据库快照 > 冻结 ML 模型 > 专家 rubric > LLM-as-a-judge。
- 在线服务不能作为首版唯一评价路径；如用 Materials Project、ChEMBL、PDB、OpenAlex 等，正式 benchmark 应使用冻结快照或预下载标签。
- ML surrogate 必须冻结 checkpoint、依赖版本、随机种子、输入预处理、单位和 failure policy。

本文将工具的部署形态分为：

- `本机 CPU`：普通笔记本/工作站可安装，运行成本低。
- `本机 GPU/工作站`：可本机部署，但建议有 CUDA/GPU；小规模 benchmark 可以本机跑。
- `计算集群/远程服务`：DFT、长时间 MD、大批量筛选或异步队列，工程上应作为集群服务或预计算服务。
- `在线 API/冻结快照`：调研时可在线调用，正式 verifier 应冻结数据。
- `候选生成/辅助`：可帮助 agent 找候选，但不应直接作为最终性质 verifier。

Verifier 适配性分为：

- `可直接作为 verifier`：适合指定题目，工程风险低或已经可冻结。
- `条件可作为 verifier`：需要固定 checkpoint、结构模板、数据库快照、计算协议、资源上限或队列服务。
- `只适合作辅助/生成`：用于候选生成、可视化、检索、制备流程、模型训练等，不适合作最终评分器。
- `不建议首版作为 verifier`：不可复现、强依赖在线/人工/LLM、或科学问题太开放。

## 3. MCP 工具逐项整理

| MCP server / tool | 功能 | 可部署形态 | 是否可作为 benchmark verifier |
|---|---|---|---|
| `base.create_research_dir` | 创建研究目录 | 本机 CPU | 否。运行态管理工具，不验证候选性质。 |
| `base.search_materials_project_by_formula` | 按化学式查 Materials Project 并保存结构 | 在线 API/冻结快照 | 条件可用。适合 MP 标签/结构检索型 verifier，但正式路径应冻结 MP snapshot，不能只依赖在线 API。 |
| `base.search_materials_project_by_chemsys` | 按元素体系查 MP hull 稳定结构 | 在线 API/冻结快照 | 条件可用。可用于材料稳定性、band gap 标签模式；正式 benchmark 需冻结数据。 |
| `base.visualize_structure` | 结构渲染 | 本机 CPU | 否。只适合 QA/人工检查，不是性质 verifier。 |
| `base.search_literature` | OpenAlex 文献搜索和下载 | 在线 API | 否。不适合作自动性质评分；只可用于 agent 参考资料检索。 |
| `base.supercell_expansion` | 结构超胞生成 | 本机 CPU | 可直接作为结构操作 verifier。当前仓库已有 `atomisticskills_base_supercell_001` smoke 题；但它不是 `INITIAL-DESIGN.md` 核心 open-generation 性质题。 |
| `base.modify_structure` | 元素替换/掺杂结构生成 | 本机 CPU | 条件可用。可验证结构编辑任务；作为开放材料生成 verifier 时还需接稳定性/性质计算。 |
| `base.search_model_registry` | 本地 MLIP checkpoint registry 查询 | 本机 CPU | 否。只用于选择模型和避免重复训练。 |
| `base.register_model` | 注册 fine-tuned MLIP | 本机 CPU | 否。模型管理工具。 |
| `drugdisc.parse_smiles_input` | SMILES 解析 | 本机 CPU | 可作为 validity/candidate parser 的一部分；不是完整 property verifier。 |
| `drugdisc.standardize_molecule` | RDKit 分子标准化 | 本机 CPU | 可作为小分子 verifier 的 canonicalization/domain gate。 |
| `drugdisc.convert_to_pdbqt` | 小分子/蛋白 PDBQT 准备 | 本机 CPU | 条件可用。可服务 docking 题，但 docking verifier 必须固定受体、盒子、Vina 版本、构象生成和失败策略。 |
| `drugdisc.compute_molecular_descriptors` | RDKit descriptors、Ro5、Veber、QED | 本机 CPU | 可直接作为 P0-1 小分子基础性质 verifier。也已用于 `atomisticskills_drugdisc_descriptor_001` smoke 题。注意它不预测 hERG/AMES/DILI 等实验 ADMET endpoint。 |
| `drugdisc.compute_molecular_fingerprints` | Morgan/ECFP、Tanimoto、Butina | 本机 CPU | 条件可用。适合作 novelty/diversity/applicability-domain 辅助 gate；不宜作为主要性质目标。 |
| `matgl.load_model` | 加载 MatGL/CHGNet/M3GNet/TensorNet/eform 模型 | 本机 GPU/工作站 | 否。模型加载步骤。 |
| `matgl.predict_structure` | 预测能量、力、应力、可选电荷 | 本机 GPU/工作站 | 条件可用。适合 formation energy proxy、relaxed energy proxy、charge sanity，但需冻结模型和输入结构规范。 |
| `matgl.predict_atomic_features` | 原子 latent feature | 本机 GPU/工作站 | 通常不建议。可作 novelty/applicability-domain 研究指标，但不是 `INITIAL-DESIGN.md` 首版核心性质。 |
| `matgl.predict_bandgap` | MEGNet band gap 预测 | 本机 GPU/工作站 | 条件可用。匹配 P0-4 band gap surrogate；正式 benchmark 应固定模型、functional、单位、适用域并校准误差。 |
| `matgl.get_info` | 当前模型状态 | 本机 GPU/工作站 | 否。运行态检查。 |
| `matgl.relax_structure` | MatGL/CHGNet/M3GNet 结构弛豫 | 本机 GPU/工作站 | 条件可用。可作为材料 verifier 前处理或稳定性 proxy，但需要固定 fmax、steps、cell relaxation、失败策略。 |
| `matgl.run_md` | MatCalc MD | 本机 GPU/工作站；长 MD 建议集群 | 条件可用。适合 diffusion、melting、amorphization 等任务，但首版不宜大规模使用，需严格资源上限。 |
| `mace.load_model` | 加载 MACE 模型 | 本机 GPU/工作站 | 否。模型加载步骤。 |
| `mace.predict_structure` | MACE 能量/力/应力 | 本机 GPU/工作站 | 条件可用。可作为 MLIP 能量/力 verifier 或 formation energy proxy；需冻结 model head/checkpoint。 |
| `mace.predict_atomic_features` | MACE 原子特征 | 本机 GPU/工作站 | 通常不建议作为主 verifier；可辅助 novelty/domain。 |
| `mace.relax_structure` | MACE 弛豫 | 本机 GPU/工作站 | 条件可用。可用于材料稳定性/表面/吸附前处理；需固定协议。 |
| `mace.run_md` | MACE MD | 本机 GPU/工作站；长 MD 建议集群 | 条件可用。可用于 diffusion、melting、phase stability 等指定题；资源成本高。 |
| `mace.get_info` | 当前模型状态 | 本机 GPU/工作站 | 否。 |
| `fairchem.load_model` | 加载 UMA/ESEN/FairChem 模型 | 本机 GPU/工作站 | 否。 |
| `fairchem.predict_structure` | FairChem 能量/力/应力 | 本机 GPU/工作站 | 条件可用。可用于 OMat/OC/OMol/ODAC 等固定 task head 的 surrogate verifier。 |
| `fairchem.get_info` | 当前模型状态 | 本机 GPU/工作站 | 否。 |
| `fairchem.relax_structure` | FairChem 弛豫 | 本机 GPU/工作站 | 条件可用。可用于 bulk/surface/adsorbate relaxation；需固定 task head 和模型版本。 |
| `fairchem.run_md` | FairChem MD | 本机 GPU/工作站；长 MD 建议集群 | 条件可用。资源成本高，首版只建议小型固定任务。 |
| `atomate2.run_atomate2_vasp_calculation` | VASP workflow，本地或 remote | 计算集群/远程服务 | 条件可用但不适合首版在线实时评分。可作为高可信 DFT verifier 服务或预计算标签生成器；需要 VASP license、Atomate2 preset、队列、数据库和 timeout 策略。 |
| `atomate2.get_atomate2_results_by_id` | 按 job/flow id 取结果 | 计算集群/远程服务；冻结结果库 | 条件可用。适合读取冻结 DFT 结果库作为 verifier。 |
| `atomate2.get_atomate2_results_by_formula` | 按 formula/chemsys 取 DFT 结果 | 计算集群/远程服务；冻结结果库 | 条件可用。适合材料数据库标签模式；需冻结 DB。 |
| `atomate2.get_atomate2_summary` | Atomate2 DB 统计 | 计算集群/远程服务 | 否。 |
| `atomate2.get_atomate2_recent_jobs` | 最近 job 列表 | 计算集群/远程服务 | 否。 |
| `atomate2.get_atomate2_job_status` | job 状态 | 计算集群/远程服务 | 否。 |
| `atomate2.get_atomate2_project_status` | 项目队列状态 | 计算集群/远程服务 | 否。 |
| `smol.sample_ordered_structures` | 枚举/采样有序结构 | 本机 CPU/工作站 | 只适合作候选生成或固定 lattice 题的构造步骤；不是性质 verifier。 |
| `smol.train_cluster_expansion` | 训练 cluster expansion | 本机 CPU/工作站 | 条件可用。训练过程不应在评分时发生；若固定 CE 模型，可作为后续 MC/energy verifier 的前置资产。 |
| `smol.run_monte_carlo` | CE Monte Carlo | 本机 CPU/工作站 | 条件可用。适合固定 disordered lattice、固定 CE、固定温度/化学势的 order/disorder 或 phase fraction 题。 |
| `smol.compute_feature_vectors` | 计算相关向量 | 本机 CPU/工作站 | 条件可用。可做结构映射/domain gate；不宜单独作为性质目标。 |
| `smol.get_feature_matrix` | 获取训练集 feature matrix | 本机 CPU/工作站 | 否。训练诊断。 |
| `smol.fit_feature_matrix` | 直接拟合 feature matrix | 本机 CPU/工作站 | 否，除非固定模型生成流程；不应在评分时训练。 |
| `smol.check_mapping` | 检查 relaxed structure 是否仍映射到同一 configuration | 本机 CPU/工作站 | 条件可用。适合 disordered-material validity/domain gate。 |
| `mattergen.generate_structures` | MatterGen 晶体生成 | 本机 GPU/工作站 | 只适合作候选生成。不能作为最终 verifier；生成器不应给自己的候选打分。 |
| `adit.generate_structures` | ADiT 晶体/分子生成 | 本机 GPU/工作站 | 只适合作候选生成。可辅助构造 benchmark 候选池，但不是 verifier。 |
| `diffcsp.generate_structures_with_symmetry` | DiffCSP++ 对称约束晶体生成 | 本机 GPU/工作站 | 只适合作候选生成。可用于生成材料候选或 adversarial cases，不是性质 verifier。 |

## 4. Script 工具按 skill 包整理

下表按公开 skill 包聚合 script 工具，并列出包内脚本文件。若同一包有多个脚本，它们通常组成一个任务级 workflow；是否能作为 verifier 取决于能否固定输入 schema、版本、资源和 scoring。

| Skill / scripts | 可部署形态 | Verifier 适配性 |
|---|---|---|
| `chem-bond-dissociation`: `calculate_bde.py` | 本机 GPU/工作站；MACE/FairChem backend | 条件可用。可验证 BDE/断键能题，但需固定构象、charge/spin、模型或 DFT 协议。 |
| `chem-conformer-search`: `conformer_search.py` | 本机 CPU/GPU | 条件可用。适合 lowest-conformer energy/strain gate；随机种子和 force field/MLIP 必须固定。 |
| `chem-db-mof`: `query_mof_db.py` | 在线 API/冻结快照 | 条件可用。正式 verifier 需冻结 MOF/QMOF/MP 数据，不应实时在线查库。 |
| `chem-db-qmof`: `query_qmof.py` | 在线 API/冻结快照 | 条件可用。适合 QMOF 标签查证；需冻结 snapshot。 |
| `chem-db-spectra`: `query_spectra.py` | 在线 API/冻结快照 | 条件可用。适合谱图标签检索；正式路径需冻结谱图库。 |
| `chem-dft-orca-advanced-calculation`: `parse_orca_output.py`, `run_orca_input.py` | 本机 x86_64 或计算集群；需 ORCA binary/license | 条件可用。可验证低成本/DFT 分子性质，但评分时实时 ORCA 成本高；建议预计算或小题。 |
| `chem-dft-orca-optimization`: `run_optimization.py` | 本机 x86_64 或计算集群；需 ORCA | 条件可用。适合固定分子优化/TS/构象题；需严格 timeout。 |
| `chem-dft-orca-singlepoint`: `run_singlepoint.py` | 本机 x86_64 或计算集群；需 ORCA | 条件可用。可作为 HOMO/LUMO、dipole 等 verifier 的高成本路径；首版更建议 xTB。 |
| `chem-docking-void`: `run_docking.py` | 本机 CPU/工作站；VOID/zeopp | 条件可用。可做 MOF/孔道 docking 题，但需固定 adsorbate、framework、参数和随机种子。 |
| `chem-hazard-toxicity`: `get_safety_data.py` | 在线 API/冻结快照 | 条件可用作 safety gate 的数据源；正式 benchmark 应冻结毒性/安全数据，避免在线漂移。 |
| `chem-irc-verification`: `verify_irc_sella.py` | 本机 GPU/工作站或集群 | 条件可用。适合 reaction path/TS 验证题，但不是首版 P0。 |
| `chem-neb-barrier`: `calculate_barrier.py` | 本机 GPU/工作站或集群 | 条件可用。适合固定端点的 barrier 题；需固定 optimizer、images、MLIP/DFT。 |
| `chem-nmr-analysis`: `deconvolve.py`, `kinetics.py`, `plot.py`, `predict_products.py`, `spectra.py` | 本机 CPU | 条件可用。可验证固定 NMR deconvolution/kinetics 数值题；对 open-generation 候选性质不是首版核心。 |
| `chem-nmr-predict`: `predict_nmr.py` | 本机 CPU | 条件可用。可作为 NMR prediction surrogate verifier；需固定模型/规则和容差。 |
| `chem-react-ot`: `generate_ts.py` | 本机 GPU/工作站 | 只适合作候选生成。TS 生成模型不宜直接作为最终 verifier。 |
| `chem-similarity-search`: `similarity_search.py` | 本机 CPU | 条件可用作 novelty/similarity gate；不宜单独作为主性质 verifier。 |
| `chem-solution-md`: `build_solvation_box.py`, `analyze_solution_md.py` | 本机 GPU/工作站；长 MD 建议集群 | 条件可用。可验证 diffusion/solvation 统计量，但资源成本和随机性高。 |
| `chem-sorption-gcmc`: `gcmc_common.py`, `run_gcmc.py`, `run_gcmc_multi.py` | 本机 GPU/工作站；筛选建议集群 | 条件可用。适合 MOF gas uptake/isotherm 题；需固定 force field/MLIP、T/P、MC steps、seed。 |
| `chem-sorption-relax`: `build_supercell.py`, `relax_structure.py` | 本机 CPU + GPU/MLIP | 条件可用。可作为 sorption workflow 前处理，不宜单独评分。 |
| `chem-sorption-widom`: `widom_common.py`, `run_widom.py` | 本机 GPU/工作站 | 条件可用。适合 Henry coefficient/adsorption proxy；需固定 sampling。 |
| `chem-thermochemistry`: `calculate_thermochemistry.py`, `run_benchmarks.py` | 本机 GPU/工作站或集群 | 条件可用。适合指定分子热化学题；需固定模型、构象和温度。 |
| `chem-ts-optimization`: `optimize_ts_sella.py` | 本机 GPU/工作站或集群 | 条件可用但不建议首版。TS 搜索失败模式复杂。 |
| `chem-vibration`: `calculate_vibrations.py` | 本机 GPU/工作站或集群 | 条件可用。可验证频率/虚频/谱峰题；需固定 displacement、calculator。 |
| `drug-binding-site-definition`: `define_binding_site.py`, `visualize_box.py` | 本机 CPU | 条件可用作 docking verifier 前处理；单独不验证候选性质。 |
| `drug-bioactivity-assay`: `get_assays.py` | 在线 API/冻结 ChEMBL snapshot | 条件可用。适合 target activity 标签模式；必须冻结 assay selection、pChEMBL/IC50/Ki/Kd 规则。 |
| `drug-complex-system-builder`: `build_complex.py` | 本机 CPU/GPU | 辅助工具。可构建 MD/docking 输入，不适合作最终 verifier。 |
| `drug-db-chembl`: `query_chembl.py` | 在线 API/冻结 ChEMBL snapshot | 条件可用。匹配 `initial-design.md` P1-9，但必须冻结数据库和 assay filters。 |
| `drug-db-pdb`: `query_pdb.py` | 在线 API/冻结 PDB snapshot | 条件可用作 receptor/structure source；不直接验证小分子性质。 |
| `drug-db-pubchem`: `query_pubchem.py` | 在线 API/冻结 PubChem snapshot | 条件可用作 identifier/canonicalization/known compound gate；不能作为唯一性质 verifier。 |
| `drug-docking-analysis`: `analyze_docking.py` | 本机 CPU | 条件可用。可验证 docking pose/score 后处理；需固定 docking protocol。 |
| `drug-docking-vina`: `collect_results.py`, `compute_box_from_pdbqt.py`, `run_docking.py` | 本机 CPU/工作站 | 条件可用。可作为 narrow target docking score verifier；对首版 open-generation 要谨慎，Vina 分数不是实验活性。 |
| `drug-ligand-prep`: `prepare_ligand.py` | 本机 CPU | 可作为 ligand validity/3D prep gate；不宜单独评分。 |
| `drug-mmpbsa-gbsa`: `compute_mmgbsa.py`, `compute_mmpbsa.py` | 本机 GPU/工作站或集群 | 条件可用但资源重。适合固定 complex 的 binding energy proxy；不建议首版。 |
| `drug-pocket-detection`: `detect_pockets.py`, `pocket_to_box.py`, `visualize_pockets.py` | 本机 CPU | 辅助工具。可用于 docking box 生成，不是候选性质 verifier。 |
| `drug-pose-validation`: `validate_poses.py` | 本机 CPU | 条件可用作 docking pose validity gate；不是主性质。 |
| `drug-protein-ligand-md`: `run_md.py` | 本机 GPU/工作站或集群 | 条件可用但不建议首版。MD binding/pose stability 成本高、随机性强。 |
| `drug-protein-prep`: `prepare_protein.py` | 本机 CPU | 辅助工具。 |
| `drug-redocking-rmsd`: `compute_rmsd.py` | 本机 CPU | 条件可用。适合 docking benchmark 的 pose RMSD verifier；不是本项目首版 P0。 |
| `drug-retrosynthesis`: `evaluate_ibm_rxn.py` | 在线服务/冻结 planner output | 不建议首版。IBM RXN/retrosynthesis 输出难冻结；若用需固定 stock、policy、服务版本。 |
| `drug-trajectory-analysis`: `analyze_trajectory.py` | 本机 CPU | 条件可用作 MD 后处理；依赖上游 MD protocol。 |
| `general-arxiv-search`: `arxiv_search.py` | 在线 API | 否。检索辅助。 |
| `general-chemical-literature`: `get_xrefs.py` | 在线 API | 否。文献辅助。 |
| `general-chemical-pricing`: `get_pricing.py` | 在线 API | 不建议作为正式 verifier。价格漂移且供应商状态变化；可作调研辅助。 |
| `general-patent-search`: `query_google_patents.py` | 在线 API/网页 | 否。检索辅助。 |
| `general-plot-digitizer`: `digitize_pipeline.py`, `extract_metadata.py`, `isolate_curves.py`, `pixel_to_data.py`, `plot_utils.py`, `suggest_colors.py`, `upscale_image.py`, prompt 文本 | 本机 CPU + VLM/图像处理 | 不建议作为首版自动 verifier。可用于多模态题的数据抽取，但 VLM/图像 pipeline 需要人工或冻结模型校准。 |
| `general-presentation`: `slide_utils.py` | 本机 CPU | 否。报告生成辅助。 |
| `mat-amorphization`: `prep_supercell.py`, `analyze_amorphous.py` | 本机 GPU/工作站；长 MD 建议集群 | 条件可用。适合固定材料的 amorphization/structure metric 题；需固定 MD protocol。 |
| `mat-calphad-phase-diagram`: `plot_phase_diagram.py` | 本机 CPU | 条件可用。适合 CALPHAD 数据库固定后的相图/phase fraction verifier；需固定 TDB database。 |
| `mat-calphad-property-diagram`: `plot_phase_fractions.py` | 本机 CPU | 条件可用。同上，需冻结 TDB 和条件。 |
| `mat-db-mp`: `query_mp.py`, `get_structure_by_id.py`, `get_elasticity.py`, `get_magnetism.py`, `find_similar_structures.py` | 在线 API/冻结 MP snapshot | 条件可用。适合 MP label verifier；正式 benchmark 必须冻结 snapshot 和 query result。 |
| `mat-db-nist-janaf`: `query_janaf.py` | 在线 API/冻结表 | 条件可用。适合热化学表值查证；需冻结数据。 |
| `mat-db-optimade`: `query_optimade.py` | 在线 API/冻结结构集 | 条件可用作 structure source/novelty gate；不应唯一评分。 |
| `mat-defect-energy`: `generate_defects.py`, `calculate_defect_energy.py` | 本机 GPU/工作站或集群 | 条件可用。适合固定 bulk/defect schema 的 defect formation energy；需固定 chemical potential 和 relaxation。 |
| `mat-defect-energy-dft`: `generate_defect_structures.py`, `parse_defect_results.py` | 计算集群/远程 DFT | 条件可用但不建议首版在线实时评分。 |
| `mat-dft-electron-phonon`: `generate_inputs.py` | 计算集群 | 辅助输入生成；真正 verifier 是后续 DFT/phonon/e-ph 输出解析，首版不建议。 |
| `mat-dft-electronic-transport`: `generate_inputs.py` | 计算集群 | 辅助输入生成；AMSET/DFT transport 可条件作为 verifier，但资源重。 |
| `mat-dft-ferroelectric`: `generate_inputs.py` | 计算集群 | 辅助输入生成；不建议首版。 |
| `mat-dft-lobster`: `generate_inputs.py`, `analyze_lobster.py` | 计算集群；需 VASP/LOBSTER | 条件可用。适合 bonding/COHP 题；不建议首版。 |
| `mat-dft-mixing-functionals`: `check_compatibility.py`, `apply_correction.py` | 本机 CPU | 条件可用作 energy correction/domain gate；需固定 correction table。 |
| `mat-dft-vasp`: `prepare_vasp_inputs.py`, `parse_vasp_results.py` | 计算集群；需 VASP | 条件可用。高可信但资源和 license 要求高；更适合预计算 verifier。 |
| `mat-dielectric-response`: `plot_dielectric.py` | 本机 CPU + DFT/MP data | 条件可用。若使用冻结 MP/DFT optics 输出，可验证 dielectric/refractive 指标。 |
| `mat-diffusion-analysis`: `analyze_diffusion.py`, `calculate_activation_energy.py` | 本机 CPU 后处理；MD 需 GPU/集群 | 条件可用。适合 ionic diffusion/activation energy 题；需固定 MD trajectories 或 protocol。 |
| `mat-disorder`: `order_disorder_sampler.py`, `run_ordering.py`, `relax_wrapper.py`, `iterative_ce_training.py` | 本机 CPU/GPU | 条件可用。固定 disordered lattice 和 CE/MLIP 后可验证 ordering/energy；训练迭代不应在评分时发生。 |
| `mat-elasticity`: `calculate_elasticity.py` | 本机 GPU/工作站或集群 | 条件可用。适合 bulk/shear modulus verifier；需固定 strain grid 和 calculator。 |
| `mat-electrochemical-window`: `calculate_ecw.py` | 本机 CPU + frozen MP/energy data | 条件可用。适合 electrochemical stability window；需冻结 reference entries。 |
| `mat-electronic-structure`: `get_mp_electronic_structure.py`, `plot_band_structure.py`, `plot_dos.py` | 在线 API/冻结 MP data；DFT 需集群 | 条件可用。适合 band gap/DOS 标签模式；正式路径冻结数据。 |
| `mat-elemental-energies`: `query_elements.py`, `get_elemental_energies.py` | 本机 CPU | 条件可用作 formation energy reference；需固定模型 elemental energy table。 |
| `mat-equation-of-state`: `calculate_eos.py` | 本机 GPU/工作站 | 条件可用。适合 bulk modulus/EOS 题；需固定 volume grid、fit model、calculator。 |
| `mat-grain-boundary`: `create_grain_boundary.py`, `calculate_gb_energy.py` | 本机 GPU/工作站或集群 | 条件可用但复杂。适合固定 GB geometry 题；不建议首版。 |
| `mat-grand-canonical-mc`: `run_gcmc_sweep.py`, `analyze_gcmc_results.py` | 本机 CPU/工作站 | 条件可用。适合 lattice gas/GCMC 指定题；需固定 potential 和 seed。 |
| `mat-intercalation-voltage`: `remove_atoms.py`, `calculate_voltage.py` | 本机 CPU + MLIP/DFT data | 条件可用。适合 battery voltage 题；需冻结 endpoint energies 和 references。 |
| `mat-ionic-substitution`: `propose_substitutions.py`, `find_structures_for_composition.py` | 本机 CPU + MP API | 主要是候选生成/检索。可作为 structure edit verifier 的辅助，不宜主评分。 |
| `mat-kinetic-monte-carlo`: `build_lattice_from_structure.py`, `run_lattice_kmc.py`, `analyze_kmc_msd.py`, `validate_detailed_balance.py` | 本机 CPU | 条件可用。适合 fixed-lattice diffusion/KMC 题；需固定 rate model。 |
| `mat-lammps-md`: `three-backends-build-check` | 本机 GPU/工作站或集群 | 只是环境/build check；不是 verifier。 |
| `mat-lattice-thermal-conductivity`: `calculate_thermal_conductivity.py` | 本机 GPU/工作站或集群 | 条件可用但资源重。适合 thermal conductivity 题；不建议首版。 |
| `mat-magnetic-density`: `extract_spin_density.py`, `parse_magnetic_moments.py`, `visualize_magnetic_structure.py` | 本机 CPU 后处理；DFT 需集群 | 条件可用。适合 magnetic moment/density 题，需冻结 DFT 输出或 workflow。 |
| `mat-md-probability-density`: `calculate_probability_density.py` | 本机 CPU 后处理 | 条件可用。依赖固定 MD trajectory/protocol。 |
| `mat-melting-point`: `create_supercell.py`, `create_interface.py`, `check_phase.py`, `get_features.py`, `monitor_melting.py`, `test_exact_copy.py` | 本机 GPU/工作站；建议集群 | 条件可用但不建议首版。melting-point MD 成本高且判据复杂。 |
| `mat-phase-diagram`: `get_phase_diagram.py` | 本机 CPU + frozen entries | 可直接/条件作为 P0-5 energy above hull verifier 的核心脚本，只要冻结 entry set 和 energy compatibility。 |
| `mat-phase-field-conservative`: `run_spinodal_decomposition.py` | 本机 CPU/工作站 | 条件可用作物理模拟题；与首版化学对象性质距离较远。 |
| `mat-phase-field-non-conservative`: `run_dendrite_growth.py`, `run_grain_growth.py` | 本机 CPU/工作站 | 同上，不建议首版。 |
| `mat-phonon`: `calculate_phonon.py`, `get_mp_phonon.py` | 本机 GPU/工作站或集群；MP data 可冻结 | 条件可用。适合 dynamical stability/phonon DOS 题；需固定 supercell/displacement/calculator。 |
| `mat-pourbaix-diagram`: `get_pourbaix_structures.py`, `calculate_pourbaix.py`, `calculate_pourbaix_mp.py` | 本机 CPU + frozen MP/Pourbaix entries | 条件可用。适合 aqueous stability 题；需冻结 ion references 和 pH/V 条件。 |
| `mat-qha-thermal-expansion`: `calculate_qha.py` | 本机 GPU/工作站或集群 | 条件可用但资源重。 |
| `mat-raman-spectra`: `analyze_raman_modes.py` | 本机 CPU 后处理；phonon/DFT 需 GPU/集群 | 条件可用。适合 Raman peak 题；需固定 phonon workflow。 |
| `mat-random-structure-search`: `generate_random_structures.py` | 本机 CPU/GPU | 只适合作候选生成，不能作为最终 verifier。 |
| `mat-reaction-network`: `enumerate_reactions.py`, `find_pathways.py` | 本机 CPU | 条件可用。适合 fixed reaction-network/pathway 题；不属于首版 open-generation 性质核心。 |
| `mat-sample-pes-by-md`: `feature_calculators.py`, `sampler.py`, `run_sampling.py` | 本机 GPU/工作站 | 主要用于生成训练/benchmark structures；不是最终 verifier，除非固定采样任务。 |
| `mat-solid-free-energy`: `run_frenkel_ladd.py` | 本机 GPU/工作站或集群 | 条件可用但资源重。 |
| `mat-stability`: `query_mp_hull.py`, `compute_ehull.py` | 本机 CPU + frozen MP entries/MLIP energies | 可作为 P0-5 energy above hull verifier 的核心候选。需冻结 reference entry set、energy correction 和 candidate energy source。 |
| `mat-structure-novelty`: `match_structure.py` | 本机 CPU + frozen structure database | 条件可用作 novelty/duplicate gate；不是主性质分数。 |
| `mat-surface-adsorption`: `calculate_adsorption.py` | 本机 GPU/工作站或集群 | 条件可用。匹配 P1-10 adsorption energy/HER descriptor；需固定 slab、adsorbate、site、relax protocol。 |
| `mat-surface-energy`: `create_slabs.py`, `calculate_surface_energy.py`, `generate_wulff.py` | 本机 GPU/工作站或集群 | 条件可用。适合 surface energy 题；需固定 Miller indices、slab thickness、reference energy。 |
| `mat-synthesis-recommendation`: `recommend_synthesis.py` | 在线/文本挖掘 | 不建议作为自动 verifier。可作 synthesis context，但不适合最终打分。 |
| `mat-xrd-calculator`: `calculate_xrd.py`, `xrd_utils.py` | 本机 CPU | 可直接作为固定结构 XRD pattern/peak verifier。当前已有 `atomisticskills_xrd_peak_001` smoke 题；若用于 open-generation，需要 candidate 是 CIF/structure 而不是模型自报峰位。 |
| `mat-xrd-digitizer`: `digitize_plot.py` | 本机 CPU + 图像输入/VLM 辅助 | 不建议首版作为 verifier。适合多模态数据抽取，不是稳定自动评分器。 |
| `mat-xrd-phase-analysis`: `dara_utils.py`, `phase_search.py` | 本机 CPU/GPU；Dara model | 条件可用。适合固定 experimental/synthetic XRD phase identification 题；需冻结 phase database/model 和输入谱图。 |
| `mat-xrd-refinement`: `convert_xrd_to_xy.py`, `dara_utils.py`, `plot.py`, `refine.py` | 本机 CPU/GPU；Dara/refinement | 条件可用。适合 Rietveld refinement 数值题；需冻结 initial phases、bounds、model。 |
| `ml-bayesian-optimization`: `suggest_candidates.py`, `plot_bo_results.py` | 本机 CPU | 只适合作 agent 搜索策略，不是 verifier。 |
| `ml-cluster-expansion`: `prepare_disordered.py`, `extract_mc_structures.py` | 本机 CPU | 辅助 CE workflow；固定 CE 后的 verifier 应用 `smol` 运行工具。 |
| `ml-committee-uncertainty`: `run_committee_inference.py` | 本机 GPU/工作站 | 条件可用作 uncertainty/domain gate；不宜主性质目标。 |
| `ml-fairchem-finetune`: `prepare_fairchem_data.py`, `generate_fairchem_config.py`, `extract_fairchem_logs.py` | 本机 GPU/集群 | 否。训练工具，不应在评分时运行。 |
| `ml-generative-diffcsp`: `batch_generate.py`, `unconditional_generate.py` | 本机 GPU/工作站 | 只适合作候选生成。 |
| `ml-generative-mattergen`: `prepare_training_data.py`, `run_finetuning.py` | 本机 GPU/集群 | 只适合作模型训练/候选生成，不是 verifier。 |
| `ml-mace-finetune`: `prepare_mace_data.py`, `generate_mace_config.py`, `extract_mace_logs.py` | 本机 GPU/集群 | 否。训练工具。 |
| `ml-matgl-finetune`: `prepare_matgl_data.py`, `generate_matgl_config.py`, `train_matgl.py` | 本机 GPU/集群 | 否。训练工具。 |
| `ml-mlip-benchmark`: `run_benchmark.py`, `plot_benchmark.py` | 本机 GPU/工作站 | 条件可用作 model selection/calibration；不直接评估 candidate，除非题目要求 benchmark MLIP 本身。 |
| `ml-mlip-speed`: `benchmark_mlips.py` | 本机 GPU/工作站 | 否。性能测试，不是化学性质 verifier。 |
| `ml-property-predictor`: `train_mace_property.py`, `train_matgl_property.py` | 本机 GPU/集群 | 否，训练工具；只有训练后冻结 checkpoint 才能作为 verifier。 |

无独立 script 但与工具相关的 skill：

- `drug-admet-prediction`：调用 `drugdisc.compute_molecular_descriptors`，可直接覆盖 RDKit descriptor/QED/Ro5/Veber，但不是实验 ADMET endpoint verifier。
- `drug-molecular-fingerprints`：调用 `drugdisc.compute_molecular_fingerprints`，适合 similarity/novelty/domain gate。
- `general-deep-research`、`general-peer-review`、`general-property-units`、`general-query-literature-database`、`general-workflow-planner`：知识/流程辅助，不适合最终性质 verifier。
- `mat-md-monitors`、`ml-foundation-potentials`、`ml-generative-adit`、`ml-mlip-automl`、`ml-property-predict-scd`：主要是 orchestration、model selection、generation 或 property-model setup；需要转化为冻结模型/固定脚本后才可能进入 verifier。

## 5. 与 `INITIAL-DESIGN.md` 首版性质方向的映射

| `INITIAL-DESIGN.md` 性质方向 | AtomisticSkills 中最接近的可用工具 | 部署建议 | 结论 |
|---|---|---|---|
| P0-1 RDKit QED/logP/TPSA/MW/HBD/HBA/rotatable bonds/SA score | `drugdisc.compute_molecular_descriptors`、`drug-admet-prediction`；本项目已有独立 RDKit verifier | 本机 CPU | 可直接采用。注意 AtomisticSkills descriptor 工具未覆盖 SA score；SA score 仍建议用本项目 RDKit Contrib 路径。 |
| P0-2 logS | AtomisticSkills 当前未提供 OPERA/SolTranNet/logS 专门工具 | 本机 CPU/GPU 或冻结数据 | 不宜从 AtomisticSkills 直接拿。继续按设计文档选择 OPERA/TDC/AqSolDB/ADMET-AI。 |
| P0-3 hERG/AMES/DILI safety endpoint | 当前 `drug-admet-prediction` 是 physchem heuristic，不是真 ADMET；`chem-hazard-toxicity` 可查安全数据 | 冻结数据/模型 | AtomisticSkills 不能直接覆盖正式 endpoint verifier。需 ADMET-AI/TDC/OPERA/CATMoS 等冻结模型或标签。 |
| P0-4 materials band gap | `matgl.predict_bandgap`；`mat-electronic-structure.get_mp_electronic_structure` | 本机 GPU/工作站或冻结 MP/Matbench | 可条件采用。首选冻结 MP/Matbench 标签；MatGL bandgap 作为 surrogate。 |
| P0-5 formation energy / energy above hull | `mat-stability.compute_ehull`、`mat-phase-diagram.get_phase_diagram`、`matgl/mace/fairchem.predict_structure`、`atomate2` | 本机 CPU + GPU，或冻结 DFT 数据/集群 | 可条件采用。正式应冻结 entry set、energy source、compatibility correction；Atomate2/VASP 更适合预计算。 |
| P0-6 HOMO-LUMO gap | ORCA scripts 可做 DFT；AtomisticSkills 没有 xTB verifier | 本机 x86_64/集群 | 不建议首版直接用 ORCA。按设计文档仍优先 xTB/GFN2-xTB。 |
| P0-7 dipole / polarizability / charges | ORCA scripts；MatGL/CHGNet charges 仅材料 surrogate | 本机/集群 | 条件可用但非首选。小分子建议 xTB/cclib；材料电荷可作辅助 descriptor。 |
| P1-8 Caco-2/BBB/CYP/PPB/clearance | AtomisticSkills 当前无真正 ADME endpoint 模型 | 冻结模型/数据 | 不直接采用。 |
| P1-9 target activity / binding affinity proxy | `drug-db-chembl`, `drug-bioactivity-assay`, `drug-docking-vina`, `drug-mmpbsa-gbsa` | 冻结 ChEMBL/BindingDB；docking 可本机，MD/GBSA 建议集群 | 条件可用。首版只建议窄 target、冻结 assay 或固定 docking protocol。 |
| P1-10 adsorption energy / HER descriptor | `mat-surface-adsorption`, `mat-surface-energy`, FairChem UMA OC/OMat, `atomate2` | 本机 GPU/集群 | 条件可用。必须固定 slab/adsorbate/site/relax protocol；更适合作 P1。 |
| P1-11 reaction validity / retrosynthesis / yield | `mat-reaction-network`, `drug-retrosynthesis`, `chem-react-ot`, `chem-irc-verification`, `chem-neb-barrier` | 本机 CPU/GPU 或在线服务/集群 | 大多不适合首版。可从 RDKit reaction validity 另行实现；AtomisticSkills 相关工具更偏 workflow 辅助。 |

## 6. 当前仓库已落地的 AtomisticSkills smoke verifier 判断

当前本项目已经定义 3 个 AtomisticSkills smoke tasks：

- `atomisticskills_base_supercell_001`：使用 `base.supercell_expansion`。可本机安装 `base-agent` 后通过 MCP 运行；适合验证 MCP adapter 和结构操作，不属于首版核心 open-generation property satisfaction。
- `atomisticskills_drugdisc_descriptor_001`：使用 `drugdisc.standardize_molecule` + `drugdisc.compute_molecular_descriptors`。可本机 CPU 安装 `drugdisc-agent`；可作为 P0-1 RDKit descriptor verifier 的变体。
- `atomisticskills_xrd_peak_001`：使用 `mat-xrd-calculator/scripts/calculate_xrd.py`。可本机 CPU 安装 `xrd-agent`；适合固定 structure -> XRD peak verifier。若要符合 `INITIAL-DESIGN.md` 的 open-generation 定位，题目应要求模型输出 CIF/structure，然后 verifier 计算 XRD pattern，而不是让模型直接报数值峰位。

## 7. 建议进入 benchmark 的优先级

优先级 A：可以近期纳入正式/半正式 verifier。

- `drugdisc.compute_molecular_descriptors`：小分子 QED/logP/TPSA/MW/HBD/HBA/Ro5/Veber。
- `drugdisc.standardize_molecule`、`parse_smiles_input`：小分子 parser/canonicalization/domain gate。
- `mat-xrd-calculator.calculate_xrd`：固定 CIF 的 XRD pattern/peak verifier。
- `mat-stability.compute_ehull` + `mat-phase-diagram.get_phase_diagram`：冻结 entry set 后用于 materials stability。
- `matgl.predict_bandgap`：冻结 surrogate 后用于 band gap smoke/medium tasks。

优先级 B：可作为 P1 或资源受控 benchmark。

- `matgl/mace/fairchem.predict_structure`、`relax_structure`：MLIP energy/force/relaxation verifier。
- `mat-diffusion-analysis`、`mace/matgl/fairchem.run_md`：小规模 diffusion/MD property tasks。
- `drug-docking-vina`、`drug-redocking-rmsd`：窄 target docking/pose tasks。
- `mat-surface-adsorption`：固定 slab/adsorbate 的 adsorption energy/HER descriptor。
- `smol.run_monte_carlo`：固定 CE 和 disordered lattice 的 thermodynamics task。

优先级 C：只用于候选生成、题目构造或 agent 工具增强，不作为最终 verifier。

- `MatterGen`、`ADiT`、`DiffCSP++` 生成工具。
- `ml-*finetune`、`ml-bayesian-optimization`、`ml-mlip-speed`。
- 文献、专利、pricing、presentation、workflow planner。
- XRD digitizer、synthesis recommendation、general deep research 这类依赖 VLM/文本检索的辅助工具。

## 8. 主要工程结论

1. AtomisticSkills 最适合给本 benchmark 提供三类资源：本机 deterministic descriptor/structure tools、冻结 ML surrogate/verifier wrappers、以及用于 P1 的集群型物理模拟后端。
2. 不能把 AtomisticSkills 的 agent workflow 本身当作 verifier。Benchmark 评分需要抽取其中可复现、可冻结、接口稳定的底层 tool/script。
3. 生成模型类工具应明确排除在 verifier 之外，避免“生成器自证”。
4. 在线数据库工具可以用于构造题目和调研，但正式评分必须冻结 snapshot 或预下载标签。
5. Atomate2/VASP、ORCA、长 MD、surface adsorption、GBSA/PBSA 等可以成为高可信 verifier，但部署形态应是计算集群服务或预计算标签库，不适合在公开首版中无资源控制地实时运行。
6. 与 `INITIAL-DESIGN.md` 最一致的首批 AtomisticSkills 候选是：`drugdisc` descriptors、`mat-xrd-calculator`、`mat-stability`/`mat-phase-diagram`、`matgl.predict_bandgap`、以及冻结 MLIP energy/relaxation wrappers。
