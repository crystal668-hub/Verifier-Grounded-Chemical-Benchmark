# 轻量分子动力学与力场 verifier 候选调研

日期：2026-06-30

## 1. 背景与筛选标准

上一份覆盖报告确认当前仓库缺少“分子模拟、力场、MD/MC”方向的 verifier backend。该方向的关键矛盾是：真实 MD/GCMC/FEP/材料动力学通常成本高、随机性强、依赖复杂，不适合直接作为首批同步评分器。因此本报告只评估能作为轻量 verifier 的工具和模型候选。

筛选标准：

- CPU 可运行，不要求 GPU。
- 单候选评分可在秒级到十几秒内完成；首批目标 timeout 不超过 30-60 秒。
- 输入 schema 可控：SMILES、SDF/mol block、XYZ、CIF 或固定 fixture + candidate edit。
- 能明确失败类型：解析失败、力场参数缺失、优化未收敛、domain 外、timeout。
- 能冻结版本、随机种子、力场名称、步数、温度、timestep、平台和输出单位。
- 尽量优先复用当前依赖；新增依赖必须部署路径清楚。

本地环境探针：

- 当前项目已有 `rdkit==2026.3.2`、`ase==3.28.0`，没有 OpenMM/OpenFF/Open Babel/TorchANI。
- RDKit ETKDGv3 + MMFF 对一个中等小分子生成 20 个构象并优化，约 `0.105s`。
- `uv run --with openmm` 可安装并导入 OpenMM，暴露 `Reference`、`CPU`、`OpenCL` 平台。
- `uv run --with openff-toolkit` 当前不能直接解析可用 PyPI 依赖；官方推荐 mamba/conda-forge。
- `uv run --with openmmforcefields --with openmm` 可导入 GAFF/SMIRNOFF template generator 类，但真实小分子参数化仍取决于 OpenFF/AmberTools 等依赖链。
- `uv run --with openbabel-wheel` 可安装 Open Babel Python binding，但从 SMILES 直接建 3D + MMFF94 的快速探针返回极端能量，说明它不适合作首批主 oracle。
- `uv run --with torchani` 可运行 ANI2x，但会拉入 PyTorch；首次 methane 能量/力计算约 `26.7s`，更适合作二线可选 backend。
- ASE EMT 对 4 原子 Cu bulk static/optimization 探针约 `0.006s`，适合极轻材料力场 sanity verifier。

## 2. 推荐结论

| 优先级 | 候选 | 适用对象 | 推荐 verifier 性质 | 结论 |
|---|---|---|---|---|
| P0 | RDKit ETKDGv3 + MMFF94/MMFF94s/UFF | 小分子 SMILES 或 mol block | conformer strain、MMFF/UFF minimized energy、energy spread、embedding success、force-field parameter coverage、clash/geometry gate | 首批最合适。已在项目依赖中，速度快，失败模式简单。 |
| P0/P1 | ASE built-in calculators：EMT、LennardJones、Morse | 小材料/金属/玩具原子体系 | static energy、relaxed energy、max force、relaxation energy、volume/nearest-neighbor sanity | 适合材料力场入门 verifier，但 domain 必须窄。 |
| P1 | xTB GFN-FF | 小分子或较大有机/非共价体系 XYZ | force-field-level relaxation energy、short MD sanity、cheap conformer/geometry prefilter | 与现有 xTB CLI 路径相近，适合作 xTB backend 的低成本补充。 |
| P1 | OpenMM core + fixed built-in biomolecular force fields | 固定 peptide/protein/water fixture，不接受任意小分子 | minimization energy drop、max force、short restrained MD stability | OpenMM 本体部署可行；首批应避开任意 SMILES 参数化。 |
| P1/P2 | OpenMM + OpenFF/GAFF via conda-forge environment | 小分子/ligand | OpenFF/GAFF energy, minimization convergence, very short MD stability | 科学价值高，但部署复杂度高于 RDKit；需要独立环境验证。 |
| P2 | TorchANI ANI-2x | H/C/N/O/F/S/Cl 小分子 | neural potential energy/forces, geometry relaxation sanity | 可 CPU 跑但 PyTorch 和冷启动较重；适合作交叉验证或离线校准。 |
| P2 | Open Babel MMFF94/UFF/GAFF | 小分子格式转换、备用优化 | fallback minimization 或 cross-check | 可安装但探针显示直接当主 oracle 风险高；不建议首批。 |
| P3 | GROMACS/LAMMPS/RASPA/long MD/GCMC | 大体系、吸附、扩散、真实 MD | diffusion、RDF、uptake、free energy | 当前不适合同步评分；应作为预计算或固定 fixture 后处理。 |

