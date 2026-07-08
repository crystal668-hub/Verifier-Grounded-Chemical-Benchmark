# Verifier backend 方法覆盖与遗漏方向调研报告

日期：2026-06-30

## 1. 范围与核对口径

本报告从“传统规则、量子化学、分子模拟、机器学习、热力学建模、反应网络建模”等方法学角度，核对当前仓库已经实现的 verifier backend，并整理可用于材料/化学性质计算或预测的高影响力方法。

本地实现核对来源：

- `verifier_grounded_benchmark/registry.py`
- `tasks/*/verifier_specs.yaml`
- `tasks/rdkit_baseline/tasks.yaml`
- `tasks/xtb_xyz/tasks.yaml`
- `verifiers/*/backend.py`
- `verifiers/openmm/runtime.py`
- 既有 track/research 文档：`docs/tracks/` 与 `docs/research/`

外部方法调研优先采用官方文档、官方仓库、论文页或项目主页。报告中的“已实现”按代码和 task spec 认定；“正式 track”按 builtin registry 认定；“prototype / smoke”不等同于正式 benchmark track。

## 2. 结论摘要

当前正式注册的 benchmark track 只有两类：

| track | 方法类别 | 输入 | 当前主要性质 | 状态 |
|---|---|---|---|---|
| `rdkit` | 传统规则/描述符 | SMILES | QED、logP、TPSA、MW、HBA/HBD、SA score、fraction Csp3 | 正式 |
| `xtb` | 低成本半经验量子化学 | explicit-H XYZ | HOMO-LUMO gap、dipole、relaxation energy、LUMO、polarizability、ALPB solvation selectivity、electrophilicity、Fukui、Hessian thermo | 正式 |

代码和 task specs 中还存在以下非正式或 prototype 后端：

| backend | 方法类别 | 当前性质 | 状态 |
|---|---|---|---|
| `admet_ai` | 小分子 ML/QSAR | AqSolDB solubility、hERG、AMES、BBB、Caco-2 等脚本 | 已实现 backend，未进入 builtin registry |
| `matgl` | 材料 GNN/ML surrogate | formation energy、band gap | 已实现 native backend，未进入 builtin registry |
| `mace_mp` | 材料 MLIP | energy、energy per atom、max force、stress norm | 已实现 native backend，未进入 builtin registry |
| `atomisticskills_smoke` | 结构操作/描述符/XRD script | supercell、DrugDisc descriptors、XRD peak | smoke，非正式性质 track |

主要覆盖强项：

- 小分子 2D 描述符和基础 drug-likeness：覆盖较完整。
- 小分子 3D 低成本量子性质：覆盖已从 gap/dipole 扩展到 LUMO、极化率、溶剂化、Fukui、热化学等。
- 小分子 ADMET/QSAR：已有 backend 雏形，适合进入下一批正式 track。
- 材料 ML surrogate：已有 MatGL/MACE 雏形，可扩成材料性质 track。

主要遗漏：

- 经典力场、分子动力学、蒙特卡洛、吸附/扩散等分子模拟 backend。
- DFT/ab initio 量子化学与通用量化输出解析 backend，例如 Psi4/ORCA/Gaussian+cclib。
- 相图、energy-above-hull、CALPHAD、Pourbaix、电化学稳定窗口等热力学建模 backend。
- 反应网络、动力学、自动机理生成、逆合成、反应有效性/产率预测 backend。
- 材料声子、弹性、介电、磁性、表面/吸附/催化、缺陷等二级材料性质 backend。
- 冻结数据库快照型 backend，例如 Materials Project/Matbench/ChEMBL/BindingDB/ORD，而不是实时在线查询。
- 通用 applicability domain、uncertainty、novelty/duplicate gate 和 provenance/hash 固化机制。

建议优先级：

| 优先级 | 建议新增方向 | 理由 |
|---|---|---|
| P0 | ADMET-AI 正式小分子 ADMET track | backend 已实现，依赖已 pin，性质重要且低成本 |
| P0 | Materials stability/phase backend：pymatgen PhaseDiagram + 冻结 entries + MatGL/MACE energy | 材料 benchmark 核心性质，能补足 formation energy 到 energy above hull 的落地链路 |
| P1 | OpenMM/RDKit force-field conformer/strain backend | 低成本补足分子模拟与构象质量，能作为 RDKit/xTB 之间的桥 |
| P1 | cclib/Psi4/ORCA parser backend | 扩展到可替换高精度 QM、TDDFT、IR/Raman/NMR 等谱学性质 |
| P1 | XRD/phonon/elasticity backend | 材料结构-性质验证维度明确，已有 AtomisticSkills XRD smoke 可延展 |
| P2 | Cantera/RMG reaction-network backend | 价值高，但输入 schema 和 domain 需要先收窄 |
| P2 | Docking/adsorption/catalysis backend | 可做高区分任务，但 protocol 固化复杂，首批需窄 target/窄 slab |

