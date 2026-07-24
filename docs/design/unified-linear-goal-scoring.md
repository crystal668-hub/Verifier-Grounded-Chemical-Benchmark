# 统一评价系统与线性目标评分规格

日期：2026-07-17
状态：架构与评分设计规格草案，参数待定，尚未替换正式实现

## 1. 目的

本文同时规定 verifier-grounded benchmark 的评价系统架构和统一连续评分方式。目标是把当前分散在 `benchmark`、`verifiers` 和 `verifier_grounded_benchmark` 三套 Python 包中的答案解析、verifier 执行、打分、聚合、reporting、task 加载与公共 API 收敛为职责清晰、依赖单向的模块。

所有可连续评分的数值约束都转换为：

1. 一个满分区域；
2. 满分区域两侧可选的线性衰减区间；
3. 超出衰减区间后的零分区域。

统一评分只依赖任务声明的目标、窗口、gold answer 和衰减宽度，不拟合“全化学空间”的性质分布。最大化和最小化任务的满分目标可以来自文献、同协议 reference 或其他预先冻结且可审计的科学依据。

本规格解决以下问题：

- 统一 `target`、`window`、`maximize`、`minimize` 和数值 Property Calculation 的评分内核；
- 明确窗口内、超过单向优化目标后以及 hard gate 通过后的满分语义；
- 明确 Property Calculation 在 gold 附近连续衰减，而不是 tolerance 内二元通过；
- 明确多约束、quality gate、stability gate 和 Property Calculation comparison group 的聚合方式；
- 为当前四个 task pack 中的 33 道题给出逐题迁移规则。
- 定义 `evaluation`、`task`、`scripts` 和 `releases` 四个责任域及其依赖边界；
- 将 open-generation verifier 从独立顶层包收归 `evaluation/open_generation`；
- 定义 parser、verifier evidence、constraint score、task result 和 benchmark report 的稳定接口；
- 给出从当前目录到目标目录的逐文件迁移方案、兼容策略和验收标准。

本文不确定具体目标值和衰减宽度。所有标记为 `TBD` 的参数必须经过独立研究、审核和版本冻结后才能进入正式 task pack。旧 `lower`、`upper`、`sigma` 和 `absolute_tolerance` 不得未经审核直接解释成新参数。

## 2. 分数语义

单个数值约束的分数属于 `[0, 1]`：

- `1`：性质值位于任务定义的满分区域；
- `(0, 1)`：性质值未达到满分区域，但仍位于预先声明的线性衰减区间；
- `0`：性质值已经到达或超过零分锚点；
- 分数表示相对于任务目标的线性完成度，不表示候选属于某个性质总体分布的分位数，也不表示成功概率或 verifier uncertainty。

不同性质可以使用相同公式，但目标和衰减宽度仍是任务参数。这里的“统一”指统一数学内核、边界行为、字段含义和聚合协议，不要求所有性质共享同一个数值零点或相同物理尺度。

## 3. 统一数学内核

### 3.1 参数

设 verifier 输出的性质值为 `x`。一个线性目标约束最多包含四个参数：

- `L`：满分区域下界；可以省略，表示下方无界；
- `U`：满分区域上界；可以省略，表示上方无界；
- `rL > 0`：从 `L` 向左到零分所需的距离；仅在 `L` 存在且左侧需要衰减时使用；
- `rU > 0`：从 `U` 向右到零分所需的距离；仅在 `U` 存在且右侧需要衰减时使用。

有限边界必须满足 `L <= U`。所有边界和衰减宽度必须与 `x` 使用相同单位。

### 3.2 标准化违规程度

```text
violation(x) =
    (L - x) / rL    if L exists and x < L
    0               if x is inside the full-score region
    (x - U) / rU    if U exists and x > U
```

满分区域由存在的边界决定：

- 同时存在 `L`、`U`：`L <= x <= U`；
- 只有 `L`：`x >= L`；
- 只有 `U`：`x <= U`。

约束分数为：

```text
score(x) = clip(1 - violation(x), 0, 1)

clip(z, 0, 1) = max(0, min(1, z))
```

### 3.3 等价的零分锚点

左右零分锚点分别是：

```text
B_L = L - rL
B_U = U + rU
```

当两个边界和两个衰减宽度都存在时，完整分段函数为：

```text
score(x) =
    0                              if x <= L - rL
    (x - (L - rL)) / rL           if L - rL < x < L
    1                              if L <= x <= U
    ((U + rU) - x) / rU           if U < x < U + rU
    0                              if x >= U + rU
```

边界行为必须精确满足：

```text
score(L - rL) = 0
score(L)      = 1
score(U)      = 1
score(U + rU) = 0
```

### 3.4 数学性质

实现必须满足：

- 有界性：所有有限输入的分数都位于 `[0, 1]`；
- 连续性：分数在有限满分边界和零分锚点处连续；
- 单调性：左衰减区间单调递增，右衰减区间单调递减；
- 饱和性：进入满分区域后不因继续沿正确方向优化而扣分；
- 单位一致性：若 `x`、`L`、`U` 和 `r` 一致换算单位，分数不变；
- 符号无关性：目标可以为正、零或负，衰减尺度始终由正数 `rL/rU` 表示；
- 可复现性：同一 scoring version 下参数和公式不得根据正式提交结果动态调整。

## 4. 各题型的具体规则

### 4.1 Target

Target 题要求性质尽量接近目标 `T`。令：

```text
L = T
U = T
rL = target_lower_decay_width
rU = target_upper_decay_width
```

评分为：

```text
score_target(x) =
    clip(1 - (T - x) / rL, 0, 1)    if x < T
    1                                if x = T
    clip(1 - (x - T) / rU, 0, 1)    if x > T
```

`rL` 和 `rU` 可以相等，也可以根据两侧误差的科学代价分别设置。这里没有满分平台，目标点得 1 分，两侧分别线性衰减到 0。

### 4.2 Window

Window 题要求性质落入闭区间 `[L, U]`。窗口内全部满分：

```text
score_window(x) =
    clip(1 - (L - x) / rL, 0, 1)    if x < L
    1                                if L <= x <= U
    clip(1 - (x - U) / rU, 0, 1)    if x > U
```

左右衰减宽度相互独立。对于物理上不可能越过的一侧，可以在 schema 中将该侧标记为 `inactive_by_domain`，但 verifier 若输出违反物理域的值，必须返回 verifier error，不能静默给分。

离散整数窗口也使用同一公式。其分数只会出现在 verifier 实际可产生的整数点上。

### 4.3 Maximize

Maximize 题使用满分目标 `T`。候选达到或超过 `T` 后均为满分：

```text
L = T
U omitted
rL = T - B
```

其中 `B < T` 是零分锚点。评分为：

```text
score_maximize(x) =
    0                         if x <= B
    (x - B) / (T - B)        if B < x < T
    1                         if x >= T
```

`T` 是成功目标，不是性质的理论上确界。超过文献或 reference 目标不会得到超过 1 的分数，也不会被反向扣分。

### 4.4 Minimize

Minimize 题使用满分目标 `T`。候选达到或低于 `T` 后均为满分：

```text
L omitted
U = T
rU = B - T
```

其中 `B > T` 是零分锚点。评分为：

```text
score_minimize(x) =
    1                         if x <= T
    (B - x) / (B - T)        if T < x < B
    0                         if x >= B
```

