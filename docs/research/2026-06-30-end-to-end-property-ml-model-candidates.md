# 端到端化学/材料性质预测 ML verifier 候选模型清单

日期：2026-06-30

## 1. 调研口径

本清单面向 `docs/design/INITIAL-DESIGN.md` 中的 verifier-grounded
open-generation benchmark。候选对象必须能被 verifier 在运行时重新解析、
规范化并输入固定模型或固定工作流做性质预测；不能只把公开数据库或数据集字段当作
正式性质 oracle。

本文件与既有研究文档的关系：

- `2026-05-26-verifier-grounded-chemical-benchmark-target-properties.md`
  已经定义了适合进入 benchmark 的性质类别。
- `2026-06-29-admet-opera-materials-verifier-deployment-report.md`
  深入分析了 ADMET-AI、OPERA、CHGNet/pymatgen 和 MatGL 的部署路径。
- `2026-06-30-verifier-backend-method-coverage-gap-report.md`
  按方法类别梳理了当前 backend 覆盖缺口。
- 本文件只补齐“模型级候选清单”：项目地址、部署要求、输入对象、可预测性质、
  可用性、成熟度证据、verifier 适配价值和风险，供后续筛选 50 个以上候选模型。

筛选标准：

1. 有明确项目地址、文档、README、package 或 release/checkpoint 入口。
2. 可以本地、容器或固定环境部署，或可通过官方包加载固定 checkpoint。
3. 预测内容是化学、药物、反应、量子化学、催化或材料性质/代理性质。
4. 在领域内有相对较高使用率，证据包括 GitHub stars、常见 benchmark、论文影响力、
   官方维护状态或已经被既有文档列为主流候选。
5. 适合作为 property-level verifier script 的后端；若只能作为候选生成器，则排除。

许可证和 stars 以 2026-06-30 GitHub API 或项目页可见信息为准；`未检测到 SPDX`
表示 GitHub API 没有返回规范 license id，后续进入 verifier image 前必须人工复核。

## 2. 总览

本轮整理 56 个唯一 ML/model-project 候选，另列 1 个非 ML 但高价值的辅助
domain gate 工作流，超过“至少 50 个”的目标。优先级含义：

- P0：下一批 verifier 最值得优先原型化或正式化。
- P1：可作为第二批或特定 track 的候选。
- P2：研究储备，适合离线校准、窄域任务或后续扩展。