## 3. 当前已实现 backend 逐项核对

### 3.1 传统规则与描述符

当前实现：

| backend/spec | 输入 | 性质 | 代码入口 | 状态 |
|---|---|---|---|---|
| `rdkit_descriptors` | SMILES | QED、logP、TPSA、MW、HBA、HBD、SA score、fraction Csp3；backend 还支持 rotatable bonds、ring count | `verifiers/rdkit_descriptors/backend.py` | 正式 track |
| AtomisticSkills DrugDisc descriptors | SMILES | descriptor/Ro5/Veber/QED 等外部 MCP 输出 | `tasks/atomisticskills_smoke/verifier_specs.yaml` | smoke |

实现评价：

- 这是当前最稳定、最确定、最便宜的一类 verifier。SMILES 解析、canonicalization、元素/分子量/电荷 domain gate 都已实现。
- 适合做基础 open-generation sanity layer，但单独使用容易被简单分子或 descriptor gaming 利用，建议与 ADMET、构象、novelty 或合成可行性组合。

普遍使用方法：

- RDKit descriptors：QED、Crippen logP、TPSA、HBD/HBA、rotatable bonds、ring count、formal charge、元素和拓扑规则。
- 合成可及性 heuristic：SA score、SCScore、route-based retrosynthesis feasibility。
- 结构过滤：PAINS、Brenk、reactive/toxicophore alerts、Lipinski/Veber/Ghose/Egan rules。
- 相似性与多样性：Morgan/ECFP fingerprint、Tanimoto、Bemis-Murcko scaffold、Butina clustering。

可补充方向：

- `rotatable_bonds` 与 `ring_count` 已在 backend 字典中有函数，但当前没有正式 verifier spec/task。
- PAINS/Brenk/structural alert gate。
- Tautomer/protonation/standardization policy，避免同一结构多种 SMILES 或电荷态带来的评分漂移。
- Novelty/duplicate gate：对训练集、sample answers、公共数据库或历史 submissions 做 scaffold/fingerprint 距离过滤。

外部依据：

- RDKit QED 文档说明 QED 由 MW、logP、TPSA、HBD/HBA、芳香环、可旋转键和结构 alerts 等组成：https://www.rdkit.org/docs/source/rdkit.Chem.QED.html
- RDKit 官方源码和 Contrib 提供 SA_Score 实现入口：https://github.com/rdkit/rdkit/tree/master/Contrib/SA_Score

### 3.2 低成本量子化学与电子结构

当前实现：

| backend/spec | 输入 | 性质 | 代码入口 | 状态 |
|---|---|---|---|---|
| `local_xtb` | explicit-H XYZ | HOMO-LUMO gap、dipole moment、relaxation energy | `verifiers/xtb/backend.py` | 正式 |
| `local_xtb` | explicit-H XYZ | LUMO energy、polarizability per heavy atom、ALPB water/hexane selectivity、global electrophilicity、Fukui f+ carbon site、imaginary frequency count、entropy per heavy atom | `tasks/xtb_xyz/verifier_specs.yaml` + `verifiers/xtb/backend.py` | 正式 spec/task |

实现评价：

- xTB backend 已不只是 gap/dipole；当前 specs 已覆盖较宽的小分子量子性质集。
- Direct-XYZ schema 能测试模型提交可优化、几何合理的 3D 分子，而不是只生成拓扑结构。
- 现实现固定 neutral closed-shell、限定元素与尺寸，这对可复现性是必要的。

普遍使用方法：

- 半经验/紧束缚：GFN0/1/2-xTB、DFTB+，适合快速几何优化、能量、轨道能级、偶极、极化率、局部反应性和溶剂化 proxy。
- DFT/ab initio：Psi4、ORCA、Q-Chem、Gaussian、NWChem、PySCF，适合更可信的 HOMO/LUMO、IP/EA、TDDFT 激发能、IR/Raman/NMR、热化学。
- 通用输出解析：cclib 解析 `moenergies`、`homos`、`moments`、`polarizabilities`、`vibfreqs`、`enthalpy`、`entropy`、`freeenergy`、`etenergies`、`etoscs` 等。
- 溶剂模型：GBSA/ALPB、COSMO/CPCM/SMD。
- 反应性指标：Fukui functions、electrophilicity、partial charges、bond orders、BDE、proton affinity。

