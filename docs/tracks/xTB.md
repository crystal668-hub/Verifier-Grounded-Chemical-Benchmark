# xTB 题目设计与实现同步

更新日期：2026-07-24

## 1. Track 边界与答案格式

xTB track 包含两类 open-generation 任务，具体格式由每题 `answer_schema` 决定：

- direct-XYZ：提交全氢显式的 fenced XYZ；候选坐标是答案的一部分。
- SMILES-to-conformer：提交单个 SMILES；verifier 生成初始几何并执行冻结的 CREST/xTB workflow。

因此“xTB track 只接受 XYZ”不再是 track 不变量。正式资源位于 `src/verifier_grounded_benchmark/task/packs/xtb/`，当前只有任务 020 使用 SMILES，其余任务使用 XYZ。

direct-XYZ 基线 domain 要求单连通分子、有限 Angstrom 坐标，并按任务验证元素、原子数、电子态和结构限制。任务 019 进一步要求中性闭壳层、全氢显式、至少 7 个重原子、至少 3 种非氢元素，且每种实际出现的非氢元素计数均为奇数。

## 2. 当前任务

- 正式题目：20。
- verifier specs：15。
- 001-013 使用 `relaxation_energy` geometry quality gate；014-020 严格按各题公开约束，不额外应用该乘子。

| task_id | 主目标 | 输入/特殊协议 |
|---|---|---|
| `xtb_gap_window_001` | gap window | XYZ |
| `xtb_dipole_window_002` | dipole window | XYZ |
| `xtb_gap_max_003` | maximize gap | XYZ |
| `xtb_gap_min_004` | minimize gap | XYZ |
| `xtb_dipole_max_005` | maximize dipole | XYZ |
| `xtb_low_gap_high_dipole_opt_006` | gap + dipole | XYZ |
| `xtb_gap_dipole_window_007` | gap + dipole windows | XYZ |
| `xtb_lumo_min_008` | minimize LUMO | XYZ |
| `xtb_polarizability_dipole_opt_009` | polarizability + dipole | XYZ |
| `xtb_solvation_selectivity_alpb_010` | ALPB selectivity | XYZ |
| `xtb_electrophilicity_max_011` | electrophilicity | XYZ |
| `xtb_fukui_carbon_site_012` | carbon Fukui response | XYZ |
| `xtb_hessian_thermo_stability_013` | maximize entropy, zero-imaginary-frequency hard constraint | XYZ |
| `xtb_formula_dipole_min_014` | exact-formula dipole | XYZ, neutral doublet |
| `xtb_two_fluorine_gap_min_015` | minimize gap | XYZ, exact F count |
| `xtb_c10_f2_gap_min_016` | minimize gap | XYZ, `C10F2` domain |
| `xtb_roy_singlepoint_energy_min_017` | ROY single-point energy | XYZ, graph identity |
| `xtb_ritonavir_optimized_energy_min_018` | Ritonavir optimized energy | XYZ, graph/stereo identity |
| `xtb_odd_element_counts_gap_max_019` | maximize gap | XYZ, odd element counts, dipole `<2 D` |
| `xtb_pyrene_substituent_energy_min_020` | minimize total energy | SMILES, CREST ensemble + xTB single-point |

## 3. 新增专家协议

### 3.1 Joint dipole/gap

`xtb_odd_element_gap_dipole_gfn2_v1` 对任务 019 只运行一次 GFN2-xTB optimization，并从同一份收敛 evidence 解析 dipole 和 orbital-energy HOMO-LUMO gap。dipole `>=2 D` 触发 `hard_constraint_failed`；只有硬门通过才用 gap 评分。xTB 缺失、超时或未收敛属于环境/工具故障。

冻结锚点为 `B=3.6 eV`、`T=11.9 eV`。这里的 gap 是 GFN2-xTB 轨道能级差，不是实验 optical gap 或高精度 ab initio band gap。

### 3.2 CREST pyrene energy

`xtb_pyrene_crest_energy_v1` 接收 SMILES，并验证候选相对冻结 pyrene reference 的精确 graph delta：16 个 scaffold carbon 与 bond graph 不变，三个不同原 C-H 位点分别连接一个 nitro、amino、carboxyl，且无额外原子或键。初始 ETKDGv3 几何和 CREST ensemble 最低成员都必须通过 identity check。

冻结环境为 RDKit 2026.3.2、CREST 2.12、xTB 6.7.1、GFN2-xTB、`charge=0`、`uhf=0`、单线程、`-mquick`，seed `61453`。最低 ensemble member 再运行 xTB single-point；冻结锚点为 `T=-63.56975 Eh`、`B=-63.5669 Eh`。该能量只在相同 formula、charge、电子态和冻结协议内比较，不代表实验生成自由能、溶液平衡或合成产率。

校准明细和配置哈希见 `docs/research/2026-07-23-expert-open-generation-009-013-calibration.md`，可复现环境见 `envs/crest-xtb.yml`。

## 4. 执行与 failure 语义

direct-XYZ 路径解析坐标、推断连通性并应用 task-level structural domain，再运行对应 xTB property workflow。任务 020 按 SMILES 路由到 CREST backend。模型自报数值不参与评分。

001-013 的 relaxation quality score 与主性质分开聚合：主性质取 geometric mean，quality gates 取最小值，最终相乘。014-020 没有该通用 gate。任务 013 要求 `imaginary_frequency_count` 严格等于 0，任务 019 要求 dipole `<2 D`；两者都是先于主评分执行的硬约束，不是连续 multiplier。

所有连续 profile 使用 `linear_goal_v2`。缺失 `xtb`/`crest`、超时、未产生 ensemble 或 backend 未收敛映射为环境/工具 failure；候选结构域不满足、硬性质失败和搜索后分子图改变分别保留候选级 failure 类型。

## 5. 数据与发布边界

`sample_answers.jsonl` 只包含公开 showcase examples，用于展示两种 answer schema 和验证 pipeline；当前 9 条样例不覆盖全部 20 个正式任务，也不代表 benchmark 或校准分布。冻结校准记录可以公开协议和锚点证据，但 private calibration answers/manifest 不进入发行包。

发行包必须同时包含 20 个 task definitions、15 个 verifier specs、公开样例及 SMILES/XYZ routing 所需代码。任务 020 的 CREST/xTB 可执行环境是外部运行时依赖，缺失时不得把候选计为零分。

## 6. 化学解释边界

GFN2-xTB 适合作为低成本量子化学 surrogate。gap、dipole、LUMO、polarizability、solvation、electrophilicity、Fukui response、thermochemistry 和 total energy 都只在各自冻结协议中解释。绝对 total energy 不跨 formula、电子态、任务或方法比较；CREST 最低成员是有限搜索结果，不是完整自由能面或实验构象分布。

## 7. 资料

- xTB 文档：https://xtb-docs.readthedocs.io/
- xTB properties：https://xtb-docs.readthedocs.io/en/latest/properties.html
- CREST 文档：https://crest-lab.github.io/crest-docs/
- Bannwarth, Ehlert and Grimme, GFN2-xTB, JCTC 2019：https://pubmed.ncbi.nlm.nih.gov/30741547/
- Pracht et al., CREST conformer sampling, PCCP 2020：https://doi.org/10.1039/C9CP06869D
