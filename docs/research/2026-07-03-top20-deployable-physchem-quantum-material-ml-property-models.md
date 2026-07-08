# 最推荐部署的物理化学、量子化学与材料化学端到端 ML 性质预测模型 TOP20

日期：2026-07-03

## 1. 筛选口径

本文件基于以下两份候选报告继续收敛部署优先级：

- `2026-06-30-end-to-end-property-ml-model-candidates.md`
- `2026-07-02-classical-ml-qsar-property-verifier-candidates.md`

本版按用户最新要求增加一个硬约束：当前仓库已经实现的 backend 家族一律排除在
TOP20 推荐部署清单之外。排除范围来自 `src/verifiers/*/backend.py` 和对应
property-level scripts，包括：

- RDKit descriptors 与 RDKit force-field workflows。
- xTB properties。
- ADMET-AI properties。
- SolTranNet 与 MolGpKa Docker-backed properties。
- MatGL properties/PES，包括通过 MatGL 交付的 MEGNet、M3GNet、CHGNet、
  TensorNet 具体模型。
- MACE-MP MLIP properties。
- TorchANI ANI-2x properties。
- OpenMM core fixture 与 OpenMM/OpenFF/GAFF ligand force-field workflows。

因此，本文件不是“当前 verifier 能力汇总”，而是“下一批值得独立部署验证的、
尚未由现有 backend 覆盖的端到端 ML/QSAR 性质预测模型”。对材料和量子模型，
如果训练标签主要来自 DFT、量子化学或计算轨迹，本文明确标注为“计算标签”；
它们可以作为 verifier surrogate，但不同于实验测量标签。

筛选条件：

1. 研究方向优先聚焦物理化学、量子化学、材料化学；环境物化 QSPR 只保留输入输出
   非常直接、可作为物化性质 verifier 的端点。
2. 候选必须绑定到具体端到端性质预测模型、具体 endpoint、具体 checkpoint 或明确
   可执行模型包，不把 Chemprop、DeepChem、SchNetPack、TorchMD-Net 这类框架本身
   直接列入 TOP20。
3. 输入应是 SMILES、SDF/XYZ、CIF/ASE Atoms、composition 或同类化学对象；输出应是
   可直接评分的性质值、概率、分类或固定向量。
4. 优先选择已有 Docker、CLI、pip/ASE calculator、预训练权重或商业批处理路径的候选。
5. 同一 backend 家族中如果已有当前仓库实现，则即使科学价值高也不再列入推荐表。

## 2. 本机部署与可用性验证记录

本轮重新测试了本机 Docker 和新增候选的部署状态：

- `docker version --format '{{.Server.Os}}/{{.Server.Arch}} {{.Server.Version}}'`
  返回 `linux/arm64 29.6.1`，本机 Docker 可用。
- `ghcr.io/quanted/cts-molgpka:dev-acafcb3fb93dbf8dcf6c952cbf3b12161e7f468d`
  的 Docker manifest 可查询，并已成功拉取到本机。镜像 digest 为
  `sha256:8b657f31d25017fe5aa7589e6137fc715299d7ea6f123175bb48f8319c669f40`。
- 该 MolGpKa 镜像是 `linux/amd64`，在当前 `linux/arm64` Docker Desktop 上通过
  emulation 可运行。容器内直接调用
  `CTSMolgpka().main("CC(O)=O")` 成功返回 `["CC(O)=O", 1, [8.34]]`。
- MolGpKa 默认 uWSGI 配置使用 `socket = :8080`，不是 HTTP socket；作为 verifier
  推荐走容器内 Python entrypoint 或重包一层 HTTP wrapper，而不是直接复用默认服务端口。
- `ersiliaos/eos2b6f:v1.0.0` manifest 检查本轮失败，原因为 Docker Hub DNS：
  `lookup registry-1.docker.io: no such host`。因此 pKaSolver-light 当前只标记为
  “项目提供 Docker 路径，需重试 Docker Hub/amd64 emulation smoke”。
- 旧版本机记录中，`ersiliaos/eos6oli:v1.0.0` 已完成 pull、serve、`/run` 预测 smoke：
  输入 `CCO` 和 `c1ccccc1` 分别返回 solubility `2.297180414199829` 和
  `-1.052748203277588`。