遗漏方向：

- DFT/ab initio backend：当前没有 Psi4/ORCA/PySCF/cclib 统一 parser backend。
- 谱学性质：IR/Raman/NMR/UV-Vis/oscillator strength 尚无正式 verifier。
- 电荷模型：AM1-BCC、RESP/ESP、Mulliken/NPA/CM5/xTB charges 还未作为任务性质。
- 构象集合：CREST/RDKit ETKDG/MMFF/xTB conformer ensemble、Boltzmann-weighted properties 尚未覆盖。
- 高阶反应性质：BDE、pKa/proton affinity、redox potential、barrier/TS verification 尚未覆盖。

外部依据：

- xTB properties 文档展示 HOMO/LUMO、HOMO-LUMO gap、dipole 等输出：https://xtb-docs.readthedocs.io/en/latest/properties.html
- cclib 官方 parsed data 列出可解析的量化输出属性：https://cclib.github.io/data.html
- Psi4 是开源量子化学程序，可作为本地 DFT/ab initio backend 候选：https://psicode.org/

### 3.3 小分子机器学习、QSAR 与 ADMET

当前实现：

| backend/spec | 输入 | 性质 | 代码入口 | 状态 |
|---|---|---|---|---|
| `admet_ai` | SMILES | ADMET-AI endpoint，例如 solubility、hERG、AMES、BBB、Caco-2 | `verifiers/admet_ai/backend.py` 与 `verifiers/admet_ai/*.py` | backend/task script 已实现，未进入 builtin registry |

实现评价：

- ADMET-AI 是最接近可立即正式化的遗漏方向：`pyproject.toml` 已 pin `admet-ai==2.0.1`，backend 直接用 Python API。
- OPERA wrapper 曾作为外部部署候选评估；当前 active codebase 已移除 OPERA 路径，若恢复应作为 Linux verifier image 重新设计。
- 当前缺少统一的 applicability-domain/uncertainty 接口；ADMET-AI backend 当前只用结构 domain gate。

普遍使用方法：

- 图神经网络/MPNN：Chemprop、D-MPNN、AttentiveFP、GROVER 等，常用于 ADMET、溶解度、毒性、活性预测。
- Transformer/预训练分子模型：ChemBERTa、MolBERT、Uni-Mol、Graphormer 类模型。
- QSAR/传统 ML：随机森林、XGBoost、SVM、kNN、PLS，配合 RDKit/PaDEL/Mordred descriptors 和 fingerprints。
- 数据基准：TDC ADMET、MoleculeNet、AqSolDB/ESOL、FreeSolv、Lipophilicity、Tox21、ClinTox、BBBP、hERG、AMES、DILI。
- ADMET endpoints：solubility/logS、Caco-2/PAMPA、BBB、P-gp、bioavailability、PPB、VDss、clearance、half-life、CYP inhibition/substrate、hERG、AMES、DILI、LD50、Tox21/ClinTox。

遗漏方向：

- 将 ADMET-AI endpoint 正式注册为 track，并明确分类/回归分数含义、单位、阈值、calibration 和 AD gate。
- OPERA Linux verifier image，使用固定 OPERA release 和 MATLAB Runtime 目录。
- SolTranNet/ESOL/FreeSolv 等独立物化性质模型，用于交叉验证 logS/hydration free energy。
- ChEMBL/BindingDB/TDC DTI 冻结快照或 DeepPurpose/DeepDTA 类 target activity backend。
- 多目标 ADMET 聚合：例如 solubility + hERG + AMES + BBB/Caco-2。

外部依据：

- ADMET-AI 官方仓库说明其使用 Chemprop 模型、训练于 TDC ADMET 数据，支持 CLI/Python API/web server：https://github.com/swansonk14/admet_ai
- ADMET-AI 论文介绍其作为 Python package 与 web 平台提供快速 ADMET 预测：https://pmc.ncbi.nlm.nih.gov/articles/PMC11226862/
- OPERA 官方仓库说明其是开源/开放数据 QSAR 套件，覆盖 physicochemical、environmental fate、toxicity，并提供 applicability domain：https://github.com/kmansouri/OPERA
- TDC ADMET benchmark 列出常用 ADMET endpoint：https://tdcommons.ai/benchmark/admet_group/overview/
- Chemprop 官方文档：https://chemprop.readthedocs.io/

