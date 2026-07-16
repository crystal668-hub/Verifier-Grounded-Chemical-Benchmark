# 基于验证不确定度的概率约束满足评分研究

日期：2026-07-16

状态：研究结论与迁移建议；本文不修改正式评分实现或 task pack

## 摘要

本文研究一种比当前 `window`、`maximize_bounded` 和
`minimize_bounded` 更容易解释的通用评分框架：把单题分数定义为
“候选满足任务成功事件的条件概率”。核心形式是：

```text
score(x) = hard_gate(x) * P(A_t(x) | verifier evidence)
```

其中 `A_t(x)` 是任务 `t` 对候选 `x` 定义的成功事件，例如性质落入窗口、
候选可靠地优于冻结基线、几何弛豫能低于质量门，或者固定分子构象比参考构象
能量更低。概率分布建模的是 verifier 误差、方法偏差或协议扰动，而不是假设
“性质在所有化学空间中服从正态分布”。

主要结论如下：

1. 对已经声明数值窗口的正式题 001、002 和 007，可以直接使用高斯区间概率；
   题面窗口保持不变，原先窗口外指数衰减使用的 `sigma` 被可验证的不确定度替代。
2. 对只声明“最大化”或“最小化”的题，单个性质值本身不能定义绝对成功事件。
   要获得严格概率语义，必须把评分事件改为“相对冻结基线取得至少
   `delta` 的可靠改善”。这适用于 003-006、008-016。
3. 多目标题不能把边际概率随意做几何平均后称为联合成功概率。已知协方差时应
   计算多元正态矩形或正交区域概率；未知依赖结构时应报告 Fréchet 下界，或使用
   JCGM 推荐的分布传播 Monte Carlo。
4. 001-013 的 relaxation-energy quality gate 可以保留 `0.35 eV` 作为有热力学
   解释的成功边界，再把线性乘子改成 `P(R <= 0.35 eV)`。在 298.15 K 下，
   `0.35 eV` 约为 `13.62 k_B T`，相对 Boltzmann 权重约 `1.2e-6`。
5. 017 和 018 应使用同一分子固定参考构象的能量优越概率，并同时报告
   Boltzmann-like 相对能量分数。当前 `0.05 Eh` 的线性评分宽度约为
   `52.96 k_B T`，不适合作为热力学意义上的连续尺度。
6. 该方案的数学严谨性是有条件的：只有当不确定度模型经过留出数据校准时，
   输出才能解释为概率。若 xTB 被定义为完全确定的 benchmark oracle，且不引入
   方法误差或协议扰动，则不确定度趋近于零，概率分数必然退化成硬通过/失败。
   任何平滑的部分分都仍然需要一个科学容差或最小有意义改善尺度。
7. 若 18 道题等权，单题成功概率的算术平均恰好是“成功题目占比”的条件期望；
   这一解释只依赖期望的线性性，不要求题目之间相互独立。题间相关性只会影响总分
   的方差和置信区间。

因此，本文不建议把现有全部分数机械替换成一个正态 CDF。推荐的迁移对象是一个
统一的事件概率接口，下设三种有不同科学语义的 primitive：

```text
probabilistic_interval       # 已声明窗口或阈值
probabilistic_superiority    # 开放式最大化/最小化
relative_conformer_energy    # 固定分子构象能量
```

## 1. 问题与范围

### 1.1 当前评分方式

当前共享评分实现位于
[`src/verifiers/common/scoring.py`](../../src/verifiers/common/scoring.py)，包含：

```text
window:
    1                                      if L <= y <= U
    exp(-distance(y, [L, U]) / sigma)      otherwise

maximize_bounded:
    clamp((y - lower) / (upper - lower), 0, 1)

minimize_bounded:
    clamp((upper - y) / (upper - lower), 0, 1)
```

18 道正式 xTB 题定义在
[`tasks/xtb_xyz/tasks.yaml`](../../tasks/xtb_xyz/tasks.yaml)。其中：

- 001、002 是单性质窗口题；
- 003-005、008、010、011、014-016 是单向优化题；
- 006、009、012、013 是多目标或目标加门控题；
- 007 是双窗口题；
- 017、018 是固定分子构象能量题；
- 001-013 还包含 relaxation-energy quality gate；
- 013 还包含 imaginary-frequency stability gate。

当前 `lower`、`upper`、`sigma` 同时承担三种互相不同的职责：

1. 描述题目真正要求；
2. 决定何处开始给部分分；
3. 人为控制题目难度和分数梯度。

后两种职责使阈值很容易随少量 calibration controls 调整，且难以说明一个单位的
性质改善为何应该对应某个固定分数增量。

### 1.2 本文解决与不解决的问题

本文解决：

- 如何把明确的性质约束转换成可解释的 `[0, 1]` 分数；
- 如何让连续部分分来自 verifier uncertainty，而不是性质总体分布；
- 如何处理相关的多性质目标；
- 如何逐题迁移当前正式 xTB 任务；
- 如何验证概率分数是否真的校准。

本文不解决：

- xTB surrogate 是否等同实验性质；
- 如何为完全没有目标、阈值或基线的开放优化问题凭空定义绝对效用；
- 如何用一个不分元素、分子大小和电子态的误差模型覆盖全部化学空间；
- 如何通过评分函数本身修复 verifier 的适用域外推问题。

## 2. 为什么不应假设性质总体正态

### 2.1 “所有化学空间”没有自然概率测度

要声明随机变量 `Y` 服从某个分布，必须先定义如何从化学空间抽样。对分子而言，
不存在天然的“均匀抽一个分子”：按分子式、重原子数、数据库记录、构象、材料晶胞
或合成可及分子加权，会得到完全不同的总体。因此，写成

```text
Y_property ~ Normal(mu, sigma^2)
```

