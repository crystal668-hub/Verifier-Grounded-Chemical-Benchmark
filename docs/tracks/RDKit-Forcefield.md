# RDKit Forcefield Prototype 题目设计与实现同步

更新日期：2026-06-30

## 1. 定位

`rdkit_forcefield` 是轻量分子模拟/力场方向的 prototype task pack。它采用现有 RDKit 依赖中的 ETKDGv3 conformer generation 与 MMFF94s/MMFF94/UFF minimization，目标是先建立一个 CPU 友好、秒级、可复现的小分子 force-field baseline。

该 pack 当前不进入 builtin registry，不属于正式 track。它用于验证 backend 部署面和后续任务设计。

## 2. 当前实现

当前 task pack：`tasks/rdkit_forcefield/`

- 题目数量：2。
- verifier specs：2。
- 输入：单组分 SMILES。
- backend：`verifiers/rdkit_forcefield/backend.py`。
- scripts：`verifiers/rdkit_forcefield/rdkit_energy_range.py`、`verifiers/rdkit_forcefield/rdkit_convergence.py`。

统一 backend 配置：

- embedder：ETKDGv3。
- random seed：61453。
- requested conformers：20。
- prune RMS threshold：0.5 Angstrom。
- force-field priority：MMFF94s, MMFF94, UFF。
- max minimization iterations：200。

统一 domain gate：

- 单组分 SMILES。
- allowed elements：H、B、C、N、O、F、P、S、Cl、Br、I。
- heavy atom count：5 到 60。
- molecular weight：0 到 600 dalton。
- formal charge：-1 到 1。

## 3. 当前性质

| property | 含义 | 用途 |
|---|---|---|
| `energy_range_kcal_mol` | retained conformers 中最高与最低 RDKit force-field energy 的差 | 构象 ensemble 的粗略 flexibility/strain proxy |
| `optimization_converged_fraction` | retained conformers 中 RDKit minimization 返回 converged status 的比例 | 几何/参数化质量 proxy |
| `embedding_success_rate` | retained conformers / requested conformers | 3D embedding 可实现性辅助指标 |
| `min_nonbonded_distance_angstrom` | 第一个 retained conformer 的最短非键合原子距离 | clash 辅助指标 |

注意：MMFF/UFF energy 不是跨分子可直接比较的实验热力学能量。当前性质应解释为固定 RDKit workflow 的 surrogate descriptor 或 quality gate。

## 4. 当前题目

| task_id | 目标性质 | 约束 |
|---|---|---|
| `rdkit_forcefield_energy_range_window_001` | `energy_range_kcal_mol` | window `[0.0, 20.0]`, `sigma=5.0` |
| `rdkit_forcefield_convergence_max_002` | `optimization_converged_fraction` | maximize bounded `[0.0, 1.0]` |

## 5. OpenMM 后续路线

本轮没有把 OpenMM/OpenFF 加入默认依赖。原因是 OpenMM engine 本体可轻量安装，但任意小分子的 OpenMM System 参数化需要 OpenFF Toolkit、AmberTools/GAFF、template generator 和独立环境管理，部署风险高于 RDKit baseline。

后续建议：

1. 先用当前 RDKit force-field backend 作为 P0 baseline。
2. 再尝试 OpenMM core fixed-fixture verifier，不接受任意 SMILES 参数化。
3. 最后在独立 optional environment 或 Docker image 中评估 OpenMM + OpenFF/GAFF。