### 3.4 材料机器学习与 ML interatomic potentials

当前实现：

| backend/spec | 输入 | 性质 | 代码入口 | 状态 |
|---|---|---|---|---|
| `matgl` | CIF | formation energy、band gap | `verifiers/matgl/backend.py` | native backend 已实现 |
| `mace_mp` | CIF | energy、energy per atom、max force、stress norm | `verifiers/mace_mp/backend.py` | native backend 已实现 |

实现评价：

- 当前材料 ML backend 已能解析 CIF、做元素/原子数/体积 gate，并调用 MatGL/MACE 预测。
- `verifiers/matgl/backend.py` 支持 native MatGL model load，是正式化的好基础；MCP prototype 路径已从 active codebase 移除。
- 当前 prototype domain 只覆盖非常窄的 Si fixture/小结构，尚不能代表真正材料 discovery track。

普遍使用方法：

- 材料图神经网络 property predictor：MEGNet、M3GNet、MatGL、CGCNN、SchNet、DimeNet、ALIGNN、Matformer、MODNet、CrabNet/Roost。
- ML interatomic potentials：MACE-MP、CHGNet、M3GNet universal potential、MatterSim、FairChem/UMA、SevenNet、NequIP/Allegro。
- 典型性质：formation energy、band gap、total energy、forces、stress、magnetic moments、elastic moduli、dielectric constant、density、relaxed structure、phonons、surface/adsorption energy。
- 标准数据：Materials Project、Matbench、JARVIS、OQMD、AFLOW、MPTrj、Alexandria、OMat/OC datasets。

遗漏方向：

- Energy above hull：formation energy 还不是 stability verifier；需要 PhaseDiagram、reference entries 和 compatibility corrections。
- Relaxation protocol：MatGL/MACE/CHGNet relaxation 后性质，而不是只对输入 CIF 做 static prediction。
- Elasticity、phonon/dynamical stability、dielectric/refractive、magnetism、defect energy、surface/adsorption energy。
- Materials Project/Matbench 冻结标签 backend，避免实时 API 和版本漂移。
- Applicability/domain：结构匹配、元素覆盖、训练集近邻距离、uncertainty/committee、volume/coordination sanity。

外部依据：

- MatGL 文档说明提供 Materials Project formation energy 和 multi-fidelity band gap 等预训练模型：https://matgl.ai/
- CHGNet 官方仓库说明可预测 energy、force、stress 和 magmom：https://github.com/CederGroupHub/chgnet
- MACE 文档说明 MACE-MP 覆盖 89 元素、基于 MPTrj 训练：https://mace-docs.readthedocs.io/en/latest/guide/foundation_models.html
- Materials Project API examples 展示 band gap、energy above hull、thermo phase diagram 等字段/查询：https://docs.materialsproject.org/downloading-data/using-the-api/examples
- Matbench benchmark 覆盖 dielectric、expt_gap、mp_gap、formation energy、elastic moduli 等材料性质：https://github.com/materialsproject/matbench

### 3.5 分子模拟、力场、MD 与 MC

当前实现：没有正式 backend。`pyproject.toml` 已包含 `ase==3.28.0` 和 `cclib==1.8.1`，但尚无 OpenMM/GROMACS/LAMMPS/RASPA/ASE simulation verifier。

普遍使用方法：

- 小分子/生物分子力场：OpenMM + OpenFF/GAFF/Amber/CHARMM；RDKit ETKDG + MMFF/UFF；OpenFF Toolkit/Interchange。
- 材料/原子模拟：ASE calculators、LAMMPS、GROMACS、HOOMD-blue、MACE/CHGNet/MatGL ASE calculators。
- 蒙特卡洛/吸附：RASPA、Towhee、GCMC、Widom insertion，用于 MOF/porous materials Henry coefficient、gas uptake/isotherms。
- 增强采样/自由能：PLUMED、alchemical FEP/TI、umbrella sampling、metadynamics。
- 后处理：MSD/diffusion coefficient、RDF、density, radius of gyration, order parameters, adsorption energy distributions。

适合 verifier 的性质：