`T` 是成功目标，不是性质的理论下确界。继续沿更小方向优化不会扣分。

### 4.5 Property Calculation 数值答案

数值 Property Calculation 以 gold answer `g` 为唯一峰值，以左右容错宽度 `tauL > 0`、`tauU > 0` 定义非零得分范围：

```text
L = g
U = g
rL = tauL
rU = tauU
```

评分为：

```text
score_numeric_gold(x) =
    0                               if x <= g - tauL
    1 - (g - x) / tauL             if g - tauL < x < g
    1                               if x = g
    1 - (x - g) / tauU             if g < x < g + tauU
    0                               if x >= g + tauU
```

当左右容错相等为 `tau` 时：

```text
score_numeric_gold(x) = clip(1 - abs(x - g) / tau, 0, 1)
```

本题型中的“容错区间”是 `(g - tauL, g + tauU)` 内的非零得分支撑区间，不是满分平台。gold 得 1 分，半个容错宽度处得 0.5 分，容错边界及其外侧得 0 分。

`tauL/tauU` 的新语义与当前 `absolute_tolerance` 不同。迁移时必须使用新字段，禁止保留旧字段名却改变边界含义。

### 4.6 Property Calculation 字符串答案

字符串、标签和离散映射不使用线性距离：

```text
score_exact_string(x) = 1    if normalized(x) == normalized(gold)
score_exact_string(x) = 0    otherwise
```

除非任务显式定义 normalization，否则比较必须区分大小写并要求精确匹配。字符串映射不得为了产生连续分数而任意嵌入数轴。

## 5. Gate 与失败语义

### 5.1 Hard gates

以下检查保持二元 gate，不进入线性目标公式：

- answer parse；
- candidate validity；
- verifier applicability domain；
- formula、charge、multiplicity 和 structure identity；
- 任务显式声明为 hard constraint 的结构或电子态要求。

候选导致的 hard-gate failure 令候选最终得分为 0：

```text
hard_gate = parse_gate * validity_gate * domain_gate * identity_gate
```

verifier 环境缺失、超时、进程崩溃或结果 schema 错误属于 measurement/infrastructure failure，应报告 error 并重试，不得伪装成候选性质零分。

### 5.2 Quality gate

当前 xTB 001-013 的 `relaxation_energy` 使用 `role: quality_gate`。它按 Minimize 规则得到连续分数：

```text
q = score_minimize(relaxation_energy; T_quality, B_quality)
```

`T_quality` 是满分质量目标，`B_quality` 是零分质量锚点，均为 `TBD`。同一道题有多个 quality gate 时：

```text
quality_gate_score = min(q_1, ..., q_n)
```

### 5.3 Hard constraints

硬性质约束在连续评分前执行，不产生连续门控分数。任一硬约束失败时，候选以
`hard_constraint_failed` 结束并记 0 分；全部通过后才计算主性质和 quality gate。

`xtb_hessian_thermo_stability_013` 的 `imaginary_frequency_count` 使用严格闭区间：

```yaml
hard_constraints:
- property: imaginary_frequency_count
  verifier_id: xtb_hessian_thermo_gfn2_v1
  operator: closed_window
  lower: 0
  upper: 0
```

## 6. 多约束与 benchmark 聚合

### 6.1 Open-generation 单题

当前 open-generation 任务继续使用等权几何平均聚合所有 `role: main` 的约束：

```text
property_score = geometric_mean(main_constraint_scores)
```

若任一主约束为 0，则 `property_score = 0`。quality gate 不进入几何平均，而是取最小值后作为乘法 gate：

```text
task_score = property_score * quality_gate_score
```

没有 quality gate 时，其分数默认为 1。硬约束失败会在进入上述聚合前直接返回 0 分。

本规格不引入约束权重。未来如需加权，必须升级 scoring version 并在 task metadata 中显式公布。

### 6.2 Property Calculation comparison group

先为每个请求字段计算 field score：

- 数值字段使用 `score_numeric_gold`；
- 字符串字段使用 `score_exact_string`。

当前 comparison group 均为 `mode: all`。为了保留“组内全部正确”的语义并允许数值字段连续得分，group score 定义为组内最小值：

```text
group_score = min(field_scores_in_group)
```

任务分数继续使用 comparison group 的等权算术平均：

```text
task_score = arithmetic_mean(group_scores)
```

因此一个组中的错误字符串会使该组为 0，但不会自动抹去其他独立 comparison group 的得分。

### 6.3 Benchmark 总分

完成覆盖检查后，benchmark 总分为当前选定并发布的 task set 中全部正式任务分数的等权算术平均：

```text
benchmark_score = arithmetic_mean(task_scores)
```

缺题、重复 task id 或未知 task id 时，run 不完整，正式 `benchmark_score` 必须为空。基础设施失败必须在重试后仍单独报告，不能从分母静默删除。

## 7. 建议的规范化 schema

所有连续数值约束在评分层规范化为同一种结构：

```yaml
scoring:
  version: linear_goal_v1
  function: linear_goal_distance
  full_score_region:
    lower: <number-or-null>
    upper: <number-or-null>
  decay:
    lower_width: <positive-number-or-null>
    upper_width: <positive-number-or-null>
  unit: <property-unit>
  provenance:
    target_source: <TBD>
    decay_source: <TBD>
```

各题型的规范化方式：

| 题型 | `lower` | `upper` | `lower_width` | `upper_width` |
| --- | ---: | ---: | ---: | ---: |
| Target | `T` | `T` | `rL` | `rU` |
| Window | `L` | `U` | `rL` | `rU` |
| Maximize | `T` | `null` | `T-B` | `null` |
| Minimize | `null` | `T` | `null` | `B-T` |
| Numeric gold | `g` | `g` | `tauL` | `tauU` |

实现可以保留便于作者阅读的题型字段，但进入 scorer 前必须转换成上述规范化表示。`null` 表示该侧无界，代码不得对无穷值执行减法。

## 8. 当前任务逐题应用

本节覆盖顶层四个 task pack 的全部 33 道题。`tasks/xtb_xyz/expert_calibration/tasks.yaml` 中的 014-018 是正式 xTB 同 id 任务的 calibration 副本，必须继承对应规则和参数版本，不重复计数。

表中 `TBD` 仅表示具体数值待定，不表示公式或参数角色待定。

### 8.1 RDKit baseline：11 题

| Task | 主约束规则 | 单题计算 |
| --- | --- | --- |
| `rdkit_qed_max_001` | QED Maximize：满分目标 `T_qed`，左衰减宽度 `rL_qed` | `s_qed` |
| `rdkit_sa_min_002` | SA score Minimize：满分目标 `T_sa`，右衰减宽度 `rU_sa` | `s_sa` |
| `rdkit_logp_window_003` | logP Window：满分 `[1.0, 3.0]`，两侧宽度 `rL_logp/rU_logp` | `s_logp` |
| `rdkit_tpsa_window_004` | TPSA Window：满分 `[35.0, 75.0]`，两侧宽度 `rL_tpsa/rU_tpsa` | `s_tpsa` |
| `rdkit_hba_window_005` | HBA Window：满分 `[2, 4]`，整数两侧宽度 `rL_hba/rU_hba` | `s_hba` |
| `rdkit_hbd_window_006` | HBD Window：满分 `[1, 2]`，整数两侧宽度 `rL_hbd/rU_hbd` | `s_hbd` |
| `rdkit_fsp3_max_007` | fraction Csp3 Maximize：满分目标 `T_fsp3`，左衰减宽度 `rL_fsp3` | `s_fsp3` |
| `rdkit_qed_sa_008` | QED Maximize + SA Minimize，各自参数同单性质定义 | `sqrt(s_qed * s_sa)` |
| `rdkit_logp_tpsa_009` | logP Window + TPSA Window，各自参数同单性质定义 | `sqrt(s_logp * s_tpsa)` |
| `rdkit_hba_hbd_010` | HBA Window + HBD Window，各自参数同单性质定义 | `sqrt(s_hba * s_hbd)` |
| `rdkit_logp_target_011` | logP Target：`T_logp = 3.0`，两侧宽度 `rL_target_logp/rU_target_logp` | `s_target_logp` |