并没有消除总体选择，只是把它隐藏在 `mu` 和 `sigma` 的来源中。

### 2.2 现有 xTB 数据明确不支持总体正态

本文使用 SciPy `1.17.1` 对 2026-06-22 formal Expanded Run 的
`light_results.json`、`medium_results.json` 和 `expensive_results.json`
进行了 D'Agostino-Pearson 正态性检查。下表是诊断结果；大样本下 p-value 会对细小
偏差敏感，因此同时给出偏度和超额峰度作为 effect size。

| Property | N | Skewness | Excess kurtosis | Normal-test p-value |
| --- | ---: | ---: | ---: | ---: |
| `homo_lumo_gap` | 10,000 | 1.876 | 3.594 | `< 1e-300` |
| `dipole_moment` | 10,000 | 1.095 | 2.494 | `< 1e-300` |
| `lumo_energy` | 10,000 | 1.780 | 3.174 | `< 1e-300` |
| `polarizability_per_heavy_atom` | 10,000 | -0.146 | 1.785 | `4.0e-97` |
| `relaxation_energy` | 10,000 | 11.990 | 359.805 | `< 1e-300` |
| `alpb_water_hexane_selectivity` | 2,000 | 0.488 | 0.579 | `2.9e-20` |
| `global_electrophilicity` | 1,999 | 0.191 | -0.838 | `1.8e-46` |
| `imaginary_frequency_count` | 500 | 5.510 | 28.364 | `3.7e-122` |
| `entropy_298_per_heavy_atom` | 500 | 0.093 | -0.985 | `5.1e-21` |