- 小分子 conformer strain / MMFF minimized energy / force-field clash score。
- 短 MD stability sanity：RMSD、bond/angle violation、temperature drift。
- Diffusion coefficient 或 ionic conductivity，但需固定体系、温度、时长和随机种子。
- MOF/porous material Henry coefficient、single-component uptake、selectivity。
- Surface/adsorption energy with fixed slab/site/adsorbate and fixed calculator。

主要风险：

- 随机性和资源成本高；长 MD/MC 不适合首版同步评分。
- 力场参数化失败模式复杂，尤其是 charged species、metals、coordination compounds、reactive systems。
- 需要严格固定 seed、ensemble、time step、thermostat/barostat、cutoff、force field 和 topology builder。

推荐落地顺序：

1. RDKit ETKDG/MMFF 或 OpenMM/OpenFF 小分子 conformer strain verifier。
2. ASE + fixed MLIP static/relax energy verifier。
3. RASPA/GCMC 或 Widom insertion 只在固定 MOF/adsorbate 小体系中试点。

外部依据：

- OpenMM 官方文档定位为 high-performance molecular simulation toolkit，支持 Python API、minimization 和 MD：https://openmm.org/
- ASE 官方文档提供 calculators、optimizers 和 MD workflow：https://wiki.fysik.dtu.dk/ase/
- GROMACS 官方文档：https://manual.gromacs.org/
- LAMMPS 官方文档：https://docs.lammps.org/
- RASPA3 文档/仓库：https://github.com/iRASPA/RASPA3

### 3.6 热力学建模、相图与稳定性

当前实现：没有正式 phase/stability backend。MatGL 已能给 formation energy，AtomisticSkills 调研中也识别了 `mat-stability.compute_ehull` 和 `mat-phase-diagram.get_phase_diagram` 的潜力，但当前仓库未实现冻结 entries + PhaseDiagram verifier。

普遍使用方法：

- `pymatgen.analysis.phase_diagram.PhaseDiagram`：用 computed entries 计算 decomposition、energy above hull、stable entries。
- Materials Project thermo：GGA/GGA+U/R2SCAN mixed phase diagram、formation energy、energy above hull。
- CALPHAD：pycalphad + TDB 数据库，计算 equilibrium phase fractions、phase diagrams、driving forces。
- Pourbaix/electrochemical：pymatgen PourbaixDiagram、aqueous stability、electrochemical window。
- 电池材料：intercalation voltage、chemical potentials、grand potential phase diagrams。
- 分子热力学：JANAF/NIST 数据、Cantera thermo models、NASA polynomials、partition-function thermochemistry。

适合 verifier 的性质：

- Crystal candidate 的 `energy_above_hull`，基于冻结 reference entries 和 candidate predicted/DFT energy。
- Stable/metastable classification，例如 `E_hull <= 0.05 eV/atom`。
- Battery voltage、aqueous stability window、Pourbaix stable region。
- CALPHAD phase fraction at fixed composition/T/P。
- Molecular reaction enthalpy/free energy from frozen thermochemical table or fixed quantum workflow。

主要风险：

- 不能实时依赖 Materials Project API 作为唯一 oracle；正式 benchmark 应冻结 entry set、compatibility correction 和 thermo type。
- MLIP/MatGL formation energy 与 MP DFT entries 的 reference state 需要统一，否则 energy above hull 会无意义。
- CALPHAD 数据库许可证和版本需要明确。

推荐落地顺序：

1. `pymatgen PhaseDiagram + frozen entries` backend。
2. `MatGL/MACE energy -> corrected entry -> E_hull` workflow。
3. Pourbaix/electrochemical window narrow tasks。
4. pycalphad phase fraction tasks。

外部依据：

- pymatgen PhaseDiagram 文档：https://pymatgen.org/pymatgen.analysis.html
- Materials Project API examples 包含 energy-above-hull 和 thermo phase diagram 查询：https://docs.materialsproject.org/downloading-data/using-the-api/examples
- pycalphad 文档：https://pycalphad.org/docs/latest/

### 3.7 反应网络、动力学、合成与反应性质

当前实现：没有正式 reaction backend。仓库依赖中已有 `ord-schema==0.6.5` 和 `chembl-webresource-client==0.10.9`，但没有反应 schema verifier、yield predictor、retrosynthesis planner 或 reaction-network backend。

普遍使用方法：