- 本轮用 `git ls-remote ... HEAD` 轻量确认了 SolTranNet、MolGpKa、SevenNet、
  Orb models、FAIR-Chem、MatterSim、MACE、TorchANI、AIMNet2、SchNetPack、
  TorchMD-Net 和 ALIGNN 等关键项目地址仍可访问。

2026-07-06 对 TOP20 表格新增一轮部署确认，口径如下：

- 本机直接部署：当前项目环境已经可直接 import/run，或在不改动项目 `.venv` 的前提下，
  `uv pip install --dry-run --target ...` 能解析出 macOS arm64/Python 3.12 安装计划。
  这类条目仍需单独做模型权重下载和推理 smoke 后才能进入正式 verifier。
- Docker Desktop 部署：本机 Docker Desktop 实际启动容器并完成预测 smoke，或至少能查询
  manifest/pull 已缓存镜像。实际预测 smoke 优先级高于 manifest 级确认。
- 当前未能确认部署：当前项目环境未安装，且本轮没有完成 Docker manifest/pull/run 或
  本机 dry-run 解析；可能原因包括 Docker Hub DNS、商业/Windows-only 软件、旧 Web/Java
  形态、权重许可或 PyG/torch-cluster 构建失败。

本轮新增确认结果：

- `eos6oli` 缓存 Docker 镜像可在 Docker Desktop 启动，并通过 `/run` 返回
  `CCO -> 2.297180414199829`、`c1ccccc1 -> -1.052748203277588`。
- MolGpKa GHCR 镜像可在 Docker Desktop 以 amd64 emulation 运行，容器内 Python 调用
  `CTSMolgpka().main("CC(O)=O")` 返回 `["CC(O)=O", 1, [8.34]]`。
- 当前项目 `.venv` 未安装 `torchani`、`alignn`、`mace`、`mattersim`、`sevenn`、
  `orb_models`、`fairchem`、`aimnet2` 等候选包；`torch`、`torch-geometric`、`ase`
  已存在。
- `torchani`、`alignn`、`mace-torch`、`mattersim`、`sevenn`、`orb-models`、
  `fairchem-core` 的 PyPI JSON 或 dry-run 解析成功，说明可优先走本机新环境或自建
  Dockerfile；尚未下载权重或跑通模型推理。
- AIMNet2 Git 安装 dry-run 在当前 macOS/Python 3.12 环境因 `torch-cluster==1.6.3`
  build dependency 失败，需专门 PyG/torch-cluster 环境或 Dockerfile。
- Docker Hub 仍然 DNS 失败，`ersiliaos/eos2b6f:v1.0.0` 和
  `ersiliaos/eos3wzy:v1.0.0` 未能完成 manifest 确认。
- EPA TEST、VEGA、EPI Suite 页面可访问，但本轮未下载或跑通 headless/batch；
  ALOGPS 页面本轮 SSL 读取失败。

## 3. 从上一版 TOP20 移除的重合项

上一版 TOP20 中以下条目因已实现 backend 重合，或因前期部署尝试已确认不适配
当前本机架构而移除：

| 移除条目 | 移除原因 |
|---|---|
| SolTranNet aqueous solubility (`eos6oli`) | 当前仓库已有 SolTranNet backend 与 property script |
| ADMET-AI `Solubility_AqSolDB` | 当前仓库已有 ADMET-AI backend 与多个 property scripts |
| OPERA WS model | 前期本机部署尝试已确认架构不适配，相关实验实现已移除 |
| OPERA LogP model | 前期本机部署尝试已确认架构不适配，相关实验实现已移除 |
| OPERA pKa / LogD models | 前期本机部署尝试已确认架构不适配，相关实验实现已移除 |
| MolGpKa GCN pKa model | 当前仓库已有 MolGpKa backend 与 property scripts |
| MEGNet formation energy via MatGL | 当前仓库已有 MatGL backend |
| M3GNet formation energy via MatGL | 当前仓库已有 MatGL backend |
| MatGL/MEGNet band gap | 当前仓库已有 MatGL backend |
| CHGNet-PES via MatGL | 当前仓库已有 MatGL backend |
| M3GNet-PES via MatGL | 当前仓库已有 MatGL backend |
| TensorNet MatPES via MatGL | 当前仓库已有 MatGL backend |
| MACE-MP foundation potential | 当前仓库已有 MACE-MP backend 与 property scripts |
| TorchANI ANI-2x | 当前仓库已有 TorchANI backend 与 property scripts |

