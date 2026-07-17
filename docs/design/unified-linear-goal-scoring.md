# 统一线性目标评分规格

日期：2026-07-17  
状态：设计规格草案，参数待定，尚未替换正式评分实现

## 1. 目的

本文规定 verifier-grounded benchmark 的统一连续评分方式。所有可连续评分的数值约束都转换为：

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

### 5.3 Stability gate

`xtb_hessian_thermo_stability_013` 的 `imaginary_frequency_count` 使用 `role: stability_gate`。它是定义域为非负整数的 Window 约束：

```text
L = 0
U = 0
right decay width = rU_stability
```

由于计数不可能小于 0，左侧不激活。其分数为：

```text
s_stability(n) = clip(1 - n / rU_stability, 0, 1)
```

同一道题有多个 stability gate 时：

```text
stability_gate_score = min(s_1, ..., s_n)
```

## 6. 多约束与 benchmark 聚合

### 6.1 Open-generation 单题

当前 open-generation 任务继续使用等权几何平均聚合所有 `role: main` 的约束：

```text
property_score = geometric_mean(main_constraint_scores)
```

若任一主约束为 0，则 `property_score = 0`。quality gate 和 stability gate 不进入几何平均，而是分别取最小值后作为乘法 gate：

```text
task_score = hard_gate
           * property_score
           * quality_gate_score
           * stability_gate_score
```

没有某类 gate 时，该 gate 分数默认为 1。

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

## 12. 最终决策摘要

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