- 反应有效性和映射：RDKit reaction SMARTS、RXNMapper、atom balance、mapping confidence、reaction center checks。
- 产率预测：Yield-BERT/rxn_yields、Molecular Transformer、ORD/USPTO/HTE datasets。
- 逆合成可行性：AiZynthFinder、ASKCOS、Retro*、template-based MCTS，固定 stock 和 policy。
- 自动机理生成：RMG-Py，适合燃烧/大气/热解等反应网络。
- 反应动力学与热力学模拟：Cantera、Chemkin，解 ODE、敏感性分析、reaction path analysis。
- 势垒/TS/路径：NEB、IRC、Sella、xTB/DFT/MLIP barrier workflow。

适合 verifier 的性质：

- Reaction SMILES validity、atom mapping confidence、mass/charge balance。
- Fixed reaction family 的 predicted yield 或 selectivity。
- Retrosynthesis solved flag、route length、route score、stock availability。
- Fixed reaction network 的 ignition delay、major product fraction、equilibrium conversion、rate-limiting step。
- Fixed endpoint NEB barrier 或 TS imaginary-frequency verification。

主要风险：

- “通用反应”输入太开放，首版必须限定反应 family、reagent/condition schema、stock、template set 和 scoring。
- 逆合成/产率模型容易受公开训练集与 patent memorization 影响；需要 novelty 和 frozen data splits。
- RMG/Cantera 更适合给定网络/机制的数值题，不适合未限定化学空间的开放生成。

推荐落地顺序：

1. RDKit reaction validity + RXNMapper confidence backend。
2. AiZynthFinder route feasibility backend，固定 stock/template/policy。
3. Fixed family yield predictor backend。
4. Cantera/RMG reaction-network numerical tasks。

外部依据：

- RXNMapper 官方仓库：https://github.com/rxn4chemistry/rxnmapper
- AiZynthFinder 文档：https://molecularai.github.io/aizynthfinder/
- Cantera 文档：https://cantera.org/documentation/
- RMG-Py 文档：https://reactionmechanismgenerator.github.io/RMG-Py/
- Open Reaction Database schema：https://github.com/open-reaction-database/ord-schema

## 4. 分类覆盖矩阵

| 分类 | 当前实现程度 | 已有 backend/verifier | 当前性质 | 主要遗漏 |
|---|---|---|---|---|
| 传统规则/描述符 | 高 | RDKit, DrugDisc smoke | QED、logP、TPSA、MW、HBA/HBD、SA、Fsp3 | rotatable/ring tasks、alerts、novelty、standardization |
| 量子化学 | 中高 | xTB | gap、dipole、relaxation、LUMO、polarizability、solvation、electrophilicity、Fukui、thermo | DFT/ab initio、spectroscopy、charges、BDE/redox/pKa、conformer ensemble |
| 小分子 ML/QSAR | 中 | ADMET-AI, SolTranNet, MolGpKa | ADMET endpoints、logS、pKa count/min/max | formal track、AD/uncertainty、DTI/activity |
| 材料 ML/GNN/MLIP | 中 | MatGL, MACE | formation energy、band gap、energy | E_hull、relaxation、elasticity、phonon、dielectric、magnetism、surface/defect |
| 分子模拟/MD/MC | 低 | none | none | OpenMM/OpenFF、ASE/LAMMPS/GROMACS、RASPA、diffusion/adsorption/free energy |
| 热力学建模 | 低 | none | none | pymatgen PhaseDiagram/E_hull、CALPHAD、Pourbaix、Cantera thermo |
| 反应网络/合成 | 低 | none | none | RDKit reactions、RXNMapper、AiZynthFinder、yield predictor、Cantera/RMG |
| 数据库快照/标签 | 低 | partial dependencies only | none | MP/Matbench/ChEMBL/BindingDB/ORD frozen snapshots |
| 实验谱图/结构验证 | 低-中 | XRD smoke | XRD peak smoke | full XRD pattern, NMR/IR/Raman/UV, phonon spectra |

## 5. 重要遗漏小方向清单

下面按“可成为 verifier backend 的小方向”列出建议补齐项。

### 5.1 小分子