| # | 候选模型/项目 | 优先级 | 对象与输入 | 可预测性质 | 部署要求/使用方法 | 可用性与成熟度证据 | Verifier 适配价值 | 主要风险 |
|---:|---|---|---|---|---|---|---|---|
| 1 | [ADMET-AI](https://github.com/swansonk14/admet_ai) | P0 | 小分子 SMILES | Solubility、hERG、AMES、DILI、BBB、Caco-2、CYP、clearance、toxicity 等 ADMET endpoint | `pip install admet-ai`；CLI `admet_predict` 或 Python `ADMETModel().predict()`；本仓库已 pin `admet-ai==2.0.1` | MIT；GitHub API 约 325 stars；官方说明使用 Chemprop v2 与 TDC ADMET 数据 | 最适合小分子 ADMET property-level verifier；低部署成本、多 endpoint | v1/v2 预测不一致；需要固定模型目录 hash、endpoint 单位和 applicability-domain policy |
| 2 | [OPERA](https://github.com/NIEHS/OPERA) | P0/P1 | 小分子 SMILES/SDF | WS、LogP、LogD、pKa、Caco-2、FuB、Clint、CATMoS、CERAPP、CoMPARA、环境 fate/toxicity | 官方 Windows/Linux command-line release；推荐 Linux verifier image 中固定 OPERA v2.9.2 与 MATLAB Runtime | MIT；约 85 stars；监管 QSAR 语境常用；官方包含 applicability domain | 适合作为保守 QSAR/环境毒理 verifier，与 ADMET-AI 互补 | 部署包重；macOS arm64 不适合原生实测；endpoint 命名和输出 CSV 需严格解析 |
| 3 | [SolTranNet](https://github.com/gnina/SolTranNet) | P0/P1 | 小分子 SMILES | Aqueous solubility / logS | 官方 Python/CLI 项目；固定 release 和模型权重后容器化 | Apache-2.0；约 41 stars；专门面向水溶解度预测 | 单 endpoint 清晰，适合 logS open-generation 任务交叉验证 ADMET-AI/OPERA | 只覆盖 solubility；训练集公开，需 novelty/AD gate |
| 4 | [Chemprop](https://github.com/chemprop/chemprop) | P0 | 小分子 SMILES 或 reaction/molecule graph | 任意训练好的分子性质：ADMET、solubility、toxicity、reaction/property regression/classification | `pip install chemprop` 或源码安装；CLI/Python train/predict；固定 checkpoint | 约 2397 stars；分子 D-MPNN/MPNN 性质预测事实标准之一；GitHub API 未检测到 SPDX | 可训练或加载固定 checkpoint，适合自有 ADMET/QSAR verifier | 需要自己冻结 checkpoint、训练数据、normalization 和 calibration |
| 5 | [DeepChem](https://github.com/deepchem/deepchem) | P1 | 小分子 SMILES/graph/fingerprint | MoleculeNet 类回归/分类、toxicity、solubility、QM、DTI 等 | `pip install deepchem`；使用 GraphConv、Weave、MPNN、AttentiveFP 等模型或固定模型包 | MIT；约 6819 stars；长期维护的化学深度学习工具箱 | 适合作为多 baseline 模型后端和离线校准框架 | 框架大于单模型；正式 verifier 必须指定架构、weights、featurizer 和 task |
| 6 | [DGL-LifeSci / AttentiveFP 等](https://github.com/awslabs/dgl-lifesci) | P1 | 小分子图 | ADMET、toxicity、solubility、MoleculeNet property | `pip install dgllife`；DGL + PyTorch；加载官方示例或固定 checkpoint | Apache-2.0；约 805 stars；常见图模型实现集合 | 可提供 AttentiveFP/MPNN/GAT 等 baseline verifier | 维护活跃度和 DGL 版本兼容要确认；需要自备 checkpoint |
| 7 | [GROVER](https://github.com/tencent-ailab/grover) | P1 | 小分子 SMILES/graph | MoleculeNet property、ADMET、bioactivity 等 fine-tuned endpoints | 源码安装；下载官方预训练模型并 fine-tune/predict | 约 389 stars；大规模自监督分子表示模型；GitHub API 未检测到 SPDX | 可作为 SMILES/graph 预训练模型 verifier 或 cross-check | 老项目依赖可能老化；正式运行需冻结预训练和 fine-tune checkpoint |
| 8 | [ChemBERTa](https://github.com/seyonechithrananda/bert-loves-chemistry) | P1 | 小分子 SMILES | MoleculeNet property、toxicity、solubility、classification/regression | Hugging Face/Transformers 或项目 notebooks；固定 model id 与 fine-tuned head | MIT；约 499 stars；SMILES transformer 代表模型 | 适合轻量 SMILES transformer baseline 或 sanity verifier | 对 3D/tautomer 不敏感；需要 fine-tuned head，不应只用 embedding |
| 9 | [MolCLR](https://github.com/yuyangw/MolCLR) | P1 | 小分子 graph | Molecular property prediction after contrastive pretraining | Conda/PyTorch Geometric 环境；下载预训练权重后 fine-tune/predict | MIT；约 321 stars；常见对比分子表示模型 | 可作为 fixed encoder + endpoint head 的 verifier 备选 | 需要 endpoint-specific head 和 calibration；依赖 PyG/CUDA 版本 |
| 10 | [Uni-Mol](https://github.com/deepmodeling/Uni-Mol) | P1 | 小分子 3D conformer、protein-ligand、材料扩展 | 分子性质、量子性质、binding pose/score proxy、ADMET fine-tune | 源码/conda 环境；加载官方预训练模型和下游 checkpoint | MIT；约 1120 stars；3D molecular representation 影响力高 | 适合 3D 分子性质与 binding proxy verifier，能补 RDKit 2D 局限 | 模型较重；输入 conformer 生成和随机性需固定 |
| 11 | [MoLFormer](https://github.com/IBM/molformer) | P1 | 小分子 SMILES | Molecular property prediction/fine-tuned endpoints | 官方代码、Hugging Face/Transformers 路径；固定 checkpoint | Apache-2.0；约 404 stars；大规模 SMILES foundation model | 可作为文本式 SMILES property verifier 或对照模型 | 需 endpoint head；SMILES 表示对立体/构象敏感度有限 |
| 12 | [TorchDrug](https://github.com/DeepGraphLearning/torchdrug) | P1 | 小分子图、protein、drug-target graph | Molecular property、DTI、link prediction、protein-ligand tasks | `pip install torchdrug` 或源码；固定 config/checkpoint | Apache-2.0；约 1584 stars；药物发现图学习框架 | 可承载多个 fixed model verifier，尤其 DTI 和 molecule property | 框架化程度高；正式任务需锁定 dataset split 和 weights |
| 13 | [Uni-pKa](https://github.com/dptech-corp/Uni-pKa) | P1 | 小分子 SMILES/结构 | 酸/碱 pKa | 官方仓库提供模型和使用流程；固定 checkpoint 后运行 | Apache-2.0；约 111 stars；专门 pKa 预测模型 | 适合 pKa/logD 相关 ADMET 任务补位 OPERA | pKa 定义、多中心离子化和 tautomer policy 必须固定 |
| 14 | [DeepPurpose](https://github.com/kexinhuang12345/DeepPurpose) | P1 | SMILES + protein sequence/target | Drug-target interaction、binding affinity、virtual screening、drug property | `pip install DeepPurpose` 或源码；支持 pretrained BindingDB 类模型 | BSD-3-Clause；约 1166 stars；常用 DTI 工具箱 | 适合窄 target family 的 potency/binding proxy verifier | Assay leakage 和 target/domain 外推风险高；需 novelty gate |
| 15 | [DeepDTA](https://github.com/hkmztrk/DeepDTA) | P1/P2 | SMILES + protein sequence | Binding affinity / DTI | Keras/TensorFlow 源码；固定 DAVIS/KIBA/BindingDB checkpoint | 约 301 stars；经典 DTA baseline；GitHub API 未检测到 SPDX | 可作为 target activity proxy baseline | 老依赖；训练集泄漏和 assay heterogeneity 明显 |
| 16 | [MolTrans](https://github.com/kexinhuang12345/MolTrans) | P1/P2 | SMILES + protein sequence | Drug-target interaction / affinity proxy | 源码安装；固定 pretrained/fine-tuned checkpoint | BSD-3-Clause；约 234 stars；DTI transformer baseline | 可用于特定 protein family DTI verifier | 需要严格 target set、negative sampling 和 calibration |
| 17 | [GraphDTA](https://github.com/thinng/GraphDTA) | P1/P2 | Molecular graph + protein sequence | Binding affinity | PyTorch Geometric 环境；固定 trained checkpoint | 约 302 stars；经典 graph-based DTA baseline；GitHub API 未检测到 SPDX | DTI verifier 备选，与 DeepDTA/MolTrans 形成模型多样性 | 旧依赖；跨 assay/target 外推风险 |
| 18 | [gnina](https://github.com/gnina/gnina) | P1 | Ligand 3D pose + receptor structure | CNN docking score、binding pose score、affinity proxy | Conda/Docker/source build；固定 receptor、box、CNN model 和 scoring mode | Apache-2.0；约 944 stars；docking 社区常用开源 CNN scoring | 适合固定受体/盒子的 binding proxy verifier | 输入准备复杂；dock score 不是实验 affinity；安全和 target leakage 需控制 |
| 19 | [DiffDock](https://github.com/gcorso/DiffDock) | P2 | Ligand + protein structure | Binding pose、confidence score；可作为 docking feasibility proxy | PyTorch/conda 环境；固定 weights；CPU 慢，推荐 GPU | MIT；约 1534 stars；高影响力 pose prediction 模型 | 适合后续 protein-ligand pose validity 或 docking prefilter | 不是直接 potency verifier；GPU 成本和 stochastic sampling 要固定 |
| 20 | [EquiBind](https://github.com/HannesStark/EquiBind) | P2 | Ligand + protein pocket | Binding pose proxy | PyTorch/Geometric 环境；固定 checkpoint | MIT；约 546 stars；早期快速 docking GNN | 可作为 fixed pose plausibility verifier 或 DiffDock 对照 | 科学性能不如新模型；pose 评分不等于 property satisfaction |
| 21 | [TorchANI](https://github.com/aiqm/torchani) | P1 | 小有机分子 XYZ/ASE Atoms | ANI-2x energy、forces、geometry relaxation proxy | `pip install torchani`；PyTorch；加载 ANI-1x/ANI-2x 模型 | MIT；约 548 stars；ANI 神经势常用实现 | 可验证小有机 3D 几何质量、energy/force sanity | 元素域有限；冷启动较重；能量跨分子解释需谨慎 |
| 22 | [SchNetPack](https://github.com/atomistic-machine-learning/schnetpack) | P1 | Molecule/material structures | QM9/MD17/Materials energy、forces、dipole、polarizability 等 | `pip install schnetpack`；PyTorch；固定 trained model | 约 933 stars；经典 continuous-filter convolution model toolkit；GitHub API 未检测到 SPDX | 适合量子性质 surrogate 和 MLIP baseline | 需要具体 checkpoint；训练数据/domain 必须写入 spec |
| 23 | [TorchMD-Net](https://github.com/torchmd/torchmd-net) | P1/P2 | Molecular geometries | Energy、forces、molecular property | PyTorch/Lightning；固定 checkpoint | MIT；约 478 stars；equivariant neural potential 常用实现 | 适合 3D 小分子 energy/force surrogate | 模型训练/加载链较重；需固定 conformer 和 charge/spin |
| 24 | [AIMNet2](https://github.com/isayevlab/AIMNet2) | P1 | Organic/inorganic molecular geometries | Energy、forces、charges、dipole/quantum-like properties | Python package/source；加载 AIMNet2 pretrained model | MIT；约 170 stars；通用分子 NN potential/charge model | 可补 xTB 的 charge/dipole/energy cross-check | 元素/charge domain 和模型版本需人工确认 |
| 25 | [PhysNet](https://github.com/MMunibas/PhysNet) | P2 | Molecule geometry | Energy、forces、dipole、partial charges | TensorFlow/Python 源码；固定 trained checkpoint | MIT；约 117 stars；经典 neural potential with electrostatics | 适合研究型 quantum surrogate verifier | 老依赖；需要自备 checkpoint 和 validation |
| 26 | [DeepMD-kit](https://github.com/deepmodeling/deepmd-kit) | P1/P2 | Atomistic structures | Energy、forces、virial/stress for molecules/materials | Conda/pip/source；固定 Deep Potential model；LAMMPS/ASE 可接入 | LGPL-3.0；约 1975 stars；MD/MLIP 社区高使用率 | 可作为材料/分子 MLIP backend，支持 MD/relaxation | 需要训练或下载特定势；跨化学空间不可泛化 |
| 27 | [MatGL](https://github.com/materialyzeai/matgl) | P0 | CIF/pymatgen Structure/composition | Formation energy、band gap、energy/forces/stress、relaxation、M3GNet/MEGNet/CHGNet 等 | `pip install matgl`；官方预训练模型名加载；本仓库 optional `matgl==4.0.2` | BSD-3-Clause；约 557 stars；官方 Materials Graph Library | 当前材料 P0 后端首选，能覆盖 formation energy/band gap/relaxation | checkpoint 名称、PES/Property 模型、元素域和 DGL/PyTorch 版本要冻结 |
| 28 | [CHGNet](https://github.com/CederGroupHub/chgnet) | P0/P1 | CIF/Structure | Energy、forces、stress、magnetic moments、relaxation | `pip install chgnet`；加载 pretrained CHGNet；可接 pymatgen/ASE | 约 389 stars；MP trajectory 预训练 universal potential；GitHub API 未检测到 SPDX | 材料 stability/relaxation verifier 强候选，也可经 MatGL 使用 | standalone 包长期路线需关注；energy-to-hull 需 reference entries |
| 29 | [MACE / MACE-MP](https://github.com/ACEsuit/mace) | P0/P1 | Atomistic structures/CIF/ASE Atoms | Energy、forces、stress、relaxation、MD proxy | `pip install mace-torch`；加载 MACE-MP/foundation checkpoint；ASE calculator | 约 1259 stars；MACE-MP foundation model 影响力高；GitHub API 未检测到 SPDX | 可做材料/表面 relaxation、energy、force verifier | 模型大；GPU/CPU 成本、head/checkpoint 和 dispersion 选项需固定 |
| 30 | [MatterSim](https://github.com/microsoft/mattersim) | P1 | Materials/molecule structures | Energy、forces、stress、relaxation | pip/conda/source；官方 MatterSim pretrained models；ASE calculator | MIT；约 570 stars；Microsoft 预训练 atomistic model | 可作为材料 MLIP cross-check 或第二材料后端 | 新模型，生态仍在变化；需校准 domain 和 version |
| 31 | [SevenNet](https://github.com/MDIL-SNU/SevenNet) | P1 | Atomistic structures | Energy、forces、stress、relaxation | `pip install sevenn`；加载 SevenNet pretrained model；ASE/LAMMPS 接入 | MIT；约 253 stars；equivariant MLIP，支持 universal model | 适合 materials MLIP 后端候选 | checkpoint/domain 需固定；与 CHGNet/MACE 输出不可直接混用 |
| 32 | [Orb models](https://github.com/orbital-materials/orb-models) | P1 | Atomistic structures | Energy、forces、stress、relaxation | pip package/source；官方 pretrained model；ASE calculator | Apache-2.0；约 601 stars；新近通用 atomistic foundation model | 可作为 high-throughput relaxation/energy verifier 备选 | 新项目，长期可维护性和 domain 要跟踪 |
| 33 | [FAIR-Chem / UMA](https://github.com/facebookresearch/fairchem) | P1 | Molecules/materials/catalysis structures | Energy、forces、adsorption/relaxation proxy across tasks | `fairchem-core` 环境；下载 UMA/OC checkpoints；ASE calculator | 约 2170 stars；Open Catalyst/FairChem 官方后续项目；GitHub API 未检测到 SPDX | 催化、吸附、材料跨域 verifier 候选 | 权重许可/下载、GPU 成本、task head 和 model id 必须固定 |
| 34 | [MEGNet](https://github.com/materialyzeai/megnet) | P1 | Crystal graph / molecule graph | Formation energy、band gap、elastic/dielectric-like trained properties | pip/source；加载官方或自训 MEGNet models | BSD-3-Clause；约 558 stars；材料图网络经典模型 | 适合 band gap/formation energy surrogate baseline | 老模型；需确认 TF/Keras 兼容和 checkpoint 可用性 |
| 35 | [M3GNet](https://github.com/materialyzeai/m3gnet) | P1 | Materials structures | Energy、forces、stress、relaxation、formation energy proxy | pip/source；加载 pretrained universal potential；也可经 MatGL 路线 | BSD-3-Clause；约 331 stars；universal materials potential 代表 | 可做 stability/relaxation verifier 或 MatGL 对照 | 旧 standalone 项目可能被 MatGL 替代；energy alignment 要校准 |
| 36 | [CGCNN](https://github.com/txie-93/cgcnn) | P1 | CIF/crystal graph | Formation energy、band gap、elastic/property regression | PyTorch 源码；按 dataset 训练/加载 checkpoint | MIT；约 878 stars；材料 ML 经典 baseline | 简单、可解释，适合材料 property baseline verifier | 没有通用官方 checkpoint；需自训和冻结数据 |
| 37 | [ALIGNN](https://github.com/usnistgov/alignn) | P1 | Crystal graph / atomistic graph | JARVIS/MP property：formation energy、band gap、elastic、phonon 等 | pip/source；官方 JARVIS pretrained models 与 scripts | 约 327 stars；NIST/JARVIS 生态；GitHub API 未检测到 SPDX | 可覆盖多种材料性质，尤其 JARVIS 对齐任务 | checkpoint/label 来源需和数据库查表区分；版本兼容需确认 |
| 38 | [MODNet](https://github.com/ppdebreuck/modnet) | P1/P2 | Composition/structure descriptors | Refractive index、elastic、formation energy 等 descriptor ML property | pip/source；使用 matminer descriptors 和 pretrained/examples | MIT；约 112 stars；materials descriptor network 常用 | 适合 composition/descriptor-only lightweight verifier | 可能更接近 surrogate/meta-model；需要明确训练集和 features |
| 39 | [CrabNet](https://github.com/anthony-wang/CrabNet) | P1/P2 | Composition formula | Formation energy、band gap、composition property | PyTorch 源码；固定 trained checkpoint | MIT；约 129 stars；composition-only transformer baseline | 可做 formula-only task 或材料候选初筛 | 不使用结构，容易奖励不可实现结构；需搭配 structure/stability gate |
| 40 | [Roost](https://github.com/CompRhys/roost) | P1/P2 | Composition formula | Materials composition property regression/classification | PyTorch 源码；固定 checkpoint | MIT；约 61 stars；composition graph baseline | 可作为低成本 composition verifier | 缺少结构信息；不适合作为唯一材料 oracle |
| 41 | [Matformer](https://github.com/YKQ98/Matformer) | P1/P2 | Crystal structures | Formation energy、band gap、materials property | 源码安装；固定 pretrained/fine-tuned checkpoint | MIT；约 112 stars；materials transformer model | 可作为 crystal graph property verifier 备选 | 项目维护和 checkpoint 可得性需复核 |
| 42 | [Graphormer](https://github.com/microsoft/Graphormer) | P1/P2 | Molecular graph | PCQM4M/quantum property、HOMO-LUMO gap style graph property | 源码/conda；固定 OGB-LSC checkpoint | MIT；约 2459 stars；图 transformer 经典模型 | 可作为 molecular quantum property surrogate baseline | 不是化学专用 verifier；需要 endpoint head 和 exact preprocessing |
| 43 | [AIRS / PotNet 等](https://github.com/divelab/AIRS) | P1/P2 | Materials structures/compositions | Materials property prediction benchmarks and models such as potential/structure models | 源码安装；按子项目加载 checkpoint/config | GPL-3.0；约 781 stars；DIVE Lab AI-for-science model suite | 可补材料 property 模型库，尤其结构/势场方向 | 套件复杂，具体模型需单独冻结；GPL 进入镜像需法务复核 |
| 44 | [MatDeepLearn](https://github.com/Fung-Lab/MatDeepLearn) | P1/P2 | Crystal structures / atomistic graphs | Materials property prediction with graph neural networks, including energy/band-gap-style supervised targets | 源码安装；按 config 训练或加载 fixed checkpoint | 约 205 stars；材料 GNN 框架；GitHub API 未检测到 SPDX | 可作为材料 property baseline 或自训 verifier 框架 | 需要自训/fixed checkpoint；license 和维护状态需人工复核 |
| 45 | [NequIP](https://github.com/mir-group/nequip) | P1 | Atomistic structures | Energy、forces、stress for trained chemical/material domain | pip/source；训练或加载 fixed equivariant potential；ASE/LAMMPS 接入 | MIT；约 933 stars；E(3)-equivariant MLIP 代表 | 适合窄域材料/分子 relaxation and force verifier | 没有通用性质 oracle；需要 domain-specific potential |
| 46 | [Allegro](https://github.com/mir-group/allegro) | P1/P2 | Atomistic structures | Energy、forces、stress for large-scale systems | 源码安装；固定 trained checkpoint；LAMMPS/ASE 相关接入 | MIT；约 490 stars；scalable equivariant MLIP | 适合大体系或材料 MD verifier 研究储备 | 需训练/下载具体模型；部署和 GPU 成本较高 |
| 47 | [NeuralForceField](https://github.com/learningmatter-mit/NeuralForceField) | P2 | Molecules/material structures | Energy、forces、MLIP, reaction/TS-related surrogates | PyTorch 源码；固定 trained model | MIT；约 292 stars；MIT learning-matter toolkit | 可用于 research-only quantum/force verifier | 生态不如 MACE/CHGNet 活跃；需自备模型 |
| 48 | [AI2BMD](https://github.com/microsoft/AI2BMD) | P2 | Biomolecular/atomistic systems | Energy/force proxy for biomolecular MD | 源码安装；固定 pretrained model and simulation protocol | MIT；约 576 stars；Microsoft biomolecular dynamics model | 可作为后续 peptide/protein fixture verifier | 不适合首版任意分子；输入和 MD protocol 成本高 |
| 49 | [GemNet-OC / Open Catalyst checkpoint suite](https://github.com/facebookresearch/fairchem) | P1 | Slab+adsorbate structures | OC20 S2EF/IS2RE energy and force, adsorption/relaxation proxy | FairChem/OCP environment；固定 GemNet-OC checkpoint | FairChem/OCP 生态约 2170 stars；Open Catalyst baseline 模型 | 催化 adsorption energy verifier 强候选 | OC20 domain 局限；slab/site/adsorbate schema 复杂 |
| 50 | [EquiformerV2](https://github.com/atomicarchitects/equiformer_v2) | P1 | Slab+adsorbate / OC structures | Energy、forces、adsorption/relaxation proxy | PyTorch/PyG environment；下载 OC20 checkpoint | MIT；约 345 stars；OC20/OC22 高性能 equivariant model | 催化和 surface verifier 备选 | 部署较重；GPU、checkpoint 和 preprocessing 需固定 |
| 51 | [RXNMapper](https://github.com/rxn4chemistry/rxnmapper) | P1 | Reaction SMILES | Atom mapping and mapping confidence | `pip install rxnmapper`；本地 transformer mapper | MIT；约 376 stars；反应 atom mapping 常用模型 | 可作为 reaction validity/reaction-center confidence verifier | 高 confidence 不等于真实可行；需搭配 mass balance/ORD schema |
| 52 | [rxn_yields / Yield-BERT](https://github.com/rxn4chemistry/rxn_yields) | P1/P2 | Reaction SMILES | Reaction yield regression | 源码安装；固定 Yield-BERT checkpoint and reaction family | MIT；约 139 stars；yield prediction 代表实现 | 适合固定反应家族 yield verifier | 通用 yield 噪声大；条件 schema 和训练泄漏风险 |
| 53 | [Chemformer](https://github.com/MolecularAI/Chemformer) | P1/P2 | SMILES/reaction SMILES | Reaction prediction、retrosynthesis、molecular optimization/property-conditioned tasks | Python/PyTorch Lightning；固定 pretrained/fine-tuned checkpoint | Apache-2.0；约 292 stars；AstraZeneca/MolecularAI transformer | 可用于 fixed reaction/product feasibility 或 molecular optimization proxy | 生成模型要避免自证；只用固定 predictor head/workflow |
| 54 | [Molecular Transformer](https://github.com/pschwllr/MolecularTransformer) | P1/P2 | Reaction SMILES | Forward reaction product prediction, reaction likelihood proxy | TensorFlow/legacy env；固定 pretrained model | 约 426 stars；经典 reaction prediction model；GitHub API 未检测到 SPDX | 可做 reaction plausibility or product-consistency verifier | 老依赖；输出概率和 beam score calibration 不稳定 |
| 55 | [AiZynthFinder](https://github.com/MolecularAI/aizynthfinder) | P1 | Target molecule SMILES | Retrosynthesis feasibility, solved flag, route score/depth | pip/conda; fixed stock file, expansion policy, filter policy | MIT；约 860 stars；常用开源 retrosynthesis planner | 很适合作为 molecule design synthesizability gate | 不是直接实验性质；结果强依赖 stock/policy/checkpoint |
| 56 | [ASKCOS core](https://github.com/ASKCOS/askcos-core) | P1/P2 | Target molecule/reaction | Retrosynthesis, reaction plausibility, condition/predictor modules depending deployment | Local ASKCOS service/core modules；fixed models/stocks | 约 25 stars for core repo；MIT group/ASKCOS 平台领域使用率高；GitHub API 未检测到 SPDX | 可作为重型 synthesis feasibility or reaction planning verifier | 部署复杂；需要固定服务版本、models、stock 和 network-off mode |
| 辅助 | [RDKit ETKDG + MMFF/UFF force-field workflow](https://www.rdkit.org/docs/source/rdkit.Chem.rdForceFieldHelpers.html) | P0 auxiliary | 小分子 SMILES 或 submitted conformer | 3D embedding success、MMFF/UFF parameter coverage、minimized energy、strain/clash proxy | 本仓库已有 RDKit；固定 seed、numConfs、MMFF variant and maxIters | RDKit 是已采用基础依赖；非 ML，但与 ML verifier 组合价值高 | 作为 ADMET/ML property tasks 的低成本 geometry/domain gate | 不计入 50 个 ML 模型；MMFF energy 不适合作跨分子绝对性质目标 |

## 3. 适配排序建议

### 3.1 下一批 P0/P1 原型化建议

1. 小分子 ADMET：优先 `ADMET-AI`，并以 `SolTranNet` 和 `OPERA WS`
   做 logS 交叉验证候选。
2. 小分子通用 QSAR：用 `Chemprop` 固定 1-2 个自训或公开 checkpoint，
   作为 endpoint-specific verifier，而不是把整个框架注册成一个 verifier。
3. 材料 property：以 `MatGL` 为主，`CHGNet`、`MACE-MP`、`MatterSim`
   做 energy/relaxation cross-check；尽快定义 energy-above-hull 的 reference
   entry 冻结策略。
4. 催化/表面：`FAIR-Chem/UMA`、`GemNet-OC`、`EquiformerV2`
   只在固定 slab、固定 adsorbate、固定 site 构建协议下试点。
5. 反应/合成：先接 `RXNMapper` 做 low-cost validity/confidence gate；
   `AiZynthFinder` 做 target molecule synthesizability gate；yield prediction
   只限固定 reaction family。

### 3.2 不建议直接作为首版唯一 oracle 的候选

- 纯 foundation encoder，例如 ChemBERTa、MoLFormer、MolCLR、GROVER：
  必须配合固定 fine-tuned head 才能作为性质 verifier。
- DTI/binding 模型，例如 DeepPurpose、DeepDTA、MolTrans、GraphDTA：
  需要窄 target family、训练集去重、assay 清洗和 novelty gate。
- Docking/pose 模型，例如 DiffDock、EquiBind：
  只能作为 pose plausibility 或 binding workflow 的子模块，不应把 pose
  confidence 直接解释成实验 potency。
- Composition-only 材料模型，例如 CrabNet、Roost：
  适合初筛或 composition-only task，但 open-generation 材料题仍需要结构、
  密度、稳定性和重复性 gate。
- 通用 MLIP，例如 NequIP、Allegro、DeepMD-kit：
  需要为特定化学空间训练/选择势函数，不能把框架本身当成 universal oracle。

## 4. 元数据字段模板

后续如果把本清单转为机器可读 registry，建议每个候选至少保留以下字段：

```yaml
model_id: admet_ai_v2
name: ADMET-AI
project_url: https://github.com/swansonk14/admet_ai
object_type: small_molecule
input_formats: [smiles]
predicted_properties:
  - Solubility_AqSolDB
  - hERG
  - AMES
  - DILI
deployment:
  package: admet-ai==2.0.1
  entrypoints:
    cli: admet_predict
    python: admet_ai.ADMETModel
  checkpoint_policy: freeze package-managed model directory and hash it
availability:
  license: MIT
  maturity_evidence:
    - GitHub stars: 325 on 2026-06-30
    - documented CLI and Python API
verifier_fit:
  value: low-cost multi-endpoint ADMET verifier
  risks:
    - v1/v2 model differences
    - endpoint calibration and applicability domain
```

## 5. 参考链接

- ADMET-AI: https://github.com/swansonk14/admet_ai
- OPERA: https://github.com/NIEHS/OPERA
- SolTranNet: https://github.com/gnina/SolTranNet
- Chemprop: https://github.com/chemprop/chemprop
- DeepChem: https://github.com/deepchem/deepchem
- DGL-LifeSci: https://github.com/awslabs/dgl-lifesci
- GROVER: https://github.com/tencent-ailab/grover
- ChemBERTa: https://github.com/seyonechithrananda/bert-loves-chemistry
- MolCLR: https://github.com/yuyangw/MolCLR
- Uni-Mol: https://github.com/deepmodeling/Uni-Mol
- MoLFormer: https://github.com/IBM/molformer
- TorchDrug: https://github.com/DeepGraphLearning/torchdrug
- Uni-pKa: https://github.com/dptech-corp/Uni-pKa
- DeepPurpose: https://github.com/kexinhuang12345/DeepPurpose
- DeepDTA: https://github.com/hkmztrk/DeepDTA
- MolTrans: https://github.com/kexinhuang12345/MolTrans
- GraphDTA: https://github.com/thinng/GraphDTA
- gnina: https://github.com/gnina/gnina
- DiffDock: https://github.com/gcorso/DiffDock
- EquiBind: https://github.com/HannesStark/EquiBind
- TorchANI: https://github.com/aiqm/torchani
- SchNetPack: https://github.com/atomistic-machine-learning/schnetpack
- TorchMD-Net: https://github.com/torchmd/torchmd-net
- AIMNet2: https://github.com/isayevlab/AIMNet2
- PhysNet: https://github.com/MMunibas/PhysNet
- DeepMD-kit: https://github.com/deepmodeling/deepmd-kit
- MatGL: https://github.com/materialyzeai/matgl
- CHGNet: https://github.com/CederGroupHub/chgnet
- MACE: https://github.com/ACEsuit/mace
- MatterSim: https://github.com/microsoft/mattersim
- SevenNet: https://github.com/MDIL-SNU/SevenNet
- Orb models: https://github.com/orbital-materials/orb-models
- FAIR-Chem: https://github.com/facebookresearch/fairchem
- MEGNet: https://github.com/materialyzeai/megnet
- M3GNet: https://github.com/materialyzeai/m3gnet
- CGCNN: https://github.com/txie-93/cgcnn
- ALIGNN: https://github.com/usnistgov/alignn
- MODNet: https://github.com/ppdebreuck/modnet
- CrabNet: https://github.com/anthony-wang/CrabNet
- Roost: https://github.com/CompRhys/roost
- Matformer: https://github.com/YKQ98/Matformer
- Graphormer: https://github.com/microsoft/Graphormer
- AIRS: https://github.com/divelab/AIRS
- MatDeepLearn: https://github.com/Fung-Lab/MatDeepLearn
- NequIP: https://github.com/mir-group/nequip
- Allegro: https://github.com/mir-group/allegro
- NeuralForceField: https://github.com/learningmatter-mit/NeuralForceField
- AI2BMD: https://github.com/microsoft/AI2BMD
- EquiformerV2: https://github.com/atomicarchitects/equiformer_v2
- RXNMapper: https://github.com/rxn4chemistry/rxnmapper
- rxn_yields: https://github.com/rxn4chemistry/rxn_yields
- Chemformer: https://github.com/MolecularAI/Chemformer
- Molecular Transformer: https://github.com/pschwllr/MolecularTransformer
- AiZynthFinder: https://github.com/MolecularAI/aizynthfinder
- ASKCOS core: https://github.com/ASKCOS/askcos-core
- RDKit force-field helpers: https://www.rdkit.org/docs/source/rdkit.Chem.rdForceFieldHelpers.html

## 6. 按预测性质所属化学子领域分类

本节按“候选模型主要预测的性质属于哪个化学子领域”重新组织候选。一个模型如果同时
覆盖多个性质类型，会出现在多个子领域中；正式 registry 后续可以用
`property_domain`、`property_family` 和 `endpoint_id` 做多标签索引。

| 化学子领域 | 主要候选 | 预测性质或 endpoint | Verifier 使用重点 |
|---|---|---|---|
| 小分子 ADMET、药物样性质与通用 QSAR | `ADMET-AI`、`OPERA`、`SolTranNet`、`Chemprop`、`DeepChem`、`DGL-LifeSci`、`GROVER`、`ChemBERTa`、`MolCLR`、`Uni-Mol`、`MoLFormer`、`TorchDrug`、`Uni-pKa` | Solubility/logS、hERG、AMES、DILI、BBB、Caco-2、CYP、clearance、toxicity、pKa、MoleculeNet-style property | 最适合补齐 RDKit 基础描述符之外的固定小分子性质预测；进入 verifier 时必须绑定具体 endpoint、checkpoint、featurizer、单位和 applicability-domain policy。 |
| 靶点活性、药物-靶标相互作用与蛋白-配体结合 | `DeepPurpose`、`DeepDTA`、`MolTrans`、`GraphDTA`、`gnina`、`DiffDock`、`EquiBind`、`TorchDrug`、`Uni-Mol` | DTI、binding affinity/proxy、docking score、pose confidence、protein-ligand pose plausibility | 适合窄 target family 或固定 receptor/box 的 binding proxy 任务；不应把 docking confidence 或跨 assay affinity 直接当作通用 potency oracle。 |
| 分子量子化学、构象质量与神经势能 | `TorchANI`、`SchNetPack`、`TorchMD-Net`、`AIMNet2`、`PhysNet`、`DeepMD-kit`、`Graphormer`、`Uni-Mol`、`RDKit ETKDG + MMFF/UFF force-field workflow` | Energy、forces、dipole、polarizability、partial charges、HOMO-LUMO-gap-style graph property、3D embedding/strain/clash proxy | 可作为 xTB 的低成本 surrogate 或前置 geometry/domain gate；必须固定构象生成、charge/spin、元素域和跨分子能量解释规则。 |
| 无机材料、晶体结构与 composition property | `MatGL`、`CHGNet`、`MACE/MACE-MP`、`MatterSim`、`SevenNet`、`Orb models`、`MEGNet`、`M3GNet`、`CGCNN`、`ALIGNN`、`MODNet`、`CrabNet`、`Roost`、`Matformer`、`AIRS/PotNet`、`MatDeepLearn`、`DeepMD-kit`、`NequIP`、`Allegro`、`NeuralForceField`、`SchNetPack` | Formation energy、band gap、energy above hull proxy、energy/forces/stress、magnetic moments、elastic/refractive/dielectric-like property、composition-only materials property | 是材料 track 的主体候选；structure-based 模型适合作为 stability/band-gap verifier，composition-only 模型只能作初筛或 formula-only 任务，不能单独证明结构可实现。 |
| 催化、表面吸附与开放催化模型 | `FAIR-Chem/UMA`、`GemNet-OC/Open Catalyst checkpoint suite`、`EquiformerV2`、`MACE/MACE-MP`、`Orb models` | Slab+adsorbate energy、forces、adsorption/relaxation proxy、OC20/OC22 S2EF/IS2RE-style outputs | 适合后续催化或 adsorption-energy 任务；必须固定 slab、adsorbate、site 构建规则、checkpoint 和 relaxation protocol。 |
| 反应、合成可行性与 retrosynthesis | `RXNMapper`、`rxn_yields/Yield-BERT`、`Chemformer`、`Molecular Transformer`、`AiZynthFinder`、`ASKCOS core` | Atom mapping confidence、reaction yield、forward reaction/product plausibility、retrosynthesis solved flag、route score/depth | 适合作为 reaction validity、yield surrogate 或 synthesizability gate；生成模型只能作固定 predictor/workflow，不能让模型生成后自证。 |
| 生物大分子与 biomolecular dynamics 储备 | `AI2BMD`、`TorchDrug`、`DeepPurpose` | Biomolecular energy/force proxy、protein/drug graph tasks、protein-sequence-conditioned prediction | 当前更适合后续 peptide/protein fixture 或 DTI 任务储备；首版小分子 verifier 不宜直接扩展到大体系 MD。 |
| 框架型或多领域模型库 | `Chemprop`、`DeepChem`、`TorchDrug`、`SchNetPack`、`DeepMD-kit`、`AIRS`、`MatDeepLearn` | 取决于具体 checkpoint/config：ADMET、toxicity、quantum property、materials property、MLIP 等 | 不能把框架本身注册为 oracle；必须拆成具体模型工件和 property-level verifier script。 |

优先落地顺序仍建议保持为：小分子 ADMET/QSAR、材料 formation-energy/band-gap/stability、
低成本量子/geometry gate、反应/合成 gate、催化/表面吸附。这个顺序与当前
`INITIAL-DESIGN.md` 的 P0/P1 性质优先级一致，且能最大化复用已有 RDKit、xTB、
ADMET-AI、OPERA、MatGL/CHGNet/MACE 相关 backend 经验。