RDKit、xTB 和 OpenMM/OpenFF 相关条目即使出现在候选池中，也按同一原则不进入本表。

## 4. 剩余推荐候选表

优先级含义：

- P0：最建议优先部署；已有本机 Docker smoke，或能以很小改造形成 verifier wrapper。
- P1：值得部署；有明确模型、权重或批处理路径，但需要一次专门环境 spike。
- P2：科学价值高，但当前本机/Docker 部署、许可证或模型冻结风险较高。

下表保留上一版原排名，仅列出当前仓库尚未实现 backend 的候选。

| 原排名 | 推荐部署模型 | 优先级 | 子领域 | 输入 | 预测性质 | 训练标签来源 | 项目/模型地址 | 部署与本机验证状态 | 本轮部署确认（2026-07-06） | 主要风险 |
|---:|---|---|---|---|---|---|---|---|---|---|
| 3 | pKaSolver-light (`eos2b6f`) | P1 | 小分子酸碱性质 | SMILES | Microstate pKa value and uncertainty | ChEMBL pretraining + 实验 pKa fine-tuning | [pKaSolver](https://github.com/mayrf/pkasolver), [Ersilia eos2b6f](https://github.com/ersilia-os/eos2b6f) | Ersilia model card 提供 Docker/local serving path；本轮 Docker Hub DNS 导致 manifest 未验证 | 当前未能确认部署：本机无可用包；Docker Hub DNS 仍失败，未完成 manifest/pull/run | README 标注 AMD64；monoprotic/light domain 限制；需固定输出 schema |
| 4 | Uni-pKa macro-pKa model | P1 | 小分子酸碱性质 | SMILES/protonation ensemble | Macro-pKa / protonation-state ranking | ChEMBL pretraining + Dwar-iBond pKa 数据 | [Uni-pKa](https://github.com/dptech-corp/Uni-pKa) | README 提供推荐 Docker 环境、数据和 inference workflow；需单独拉权重并跑 CLI smoke | 当前未能确认部署：GitHub 可访问，但当前项目环境未安装；需按 README 构建专用 Docker/conda 并拉权重 | Uni-Core 和旧版 cheminformatics 依赖；microstate enumeration policy 必须固定 |
| 5 | QupKake micro-pKa (`eos3wzy`) | P1/P2 | 小分子酸碱/量子辅助 ML | SMILES | Acidic/basic atom pKa-bin counts | 实验 pKa 数据 + semiempirical QM features | [QupKake](https://github.com/hutchisonlab/QupKake), [Ersilia eos3wzy](https://github.com/ersilia-os/eos3wzy) | Ersilia model card 提供 DockerHub/S3；当前 Docker Hub DNS 未验证 | 当前未能确认部署：本机无 PyPI 包；Docker Hub DNS 仍失败，未完成 `eos3wzy` manifest/pull/run | 输出不是单一 pKa，而是 22 维计数；评分函数需单独设计 |
| 6 | ALOGPS 2.1 logP/logS associative NN | P1/P2 | 小分子物理化学 | SMILES/MOL | logP, aqueous solubility logS | 实验 logP/logS 数据 | [ALOGPS 2.1](https://vcclab.org/lab/alogps/) | 经典早期 ML/QSPR 模型；需要确认可离线运行包或合法重实现路径 | 当前未能确认部署：本机无离线包；页面本轮 SSL 读取失败，未找到可直接 Docker 化工件 | 老 Java/Web 形态不利于 Docker；许可证和可再分发性需复核 |
| 7 | EPA TEST water-solubility/physchem QSAR endpoint | P1 | 小分子物理化学/环境化学 | SMILES/SDF | Water solubility and related physchem endpoints | EPA curated 实验数据 | [EPA TEST](https://www.epa.gov/comptox-tools/toxicity-estimation-software-tool-test) | 免费软件；需验证 Linux/headless batch 或容器化路径 | 当前未能确认部署：EPA 页面可访问且出现 batch/command 线索，但未下载或跑通 headless/Docker smoke | 现代版本 GUI/headless 能力需实测；训练集污染和 AD policy 要处理 |
| 8 | VEGA QSAR water-solubility/logP/KOC endpoint | P1 | 小分子物理化学/环境化学 | SMILES/SDF | WS, logP, KOC, Henry, BCF 等 | Curated 实验/QSAR-ready 数据 | [VEGA models](https://www.vegahub.eu/portfolio-types/in-silico-models/) | Java standalone/online 路径明确；需挑具体 model id 并做 batch smoke | 当前未能确认部署：VEGA 页面可访问，但未确认本机 headless/batch 或 Docker Desktop 部署 | 平台含多个模型，必须拆成单 endpoint；输出 reliability 字段需解析 |
| 9 | EPI Suite WSKOWWIN / WATERNT | P1 | 小分子物理化学/环境化学 | SMILES/structure | Water solubility | 实验水溶解度 + fragment/QSPR 模型 | [EPA EPI Suite](https://www.epa.gov/tsca-screening-tools/epi-suitetm-estimation-program-interface) | 传统 QSPR endpoint 清晰；适合用 Windows/Wine 或后续 Linux-compatible wrapper spike | 当前未能确认部署：页面可访问，但官方路径偏 Windows/Java；未完成 macOS 本机或 Docker/Wine smoke | 官方桌面以 Windows 为主；不能使用 CAS/name 查表模式作为 verifier |
| 10 | EPI Suite KOWWIN | P1 | 小分子物理化学/环境化学 | SMILES/structure | logKow / logP | 实验 partition coefficient + atom/fragment QSPR | [EPA EPI Suite](https://www.epa.gov/tsca-screening-tools/epi-suitetm-estimation-program-interface) | 经典 logKow 模型，适合和 SolTranNet/pKa 模型组成物化多目标任务 | 当前未能确认部署：同 EPI Suite，未完成 macOS 本机或 Docker/Wine smoke | 与基础 logP descriptor 目标相近，需说明这是独立 QSPR model |
| 11 | ALIGNN JARVIS band-gap model | P1 | 材料电子结构 | CIF/crystal graph | Band gap, eV | JARVIS/DFT 计算标签 | [ALIGNN](https://github.com/usnistgov/alignn) | 官方项目提供 pretrained model/scripts；适合独立 Dockerfile spike | 本机新环境可部署待 smoke：当前项目环境未安装；`alignn==2026.5.20` dry-run 可解析，但未下载 JARVIS 权重或推理 | 需要确认 ARM64 PyTorch/DGL/JARVIS 兼容；不是实验标签 |
| 12 | ALIGNN formation-energy model | P1 | 材料热力学 | CIF/crystal graph | Formation energy | JARVIS/DFT 计算标签 | [ALIGNN](https://github.com/usnistgov/alignn) | 与 ALIGNN band-gap 共用部署环境 | 本机新环境可部署待 smoke：与 ALIGNN band-gap 共用 dry-run 结果；未下载 formation-energy 权重或推理 | 与不同材料数据库标签体系存在偏差；score threshold 需单独校准 |
| 14 | MatterSim pretrained model | P1/P2 | 材料 MLIP | CIF/ASE Atoms | Energy, forces, stress, relaxation | 大规模 materials simulation/DFT-like 计算标签 | [MatterSim](https://github.com/microsoft/mattersim) | pip/source + ASE calculator 路线清晰；尚未本机安装 | 本机新环境可部署待 smoke：当前项目环境未安装；`mattersim==1.2.5` dry-run 可解析但依赖重，未跑权重下载/推理 | 新项目 API/weights 可能变化；需 Docker pin 和 CPU/GPU 成本评估 |
| 15 | SevenNet-0 universal potential | P1 | 材料 MLIP | CIF/ASE Atoms | Energy, forces, stress, relaxation | DFT trajectory/energy-force 计算标签 | [SevenNet](https://github.com/MDIL-SNU/SevenNet) | `sevenn` package + pretrained universal model + ASE/LAMMPS 路线明确 | 本机新环境可部署待 smoke：当前项目环境未安装；`sevenn==0.13.0` dry-run 可解析，未下载 SevenNet-0 权重 | checkpoint/domain 需固定；与 MACE/MatterSim 能量零点不可直接混用 |
| 16 | Orb pretrained atomistic model | P1 | 材料/分子 MLIP | ASE Atoms/CIF | Energy, forces, stress, relaxation | DFT-like 计算标签 | [Orb models](https://github.com/orbital-materials/orb-models) | 官方 pretrained models + ASE calculator 路线明确；适合做独立材料 surrogate | 本机新环境可部署待 smoke：当前项目环境未安装；`orb-models==0.7.0` dry-run 可解析，未下载模型权重 | 新项目，模型 id、下载授权和长期维护需跟踪 |
| 17 | FAIR-Chem UMA pretrained checkpoint | P1/P2 | 材料/催化/表面 MLIP | ASE Atoms/slab+adsorbate | Energy, forces, relaxation/adsorption proxy | OC/DFT multi-domain 计算标签 | [FAIR-Chem](https://github.com/facebookresearch/fairchem) | `fairchem-core` + UMA/Open Catalyst checkpoints 路线明确；适合催化扩展 | 本机新环境可部署待 smoke：当前项目环境未安装；`fairchem-core==2.21.0` dry-run 可解析，未确认 UMA 权重下载权限 | 权重许可、GPU 成本、task head 和 slab/site schema 必须固定 |
| 18 | GemNet-OC Open Catalyst checkpoint | P1/P2 | 催化/表面 MLIP | Slab+adsorbate structures | OC20 S2EF/IS2RE energy and forces | Open Catalyst/DFT 计算标签 | [FAIR-Chem](https://github.com/facebookresearch/fairchem) | 可通过 FAIR-Chem/OCP 环境加载固定 checkpoint | 本机新环境可部署待 smoke：依赖 `fairchem-core` dry-run 可解析；未下载 GemNet-OC checkpoint 或跑 OC 输入 | 输入 schema 复杂；不适合作为首批通用小分子/晶体性质 oracle |
| 20 | AIMNet2 default model | P2 | 分子量子化学/电荷性质 | XYZ/ASE Atoms with charge/spin | Energy, forces, charges, dipole-like properties | Quantum-chemistry 计算标签 | [AIMNet2](https://github.com/isayevlab/AIMNet2) | README 描述 default model 自动下载和 ASE calculator；科学价值高 | 当前未能确认部署：当前项目环境未安装；Git 安装 dry-run 因 `torch-cluster` build dependency 失败，未找到可直接 Docker 镜像 | 部署链复杂度高于 TorchANI；charge/spin/domain 和模型版本需先固定 |

## 5. 推荐部署批次

### 5.1 第一批：尚未实现 backend 中最值得立刻工程 spike 的候选

1. `pKaSolver-light/eos2b6f`：和 MolGpKa、Uni-pKa 形成 pKa endpoint 多模型对照；
   先解决 Docker Hub DNS/amd64 emulation 验证。
2. `Uni-pKa` / `QupKake/eos3wzy`：补齐不同 pKa 建模口径，优先固定输出 schema。
3. `ALIGNN band-gap + formation-energy`：一个环境可覆盖两个材料 property model，
   能补当前 MatGL 之外的材料图网络 oracle。
4. `ALOGPS` / `EPA TEST` / `VEGA` / `EPI Suite`：传统物化 QSPR 可补充独立模型口径，
   但需要先确认 headless/batch 与许可证。
5. `MatterSim` / `SevenNet-0` / `Orb models`：材料 MLIP 方向可作为 MACE-MP 之外的
   独立交叉验证候选。

### 5.2 第二批：部署价值高，但需要更完整环境验证

- 小分子 pKa：`Uni-pKa`、`QupKake/eos3wzy`。
- 传统/经典物化 QSPR：`ALOGPS`、`EPA TEST`、`VEGA`、`EPI Suite WSKOWWIN/KOWWIN`。
- 材料 MLIP：`SevenNet-0`、`MatterSim`、`Orb models`。
- 催化/表面：`FAIR-Chem UMA`、`GemNet-OC`。
- 分子量子与电荷：`AIMNet2`。

### 5.3 暂不推荐进入本版 TOP20 的候选类型

- 当前仓库已实现 backend 家族：RDKit、xTB、ADMET-AI、SolTranNet、MolGpKa、
  MatGL、MACE-MP、TorchANI、OpenMM/OpenFF/GAFF。
- 前期已移除的架构不适配尝试：OPERA。
- 框架本身：`Chemprop`、`DeepChem`、`TorchDrug`、`SchNetPack`、`TorchMD-Net`。
  它们只有在绑定具体 checkpoint、endpoint、featurizer 和 normalization 后才是
  verifier 模型。
- 纯 Web-only 工具：`SwissADME`、`pkCSM`、`admetSAR`、`ProTox-II` 等。
  它们可用于调研和人工对照，但不适合作为首批官方 Docker runtime oracle。
- 只计算描述符或规则、不含训练性质模型的工具，例如单纯 RDKit descriptors、
  Toxtree alert/profiler。它们可以做 domain gate 或辅助规则，但不是本表目标。

## 6. Docker/verifier 接入建议

建议按三类镜像策略推进：

1. 直接模型镜像：
   - `eos6oli` 与 `MolGpKa` 已有 backend；后续重点是固定正式 track/spec、镜像 digest、
     输出 schema 和生产 smoke，而不是作为新部署候选。
   - `eos2b6f`、`eos3wzy` 等 Ersilia pKa 镜像等 Docker Hub DNS 恢复后再做 pull/run smoke。
2. 独立 Python/ASE 镜像：
   - `TorchANI` 与 `MACE-MP` 已有 native backend；后续重点是正式 task design、模型版本和
     资源策略。`ALIGNN`、`SevenNet`、`Orb`、`MatterSim`、`FAIR-Chem` 仍需分别构建最小
     Dockerfile，预拉 checkpoint 并记录 hash。
   - 每个模型的 verifier script 必须固定输入结构生成、元素域、charge/spin、relaxation
     protocol 和 CPU/GPU 资源上限。
3. 传统 QSAR/QSPR 镜像：
   - `EPA TEST`、`VEGA`、`EPI Suite`、`ALOGPS` 先做 headless/batch smoke plan。
   - 只允许 SMILES/SDF 结构输入，不允许 CAS/name lookup 返回数据库已知值。
   - 输出解析时必须保留 applicability domain、confidence、nearest-neighbor 或 reliability 字段。

每个正式 verifier spec 至少记录：

- `model_id`：例如 `molgpka_gcn_v2024_ghcr_acafcb3`、`torchani_ani2x_v1`。
- `property_domain`：physchem、quantum、materials、environmental_physchem、catalysis。
- `input_format`：SMILES、SDF、XYZ、CIF、ASE Atoms。
- `output_name`、单位、方向和评分解释。
- 训练标签类型：experimental、DFT/computed、hybrid。
- Docker image digest 或 package/model cache hash。
- domain gate：元素、charge、heavy atom count、crystal size、supported species。

## 7. 关键来源

- SolTranNet GitHub: <https://github.com/gnina/SolTranNet>
- Ersilia `eos6oli` model card: <https://github.com/ersilia-os/eos6oli>
- MolGpKa GitHub: <https://github.com/Xundrug/MolGpKa>
- MolGpKa GHCR image namespace: <https://ghcr.io/quanted/cts-molgpka>
- pKaSolver GitHub: <https://github.com/mayrf/pkasolver>
- Ersilia `eos2b6f` model card: <https://github.com/ersilia-os/eos2b6f>
- Uni-pKa GitHub: <https://github.com/dptech-corp/Uni-pKa>
- QupKake GitHub: <https://github.com/hutchisonlab/QupKake>
- Ersilia `eos3wzy` model card: <https://github.com/ersilia-os/eos3wzy>
- ALOGPS 2.1: <https://vcclab.org/lab/alogps/>
- EPA TEST: <https://www.epa.gov/comptox-tools/toxicity-estimation-software-tool-test>
- VEGAHUB in silico models: <https://www.vegahub.eu/portfolio-types/in-silico-models/>
- EPA EPI Suite: <https://www.epa.gov/tsca-screening-tools/epi-suitetm-estimation-program-interface>
- ALIGNN GitHub: <https://github.com/usnistgov/alignn>
- MACE GitHub: <https://github.com/ACEsuit/mace>
- MatterSim GitHub: <https://github.com/microsoft/mattersim>
- SevenNet GitHub: <https://github.com/MDIL-SNU/SevenNet>
- Orb models GitHub: <https://github.com/orbital-materials/orb-models>
- FAIR-Chem GitHub: <https://github.com/facebookresearch/fairchem>
- TorchANI GitHub: <https://github.com/aiqm/torchani>
- AIMNet2 GitHub: <https://github.com/isayevlab/AIMNet2>