| 小方向 | 性质 | 推荐方法 | 落地性 |
|---|---|---|---|
| ADMET formal track | logS、hERG、AMES、BBB、Caco-2、CYP、DILI、clearance | ADMET-AI first；OPERA 已作为本机架构不适配尝试移除 | 高 |
| 结构 alerts | PAINS、Brenk、reactive groups | RDKit SMARTS filters | 高 |
| 构象/strain | MMFF/UFF minimized energy、clash、conformer diversity | RDKit ETKDG/MMFF, OpenMM/OpenFF | 高 |
| 电荷/极性 | Gasteiger、AM1-BCC、RESP-like、xTB charges | RDKit/OpenFF/xTB/cclib | 中 |
| 水合/溶剂化 | FreeSolv/hydration free energy、logD/pKa | SolTranNet、MolGpKa、xTB GBSA/ALPB、ML models；OPERA 仅作为移除的历史候选 | 中 |
| 谱学 | IR/Raman/NMR/UV-Vis | DFT/xTB/cclib, ML surrogate | 中-低 |
| 靶点活性 | pChEMBL/pKi/pKd/probability | ChEMBL snapshot, DeepPurpose/DeepDTA | 中 |
| 合成可行性 | route solved、route depth、stock cost | AiZynthFinder | 中 |

### 5.2 材料

| 小方向 | 性质 | 推荐方法 | 落地性 |
|---|---|---|---|
| 稳定性 | energy above hull、stable/metastable class | pymatgen PhaseDiagram + frozen MP entries + MatGL/MACE energy | 高 |
| 结构弛豫 | relaxed energy、max force、volume change | MatGL/MACE/CHGNet ASE relax | 中高 |
| 弹性 | K/G/Poisson | Matbench labels、ML surrogate、ASE strain workflow | 中 |
| 声子/动力学稳定性 | imaginary phonons、phonon DOS | phonopy + MLIP/DFT; frozen MP phonon | 中 |
| 介电/光学 | dielectric constant、refractive index、band edges | MP/Matbench labels, ML surrogate | 中 |
| 表面/吸附/催化 | adsorption energy、HER ΔG_H、selectivity | ASE slab + FairChem/UMA/MACE/DFT | 中-低 |
| 缺陷 | defect formation energy, migration barrier | pymatgen defects + MLIP/DFT | 低-中 |
| XRD/结构指纹 | peak positions/intensity, pattern match | pymatgen/ASE/AtomisticSkills XRD | 高 |

### 5.3 热力学与反应

| 小方向 | 性质 | 推荐方法 | 落地性 |
|---|---|---|---|
| 相图 | phase fraction、phase boundary、E_hull | pymatgen, pycalphad | 中 |
| 电化学 | Pourbaix stability、EC window、battery voltage | pymatgen Pourbaix/intercalation | 中 |
| 反应热 | ΔH/ΔG/K_eq | Cantera thermo, JANAF/NIST frozen tables, quantum thermo | 中 |
| 机理网络 | product fraction、ignition delay、rate sensitivity | Cantera/RMG | 中-低 |
| 反应有效性 | atom balance、mapping confidence | RDKit reactions + RXNMapper | 高 |
| 产率/选择性 | predicted yield/selectivity | rxn_yields/Yield-BERT, ORD snapshot | 中 |
| 势垒/路径 | NEB barrier, TS imaginary frequency | ASE/Sella/NEB + xTB/MLIP/DFT | 低-中 |

## 6. 推荐 roadmap

### 6.1 近期可做：低风险高增益

1. ADMET-AI formal track
   - 首批 endpoint：`Solubility_AqSolDB`、`hERG`、`AMES`、`BBB_Martins`、`Caco2_Wang`。
   - 加 domain gate：allowed elements、MW、formal charge、single component。
   - 对分类 endpoint 明确是 probability minimize/maximize，不写成实验 label。

2. RDKit 补齐传统规则
   - 为 `rotatable_bonds`、`ring_count` 增加 verifier spec/task。
   - 加 PAINS/Brenk structural alert gate。
   - 加 optional fingerprint novelty gate。

3. Materials stability backend
   - 冻结一个小型 MP/Matbench reference entry set。
   - 用 `pymatgen PhaseDiagram` 计算 energy above hull。
   - 将 MatGL/MACE formation/static energy 输出纳入统一 reference convention，避免混用单位/参考态。

4. XRD pattern verifier
   - 从当前 AtomisticSkills XRD peak smoke 扩为 CIF 输入的正式/半正式结构 verifier。
   - 先做 peak position/intensity tolerance，再做 full-pattern similarity。

### 6.2 中期可做：提高 benchmark 区分度

1. OpenMM/RDKit conformer backend
   - 验证提交 3D 构象是否低 strain、无 clash、可被 force field 参数化。
   - 可作为 RDKit 和 xTB 的前置质量门。