同一 verifier、同一性质、同一目标语义的重复约束应复用同一个冻结参数 profile。例如 003 与 009 的 logP window 不得使用不同衰减宽度。

### 8.2 RDKit forcefield：2 题

| Task | 主约束规则 | 单题计算 |
| --- | --- | --- |
| `rdkit_forcefield_energy_range_window_001` | energy range Window：满分 `[0.0, 20.0] kcal/mol`；右宽度 `rU_ff_range`；左侧由非负定义域约束 | `s_ff_range` |
| `rdkit_forcefield_convergence_max_002` | converged fraction Maximize：满分目标 `T_ff_convergence`，左宽度 `rL_ff_convergence` | `s_ff_convergence` |

这两题当前 `formal_track: false`，但仍属于现有 task pack，使用相同 scoring contract。若未来转正，不得另建评分公式。

### 8.3 xTB XYZ：18 题

记统一 relaxation quality gate 分数为：

```text
q_relax = score_minimize(relaxation_energy; T_relax, B_relax)
```

001-013 使用相同、版本冻结的 `T_relax/B_relax` profile，除非 verifier protocol 本身不同并在任务中明确声明。

| Task | 主约束规则 | Gate | 单题计算 |
| --- | --- | --- | --- |
| `xtb_gap_window_001` | gap Window `[3.5, 5.5] eV`，两侧宽度 TBD | relaxation quality | `s_gap_window * q_relax` |
| `xtb_dipole_window_002` | dipole Window `[3.0, 5.5] D`，两侧宽度 TBD | relaxation quality | `s_dipole_window * q_relax` |
| `xtb_gap_max_003` | gap Maximize，`T_gap_max/B_gap_max` TBD | relaxation quality | `s_gap_max * q_relax` |
| `xtb_gap_min_004` | gap Minimize，`T_gap_min/B_gap_min` TBD | relaxation quality | `s_gap_min * q_relax` |
| `xtb_dipole_max_005` | dipole Maximize，`T_dipole_max/B_dipole_max` TBD | relaxation quality | `s_dipole_max * q_relax` |
| `xtb_low_gap_high_dipole_opt_006` | gap Minimize + dipole Maximize，各自目标和锚点 TBD | relaxation quality | `sqrt(s_gap_min * s_dipole_max) * q_relax` |
| `xtb_gap_dipole_window_007` | gap Window `[2.5, 4.2] eV` + dipole Window `[3.5, 6.0] D`，宽度 TBD | relaxation quality | `sqrt(s_gap_window * s_dipole_window) * q_relax` |
| `xtb_lumo_min_008` | LUMO energy Minimize，`T_lumo/B_lumo` TBD，可为负值 | relaxation quality | `s_lumo_min * q_relax` |
| `xtb_polarizability_dipole_opt_009` | polarizability/heavy atom Maximize + dipole Window `[3.0, 8.0] D` | relaxation quality | `sqrt(s_polarizability_max * s_dipole_window) * q_relax` |
| `xtb_solvation_selectivity_alpb_010` | ALPB selectivity Maximize，目标和锚点 TBD | relaxation quality | `s_selectivity_max * q_relax` |
| `xtb_electrophilicity_max_011` | electrophilicity Maximize，目标和锚点 TBD | relaxation quality | `s_electrophilicity_max * q_relax` |
| `xtb_fukui_carbon_site_012` | max carbon f+ Maximize + f+ contrast Maximize，各自目标和锚点 TBD | relaxation quality | `sqrt(s_fplus_max * s_contrast_max) * q_relax` |
| `xtb_hessian_thermo_stability_013` | entropy/heavy atom Maximize，目标和锚点 TBD | relaxation quality + imaginary-count stability | `s_entropy_max * q_relax * s_stability` |
| `xtb_formula_dipole_min_014` | dipole Minimize，目标和锚点 TBD | hard formula/electronic-state gates | `hard_gate * s_dipole_min` |
| `xtb_two_fluorine_gap_min_015` | gap Minimize，目标和锚点 TBD | hard composition/charge gates | `hard_gate * s_gap_min` |
| `xtb_c10_f2_gap_min_016` | gap Minimize，目标和锚点 TBD | hard exact-count/charge gates | `hard_gate * s_gap_min` |
| `xtb_roy_singlepoint_energy_min_017` | same-molecule total energy Minimize，目标和锚点 TBD | hard graph identity | `hard_gate * s_roy_energy_min` |
| `xtb_ritonavir_optimized_energy_min_018` | same-molecule optimized total energy Minimize，目标和锚点 TBD | hard graph/stereochemistry identity | `hard_gate * s_ritonavir_energy_min` |

017、018 的 `T` 和 `B` 必须来自同一分子、同一电荷/自旋、同一 xTB method 和同一 single-point/optimized protocol。不同分子或不同电子结构方法的绝对总能量不得作为其锚点。

### 8.4 Property Calculation：2 题

| Task | Field/group 规则 | 单题计算 |
| --- | --- | --- |
| `property_calc_free_energy_001` | `free_energy_difference`：gold `0.258031679 kJ/mol`，左右容错 `tauL_free/tauU_free` TBD，使用 Numeric Gold | `s_free_energy` |
| `property_calc_crystal_phase_002` | `potential_energy_difference`：gold `0.079 eV`，左右容错 TBD，使用 Numeric Gold；phase gold 为 `alpha/beta`，使用 Exact String | `(s_energy_group + s_phase_group) / 2` |

第二题的 group 计算为：

```text
s_energy_group = s_potential_energy
s_phase_group = min(s_ambient_phase, s_high_pressure_phase)
```

任一字符串 phase 错误都会令 phase group 为 0；数值能量组仍保留自身连续分数。

## 9. 参数来源与冻结要求

### 9.1 满分目标

Maximize/Minimize 的 `T` 应按以下证据优先级确定：

1. 与任务科学目标一致、条件完整的文献较优值；
2. 同一 verifier protocol 重算的公开 reference；
3. 预先冻结、通过相同 hard gates 的 benchmark baseline 或 expert control；
4. 有明确依据的工程成功阈值或性质自然边界。

Window 的 `[L,U]`、Target 的 `T` 和 Property Calculation 的 gold 来自题目本身，不需要用性质总体分布重新估计。

### 9.2 衰减宽度和零分锚点

衰减宽度回答的是“距离满分区域多远后应完全不得分”。它可以来自：

