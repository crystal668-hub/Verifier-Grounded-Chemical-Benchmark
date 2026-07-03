# 最推荐部署的物理化学、量子化学与材料化学端到端 ML 性质预测模型 TOP20

日期：2026-07-03

## 1. 筛选口径

本文件基于以下两份候选报告继续收敛部署优先级：

- `2026-06-30-end-to-end-property-ml-model-candidates.md`
- `2026-07-02-classical-ml-qsar-property-verifier-candidates.md`

筛选条件比前两份报告更严格：

1. 研究方向优先聚焦物理化学、量子化学、材料化学。ADMET/毒理模型只保留与
   solubility、pKa、logD、permeability、binding-free-energy-like 或其他物化性质紧密相关的候选。
2. 候选必须是“具体端到端性质预测模型”或具体 checkpoint/endpoint，而不是部署框架、
   训练框架、描述符计算器或从头计算工具。
3. 输入应是 SMILES、SDF/XYZ、CIF/pymatgen Structure、composition 或同类化学对象；
   输出应是可直接评分的性质值、概率或固定向量。
4. 优先选择已有本地部署路径、pip/CLI/API、Docker 镜像或预训练权重的候选。
5. 对材料模型，如果训练标签主要来自 Materials Project、JARVIS、AFLOW 等 DFT 数据，
   本文明确标注为“DFT/计算标签”。它们仍可作为 verifier surrogate，但不同于实验测量标签。

本轮也做了本机可用性 smoke：

- `docker version` 成功，Docker Desktop 后端为 `linux/arm64`。
- `docker run --rm hello-world` 成功，确认 Docker pull/run 路径可用。
- `ersiliaos/eos6oli:v1.0.0` 成功拉取并启动，镜像为 `linux/arm64`。
- `eos6oli` HTTP 服务 `/run` 成功预测 `CCO` 和 benzene 的 aqueous solubility：
  `CCO -> 2.297180414199829`，`c1ccccc1 -> -1.052748203277588`。
- 本项目环境中 `matgl==4.0.2` 可加载并运行 `MEGNet-Eform-MP-2018.6.1`，对 CsCl
  返回 formation energy `-1.9240572452545166 eV/atom`。
- `MEGNet-BandGap-mfi-MP-2019.4.1` 在当前 `matgl==4.0.2` 下触发旧模型兼容/张量形状错误；
  因此 band gap 模型虽科学价值高，但部署优先级需低于已实测通过的模型。

## 2. TOP20 总表

优先级含义：

- P0：最建议优先部署；已有本机 Docker 或 Python smoke，或工程路径非常清晰。
- P1：值得部署；有明确模型和权重，但需要一次专门环境 spike。
- P2：科学价值高，但当前本机/Docker 部署风险或许可证风险较高。