首批建议只实现两个轻量 backend：

1. `rdkit_forcefield_conformers`
   - 目标：小分子力场/构象 verifier。
   - 依赖：现有 RDKit。
   - 输入：SMILES，或后续支持 submitted SDF/mol block。
   - 输出：`mmff_parameterized`、`embedding_success_rate`、`best_mmff_energy_kcal_mol`、`energy_range_kcal_mol`、`strain_proxy_kcal_mol`、`optimization_converged_fraction`、`min_nonbonded_distance`。

2. `ase_lightweight_relaxation`
   - 目标：材料或原子体系静态/弛豫 sanity verifier。
   - 依赖：现有 ASE。
   - 输入：CIF/XYZ/fixture structure。
   - 输出：`initial_energy_ev`、`relaxed_energy_ev`、`relaxation_energy_ev`、`max_force_ev_per_angstrom`、`minimum_distance_angstrom`、`converged`。
   - 首批 calculator：`EMT`，只开放其适用元素；之后再考虑 LennardJones/Morse 或 MLIP calculators。

## 3. 候选工具逐项评估

### 3.1 RDKit ETKDG + MMFF/UFF

定位：小分子构象生成、局部力场优化、低成本几何/strain verifier。

可部署性：

- 已在项目依赖中，无需新增 package。
- RDKit 官方 API 提供 ETKDG/ETKDGv3 3D coordinate embedding，以及 MMFF/UFF force-field setup 和 optimization。
- 可以固定 `randomSeed`、`numConfs`、`maxIters`、`pruneRmsThresh`、MMFF variant。
- 对当前 RDKit domain 内小分子运行成本很低。探针中 20 conformers + MMFF 优化约 0.1 秒。

适合的 verifier 性质：

| 性质 | 含义 | 推荐用途 |
|---|---|---|
| `mmff_has_all_params` | MMFF 是否覆盖分子所有原子 | domain gate |
| `embedding_success_rate` | ETKDG 多构象嵌入成功比例 | 3D realizability gate |
| `best_mmff_energy_kcal_mol` | 优化后最低 MMFF energy | 只能在同一分子/约束上下文中解释，不适合作跨分子绝对目标 |
| `energy_spread_kcal_mol` | 多构象能量范围 | conformational flexibility/strain proxy |
| `strain_proxy_kcal_mol` | submitted conformer energy - generated ensemble best energy | 如果接受 submitted 3D，可作为构象质量门 |
| `optimization_converged_fraction` | MMFF/UFF 优化收敛比例 | geometry quality |
| `min_nonbonded_distance_angstrom` | 非键合最短距离 | clash gate |

推荐首批题型：

- “生成一个单组分小分子，RDKit/MMFF 可参数化，并且最低能构象能量分布显示 moderate flexibility。”
- “提交一个 SDF/mol block 3D 构象，要求 MMFF 优化前后 energy drop 小于阈值。”
- “在 RDKit descriptor/ADMET 任务上增加 force-field quality gate，过滤不可嵌入或严重 clash 的分子。”

注意事项：