- 明确的科学或工程不可接受边界；
- 与目标在同一协议下计算的零分 reference；
- verifier 分辨率、答案精度要求或任务声明的最大容错；
- 对具有自然零点且方向正确的 ratio-scale 性质，使用自然零点作为零分锚点。

不得仅为制造更均匀的 leaderboard 分布而调整宽度。`B=0` 不是全局默认值；只有当零点位于目标的失败侧且具有明确性质语义时才能采用。

### 9.3 Provenance

每个参数 profile 至少记录：

- property name 和 unit；
- verifier id、image/version 和 protocol；
- target/window/gold 来源；
- 零分锚点或衰减宽度来源；
- 文献 DOI、reference artifact hash 或审核记录；
- 生效 scoring version；
- 审核日期和责任人/流程。

## 10. 迁移规则

1. 新评分必须发布为新的 benchmark scoring version。
2. 旧分数与新分数不得跨版本直接比较。
3. `window.sigma` 不自动转换为 `rL/rU`。
4. `maximize_bounded/minimize_bounded.lower/upper` 不自动批准为新的 `T/B`。
5. Property Calculation 的 `absolute_tolerance` 当前表示满分通过边界，不得原名复用为零分衰减宽度。
6. task prompt、task metadata、verifier result 和公开评分说明必须引用同一个冻结参数 profile。
7. 参数未完成审核前，可以实现 shadow scoring，但不得替换正式 `score`。

## 11. 实现验收标准

### 11.1 单约束公式

测试必须覆盖：

- `x = L-rL, L, U, U+rU` 的精确边界值；
- 左右衰减区间的 0.25、0.5、0.75 分点；
- 满分区间内任意点为 1；
- Maximize 在 `x >= T` 时始终为 1；
- Minimize 在 `x <= T` 时始终为 1；
- Target 和 Numeric Gold 在左右容错边界为 0；
- 正、零、负目标值；
- 非对称 `rL != rU`；
- NaN、infinity、缺失字段、非正衰减宽度和 `L > U` 被拒绝；
- 合法单位换算后分数不变。

### 11.2 聚合

测试必须覆盖：

- 单主约束任务保持原 constraint score；
- 两个主约束使用等权几何平均；
- 任一主约束为 0 时几何平均为 0；
- quality/stability gate 取各自最小值并与 property score 相乘；
- hard gate failure 令候选为 0；
- infrastructure failure 不生成候选零分；
- Property Calculation group 使用最小值；
- Property Calculation 任务使用 group 算术平均；
- incomplete benchmark run 不生成正式 benchmark score。

### 11.3 任务覆盖

自动检查必须证明：

- 四个顶层 task pack 的 33 个 task id 全部有且只有一个迁移定义；
- 每个数值约束都能规范化为 `linear_goal_distance`；
- 每个字符串字段都绑定 exact-match policy；
- 相同 parameter profile 的重复使用不会在 task 文件间漂移；
- calibration 副本与同 id 正式任务引用相同 scoring version 和参数 profile。

## 12. 评分规则摘要

本规格采用一个统一评分内核：

```text
score = clip(1 - normalized_distance_to_full_score_region, 0, 1)
```

各题型的差异只体现在满分区域和有效衰减侧：

- Target：单点满分，左右衰减；
- Window：区间满分，左右衰减；
- Maximize：达到下阈值后满分，只在左侧衰减；
- Minimize：达到上阈值后满分，只在右侧衰减；
- Numeric Gold：gold 为 1，容错范围内线性衰减，容错边界为 0；
- Exact String：精确匹配为 1，否则为 0。

由此可以在不拟合全化学空间性质分布的前提下，为当前所有题目提供形式统一、边界明确、可版本化且可审计的连续评分规则。

## 13. 架构重构目标

### 13.1 当前结构的问题

当前评价职责分散在三个顶层 Python 包中：

| 当前包 | 实际职责 | 问题 |
| --- | --- | --- |
| `src/benchmark` | 答案抽取、评价编排、verifier 子进程、Property Calculation、汇总 | 名称过于宽泛，且与正式公共包并列 |
| `src/verifiers` | open-generation verifier、runtime、result helper、单约束评分 | verifier 同时计算性质和打分，职责耦合 |
| `src/verifier_grounded_benchmark` | registry、task resource、Track/Suite、CLI、公共 facade | 通过 `legacy_*` 调用回到 `benchmark`，不是唯一实现所有者 |
| `src/vgb` | 短包名 re-export | 仅为公共别名，不应承载实现 |

由此产生以下具体问题：

- 一个完整评价流程需要跨三个包追踪；
- answer parsing 同时包含两个主题型的分支；
- verifier backend 既负责化学计算，又直接调用 scoring；
- verifier script 的结果已经包含 constraint score，runner 又有 reuse 重打分路径；
- task schema 校验分散在 loader、evaluator 和 backend；
- Property Calculation 使用独立二元公式，无法复用统一线性内核；
- release builder 必须硬编码多个历史包名和仓库根 task 路径；
- 基础设施失败和候选失败都可能成为数值 0，污染 benchmark mean。

### 13.2 目标

重构后的系统必须达到：

1. `verifier_grounded_benchmark` 是唯一正式 Python 实现包。
2. `evaluation` 拥有从答案解析到 report 生成的完整评价生命周期。
3. `task` 拥有 task schema、资源、registry 和 pack 加载，不包含打分算法。
4. open-generation 和 Property Calculation 作为两个纵向主题型，各自拥有 parsing、scoring 和 evaluator。
5. open-generation 的 concrete verifiers 收归 `evaluation/open_generation/verifiers`。
6. verifier 只返回可验证 evidence，不直接决定 benchmark score。
7. 所有连续数值分数最终调用同一个 `linear_goal_distance` 数学内核。
8. `scripts` 只做维护、校准、验证和发行的离线编排，不复制 task/evaluation 运行时逻辑。
9. `releases` 只保存不可变发行元数据和校验值，不被运行时导入。
10. 公共 `vgb-score`、`load_track`、`load_suite`、`Track`、`Suite` 和 `EvaluationReport` API 保持稳定。

### 13.3 目录解释与约束

本规格保留标准 `src/` layout。用户所说的 benchmark 根模块按以下方式具象化：

- Python package root `src/verifier_grounded_benchmark/` 下包含 `evaluation/` 和 `task/`；
- repository root 下保留 `scripts/` 和 `releases/`；
- `docs/`、`tests/`、`envs/` 和构建配置继续作为支持目录，不属于运行时业务域。

不在仓库根创建可直接 `import evaluation` 或 `import task` 的通用顶层 Python 包，以免发生命名冲突并破坏 wheel 的单包边界。

### 13.4 非目标

本轮架构重构不负责：

- 确定本文所有 `TBD` 评分参数；
- 引入新的化学 verifier 或修改现有计算协议；
- 引入动态 plugin discovery、依赖注入容器或通用工作流框架；
- 用 Pydantic 等新依赖替代当前轻量 schema validation；
- 修改 prompt 的科学任务要求；
- 合并本来具有不同 verifier protocol 的 parameter profiles。

## 14. 目标目录结构