| 排名 | 推荐部署模型 | 优先级 | 子领域 | 输入 | 预测性质 | 训练标签来源 | 项目/模型地址 | 部署与本机验证状态 | 主要风险 |
|---:|---|---|---|---|---|---|---|---|---|
| 1 | SolTranNet aqueous solubility (`eos6oli`) | P0 | 小分子物理化学 | SMILES | Aqueous solubility / logS | AqSolDB 实验溶解度 | [SolTranNet](https://github.com/gnina/SolTranNet), [Ersilia eos6oli](https://github.com/ersilia-os/eos6oli) | Docker `ersiliaos/eos6oli:v1.0.0` 已在本机 `linux/arm64` 拉取、启动并完成 `/run` 预测；输入列 `smiles`，输出 `solubility` | 需要固定 Docker digest、Ersilia API schema、logS 单位和 applicability-domain policy |
| 2 | ADMET-AI `Solubility_AqSolDB` | P0 | 小分子物理化学/ADMET | SMILES | Aqueous solubility, log(mol/L) | TDC/AqSolDB 实验标签 | [ADMET-AI](https://github.com/swansonk14/admet_ai) | 本项目已 pin `admet-ai==2.0.1`；`ADMETModel` 可本机加载；可用 Python 或 CLI 包装成 Docker verifier | v1/v2 模型不一致；需固定 Chemprop v2 模型目录 hash 和 endpoint 元数据 |
| 3 | OPERA WS model | P0/P1 | 小分子物理化学/环境化学 | SMILES/SDF | Water solubility | QSAR-ready curated experimental datasets | [OPERA](https://github.com/NIEHS/OPERA) | 官方 Linux command-line release 明确；当前 macOS arm64 不能原生跑，需 Linux Docker spike | 包体约 GiB 级且依赖 MATLAB Runtime；需确认 batch/headless 输出列 |
| 4 | OPERA LogP model | P1 | 小分子物理化学 | SMILES/SDF | Octanol/water partition coefficient LogP | Curated experimental logP | [OPERA](https://github.com/NIEHS/OPERA) | 同 OPERA WS；适合作为 RDKit Crippen 和 EPI KOWWIN 的 ML/QSAR 交叉模型 | 与 RDKit 基础描述符重叠，正式任务需说明为何使用 ML/QSAR oracle |
| 5 | OPERA pKa / LogD models | P1 | 小分子酸碱/分配性质 | SMILES/SDF | pKa, LogD | Curated experimental ionization/partition data | [OPERA](https://github.com/NIEHS/OPERA) | 同 OPERA WS；对 drug-like pH-dependent property task 价值高 | 多中心离子化、tautomer 和 pH policy 必须固定 |
| 6 | pKaSolver-light (`eos2b6f`) | P1 | 小分子酸碱性质 | SMILES | Microstate pKa value and uncertainty | ChEMBL pretraining + experimental pKa fine-tuning set | [pKaSolver](https://github.com/mayrf/pkasolver), [Ersilia eos2b6f](https://github.com/ersilia-os/eos2b6f) | Ersilia model card 提供 DockerHub/S3 和 local serving path；README 标注 Docker architecture 为 AMD64，本机 ARM64 需 emulation | GPL-3.0 wrapper + MIT model；monoprotic/light model domain 限制 |
| 7 | Uni-pKa macro-pKa model | P1 | 小分子酸碱性质 | SMILES/protonation ensemble | Macro-pKa / protonation-state ranking | ChEMBL pretraining + Dwar-iBond pKa 数据 | [Uni-pKa](https://github.com/dptech-corp/Uni-pKa) | README 给出推荐 Docker 环境、数据和 inference workflow；需要单独拉取权重和验证 CLI | Uni-Core/RDKit 旧版本依赖；workflow 包含 microstate enumeration，wrapper 需严格固定模式 |
| 8 | QupKake micro-pKa (`eos3wzy`) | P1/P2 | 小分子酸碱/量子辅助 ML | SMILES | Micro-pKa binned acidic/basic atom counts | pKa 数据 + semiempirical QM features | [QupKake](https://github.com/hutchisonlab/QupKake), [Ersilia eos3wzy](https://github.com/ersilia-os/eos3wzy) | Ersilia model card 提供 DockerHub/S3；README 标注 AMD64，当前 ARM64 需 emulation | 输出是 22 维计数，不是单一 pKa；推理较慢，需定义 scoring |
| 9 | MEGNet formation energy (`MEGNet-Eform-MP-2018.6.1`) | P0 | 材料化学 | CIF/pymatgen Structure | Formation energy, eV/atom | Materials Project DFT 标签 | [MatGL](https://github.com/materialsvirtuallab/matgl) | `matgl==4.0.2` 已在本机加载该具体模型并对 CsCl 完成预测 | 旧模型版本兼容 warning；需固定 Hugging Face/model cache 和 MatGL 版本 |
| 10 | M3GNet formation energy (`M3GNet-Eform-MP-2018.6.1`) | P0/P1 | 材料化学 | CIF/pymatgen Structure | Formation energy, eV/atom | Materials Project DFT 标签 | [MatGL](https://github.com/materialsvirtuallab/matgl) | `matgl.get_available_pretrained_models()` 本机可见该模型；与 MEGNet 同容器即可验证 | 仍需单独 smoke；输出与 MEGNet 可能有系统偏差 |
| 11 | MatGL/MEGNet band gap (`MEGNet-BandGap-mfi-MP-2019.4.1`) | P1 | 材料电子结构 | CIF/pymatgen Structure | Band gap, eV | Materials Project multi-fidelity DFT 标签 | [MatGL](https://github.com/materialsvirtuallab/matgl) | 模型可列出和加载，但当前 `matgl==4.0.2` smoke 在 Si 上触发张量形状错误；需要版本锁定或旧环境容器 | 不能直接进入 P0；必须先找到兼容 MatGL/model 组合 |
| 12 | CHGNet-PES MatPES PBE (`CHGNet-PES-MatPES-PBE-2025.2.10`) | P1 | 材料 MLIP/稳定性 proxy | CIF/pymatgen Structure | Energy, forces, stress, magnetic moments / relaxation proxy | MatPES/DFT trajectory labels | [MatGL CHGNet model](https://github.com/materialsvirtuallab/matgl) | 本机 MatGL 可列出该具体模型；适合与 pymatgen hull workflow 组合 | 是 PES 而非直接实验性质；E-hull 还需固定 reference entries |
| 13 | M3GNet universal potential (`M3GNet-PES-MatPES-PBE-2025.2`) | P1 | 材料 MLIP/稳定性 proxy | CIF/ASE Atoms | Energy, forces, stress, relaxation | MatPES/DFT trajectory labels | [MatGL](https://github.com/materialsvirtuallab/matgl) | 本机 MatGL 可列出该模型；同一 Docker image 可统一部署 MatGL models | 预测的是 surrogate energy/force；跨模型能量零点和 relaxation protocol 要固定 |
| 14 | TensorNet MatPES PBE (`TensorNet-PES-MatPES-PBE-2025.2`) | P1 | 材料 MLIP/稳定性 proxy | CIF/ASE Atoms | Energy, forces, stress, relaxation | MatPES/DFT trajectory labels | [MatGL](https://github.com/materialsvirtuallab/matgl) | 本机 MatGL 可列出；MatGL README 指出新权重在 Hugging Face `materialyze` org | 可能需要较新 MatGL/JAX/Warp optional path；CPU 成本需评估 |
| 15 | ALIGNN JARVIS band-gap model | P1 | 材料电子结构 | CIF/crystal graph | Band gap | JARVIS/DFT labels | [ALIGNN](https://github.com/usnistgov/alignn) | 官方项目提供 pretrained model/scripts；需要单独 Dockerfile spike | 不是当前项目依赖；需要确认 ARM64 PyTorch/DGL/JARVIS 兼容 |
| 16 | ALIGNN formation-energy model | P1 | 材料热力学 | CIF/crystal graph | Formation energy | JARVIS/DFT labels | [ALIGNN](https://github.com/usnistgov/alignn) | 与 ALIGNN band-gap 共用部署环境 | 与 MP/MatGL 标签体系不同；score threshold 需单独校准 |
| 17 | MACE-MP foundation potential | P1 | 材料/表面 MLIP | CIF/ASE Atoms | Energy, forces, stress, relaxation proxy | MP/DFT-like training corpus depending checkpoint | [MACE](https://github.com/ACEsuit/mace) | `mace-torch` pip/ASE route 清晰；适合独立 Docker spike | 模型较大，CPU 速度和 checkpoint license 需确认 |
| 18 | MatterSim pretrained model | P1/P2 | 材料 MLIP | CIF/ASE Atoms | Energy, forces, stress, relaxation | Large materials simulation/DFT-like corpus | [MatterSim](https://github.com/microsoft/mattersim) | pip/source 路线清晰，ASE calculator；尚未本机安装 | 新项目，API/weights 可能变化；需 Docker pin |
| 19 | TorchANI ANI-2x | P1 | 分子量子化学/有机分子势能 | XYZ/ASE Atoms | Molecular energy and forces | ANI quantum-chemistry labels | [TorchANI](https://github.com/aiqm/torchani) | `pip install torchani`；内置/可下载 ANI-1x/ANI-2x/ANI-1ccx 参数；适合轻量 Docker spike | 元素域有限，不覆盖任意药物/材料；标签是量化计算不是实验 |
| 20 | AIMNet2 default model | P2 | 分子量子化学/电荷性质 | XYZ/ASE Atoms with charge/spin | Energy, forces, charges, stress/Hessian optional | Quantum-chemistry training labels | [AIMNet2](https://github.com/isayevlab/AIMNet2) | 科学价值高，README 描述 default model 自动下载和 ASE calculator | 当前 README 仍显示手工 conda/private repo 痕迹；部署复杂度高于 TorchANI/MatGL |

## 3. 推荐部署批次

### 3.1 第一批：立刻值得工程化的 5 个模型

1. `SolTranNet/eos6oli`：已经完成 Docker ARM64 pull、serve、predict smoke，是最直接的
   “输入 SMILES -> 输出 logS” verifier。
2. `ADMET-AI Solubility_AqSolDB`：项目环境已经可加载 ADMET-AI；与 SolTranNet 构成两个
   独立 logS 模型，可用于 consensus 或交叉验证。
3. `MEGNet-Eform-MP-2018.6.1`：本机 MatGL 已完成 formation energy 预测；材料方向最接近
   可落地 property verifier。
4. `M3GNet-Eform-MP-2018.6.1`：同 MatGL 部署栈，优先做第二个 formation-energy
   surrogate 以检查模型间稳定性。
5. `OPERA WS`：虽然当前 Mac ARM64 不能原生跑，但 Linux command-line release 和 wrapper
   设计已清楚；值得用 Docker/Linux 做专门 spike。

### 3.2 第二批：需要环境 spike 但价值高

- pKa：`pKaSolver-light/eos2b6f`、`Uni-pKa`、`QupKake/eos3wzy`。
- 材料 band gap：`MEGNet-BandGap-mfi-MP-2019.4.1`、`ALIGNN JARVIS band-gap`。
- 材料 MLIP/stability proxy：`CHGNet-PES-MatPES-PBE`、`M3GNet-PES-MatPES-PBE`、
  `TensorNet-PES-MatPES-PBE`、`MACE-MP`。
- 分子量子 surrogate：`TorchANI ANI-2x`。

### 3.3 暂不推荐进入首批部署的候选类型

- `Chemprop`、`DeepChem`、`TorchDrug`、`MatGL`、`SchNetPack` 这类框架本身：
  它们只有在绑定具体 checkpoint/endpoint 后才是 verifier 模型。
- 纯 Web-only 的 `SwissADME`、`pkCSM`、`admetSAR`、`ProTox-II`：
  它们适合参考，不适合作为首批官方 Docker runtime oracle。
- 商业闭源工具如 `ACD/Labs Percepta`、`QikProp`、`ADMET Predictor`：
  物化性质价值很高，但部署和再分发许可证不适合当前优先级。
- 只计算描述符或规则的工具，例如单纯 RDKit descriptor、Toxtree alert：
  它们不是“机器学习方法 + 训练数据”的端到端性质预测模型。

## 4. Docker/verifier 接入建议

第一批建议采用两类镜像策略：

1. 直接模型镜像：对 `eos6oli` 这类已经有 DockerHub 镜像的模型，冻结 image digest，
   verifier script 通过 HTTP `/run` 或容器内 Ersilia CLI 调用。
2. 项目统一镜像：对 `ADMET-AI` 和 `MatGL` 模型，基于本仓库 `uv` 环境构建统一
   verifier image，模型 checkpoint 在 build 阶段或首次运行前预拉取并记录 hash。

每个正式 verifier spec 至少记录：

- `model_id`：例如 `soltrannet_eos6oli_v1`、`matgl_megnet_eform_mp_2018_6_1`。
- `property_domain`：physchem、quantum、materials。
- `input_format`：SMILES、XYZ、CIF、pymatgen Structure。
- `output_name`、单位和方向。
- 训练标签类型：experimental、DFT/computed、hybrid。
- Docker image digest 或 package/model cache hash。
- domain gate：元素、charge、heavy atom count、crystal size、supported species。

## 5. 关键来源

- SolTranNet GitHub: <https://github.com/gnina/SolTranNet>
- Ersilia `eos6oli` model card: <https://github.com/ersilia-os/eos6oli>
- ADMET-AI GitHub: <https://github.com/swansonk14/admet_ai>
- OPERA GitHub: <https://github.com/NIEHS/OPERA>
- pKaSolver Ersilia model card: <https://github.com/ersilia-os/eos2b6f>
- Uni-pKa GitHub: <https://github.com/dptech-corp/Uni-pKa>
- QupKake Ersilia model card: <https://github.com/ersilia-os/eos3wzy>
- MatGL GitHub: <https://github.com/materialsvirtuallab/matgl>
- MatGL pretrained model discovery via local `matgl.get_available_pretrained_models()`
- ALIGNN GitHub: <https://github.com/usnistgov/alignn>
- MACE GitHub: <https://github.com/ACEsuit/mace>
- MatterSim GitHub: <https://github.com/microsoft/mattersim>
- TorchANI GitHub: <https://github.com/aiqm/torchani>
- AIMNet2 GitHub: <https://github.com/isayevlab/AIMNet2>