- MMFF/UFF energy 不是跨不同分子的可比较实验能量。更适合作 domain gate、strain gate 或同一分子不同构象的比较。
- UFF 覆盖面比 MMFF 更广但精度/药化解释更弱；建议优先 MMFF，UFF 作为 fallback 时在 `versions/provenance` 中明确记录。
- 多构象任务必须固定 seed 和最大构象数，避免随机性和成本漂移。

依据：

- RDKit `rdDistGeom` 文档说明其可用 distance geometry 生成 3D coordinates，并有 ETKDGv3 参数入口：https://www.rdkit.org/docs/source/rdkit.Chem.rdDistGeom.html
- RDKit `rdForceFieldHelpers` 文档提供 MMFF/UFF 参数检查、force field 创建、优化和返回码：https://www.rdkit.org/docs/source/rdkit.Chem.rdForceFieldHelpers.html

### 3.2 ASE built-in calculators

定位：材料/原子体系的极轻量力场 sanity verifier。

可部署性：

- 项目已有 `ase==3.28.0`。
- ASE 提供统一 Atoms/calculator/optimizer 抽象；当前 MatGL/MACE 材料 backend 已经与材料结构输入相邻。
- 内置 EMT、Lennard-Jones、Morse 等 calculator 可 CPU 快速运行。

适合的 verifier 性质：

| 性质 | 适用 calculator | 推荐用途 |
|---|---|---|
| `emt_energy_per_atom` | EMT | 金属/少数元素材料 sanity |
| `relaxation_energy_ev` | EMT/LJ/Morse | 输入结构是否接近局部低能 |
| `max_force_ev_per_angstrom` | EMT/LJ/Morse | 结构质量 gate |
| `volume_change_fraction` | cell relaxation 后续可加 | 晶胞合理性 |
| `minimum_distance_angstrom` | calculator independent | 原子重叠 gate |

推荐首批题型：

- 固定元素体系，例如 Cu/Ni/Al/Pt/Au 等 EMT 支持体系，要求生成 CIF 的 nearest-neighbor distance 和 EMT relaxed energy 在窗口内。
- 作为材料 ML backend 的前置 quality gate：先用 ASE 做几何 sanity，再调用 MatGL/MACE。

注意事项：

- EMT 适用域很窄；不能拿来泛化所有材料或化学键类型。
- LJ/Morse 更像教学/模型势，适合固定 toy task 或结构质量门，不适合真实化学性质声明。
- 若做 cell relaxation，需要明确 cell filter、压力、约束和步数；首批可只做 fixed-cell atomic relaxation。

依据：

- ASE 文档提供 Atoms/calculators/optimizers/MD 工作流：https://wiki.fysik.dtu.dk/ase/
- ASE EMT calculator 文档：https://wiki.fysik.dtu.dk/ase/ase/calculators/emt.html

### 3.3 xTB GFN-FF

定位：比 GFN2-xTB 更便宜的通用分子力场路径，可作为现有 xTB backend 的轻量补充。

可部署性：

- 当前 xTB backend 已能调用本地 `xtb` executable、处理 XYZ、timeout、domain、failure mapping。
- GFN-FF 属于 xTB 生态，理论上可以复用现有 CLI runner、XYZ parser 和 geometry gates。
- 需要实际验证当前本地/CI xTB 版本是否支持 `--gfnff` 或等价参数，并冻结命令。

适合的 verifier 性质：

- `gfnff_relaxation_energy`
- `gfnff_max_force_after_opt`
- very short MD sanity，例如温度漂移、bond break、RMSD，但首批建议先不做 MD。
- large-molecule prefilter：比 GFN2 更低成本地检查粗糙 XYZ。

注意事项：

- GFN-FF 仍依赖 xTB executable，不是纯 Python 依赖。
- 若目标是“引入 MD/力场方向”，它很适合与既有 xTB track 形成连续路径；但不要把 GFN-FF 输出写成高精度 MD 结果。

依据：

- xTB GFN-FF 文档包含 GFN-Force-Field、parallelization、MD simulations 和 2D-to-3D converter 章节：https://xtb-docs.readthedocs.io/en/latest/gfnff.html