```text
src/
  verifier_grounded_benchmark/
    __init__.py
    track.py
    cli/
      score_answers.py

    evaluation/
      __init__.py
      config.py
      engine.py
      io.py

      common/
        failures.py
        models.py
        results.py
        scoring/
          linear_goal.py
          aggregation.py

      reporting/
        coverage.py
        summary.py

      open_generation/
        evaluator.py

        parsing/
          dispatcher.py
          final_answer_line.py
          final_answer_block.py
          structured_candidates.py

        scoring/
          target.py
          window.py
          maximize.py
          minimize.py
          gates.py
          task_score.py

        verification/
          protocol.py
          evidence.py
          runner.py
          reuse.py

        verifiers/
          common/
            property_cli.py
            result.py
            docker_runtime.py
          rdkit_descriptors/
          rdkit_forcefield/
          xtb/
          admet_ai/
          soltrannet/
          molgpka/
          matgl/
          torchani/
          mace_mp/
          openmm/

      property_calculation/
        evaluator.py

        parsing/
          dispatcher.py
          single_value.py
          multi_property.py

        scoring/
          numeric_gold.py
          exact_string.py
          comparison_group.py
          task_score.py

    task/
      __init__.py
      models.py
      loader.py
      registry.py
      resources.py

      schema/
        common.py
        open_generation.py
        property_calculation.py
        verifier.py

      packs/
        rdkit/
          tasks.yaml
          verifier_specs.yaml
          sample_answers.jsonl
        xtb/
          tasks.yaml
          verifier_specs.yaml
          sample_answers.jsonl
        property_calculation/
          tasks.yaml
          verifier_specs.yaml
          sample_answers.jsonl
        experimental/
          rdkit_forcefield/

      calibration/
        xtb/

  vgb/
    __init__.py

scripts/
  env/
  validation/
  calibration/
  research/
  release/

releases/
  v<version>/
    manifest.json
    task-inventory.json
    scoring-profiles.json
    SHA256SUMS
```

目录中的每个文件必须有明确所有权。不得新增 `utils.py`、`misc.py` 或 `common/helpers.py` 作为无边界代码堆放处；真正共享的功能按 `failures`、`results`、`linear_goal`、`aggregation` 等具体职责命名。

## 15. 模块职责与依赖方向

### 15.1 `task`

`task` 只负责定义和加载“要评价什么”：

- raw YAML/JSONL resource；
- `TaskSpec`、`ConstraintSpec`、`VerifierSpec` 和 `TaskPack` 数据模型；
- open-generation 与 Property Calculation task schema validation；
- scoring parameter schema validation，但不执行评分；
- builtin track registry；
- package resource 定位和加载；
- calibration resource 与 formal pack 的隔离。

所有 task pack 必须在加载时一次性验证。evaluation 不应在每个 answer 上重复发现 `L > U`、缺失 verifier id、非正 decay width 或 requested/gold 字段不一致等静态 task 错误。

### 15.2 `evaluation/common`

`evaluation/common` 只放两个主题型都实际使用的稳定能力：

- failure taxonomy 和 failure scope；
- evaluation/result 数据模型与 JSON serialization；
- `linear_goal_distance`；
- arithmetic mean、geometric mean 和 minimum aggregation；
- finite-number、clamp 等只服务于评分内核的窄辅助函数。

主题型特有的答案 shape、candidate、verifier payload、gold group 不得进入 common。

### 15.3 `evaluation/open_generation`

该主题型负责“模型生成候选对象，由 verifier 重新计算性质”的完整流程：

- 根据 answer schema 抽取 SMILES、XYZ、CIF、number 或 JSON candidate；
- 逐 constraint 调度 property verifier；
- 对同一 verifier evidence 做安全复用；
- 将 verifier properties 与 constraint scoring spec 送入统一评分函数；
- 根据 `role` 聚合 main、quality 和 stability constraint；
- 应用 parse、validity、domain、identity hard gates；
- 返回 task-level evaluation result。

### 15.4 `evaluation/property_calculation`

该主题型负责“模型直接报告固定输入的性质答案，与 gold 比较”：

- 解析 single-value 或 multi-property JSON answer；
- 校验 property name、value type 和 unit；
- 数值字段调用 Numeric Gold 线性公式；
- 字符串字段 exact match；
- `mode: all` group 取成员最小值；
- task score 对 group 做等权算术平均。

该主题型当前不需要 property verifier，不应为了目录对称创建空 verifier layer。

### 15.5 `evaluation/reporting`

Reporting 只负责：

- row normalization；
- task coverage；
- missing、duplicate、unknown task id；
- scored/error/submission-rejected/candidate-rejected 计数；
- task-set mean 和正式 benchmark score；
- `EvaluationReport` serialization。

Reporting 不重新计算 constraint score，也不读取 verifier backend internals。

### 15.6 `track.py` 与公共 facade

Package root 的 `track.py` 是 composition layer：

- 从 `task` 加载和验证 pack；
- 创建 `EvaluationEngine`；
- 提供 `Track`、`Suite`、`prompts()`、`evaluate_one()` 和 `evaluate_answers()`。

`task` 不导入 `evaluation`，`evaluation` 只依赖 `task.models` 中的只读协议或数据模型；`track.py` 同时依赖两者并完成组合，避免循环依赖。

### 15.7 `scripts` 与 `releases`

`scripts` 中的文件必须是 thin entrypoint 或明确的离线编排器：

- 可以解析命令行参数、读取文件和调用公共 API；
- 不得定义 scorer、task loader 或 verifier backend 的第二份实现；
- calibration、research 和 validation script 必须调用正式 task/evaluation API；
- `scripts/release` 可以作为 release artifact assembly 的唯一离线实现，但只能消费 package 暴露的 task/scoring/version metadata，不得重新解释评分规则；
- 可被运行时复用的业务逻辑应先放入正式 package，再由 script 调用。

`releases` 只保存构建结果的 metadata、inventory 和 checksums。运行时 package 不得从 `releases/` 加载 task 或 scoring 参数。

### 15.8 依赖图

下图中 `A -> B` 表示 A 可以 import B：

```text
evaluation open_generation ------> evaluation common
             |                              ^
             +------> task models           |
                                            |
evaluation property_calculation ------------+
             |
             +------> task models

evaluation engine ------> evaluation topics/common/reporting
package track/API ------> task loader/registry + evaluation engine
CLI --------------------> package track/API + evaluation I/O
scripts ----------------> public package APIs
scripts/release --------> releases (write-only artifact output)
```

禁止的依赖包括：

- `task -> evaluation`；
- verifier backend -> task registry/resource loader；
- common -> open_generation/property_calculation；
- package runtime -> `scripts`；
- package runtime -> `releases`；
- Property Calculation -> open-generation verifier；
- concrete verifier -> benchmark task aggregation。

## 16. 主题型内部设计

### 16.1 统一主题型接口

`EvaluationEngine` 使用一个显式、静态的 topic evaluator mapping：

```text
open_generation      -> OpenGenerationEvaluator
property_calculation -> PropertyCalculationEvaluator
```

不引入运行时 plugin discovery。每个 topic evaluator 实现以下逻辑接口：

```python
class TopicEvaluator(Protocol):
    def parse_answer(self, record: AnswerRecord, task: TaskSpec) -> ParsedAnswer: ...
    def evaluate(
        self,
        parsed: ParsedAnswer,
        task: TaskSpec,
        context: EvaluationContext,
    ) -> EvaluationResult: ...
```

`EvaluationContext` 持有经过验证的 verifier specs、scoring profiles、evaluation config 和版本信息。公共 engine 接口为：