此外，现有报告已经记录明显的 source shift：QM9、QMugs 和 GEOM-Drugs 的 gap
中位数分别为 `4.500`、`2.786` 和 `2.889 eV`，entropy/heavy-atom 中位数分别为
`47.205`、`32.756` 和 `30.747 J mol-1 K-1`。详见
[`2026-06-15-xtb-real-dataset-property-distributions.md`](2026-06-15-xtb-real-dataset-property-distributions.md#2026-06-22-formal-expanded-run-results)。

### 2.3 正态假设应放在误差模型，而不是性质总体

性质总体可以偏斜、截断、离散或多峰，但同一候选在固定协议下的数值误差、方法残差
或小扰动响应可能近似正态。后者是有限、可重复测量和可做覆盖率检验的对象。因此
本文使用：

```text
latent property conditional on verifier evidence ~ calibrated error model
```

而不使用：

```text
property over all molecules ~ universal normal distribution
```

## 3. 评分对象与不确定度声明

### 3.1 两种可能的 benchmark claim

在构建概率分数之前，必须选择分数究竟针对什么“真值”。

#### Claim A：fixed-xTB surrogate

`theta(x)` 定义为候选在冻结 xTB 版本、电子态、优化协议和解析器下的协议性质。
这是当前 benchmark 文档实际支持的解释。此时：

- 不包含 xTB 相对实验或高等级量化方法的模型误差；
- 不确定度只来自数值协议、平台差异和明确规定的坐标/构象扰动；
- 若协议完全确定且无扰动，方差接近零，分数趋向硬判定。

#### Claim B：scientific property estimate

`theta(x)` 定义为实验或更高等级电子结构方法下的性质。此时必须使用 paired
reference calculations 或实验数据估计 xTB bias 和 method discrepancy。该 claim
更接近科学真实性，但需要按性质、元素空间、电子态和结构类别验证，不能直接从
GFN2-xTB 的一般方法名称推断。

本文建议首版保持 Claim A，以免悄然改变 benchmark 的研究主张；同时在结果 schema
中保留 `claim_target`，允许未来经单独验证后引入 Claim B。

### 3.2 标量测量模型

对候选 `x` 的性质，设第 `r` 次 verifier 结果为：

```text
Y_r(x) = theta(x) + b_t + epsilon_r(x)
epsilon_r(x) ~ Normal(0, sigma_protocol,t^2)
```

其中：

- `theta(x)`：声明目标下的 latent property；
- `b_t`：任务/性质对应的已估计系统偏差；
- `epsilon_r`：重复协议或受控扰动产生的随机残差；
- `t`：任务或 verifier profile，而不是整个化学空间。

若对候选运行 `K` 次，并令 `Y_bar` 为均值，则偏差校正后的中心为：

```text
m(x) = Y_bar(x) - b_t
```

需要把不会随重复次数消失的方法差异与可平均的协议噪声分开：

```text
sigma_total^2 = sigma_method^2 + sigma_protocol^2 / K
```

于是采用条件分布：

```text
theta(x) | D_x ~ Normal(m(x), sigma_total^2)
```

如果保持 Claim A，则 `sigma_method = 0`；如果使用 Claim B，则
`sigma_method` 必须由独立 paired reference residuals 估计，不能通过重复运行 xTB
把它除以 `K`。

### 3.3 向量测量模型

对 gap、dipole、relaxation energy 等共同计算或共同受几何影响的性质，独立假设通常
不成立。设性质向量为 `theta in R^d`：

```text
theta(x) | D_x ~ MVN(m(x), Sigma_total)

Sigma_total = Sigma_method + Sigma_protocol / K
```

协方差必须与边际标准差一起冻结。只保存每个性质的 `sigma` 而丢弃相关性，会使
多目标联合成功率产生系统误差。

## 4. 概率评分的统一推导

### 4.1 从二元科学效用推导分数

令 `A_t(x)` 表示候选满足任务的事件，定义二元效用：

```text
U_t(x) = 1  if A_t(x) is true
         0  otherwise
```

给定 verifier evidence `D_x`，候选的条件期望效用为：

```text
E[U_t(x) | D_x] = P(A_t(x) | D_x)
```

因此把分数定义成满足概率，不是任意的 CDF 映射，而是二元成功效用下的 Bayes
expected utility。

该概率还具有 properness。设真实事件指标为 `I_A`，报告值为 `q`，真实条件概率为
`p = P(A | D)`。条件 Brier loss 为：

```text
E[(q - I_A)^2 | D]
    = q^2 - 2qp + p
    = (q - p)^2 + p(1 - p)
```

它在且仅在 `q = p` 时最小。因此，只要后续能观察或构造留出 reference event，
诚实报告校准概率是唯一最优策略。

### 4.2 从单题概率到 benchmark 总分

设共有 `T` 道题，`D` 表示本次评测的全部 verifier evidence。把 hard gate 一并
计入第 `t` 题的最终成功指标：

```text
Z_t = G_t * 1[A_t]
q_t = E[Z_t | D] = G_t * P(A_t | D)
```

其中 `G_t` 在给定 evidence 后是确定的 `0/1` 值。定义真实成功题目占比：

```text
F = (1/T) * sum[t=1..T] Z_t
```

由条件期望的线性性：

```text
E[F | D]
  = E[(1/T) * sum[t=1..T] Z_t | D]
  = (1/T) * sum[t=1..T] E[Z_t | D]
  = (1/T) * sum[t=1..T] q_t
```

所以 18 道正式题等权时，benchmark 分数可定义为：

```text
score_benchmark = (1/18) * sum[t=1..18] q_t
```

它严格等于“该提交在 18 道题中成功比例”的后验/条件期望。这个等式不要求
`Z_1, ..., Z_T` 独立；独立性只在计算总分不确定度时才重要：

```text
Var(F | D)
  = (1/T^2) * [sum_t Var(Z_t | D)
               + 2 * sum_{s<t} Cov(Z_s, Z_t | D)]
```

同理，没有题间独立证据时，不能把 `product(q_t)` 解释成“全部题目都成功”的概率。
若未来需要非等权总分，预先冻结 `w_t >= 0` 且 `sum_t w_t = 1`，则
`sum_t w_t*q_t` 是加权二元效用 `sum_t w_t*Z_t` 的条件期望；权重本身仍是 benchmark
政策，不能从概率论自动推出。

这里的算术平均用于**题与题之间**。一道多约束题内部要求“同时满足”时，仍必须
计算约束交集的联合概率，不能把各约束概率做算术平均或几何平均。若某题发生
infrastructure measurement failure，本次 run 应标为不完整并重试，不能把该题静默
从分母删除或当成候选零分。

### 4.3 一侧阈值事件

若 `theta | D ~ Normal(m, sigma^2)`，最大化题被改写为成功事件
`theta >= T`：

```text
q_ge
  = P(theta >= T | D)
  = integral[T, +inf] Normal(theta; m, sigma^2) dtheta
  = 1 - Phi((T - m) / sigma)
  = Phi((m - T) / sigma)
```

最小化题的事件 `theta <= T` 为：

```text
q_le = Phi((T - m) / sigma)
```

其中 `Phi` 是标准正态 CDF。两者都在 `[0, 1]` 内，并且：

```text
d q_ge / d m = phi((m - T) / sigma) / sigma > 0
d q_le / d m = -phi((T - m) / sigma) / sigma < 0
```

所以最大化/最小化方向严格正确。

### 4.4 区间事件

对窗口 `[L, U]`：

```text
q_interval
  = P(L <= theta <= U | D)
  = Phi((U - m) / sigma) - Phi((L - m) / sigma)
```

其导数为：

```text
d q_interval / d m
  = [phi((L - m) / sigma) - phi((U - m) / sigma)] / sigma
```

因此分数在窗口中点之前增加、之后减少，并在对称误差模型下于中点达到最大。

当 `sigma -> 0+` 时：

```text
q_interval -> 1[L < m < U]
q_ge       -> 1[m > T]
q_le       -> 1[m < T]
```

边界处趋向 `0.5`。这说明概率方案自然包含确定性 verifier 的硬判定作为极限情况。

### 4.5 单位变换不变性与无锚评分不可能性

对合法的线性单位变换：

```text
y' = a*y + c,  a > 0
T' = a*T + c
sigma' = a*sigma
```

有：

```text
(m' - T') / sigma' = (m - T) / sigma
```

窗口的两个标准化边界同样不变。因此概率分数不依赖使用 eV、Hartree、kJ/mol
还是 kcal/mol，只要数值、边界和不确定度被一致转换。

这也说明为什么不能再进一步删除所有 threshold、baseline 和 scale，直接寻找一个
仅依赖性质值 `y` 的“无参数通用分数”。设存在函数 `f: R -> [0, 1]`，并要求它在
任意合法的正仿射单位变换后不变：

```text
f(a*y + c) = f(y)    for every y, c in R and every a > 0
```

任取两个数 `u, v in R`，令 `a=1`、`c=v-u`，则：

```text
f(v) = f(1*u + v-u) = f(u)
```

由于 `u`、`v` 任意，`f` 只能是常数。故：

```text
无锚点 + 无尺度 + 仿射不变  =>  只能得到无区分度的常数分数
```

任何非恒定且单位一致的评分，都必须至少引入会随单位共同变换的位置锚点
（`T`、`[L,U]` 或 baseline）和尺度（不确定度、容差或 `delta`），或者先构造有
物理定义的无量纲量。概率方案并没有声称“完全无参数”；它把不可避免的参数变成
有明确语义、可校准和可版本化的量。这一结论也证明，给所有性质值直接套同一个
标准正态 CDF 并不能成为通用评分：改变单位或零点就会改变分数。

### 4.6 相对冻结基线的优越概率

当前很多正式题只说“maximize”或“minimize”，并未给出成功阈值。对于这类题，
不能从一个性质值推导绝对满足概率。最小的额外语义是指定一个冻结、公开、同域的
baseline `B_t`，并定义“至少改善 `delta_t`”为成功。

设候选与基线的 latent properties 联合正态：

```text
theta_c ~ Normal(m_c, v_c)
theta_b ~ Normal(m_b, v_b)
Cov(theta_c, theta_b) = c_cb
```

差值：

```text
Delta = theta_c - theta_b
Delta ~ Normal(m_c - m_b, v_c + v_b - 2*c_cb)
v_delta = v_c + v_b - 2*c_cb
```

最大化任务的可靠改善事件 `Delta >= delta`：

```text
q_superior_max
  = Phi((m_c - m_b - delta) / sqrt(v_delta))
```

最小化任务的事件 `theta_b - theta_c >= delta`：

```text
q_superior_min
  = Phi((m_b - m_c - delta) / sqrt(v_delta))
```

`delta = 0` 表示“可靠地优于基线”；`delta > 0` 表示“达到最小有意义改善”。
`delta` 不能为了让 leaderboard 好看而调整，必须来自方法分辨率、科学最小效应或
任务声明。若无证据支持非零 `delta`，首版应使用零并公开这一点。

### 4.7 多目标联合事件

所有当前连续约束都可以写成线性不等式：

```text
A * theta <= c
```

例如区间 `L <= theta_j <= U` 可写成：

```text
[ 1] * theta_j <= [ U]
[-1]             [-L]
```

若 `theta ~ MVN(m, Sigma)`，则：

```text
A*theta ~ MVN(A*m, A*Sigma*A^T)
```

联合满足概率为对应多元正态矩形/正交区域概率：

```text
q_joint = P(A*theta <= c | D)
```

这可以用稳定的 multivariate-normal CDF 或 Monte Carlo 计算。只有当相关矩阵经过
验证为对角矩阵时，才有：

```text
q_joint = product(q_j)
```

当前几何平均：

```text
(product(q_j))^(1/d)
```

不是联合概率。例如两个边际概率分别为 `0.8` 和 `0.7` 时，联合事件概率不可能
超过 `min(0.8, 0.7) = 0.7`，但几何平均为 `0.748`。

若暂时没有协方差，任意依赖结构下都有 Fréchet bounds：

```text
max(0, sum(q_j) - (d - 1))
    <= P(intersection_j A_j)
    <= min(q_j)
```

正式分数可以保守地使用下界，同时报告上界；更推荐根据 JCGM 101/102 使用联合
residual 或 Monte Carlo 传播，避免长期以过宽区间代替实际联合概率。

### 4.8 hard gates 与测量失败

定义：

```text
G(x) = G_parse * G_validity * G_domain * G_identity
```

每项取 `0` 或 `1`。最终分数：

```text
score(x) = G(x) * q_joint(x)
```

候选导致的 parse、validity、domain、formula、charge、multiplicity 或 identity failure
令 `G=0`。

环境缺失、verifier timeout、工具崩溃和结果 schema 错误不是候选失败。严谨的评测
应将其标记为 `measurement_failed` 并重试；达到重试上限后整次 run 应报告不完整，
而不是把基础设施错误混入模型的零分。这一点不同于当前 evaluator 将所有 error row
按 0 计入均值的行为。

## 5. 不确定度从哪里来

### 5.1 不能用性质总体标准差代替 verifier uncertainty

`sigma` 应描述“给定该候选和该协议，我们对 latent property 有多不确定”，而不是
“不同分子的性质有多分散”。后者会再次引入样本种类问题，并把化学多样性错误地
解释为测量误差。

### 5.2 推荐的 uncertainty budget

每个 verifier profile 至少拆分：

```text
Sigma_total
  = Sigma_method_discrepancy
  + Sigma_platform
  + Sigma_protocol / K
  + Sigma_input_representation
```

- `Sigma_method_discrepancy`：仅 Claim B 使用，由 xTB 与更高等级 reference 的
  paired residuals 估计，重复 xTB 不会消除它；
- `Sigma_platform`：不同受支持平台、BLAS/编译和 xTB patch 版本差异；
- `Sigma_protocol`：SCF/优化重复、收敛路径和明确规定的 perturbation protocol；
- `Sigma_input_representation`：坐标有效位数、等价 atom ordering 等表示扰动；
- `K`：可平均的重复次数。

对 Claim A，如果冻结协议在支持平台上严格确定，则前三项可能接近零。此时输出
退化成硬判定是正确结果。若仍希望连续部分分，必须另行声明 `semantic_tolerance`
或最小有意义改善 `delta`；不能把人为 softness 伪装成测量不确定度。

### 5.3 正态残差的验证

使用正态模型前，应在独立 calibration/audit split 上检查：

- bias 是否在声明范围内稳定；
- standardized residual 的 Q-Q 图和尾部覆盖；
- 50%、80%、90%、95% predictive intervals 的实际 coverage；
- 不同元素组合、电子态、原子数和性质区间的 conditional coverage；
- 多性质 residual covariance 是否稳定；
- platform 与 xTB patch version 的方差贡献。

仅通过 Shapiro-Wilk 或 D'Agostino p-value 不能证明正态；大样本下应以 coverage、
尾部和 decision-region 附近的误差为主。

### 5.4 非正态回退

若残差有重尾或样本量较小：

1. 标量方差由少量重复估计时，使用 Student-t predictive CDF；
2. 有 paired residuals 时，从冻结 residual bank 重采样；
3. 多目标或非线性 workflow 使用 JCGM 101 Monte Carlo 传播；
4. 报告 Monte Carlo standard error，并固定随机种子和样本数；
5. 不允许在运行时根据候选分数临时选择最有利的误差族。

这些回退仍然只需要误差/残差样本，不要求性质在整个化学空间中的代表性分布。
但是 Claim B 的 method discrepancy 仍需覆盖 verifier 声明适用域；评分函数无法消除
模型适用域问题。

## 6. 几何质量门和稳定性门

### 6.1 relaxation energy 的热力学边界

当前实现定义：

```text
R = max(0, (E_input - E_optimized) * 27.211386245988)  # eV
```

并以 `0.35 eV` 为 quality gate。该值虽然不是普适常数，但可以从一个明确的
“可忽略相对构象权重”政策推导。设希望高于局部最低点 `R` 的构象相对权重不低于
`w_min` 才算可接受：

```text
w = exp(-R / (k_B*T))
R_max = -k_B*T*ln(w_min)
```

在 `T=298.15 K`、`w_min=1e-6` 时，使用 CODATA Boltzmann constant：

```text
k_B*T = 0.0256926 eV
R_max = 0.354956 eV
```

因此当前 `0.35 eV` 对应约 `1.2e-6` 的相对权重。`w_min=1e-6` 仍是 benchmark
policy，但它比“线性分数在 0.35 归零”更可解释、可审查。

概率质量分数为：

```text
q_geometry = P(R <= R_max | D)
           = Phi((R_max - m_R) / sigma_R)
```

它表达“几何是否可接受”，不会在所有远低于边界的合理几何之间制造额外线性偏好。

### 6.2 与主性质的组合

优先把 `R <= R_max` 与主性质事件一起放入联合向量，计算：

```text
q_task = P(A_property and R <= R_max | D)
```

只有验证残差独立时，才可写成：

```text
q_task = q_property * q_geometry
```

这比当前无条件乘法更严格，因为 rough geometry 可能同时改变 gap、dipole 和
relaxation energy，相关性通常不应先验设为零。

### 6.3 imaginary frequencies

`imaginary_frequency_count` 是离散计数，不能用高斯标量模型。首版保持：

```text
G_stability = 1[count == 0]
```

更精细的版本应让 backend 输出最低若干振动频率和数值不确定度，定义：

```text
P(all nu_j >= -nu_tolerance | D)
```

其中 `nu_tolerance` 处理接近零的数值软模。只在已有 count 上套正态 CDF没有统计
意义。

## 7. 开放优化题的冻结基线协议

### 7.1 为什么需要 baseline

题面“maximize y”只定义序关系：若 `y_1 > y_2`，候选 1 更好；它没有定义
`y=8` 应得多少分。任何非恒定的 `[0, 1]` 映射都必须引入位置和尺度。冻结 baseline
是比大规模化学空间分布更小、更透明的额外假设。

### 7.2 baseline 选择规则

每个 baseline 必须：

- 通过与参赛答案完全相同的 hard gates；
- 在评分版本冻结前选定，不读取正式模型提交结果；
- 有公开的结构或至少可重现的生成协议与 property value；
- 在同一 verifier image 和电子态下重新计算；
- 保存重复结果、uncertainty 和 covariance；
- 不因 leaderboard 饱和而在同一版本中替换；
- 若升级 baseline，必须升级 benchmark scoring version。

可以使用一个 baseline，也可以使用少量预先声明的 anchors。多个 anchors 不应按
运行时最有利结果选择；可以预先定义均值、最难 anchor 或联合优越事件。

### 7.3 minimum meaningful improvement

`delta` 的证据优先级：

1. 科学或工程上的最小有意义变化；
2. paired high-level/reference 方法的 resolution；
3. 冻结协议跨平台 reproducibility；
4. 若均不可得，使用 `delta=0`，只声明“可靠优于 baseline”。

禁止根据希望的通过率反推 `delta`。

## 8. 18 道正式 xTB 题的逐题迁移

以下记号：

```text
I(y; L, U)       = P(L <= theta_y <= U | D)
GE(y; T)         = P(theta_y >= T | D)
LE(y; T)         = P(theta_y <= T | D)
SUP+(y; b, d)    = P(theta_y - theta_b >= d | D)
SUP-(y; b, d)    = P(theta_b - theta_y >= d | D)
Q                 = event R <= 0.35 eV
S                 = hard event imaginary_frequency_count == 0
```

所有 001-013 的表中事件都应与 `Q` 计算联合概率，而不是默认独立相乘。

### 8.1 已有明确窗口的任务

| Task | 成功事件 | 概率评分 | 所需新增证据 |
| --- | --- | --- | --- |
| `xtb_gap_window_001` | `3.5 <= gap <= 5.5` 且 `Q` | `P(3.5 <= G <= 5.5, Q | D)` | `(G,R)` residual covariance |
| `xtb_dipole_window_002` | `3.0 <= dipole <= 5.5` 且 `Q` | `P(3.0 <= Dp <= 5.5, Q | D)` | `(Dp,R)` covariance |
| `xtb_gap_dipole_window_007` | 两个窗口同时满足且 `Q` | `P(2.5 <= G <= 4.2, 3.5 <= Dp <= 6.0, Q | D)` | `(G,Dp,R)` covariance |

这些题不需要重新选择性质目标。题面窗口就是成功事件，迁移只替换窗口外的主观
指数衰减和 quality-gate 线性乘子。

### 8.2 单向开放优化任务

| Task | 新成功事件 | 推荐公式 |
| --- | --- | --- |
| `xtb_gap_max_003` | gap 比冻结 baseline 高至少 `delta_gap`，且 `Q` | `P(G_c-G_b >= delta_gap, Q | D)` |
| `xtb_gap_min_004` | gap 比 baseline 低至少 `delta_gap`，且 `Q` | `P(G_b-G_c >= delta_gap, Q | D)` |
| `xtb_dipole_max_005` | dipole 比 baseline 高至少 `delta_dipole`，且 `Q` | `P(D_c-D_b >= delta_dipole, Q | D)` |
| `xtb_lumo_min_008` | LUMO 比 baseline 低至少 `delta_lumo`，且 `Q` | `P(L_b-L_c >= delta_lumo, Q | D)` |
| `xtb_solvation_selectivity_alpb_010` | selectivity 比 baseline 高至少 `delta_solv`，且 `Q` | `P(S_c-S_b >= delta_solv, Q | D)` |
| `xtb_electrophilicity_max_011` | electrophilicity 比 baseline 高至少 `delta_e`，且 `Q` | `P(E_c-E_b >= delta_e, Q | D)` |
| `xtb_formula_dipole_min_014` | hard formula/electronic-state gate 后，dipole 低于 baseline | `G * SUP-(dipole; b_014, delta_014)` |
| `xtb_two_fluorine_gap_min_015` | hard composition/charge gate 后，gap 低于 baseline | `G * SUP-(gap; b_015, delta_015)` |
| `xtb_c10_f2_gap_min_016` | hard exact-count/charge gate 后，gap 低于 baseline | `G * SUP-(gap; b_016, delta_016)` |

003-005、008、010、011、014-016 的题面目前只声明方向。若不增加 baseline event，
则概率方案无法为它们提供绝对单题分；此时应保留 raw property 并只做排序，而不是
用未经证据支持的 `upper/lower` 填补缺失语义。

### 8.3 多目标和稳定性任务

| Task | 新联合成功事件 | 计算要求 |
| --- | --- | --- |
| `xtb_low_gap_high_dipole_opt_006` | `G_b-G_c >= delta_G` 且 `D_c-D_b >= delta_D` 且 `Q` | 候选、baseline、quality 的联合 covariance |
| `xtb_polarizability_dipole_opt_009` | `P_c-P_b >= delta_P` 且 `3 <= D <= 8` 且 `Q` | superiority 与窗口混合矩形概率 |
| `xtb_fukui_carbon_site_012` | `F_c-F_b >= delta_F` 且 `C_c-C_b >= delta_C` 且 `Q` | `(max_f_plus, contrast, R)` 联合概率 |
| `xtb_hessian_thermo_stability_013` | `S` 且 `H_c-H_b >= delta_H` 且 `Q` | count hard gate 加 `(entropy,R)` 联合概率 |

如果 task owner 的真实意图是允许两个目标互相补偿，而不是要求同时优于 baseline，
那么必须定义显式 utility 或交换率。概率论不能从“minimize A and maximize B”自动推导
一个补偿权重。当前几何平均隐含了等权和特定补偿关系，应在 task semantics 中明示，
而不能包装成联合成功概率。

### 8.4 固定分子构象能量任务

| Task | hard gate | 概率事件 |
| --- | --- | --- |
| `xtb_roy_singlepoint_energy_min_017` | ROY graph identity | `P(E_ref-E_c >= delta_E | D)` |
| `xtb_ritonavir_optimized_energy_min_018` | pre/post graph 和四个 stereocenters | `P(E_ref-E_c >= delta_E | D)` |

`E_ref` 必须来自同一分子、同一电子态、同一 xTB method 和同一 single-point/optimized
模式。绝对 total energy 不允许跨分子比较。

还应同时报告一个能量 desirability：

```text
Delta_E = max(0, E_c - E_ref)
s_B = exp(-Delta_E / (k_B*T))
```

在 298.15 K：

```text
k_B*T = 0.0256926 eV = 0.000944185 Eh
```

若候选比参考高 `0.001 Eh`，则：

```text
s_B = exp(-0.001 / 0.000944185) = 0.3468
```

当前 017、018 的线性区间宽度均为 `0.05 Eh`，即约 `52.96 k_B*T`；其顶端
相对权重约 `1e-23`。这说明现有宽度适合作为防止完全异常能量的工程 envelope，
不适合作为热力学连续评分尺度。

`s_B` 只使用 electronic energy，并忽略熵、简并度和自由能，故应命名为
`boltzmann_energy_proxy`，不能宣称为实际构象占比。

### 8.5 现有 controls 能否直接成为 baseline

当前 calibration evidence 可为 baseline 审核提供起点：

| Task | 当前已观测控制值 | 适合作为 baseline 的状态 |
| --- | --- | --- |
| 003 | gap `11.616 eV` | 可作为高水平 anchor 候选，需独立重复 |
| 004 | gap `1.299 eV` | 可作为低 gap anchor 候选 |
| 005 | dipole `10.034 D` | 可作为高 dipole anchor 候选 |
| 006 | gap `1.432 eV`、dipole `13.471 D` | 可作为联合 anchor 候选 |
| 008 | near-miss `-8.029 eV`、positive `-8.566 eV` | near-miss 可作为 baseline 候选 |
| 009 | polarizability/heavy atom `9.343`、dipole `3.969 D` | 需先确认 polarizability 目标强度 |
| 010 | selectivity `0.238 eV` | 可作为 baseline 候选 |
| 011 | near-miss `1.854 eV`、positive `2.494 eV` | near-miss 可作为 baseline 候选 |
| 012 | near-miss `(0.266, 0.032)`、positive `(0.276, 0.094)` | near-miss 可作为联合 baseline 候选 |
| 013 | stable near-miss entropy `40.598`、positive `76.095` | stable near-miss 可作为 baseline 候选 |
| 015 | gap 约 `1.708 eV` | 样本过少，需新 baseline audit |
| 016 | gap 约 `1.243 eV` | 样本过少，需新 baseline audit |
| 017 | ROY energy 约 `-50.289107 Eh` | 可作为 energy reference 候选 |
| 018 | Ritonavir observed best `-148.197963 Eh` | 可作为 best-known reference 候选 |

这些数值来自当前 calibration 报告，不构成本文对 baseline 的批准。旧 controls 曾参与
旧阈值调节，直接复用可能带来 circularity。正式迁移需要在不查看模型 panel 结果的
独立 baseline review 中冻结。

## 9. 数值算例

以下 `sigma` 仅用于展示公式行为，不是阈值建议。

### 9.1 gap 窗口题 001

设：

```text
m_gap = 5.8 eV
sigma_gap = 0.2 eV
window = [3.5, 5.5] eV
```

则：

```text
q_gap
  = Phi((5.5 - 5.8) / 0.2) - Phi((3.5 - 5.8) / 0.2)
  = Phi(-1.5) - Phi(-11.5)
  = 0.06681
```

若 `m_gap=4.5 eV`，则 `q_gap=0.9999994`。分数表达的是“真实/稳健协议值落入窗口的
概率”，而不是离窗口 `0.3 eV` 应按何种主观斜率扣分。

### 9.2 relaxation quality gate

设：

```text
m_R = 0.36 eV
sigma_R = 0.03 eV
R_max = 0.35 eV
```

则：

```text
q_geometry = Phi((0.35 - 0.36) / 0.03)
           = Phi(-0.3333)
           = 0.36944
```

这个结果可以解释为候选有约 36.9% 的概率满足声明质量边界。当前线性规则只表达
“0.36 超过 upper 因而为 0”，没有不确定度语义。

### 9.3 高 gap 相对 baseline

设 task 003：

```text
m_candidate = 11.0 eV
m_baseline = 10.6 eV
delta = 0.2 eV
sigma_candidate = 0.15 eV
sigma_baseline = 0.10 eV
covariance = 0
```

则：

```text
sigma_delta = sqrt(0.15^2 + 0.10^2) = 0.18028 eV
q = Phi((11.0 - 10.6 - 0.2) / 0.18028)
  = Phi(1.1094)
  = 0.86637
```

该分数的含义是：“候选比 baseline 至少高 `0.2 eV` 的概率约为 86.6%”。它不需要
假设所有分子的 gap 正态，也不需要声明 gap 在 `12 eV` 时人为饱和。

### 9.4 两目标依赖

若低 gap 改善事件边际概率 `q_G=0.85`，高 dipole 改善事件边际概率
`q_D=0.80`，则无论依赖结构如何：

```text
0.65 <= P(A_G and A_D) <= 0.80
```

若 residual independence 经验证，联合概率为：

```text
0.85 * 0.80 = 0.68
```

当前几何平均为 `sqrt(0.68)=0.8246`，甚至高于联合概率的理论上界 `0.80`，所以它
不能解释成“两个目标同时成功的概率”。

## 10. 参数与结果 schema 建议

### 10.1 Task scoring schema

示意：

```yaml
scoring:
  model: probabilistic_constraint_v1
  claim_target: xtb_protocol_robust
  event:
    type: joint
    constraints:
      - property: homo_lumo_gap
        relation: between
        lower: 3.5
        upper: 5.5
      - property: relaxation_energy
        relation: less_than_or_equal
        threshold: 0.35
  uncertainty_profile: xtb_gap_relaxation_gfn2_v1
  joint_method: multivariate_normal
```

开放优化题：

```yaml
scoring:
  model: probabilistic_superiority_v1
  claim_target: xtb_protocol_robust
  event:
    property: homo_lumo_gap
    direction: maximize
    baseline_id: xtb_gap_max_reference_v1
    minimum_improvement: 0.0
  uncertainty_profile: xtb_gap_gfn2_v1
```

### 10.2 Uncertainty profile

```yaml
uncertainty_profile_id: xtb_gap_relaxation_gfn2_v1
verifier_image: verifier-grounded:<frozen-tag>
xtb_version: 6.7.1
claim_target: xtb_protocol_robust
properties: [homo_lumo_gap, relaxation_energy]
bias: [0.0, 0.0]
covariance:
  - [var_gap, cov_gap_relax]
  - [cov_gap_relax, var_relax]
estimation:
  source_manifest_sha256: <sha256>
  calibration_count: <n>
  audit_count: <n>
  residual_family: multivariate_normal
  coverage_report_sha256: <sha256>
```

### 10.3 Result schema

建议保留 raw properties，并增加：

```yaml
scores:
  score: number
  event_probability: number
  hard_gate: 0 | 1
  component_probabilities: [mapping]
  joint_probability_method: string
  probability_lower_bound: number | null
  probability_upper_bound: number | null
  uncertainty_profile_id: string
  baseline_id: string | null
  claim_target: string
```

这使用户可以区分“性质值是什么”“通过概率是多少”“概率依据是什么”。

## 11. 校准与验收协议

### 11.1 数据划分

不确定度数据必须至少分为：

- `fit`：估计 bias、variance 和 covariance；
- `audit`：只做 coverage、tail 和 subgroup 检查；
- `stress`：适用域边界、SCF 困难、柔性结构和平台差异。

正式模型 panel 结果不得进入 uncertainty fit，否则会重新引入按 leaderboard 调参。

### 11.2 概率校准验收

每个 uncertainty profile 至少满足：

1. audit residual bias 的置信区间符合声明；
2. 50%、80%、90%、95% predictive intervals 的 coverage 与名义值一致到预注册
   容差；
3. decision boundary 附近单独报告 false-pass 和 false-fail rate；
4. 多目标 profile 检查 joint coverage，不只检查每个边际；
5. supported element/electronic-state subgroup 无严重系统性欠覆盖；
6. 若正态模型失败，切换到预注册 Student-t 或 Monte Carlo profile；
7. profile、baseline、task 和 verifier image 均有不可变 hash。

### 11.3 评分实现验收

- 标量公式与 `scipy.stats.norm.cdf` 的固定向量一致；
- `sigma -> 0` 的数值实现稳定且符合硬判定极限；
- affine unit conversion 后分数不变；
- multivariate covariance 必须半正定；
- 独立协方差时 joint result 等于边际乘积；
- 未提供 covariance 时不得静默假设独立；
- infrastructure error 不产生候选零分；
- 同一版本重复评分 bitwise 或在声明 tolerance 内复现。

## 12. 对 RDKit 和 property-calculation track 的外推

### 12.1 RDKit

RDKit descriptors 在冻结版本下基本确定，因此 Claim A 的 `sigma` 接近零：

- logP/TPSA/HBA/HBD 窗口题会趋向硬窗口判定；
- QED、SA、Fsp3 的开放优化题需要冻结 baseline superiority；
- `rdkit_logp_target_011` 应把“接近 3”改写为公开 tolerance window，或明确
  semantic tolerance，不能把 `scale=0.5` 称为测量误差；
- 若希望保持连续分数，必须承认其来源是 decision tolerance，而非 RDKit 数值
  uncertainty。

### 12.2 Property Calculation

固定答案题已有公开 absolute tolerance。若 gold 生成协议存在不确定度，可令：

```text
answer_error = submitted_value - gold_value
```

并传播 gold/reference uncertainty。当前模型只提交点值、不提交自身 uncertainty，
所以保留确定性 tolerance indicator 更简单、更诚实。字符串 phase assignment 继续
exact match，不适用正态模型。

## 13. 迁移顺序

### Phase 0：只读 shadow evaluation

- 不修改正式 `score`；
- 为 001、002、007 和 quality gate 实现离线 probability calculator；
- 用历史 controls 和模型答案输出 old/new paired report；
- 检查 ranking stability、边界行为和 error attribution。

### Phase 1：冻结 uncertainty profiles

- 先选择 Claim A；
- 固定 verifier image、xTB 版本和电子态；
- 收集 repeat/platform/perturbation residuals；
- 完成 scalar 和 joint coverage audit；
- 对失败 profile 使用 JCGM 101 Monte Carlo。

### Phase 2：重写开放优化题的成功语义

- 为 003-006、008-016 独立审核 baseline；
- 决定 `delta=0` 或有证据的 minimum meaningful improvement；
- 在 task metadata 和用户文档公开 baseline event；
- 不把旧 `upper/lower` 自动迁移成新阈值。

### Phase 3：构象能量专用评分

- 为 ROY 和 Ritonavir 冻结同方法 reference conformer；
- 同时报告 superiority probability、raw `Delta_E` 和 Boltzmann energy proxy；
- 明确 single-point 与 optimized mode 不可混用。

### Phase 4：版本化发布

- 新评分作为新 benchmark scoring version 发布；
- 旧分数与新分数不跨版本直接比较；
- 发布 migration table、profile hashes 和 calibration audit；
- 在版本冻结后禁止按模型通过率修改 baseline、delta 或 uncertainty。

## 14. 最终建议

建议采纳以下决策：

1. 不采用“所有化学性质服从正态分布”的假设。
2. 采用 `score = P(success event | verifier evidence)` 作为统一数学接口。
3. 首批只迁移成功事件已经完整定义的 001、002、007 和 relaxation quality gate。
4. 003-006、008-016 在正式迁移前必须增加冻结 baseline superiority 语义；没有
   baseline 或阈值时，只报告 raw objective 和排序。
5. 017、018 使用同分子 reference energy 与 Boltzmann-like 辅助分数。
6. 多目标使用 joint probability；未知相关性时使用 Fréchet lower bound 或
   Monte Carlo，禁止把几何平均解释成联合概率。
7. 18 道题之间使用单题概率的等权算术平均，其含义是预期成功题目占比；一道题
   内部的多个约束仍使用联合概率。
8. 正态性只对 residual 做 coverage validation；失败时回退 Student-t 或冻结 residual
   Monte Carlo。
9. 如果 fixed-xTB 协议不产生可观不确定度，接受分数退化成 hard pass/fail，或明确
   引入 scientific decision tolerance。不能为了得到平滑曲线伪造 uncertainty。

该方案相对于当前 bounded scoring 的主要收益不是“完全无参数”，而是每个参数都
对应可审计对象：任务成功事件、冻结 baseline、最小有意义改善、方法不确定度、
相关性或热力学政策。其严谨性来自符合性评定和不确定度传播，而不是来自对无限化学
空间作未经验证的总体分布假设。

## 参考资料

### 项目内资料

- [xTB 题目设计与实现同步](../tracks/xTB.md)
- [xTB calibration reliability report](2026-06-15-xtb-calibration-reliability-report.md)
- [xTB real-dataset property distributions](2026-06-15-xtb-real-dataset-property-distributions.md)
- [Expert open-generation xTB calibration](2026-07-13-expert-open-generation-xtb-calibration.md)
- [Project-level limitations](../design/Limits.md)

### 外部资料

- JCGM 100:2008, *Evaluation of measurement data - Guide to the expression of
  uncertainty in measurement*. DOI: https://doi.org/10.59161/JCGM100-2008E
- JCGM 101:2008, *Propagation of distributions using a Monte Carlo method*.
  DOI: https://doi.org/10.59161/JCGM101-2008
- JCGM 102:2011, *Extension to any number of output quantities*.
  DOI: https://doi.org/10.59161/JCGM102-2011
- JCGM 106:2012, *The role of measurement uncertainty in conformity assessment*.
  DOI: https://doi.org/10.59161/JCGM106-2012
- NIST, *Boltzmann constant*, 2022 CODATA recommended value:
  https://physics.nist.gov/cgi-bin/cuu/Value?k
- Bannwarth, Ehlert, Grimme, *GFN2-xTB - An Accurate and Broadly Parametrized
  Self-Consistent Tight-Binding Quantum Chemical Method with Multipole
  Electrostatics and Density-Dependent Dispersion Contributions*, JCTC 2019.
  DOI: https://doi.org/10.1021/acs.jctc.8b01176