### 3.4 OpenMM core

定位：标准 MD 引擎底座，可做能量最小化、短程 MD、trajectory output 和 CPU/GPU platform control。

可部署性：

- `uv run --with openmm` 可快速安装 OpenMM 并导入。
- 本地探针显示 OpenMM 可见 `Reference`、`CPU`、`OpenCL` 平台。
- 官方文档说明 OpenMM 支持 `Simulation.minimizeEnergy()`、短程 MD、reporters，以及 `Reference`、`CPU`、`CUDA`、`OpenCL`、`HIP` 平台选择。

首批推荐范围：

- 不要直接接受任意 SMILES 并自动参数化。
- 可以接受固定 PDB/fixture + candidate scalar/edit，例如：
  - 固定小 peptide 构象，要求 minimization energy drop 低。
  - 固定 water/ion toy system，做 100-1000 step deterministic sanity。
  - 固定 ligand topology 文件，不在评分时生成参数。

不建议首批做的范围：

- 任意小分子 OpenFF/GAFF 参数化。
- protein-ligand complex MD。
- binding free energy、MM/PBSA、MM/GBSA。

依据：

- OpenMM User Guide 运行示例包含 force field、energy minimization、Langevin integrator、trajectory reporter 和 MD steps：https://docs.openmm.org/latest/userguide/application/02_running_sims.html
- OpenMM 文档列出 Reference、CPU、CUDA、OpenCL、HIP platforms，并可显式选择平台：https://docs.openmm.org/latest/userguide/application/02_running_sims.html#platforms

### 3.5 OpenMM + OpenFF/GAFF

定位：更真实的小分子力场/MD backend 候选。

可部署性结论：

- 科学上值得做，但不是 P0。
- OpenFF Toolkit 官方推荐 mamba/conda-forge 安装；文档明确 `mamba create -n openff-toolkit -c conda-forge openff-toolkit` 是最简单路径，并称 mamba 安装会自动处理依赖。
- 当前 `uv run --with openff-toolkit` 不能解析可用 PyPI 包；这与官方推荐 conda-forge 的部署方式一致。
- `openmmforcefields` 可以通过 pip/uv 安装并导入 `GAFFTemplateGenerator`、`SMIRNOFFTemplateGenerator`，但真正使用仍依赖 OpenFF Toolkit/AmberTools/RDKit/OpenEye 等组合。

适合的 verifier 性质：

- `openff_minimized_energy_kj_mol`
- `openff_energy_drop_kj_mol`
- `openff_max_force_kj_mol_nm`
- very short NVT stability: RMSD、temperature range、bond length violation。

部署建议：

- 作为独立 optional dependency group 或 Docker/conda verifier image，而不是混进默认 `uv sync`。
- 首批只允许元素 H/C/N/O/F/P/S/Cl/Br/I 和 formal charge 限制。
- 明确 force field，例如 `openff-2.2.1` 或固定 GAFF 版本。

依据：

- OpenFF Toolkit installation 文档推荐 mamba/conda-forge，并说明 OpenFF Toolkit 依赖较多：https://docs.openforcefield.org/projects/toolkit/en/stable/installation.html
- OpenMM forcefields 项目提供 OpenFF/GAFF 等 template generator，但需要配套 toolkit/parameterization 依赖：https://github.com/openmm/openmmforcefields

### 3.6 TorchANI / ANI-2x

定位：轻量神经网络势能，可给小有机分子能量和力。

可部署性：

- 可通过 `uv run --with torchani` 安装并运行，但会拉入 PyTorch。
- 本地 cold-start 探针 methane energy/force 约 `26.7s`，之后热启动会更快，但 verifier runner 的进程模型会影响真实成本。
- ANI-2x 元素覆盖有限，适合 H/C/N/O/F/S/Cl 等小分子，不适合 P、Br、I、金属、盐或复杂体系。

适合的 verifier 性质：