```python
class EvaluationEngine:
    def __init__(self, task_pack: TaskPack, config: EvaluationConfig | None = None): ...
    def evaluate_one(self, answer: AnswerRecord) -> EvaluationResult: ...
    def evaluate_many(self, answers: list[AnswerRecord]) -> EvaluationReport: ...
```

`EvaluationEngine` 不接受未验证的任意 task/spec dict；开发模式的自定义路径也必须先通过 `task.loader.load_task_pack(...)` 生成 `TaskPack`。

默认缺失 `task_type` 仅在 legacy task schema v1 中解释为 `open_generation`；新 schema v2 必须显式声明 `task_type`。

### 16.2 Open-generation parsing 小题型

Parsing 只负责从模型输出抽取候选表示，不负责判断化学有效性：

| Parser | 输入 | 输出 |
| --- | --- | --- |
| `structured_candidates` | 已有 `candidates` list | 原样规范化的 candidate records |
| `final_answer_line` | `FINAL ANSWER: <value>` | SMILES、number 或 JSON candidate |
| `final_answer_block` | fenced block | XYZ 或 CIF candidate |

RDKit sanitization、XYZ connectivity、formula、charge、multiplicity 和 stereochemistry 属于 verifier/validation，不属于文本 parser。

### 16.3 Open-generation scoring 小题型

每个作者可读题型只负责转换成第 3 节的 canonical full-score region：

| Scorer adapter | 规范化结果 |
| --- | --- |
| `target` | `L=T, U=T, rL, rU` |
| `window` | `L, U, rL, rU` |
| `maximize` | `L=T, U=null, rL=T-B` |
| `minimize` | `L=null, U=T, rU=B-T` |

四个 adapter 最终都调用：

```text
evaluation.common.scoring.linear_goal.score(value, region)
```

adapter 不得复制 `clip` 或分段线性公式。

### 16.4 Property Calculation parsing 小题型

| Parser | 输入 | 输出 |
| --- | --- | --- |
| `single_value` | `{answer, unit}` | 一个命名或 task-default property answer |
| `multi_property` | `{answers: [...]}` | 按 property name 索引的 answer mapping |
| `final_answer_json` | final line 中的 JSON | 转交 single/multi parser |

Unknown property 可以忽略并记录 diagnostic，但 duplicate requested property 必须是 parse error。缺失 requested property 产生该字段 0 分，不是 infrastructure error。

### 16.5 Property Calculation scoring 小题型

| Scorer | 规则 |
| --- | --- |
| `numeric_gold` | `L=U=gold`，左右 tolerance 为 decay width |
| `exact_string` | normalized exact match 为 1，否则为 0 |
| `comparison_group/all` | group field score 的最小值 |
| `task_score` | group score 的算术平均 |

Numeric Gold 必须调用 common linear kernel。Property Calculation 不得维护第二份三角形公式。

### 16.6 Verifier family

每个 concrete verifier family 继续按计算工具组织，而不是按 task id 组织：

```text
verifiers/<family>/
  backend.py
  cli.py
  <property-entrypoint>.py
  <family-specific helpers>
```

例如 xTB family 包含 gap、dipole、LUMO、polarizability、Fukui、thermo 和 total-energy entrypoints；它们共享 backend/runtime，但每个 `verifier_id` 仍绑定唯一 property entrypoint。

## 17. 端到端评价流程

### 17.1 Task pack 加载

```text
package resource
  -> YAML/JSONL decode
  -> schema version check
  -> topic-specific task validation
  -> verifier spec validation
  -> scoring profile validation
  -> immutable TaskPack
```

任何静态错误必须在 track 加载时失败，不能等到某个 answer 被评价时才发现。

### 17.2 单题评价

```text
answer record
  -> task_id lookup
  -> topic parser
  -> parsed answer
  -> topic evaluator
       open_generation:
         candidate -> verifier evidence -> constraint scores -> gates/aggregation
       property_calculation:
         submitted fields -> gold field scores -> groups/aggregation
  -> EvaluationResult
```

### 17.3 Open-generation verifier 与 scorer 分离

当前 backend 直接调用 `score_constraint`。重构后 verifier 必须只返回 evidence：

```python
class PropertyVerifier(Protocol):
    def verify(
        self,
        candidate: CandidateRecord,
        task: OpenGenerationTaskSpec,
        spec: VerifierSpec,
    ) -> VerificationEvidence: ...
```

subprocess runner 和 in-process test double 都实现同一个逻辑 contract。正式 release 默认使用隔离的 `python_module` subprocess；单元测试可以注入 deterministic fake verifier。

```json
{
  "outcome": "verified",
  "task_id": "...",
  "verifier_id": "...",
  "canonical_candidate": {},
  "properties": {"homo_lumo_gap": 4.2},
  "diagnostics": {},
  "versions": {}
}
```

评分层随后执行：

```text
property value + normalized constraint spec
  -> constraint score
  -> attach property/type/role/profile id
```

这种分离保证：

- 修改评分版本不需要修改化学 backend；
- 同一 evidence 可以按同一 task 的多个 constraint 重新评分；
- raw property 永远可审计；
- verifier script 不再生成局部 task score，避免 runner 二次聚合歧义。

### 17.4 Evidence reuse

Evidence 仅在以下条件全部相同时复用：

- verifier id；
- concrete entrypoint；
- candidate canonical representation；
- verifier protocol/config hash；
- property 已包含在 evidence 中。

复用发生在 scoring 之前。禁止复用旧 constraint score。

### 17.5 批量评价与 coverage

`evaluate_many` 必须：

1. 保留每个输入 row 的结果；
2. 检查 missing、duplicate 和 unknown task id；
3. 区分 candidate zero 与 evaluation failure；
4. 只有 task coverage 完整且不存在未解决 evaluation failure 时生成正式 `benchmark_score`；
5. 对所有可评分 task score 做等权算术平均。

## 18. 数据与结果契约

### 18.1 内部数据模型

建议使用标准库 `dataclass(frozen=True)` 和显式 validator，不新增 schema runtime 依赖。至少定义：

- `TaskPack`；
- `TaskSpec`；
- `OpenGenerationTaskSpec`；
- `PropertyCalculationTaskSpec`；
- `ConstraintSpec`；
- `LinearGoalSpec`；
- `VerifierSpec`；
- `AnswerRecord` / `ParsedAnswer` / `CandidateRecord`；
- `EvaluationContext`；
- `VerificationEvidence`；
- `ConstraintScore`；
- `EvaluationResult`；
- `EvaluationReport`。

外部 JSON/YAML 仍使用普通 mapping；只在 I/O boundary 转换一次。

### 18.2 Verification evidence outcome

```text
verified             verifier 成功并提供 properties
candidate_rejected   候选本身无法通过 validity/domain/identity
evaluation_failed    环境、工具、timeout、schema 或 benchmark 配置失败
```

`candidate_rejected` 产生候选 0 分；known-task 的 answer parse failure 同样是可归因于提交的 0 分；`evaluation_failed` 不产生数值分数，并令正式 run 不完整。

### 18.3 Evaluation result schema v2