2. cclib/Psi4/ORCA parser backend
   - 统一支持 DFT/TDDFT/thermochemistry output parsing。
   - 第一批只做小体系和短 timeout，避免变成高成本 runner。

3. MatGL/MACE/CHGNet relaxation backend
   - 计算 relaxed energy、volume change、max force、stress。
   - 与 E_hull、elasticity、phonon 连接。

4. Reaction validity + retrosynthesis
   - RDKit reaction parse/balance。
   - RXNMapper confidence。
   - AiZynthFinder fixed-stock route feasibility。

### 6.3 长期储备：高价值但需要窄 domain

- Adsorption/catalysis：fixed slab、fixed adsorbate、fixed site/relax protocol。
- GCMC/MD：fixed material/guest/T/P/seed，短程序列或预计算 trajectory 后处理。
- CALPHAD/Pourbaix：固定数据库和 composition grid。
- Reaction-network/kinetics：固定 reaction family 或 mechanism，Cantera/RMG 作为 numerical verifier。
- Spectroscopy：NMR/IR/Raman/UV-Vis，优先冻结数据或小体系 DFT/xTB workflow。

## 7. 工程落地原则

新增 backend 应统一记录：

- 工具和 Python package 版本。
- 模型 checkpoint 名称、来源、hash、本地 cache 路径。
- 输入标准化规则：SMILES/CIF/XYZ/reaction SMILES 的 canonicalization、tautomer/protonation、charge/spin、单位。
- 适用域：元素、尺寸、单组分、structure sanity、训练集距离、AD flag、uncertainty。
- 输出单位和 scoring policy。
- 失败分类：parse、validity、domain、environment、tool、timeout。
- 是否为 surrogate：明确区分“模型预测/固定工具输出”和“实验真实性质”。
- 数据源冻结：数据库型 verifier 必须使用 snapshot/hash，不以实时网络结果作为正式 oracle。

## 8. 与当前仓库文档的同步问题

`docs/tracks/xTB.md` 当前仍写“task pack 7 题、verifier specs 3 个”，但实际 `tasks/xtb_xyz/tasks.yaml` 已有 13 题，`tasks/xtb_xyz/verifier_specs.yaml` 已有 9 个 xTB verifier spec。后续应单独更新 xTB track 文档，避免调研报告和 track 文档出现事实不一致。

## 9. 参考资料

- RDKit QED documentation: https://www.rdkit.org/docs/source/rdkit.Chem.QED.html
- RDKit SA_Score Contrib: https://github.com/rdkit/rdkit/tree/master/Contrib/SA_Score
- xTB properties documentation: https://xtb-docs.readthedocs.io/en/latest/properties.html
- cclib parsed data documentation: https://cclib.github.io/data.html
- Psi4: https://psicode.org/
- ADMET-AI GitHub: https://github.com/swansonk14/admet_ai
- ADMET-AI paper: https://pmc.ncbi.nlm.nih.gov/articles/PMC11226862/
- OPERA GitHub: https://github.com/kmansouri/OPERA
- TDC ADMET benchmark: https://tdcommons.ai/benchmark/admet_group/overview/
- Chemprop documentation: https://chemprop.readthedocs.io/
- MatGL documentation: https://matgl.ai/
- CHGNet GitHub: https://github.com/CederGroupHub/chgnet
- MACE foundation models documentation: https://mace-docs.readthedocs.io/en/latest/guide/foundation_models.html
- Materials Project API examples: https://docs.materialsproject.org/downloading-data/using-the-api/examples
- Matbench: https://github.com/materialsproject/matbench
- pymatgen analysis documentation: https://pymatgen.org/pymatgen.analysis.html
- pycalphad documentation: https://pycalphad.org/docs/latest/
- OpenMM: https://openmm.org/
- ASE: https://wiki.fysik.dtu.dk/ase/
- GROMACS manual: https://manual.gromacs.org/
- LAMMPS documentation: https://docs.lammps.org/
- RASPA3: https://github.com/iRASPA/RASPA3
- RXNMapper: https://github.com/rxn4chemistry/rxnmapper
- AiZynthFinder documentation: https://molecularai.github.io/aizynthfinder/
- Cantera documentation: https://cantera.org/documentation/
- RMG-Py documentation: https://reactionmechanismgenerator.github.io/RMG-Py/
- Open Reaction Database schema: https://github.com/open-reaction-database/ord-schema