- `ani2x_energy_hartree`
- `ani2x_max_force`
- `ani2x_relaxation_energy`
- 与 xTB/RDKit force field 的 cross-check gate。

结论：

- 不建议作为首批默认 backend。
- 可作为 optional ML potential backend，用于小有机 molecule 3D geometry quality 或 calibration study。

依据：

- TorchANI 官方文档：https://aiqm.github.io/torchani/

### 3.7 Open Babel

定位：格式转换、分子准备、备用 MMFF94/UFF/GAFF 工具。

可部署性：

- `openbabel-wheel` 可通过 uv 安装。
- 官方文档覆盖 Python binding 和 molecular mechanics/force fields。
- 本地探针中直接从 aromatic SMILES 读入、加氢后用 MMFF94 优化，返回极端能量且没有改善；原因是没有可靠 3D coordinate generation/cleanup 流程。

结论：

- 不建议首批作为主力 verifier oracle。
- 可以作为格式转换或后续 cross-check；若使用，必须明确 3D 生成步骤和失败策略。

依据：

- Open Babel Python binding 文档：https://openbabel.org/docs/UseTheLibrary/PythonDoc.html
- Open Babel molecular mechanics/force fields 文档：https://openbabel.org/docs/Forcefields/Overview.html

## 4. 不建议首批同步评分的工具

| 工具/方向 | 原因 | 可接受替代形态 |
|---|---|---|
| GROMACS | 安装和输入准备重；真实 MD 时间长；force field/topology 生成复杂 | 预计算 trajectory 后处理，或固定 topology fixture |
| LAMMPS | 势函数和输入 deck 复杂；材料体系 domain 要窄 | 作为 ASE/LAMMPS optional backend，固定势函数和元素 |
| RASPA/GCMC | MC steps、force field、adsorbate/framework 参数复杂；随机性强 | 固定 MOF/guest/T/P/seed 的离线或 P2 task |
| PLUMED/free energy | 增强采样和 CV 设计复杂 | 非首批，只做固定教程级体系 |
| Protein-ligand MD/MMGBSA | 参数化、protonation、pose、solvent、采样误差都复杂 | 冻结 complex 和 topology，先做 minimization sanity |

## 5. 建议 backend 设计草案

### 5.1 `rdkit_forcefield_conformers`

输入：

```json
{
  "smiles": "CCOc1ccc(NC(=O)C)cc1"
}
```

Spec 关键字段：

```yaml
backend:
  type: rdkit_forcefield
  embedder: ETKDGv3
  random_seed: 61453
  num_conformers: 20
  prune_rms_thresh: 0.5
  forcefield_priority: [MMFF94s, MMFF94, UFF]
  max_iters: 200
domain:
  allowed_elements: [H, C, N, O, F, P, S, Cl, Br, I]
  heavy_atom_count: [5, 60]
  formal_charge: [-1, 1]
  require_single_component: true
```

可输出 properties：

- `conformer_count`
- `embedding_success_rate`
- `forcefield_name`
- `forcefield_parameterized`
- `best_energy_kcal_mol`
- `median_energy_kcal_mol`
- `energy_range_kcal_mol`
- `optimization_converged_fraction`
- `min_nonbonded_distance_angstrom`

推荐首批 constraints：

- `forcefield_parameterized == true` 作为 domain/validity gate。
- `optimization_converged_fraction >= 0.8`。
- `energy_range_kcal_mol` window，用于柔性/构象多样性任务。
- 若接受 submitted SDF/XYZ，则 `strain_proxy_kcal_mol <= threshold`。

### 5.2 `ase_lightweight_relaxation`

输入：

```json
{
  "cif": "<inline CIF>"
}
```

Spec 关键字段：

```yaml
backend:
  type: ase_lightweight
  calculator: EMT
  optimizer: BFGS
  fixed_cell: true
  max_steps: 100
  fmax: 0.05
domain:
  allowed_elements: [Al, Ni, Cu, Pd, Ag, Pt, Au]
  atom_count: [1, 64]
  volume: [1.0, 2000.0]
```