```yaml
schema_version: 2
task_id: string
status: scored | error
failure_scope: null | candidate | submission | task | infrastructure
failure_type: null | string
message: null | string
properties: object
scores:
  validity_gate: number | null
  domain_gate: number | null
  identity_gate: number | null
  constraint_scores: list
  property_score: number | null
  geometry_quality_score: number | null
  score: number | null
versions:
  package: string
  task_pack: string
  scoring: string
  result_schema: string
  verifiers: object
```

规则：

- `status: scored` 时 `scores.score` 必须是 `[0,1]` 数值；
- known-task 的 answer parse failure 使用 `status: scored`、`failure_scope: submission`、`score: 0`；
- candidate validity/domain/identity failure 使用 `status: scored`、`failure_scope: candidate`、`score: 0`；
- unknown task id、duplicate id 和无法关联到正式 task 的 submission error 不产生 task score，并令 coverage 无效；
- infrastructure/task/spec failure 使用 `status: error` 且 `score: null`；
- reporting 不得用 `row.get("score") or 0` 将 `null` error 转换为候选零分。

### 18.4 Constraint score provenance

每条 constraint score 至少包含：

```yaml
property: string
type: target | window | maximize | minimize | numeric_gold | exact_string
role: main | quality_gate
value: number | string
score: number
scoring_profile: string
scoring_version: linear_goal_v1
```

### 18.5 Verifier entrypoint

当前 `verification_script: verifiers/.../file.py` 应迁移为安装包稳定的 module entrypoint：

```yaml
executor:
  type: python_module
  module: verifier_grounded_benchmark.evaluation.open_generation.verifiers.xtb.xtb_gap
  timeout_seconds: 120
```

runner 使用：

```text
python -m <module>
```

这样不再依赖仓库 `src/` 物理路径、`script_root` 拼接或 wheel 顶层 `verifiers` 包。

## 19. Task schema v2

### 19.1 Pack 级字段

```yaml
schema_version: 2
task_pack:
  id: xtb
  version: <version>
  scoring_version: linear_goal_v1
scoring_profiles:
  <profile-id>: <profile-definition>
tasks: [...]
```

`scoring_profiles` 是 pack 内评分参数的单一来源。多个 constraint 可以引用同一个 profile；同一个 profile id 不允许在不同文件中出现不同内容。release builder 对规范化后的 profile definition 计算 hash。

### 19.2 Open-generation constraint

作者可读 schema 保留题型语义，不要求 task author 手工填写 canonical infinities。Window profile 示例：

```yaml
scoring_profiles:
  xtb_gap_window_3_5_5_5_v1:
    type: window
    unit: eV
    full_score:
      min: 3.5
      max: 5.5
    decay:
      lower_width: <TBD>
      upper_width: <TBD>

constraints:
  - type: window
    property: homo_lumo_gap
    verifier_id: xtb_gap_gfn2_v1
    role: main
    scoring_profile: xtb_gap_window_3_5_5_5_v1
```

Maximize/Minimize profile 使用：

```yaml
scoring_profiles:
  xtb_gap_max_v1:
    type: maximize
    unit: eV
    full_score_target: <TBD>
    zero_score_anchor: <TBD>

constraints:
  - type: maximize
    property: homo_lumo_gap
    verifier_id: xtb_gap_gfn2_v1
    scoring_profile: xtb_gap_max_v1
```

loader 解析 profile 引用并转换为 `LinearGoalSpec`。constraint type 必须与 profile type 一致，`zero_score_anchor` 必须位于失败侧。

### 19.3 Property Calculation gold

```yaml
scoring_profiles:
  free_energy_numeric_gold_v1:
    type: numeric_gold
    unit: kJ/mol
    lower_tolerance: <TBD>
    upper_tolerance: <TBD>

gold_answers:
  - property: free_energy_difference
    value: 0.258031679
    unit: kJ/mol
    scoring_profile: free_energy_numeric_gold_v1
```

字符串 profile 使用：

```yaml
scoring_profiles:
  exact_phase_string_v1:
    type: exact_string
    normalization: exact

gold_answers:
  - property: ambient_pressure_phase
    value: alpha
    scoring_profile: exact_phase_string_v1
```

旧 `absolute_tolerance` 不得在 schema v2 中继续存在。

## 20. 当前文件到目标文件的迁移

| 当前路径 | 目标路径/职责 |
| --- | --- |
| `src/benchmark/answer_extraction.py` | 拆到两个主题型的 `parsing/` |
| `src/benchmark/evaluate.py` | `evaluation/engine.py`、`open_generation/evaluator.py`、`reporting/*` |
| `src/benchmark/property_calculation.py` | `evaluation/property_calculation/{evaluator,parsing,scoring}` |
| `src/benchmark/verifier_scripts.py` | `evaluation/open_generation/verification/runner.py` |
| `src/verifiers/common/scoring.py` | `evaluation/common/scoring/linear_goal.py` 加 topic adapters |
| `src/verifiers/common/result_schema.py` | `evaluation/common/results.py` 与 `verification/evidence.py` |
| `src/verifiers/common/property_cli.py` | `evaluation/open_generation/verifiers/common/property_cli.py` |
| `src/verifiers/common/docker_model_runtime.py` | `evaluation/open_generation/verifiers/common/docker_runtime.py` |
| `src/verifiers/<family>` | `evaluation/open_generation/verifiers/<family>` |
| `src/verifier_grounded_benchmark/evaluator.py` | 被 `evaluation/engine.py` 取代，public re-export 保持 |
| `src/verifier_grounded_benchmark/io.py` | task/spec I/O 进入 `task/loader.py`；answer JSONL/report serialization 进入 `evaluation/io.py` |
| `src/verifier_grounded_benchmark/registry.py` | `task/registry.py` |
| `src/verifier_grounded_benchmark/resources.py` | `task/resources.py` |
| `tasks/<pack>` | `src/verifier_grounded_benchmark/task/packs/<pack>` |
| `tasks/xtb_xyz/expert_calibration` | `task/calibration/xtb`，默认不打入正式 wheel |
| `src/verifier_grounded_benchmark/track.py` | 保留 package-root composition layer，改用新 task/evaluation API |
| `src/vgb/__init__.py` | 保留短别名，只 re-export public API |

迁移完成后删除 `src/benchmark` 和 `src/verifiers`。不得长期保留两套真实实现。

## 21. Public API 与兼容策略

### 21.1 保持稳定

以下调用保持可用：

```python
import verifier_grounded_benchmark as vgb

vgb.list_tracks()
vgb.load_track("rdkit")
vgb.load_suite()
vgb.Evaluator(...)
track.tasks()
track.prompts()
track.evaluate_one(answer)
track.evaluate_answers(answers)
```

`vgb-score --track ... --answers ...` 命令名和基本参数保持不变。

`vgb.Evaluator(tasks, verifier_specs, config=...)` 在兼容周期内由 wrapper 将 legacy mappings 送入 task schema validator，再创建 `EvaluationEngine`。新代码应直接使用 `EvaluationEngine(TaskPack, config=...)`；legacy constructor 与旧内部包同时在后续版本删除。

### 21.2 新的正式导入

```python
from verifier_grounded_benchmark.evaluation import (
    EvaluationConfig,
    EvaluationEngine,
    EvaluationReport,
)
from verifier_grounded_benchmark.task import (
    Registry,
    TaskPack,
    TaskSpec,
    VerifierSpec,
)
```

### 21.3 历史内部包

`benchmark.*` 和 `verifiers.*` 没有出现在当前正式 README 的公共 API 中，但仓库脚本和测试大量使用。迁移采用一个短兼容周期：

1. 首个迁移提交建立新实现，并让旧模块成为带 deprecation warning 的薄 re-export；
2. 仓库内代码、tests、task verifier entrypoints 和 docs 全部改为新路径；
3. wheel smoke test 证明不再需要旧路径；
4. 发布新的 package/scoring version 后删除旧包。

兼容 shim 不得包含逻辑，也不得跨两个正式 release 长期存在。

## 22. Packaging 与 release

### 22.1 Wheel 内容

迁移完成后 `pyproject.toml` 的正式 package 只需要：

```text
src/verifier_grounded_benchmark
src/vgb
```

Task packs 作为 `verifier_grounded_benchmark.task.packs` package data 发布。使用 `importlib.resources` 定位，不再通过向上搜索仓库根的 `tasks/` 目录工作。只有 registry 标记为 formal 的 packs 和其 sample answers 进入正式 wheel；`task/calibration` 和 `task/packs/experimental` 默认由 build exclusion 排除，除非某个 release 显式提升其状态。

### 22.2 Release manifest

每个 release 必须冻结并记录：

- source commit/tree；
- package version；
- result schema version；
- scoring version；
- 每个 task pack hash；
- 每个 scoring profile id 和 hash；
- verifier spec/protocol hash；
- wheel/sdist payload digest；
- task inventory。

`scoring-profiles.json` 至少列出每个 profile 的 full-score region、decay widths、unit 和 provenance hash。

### 22.3 版本规则

- 仅移动内部模块且结果 bitwise 相同：package minor/patch 按项目策略决定，scoring version 不变；
- 修改 constraint 公式或参数：必须升级 scoring version；
- 修改 result JSON contract：必须升级 result schema version；
- 修改 task 集合或 prompt/constraint 语义：必须升级 task pack version；
- 修改 verifier protocol、model 或计算参数：必须升级 verifier spec/version。

## 23. 分阶段迁移计划

重构不得采用一次性大搬迁。每个阶段均应保持 `main` 可运行，并形成独立、可回滚的提交。

### Phase 0：冻结基线

- 保存当前 33 个 task id、sample result shape 和 release payload inventory；
- 运行并记录全量测试；
- 增加 import graph 和 legacy path inventory；
- 冻结现有 scoring 与新 shadow scoring 的对照 fixtures。

### Phase 1：建立 common scoring kernel

- 新建 `evaluation/common/scoring/linear_goal.py`；
- 实现第 3-4 节公式和边界测试；
- 新增 aggregation；
- 不改变正式 task score。

### Phase 2：建立 `task` 域

- 新建 models、schema、loader、registry 和 resources；
- 迁移 pack resources；
- 使用 `importlib.resources`；
- 保持 `Track` 公共行为不变；
- 更新 packaging/release inventory。

### Phase 3：迁移 Property Calculation

- 拆分 parsing 和 scoring；
- 接入 Numeric Gold 线性评分；
- comparison group 改为 minimum；
- 引入 result schema v2 的 failure scope；
- 更新 task pack scoring version。

### Phase 4：迁移 open-generation orchestration

- 建立 parser dispatcher；
- 建立 verification evidence/runner；
- 将 verifier evidence 与 scoring 分离；
- 实现 main/gate/task aggregation；
- 修复 infrastructure failure 不得分语义。

### Phase 5：移动 concrete verifiers

- 按 family 逐个移动；
- verification specs 改用 `python_module` entrypoint；
- 每移动一个 family，先运行该 family tests 和 installed-wheel smoke；
- 更新 env scripts 和 calibration scripts 的正式导入。

### Phase 6：切换公共 facade 和 CLI

- `Evaluator` 改为新 engine；
- `Track/Suite` 改用新 task resources；
- `vgb-score` 改用新 reporting；
- 加入 legacy thin re-exports 和 warning。

### Phase 7：版本化发布与清理

- 完成新评分参数审核；
- 发布 task/scoring/result schema 新版本；
- 验证 wheel/sdist 内容一致；
- 删除 legacy `benchmark`、`verifiers` 和旧根 `tasks`；
- 删除只为旧路径服务的 test helper 和 release branches。

## 24. 测试结构与架构验收

### 24.1 目标测试目录

```text
tests/
  evaluation/
    common/scoring/
    open_generation/parsing/
    open_generation/scoring/
    open_generation/verification/
    open_generation/verifiers/
    property_calculation/parsing/
    property_calculation/scoring/
    reporting/
  task/
    schema/
    loader/
    registry/
  integration/
    tracks/
    cli/
    installed_wheel/
  release/
```

### 24.2 必须通过的行为验收

除第 11 节评分验收外，还必须满足：

- 两个 topic 的 parser/evaluator 通过同一 engine dispatch；
- verifier evidence 不包含 benchmark score；
- concrete backend 不导入 task aggregation 或 scoring adapter；
- known-task parse/candidate failure 产生 0，infrastructure failure 产生 `score: null`；
- evidence reuse 不复用 constraint score；
- task schema 错误在 pack load 阶段失败；
- 33 个现有 task id 全部迁移；
- calibration duplicate 与正式 task 引用同一 scoring profile；
- public `Track/Suite` 和 CLI smoke 通过；
- wheel 中可以通过 module entrypoint 执行 verifier；
- wheel/sdist resource payload 一致；
- release manifest 包含 scoring profile hashes。

### 24.3 必须通过的结构验收

```text
rg "from benchmark|import benchmark|from verifiers|import verifiers" src tests scripts
```

在 legacy shim 删除阶段必须无匹配。另需验证：

- `src/benchmark` 不存在；
- `src/verifiers` 不存在；
- package runtime 不导入 `scripts` 或 `releases`；
- `task` 不导入 `evaluation`；
- `evaluation/common` 不导入任一 topic；
- verifier specs 不再包含仓库相对 `.py` 路径。

### 24.4 每阶段验证命令

每个实现阶段至少运行：

```text
uv run pytest <affected focused tests> -q
uv run pytest
uv build
installed-wheel smoke test
git diff --check
```

只修改文档的阶段无需构建 wheel，但必须运行全量测试并确认 task coverage inventory。

## 25. 最终架构决策摘要

1. 保留 `src/` layout，不创建通用顶层 `evaluation`/`task` import package。
2. `verifier_grounded_benchmark` 成为唯一正式实现包。
3. `evaluation` 是完整评价系统，按 common、open-generation、Property Calculation 和 reporting 划分。
4. topic 采用纵向切片；每个 topic 内再按 parsing、scoring、verification 和小题型组织。
5. concrete verifiers 归属 open-generation，但 verifier 只产出 evidence，不计算 benchmark score。
6. `task` 负责 schema、pack、registry 和 resources，不拥有 evaluator。
7. 所有连续数值打分统一调用 `linear_goal_distance`。
8. Property Calculation 的 numeric gold 是 common kernel 的 target 特例，容错边界为 0 分。
9. 候选失败与基础设施失败分离，后者不再污染平均分。
10. `scripts` 是薄入口，`releases` 是不可变输出。
11. 公共 API 和 CLI 保持，历史内部包短期 shim 后删除。
12. 迁移按 scoring、task、topic evaluator、verifier、facade、release 分阶段完成，禁止 big-bang rewrite。