可输出 properties：

- `initial_energy_ev`
- `relaxed_energy_ev`
- `energy_per_atom_ev`
- `relaxation_energy_ev`
- `max_force_ev_per_angstrom`
- `minimum_distance_angstrom`
- `converged`

推荐首批 constraints：

- `max_force_ev_per_angstrom <= 0.05`。
- `relaxation_energy_ev <= threshold` 作为结构质量门。
- `energy_per_atom_ev` window 只在固定元素/结构族内使用。

## 6. 推荐实施顺序

1. 先实现 `rdkit_forcefield_conformers`
   - 原因：零新增依赖、速度最快、能直接增强当前 RDKit/ADMET 小分子 tasks。
   - 测试重点：invalid SMILES、multi-component、MMFF 参数缺失、embedding failure、deterministic seed、energy unit。

2. 再实现 `ase_lightweight_relaxation`
   - 原因：已有 ASE，能补材料力场/弛豫方向。
   - 测试重点：CIF parse、unsupported elements、optimizer convergence、fixed-cell behavior、minimum distance gate。

3. 评估 `gfnff` 是否复用现有 xTB backend
   - 原因：与现有 xTB CLI 最贴近，可作为 direct-XYZ 的更便宜 quality gate。
   - 先做环境脚本检查 `xtb --gfnff` 支持情况，再加 backend mode。

4. OpenMM/OpenFF 放入 optional research branch
   - 原因：OpenMM 本体轻，但任意小分子参数化依赖链重。
   - 推荐用单独 dependency group 或 Docker/conda image，不要污染默认环境。

## 7. 最终候选清单

| 名称 | 是否建议部署 | 部署形态 | 首批任务价值 |
|---|---:|---|---|
| RDKit ETKDG/MMFF/UFF | 是，P0 | 默认依赖 | 小分子构象和力场质量门 |
| ASE EMT/LJ/Morse | 是，P0/P1 | 默认依赖 | 材料轻量弛豫/结构 sanity |
| xTB GFN-FF | 是，P1 | 复用 xTB external executable | direct-XYZ 低成本力场 gate |
| OpenMM core fixed fixtures | 条件是，P1 | optional dependency | 固定体系 minimization/short MD |
| OpenMM + OpenFF/GAFF | 暂缓，P1/P2 | conda/Docker optional image | 任意小分子真实力场 |
| TorchANI ANI-2x | 暂缓，P2 | optional PyTorch dependency | 小有机 ML potential cross-check |
| Open Babel force fields | 暂缓，P2 | optional dependency | fallback/cross-check，不做主 oracle |
| GROMACS/LAMMPS/RASPA | 暂缓，P3 | precompute/fixture only | 长 MD/MC 或吸附扩散研究 |

## 8. 参考资料

- RDKit distance geometry / ETKDG API: https://www.rdkit.org/docs/source/rdkit.Chem.rdDistGeom.html
- RDKit force-field helper API: https://www.rdkit.org/docs/source/rdkit.Chem.rdForceFieldHelpers.html
- ASE documentation: https://wiki.fysik.dtu.dk/ase/
- ASE EMT calculator: https://wiki.fysik.dtu.dk/ase/ase/calculators/emt.html
- xTB GFN-FF documentation: https://xtb-docs.readthedocs.io/en/latest/gfnff.html
- OpenMM User Guide, running simulations: https://docs.openmm.org/latest/userguide/application/02_running_sims.html
- OpenFF Toolkit installation: https://docs.openforcefield.org/projects/toolkit/en/stable/installation.html
- OpenMMForceFields: https://github.com/openmm/openmmforcefields
- TorchANI documentation: https://aiqm.github.io/torchani/
- Open Babel Python bindings: https://openbabel.org/docs/UseTheLibrary/PythonDoc.html
- Open Babel force fields: https://openbabel.org/docs/Forcefields/Overview.html
