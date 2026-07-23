# 专家开放生成题 009-013 规格

日期：2026-07-23  
状态：约束已确认，准予进入实现；连续评分锚点按本文规定完成校准后方可进入正式发布  
适用版本：`verifier-grounded-benchmark` 0.3.x 后续版本

## 1. 目的与范围

本文冻结新增专家题 009-013 的任务语义、track 归属、答案格式、候选硬约束、
性质计算协议、评分方向、失败语义、可复现性要求和实现验收标准。

本文是实现规格，不直接修改当前正式 task pack。实现提交必须以本文为依据，且不得：

- 增加题面没有公开的候选限制；
- 把模型自报的性质值用于评分；
- 把连续 quality score 当作题面要求的二元硬门；
- 用正式提交结果反向调整评分参数；
- 把 verifier 环境或工具故障记为候选零分。

新增题目仍属于现有 `rdkit` 和 `xtb` track，不新增正式 track。

## 2. 最终任务清单

| 专家题号 | task_id | track | 输入 | 主目标 |
|---|---|---|---|---|
| 009 | `rdkit_sa_logp_target_012` | `rdkit` | SMILES | LogP 接近 3 |
| 010 | `xtb_odd_element_counts_gap_max_019` | `xtb` | explicit-H XYZ | 最大化 HOMO-LUMO gap |
| 011 | `xtb_pyrene_substituent_energy_min_020` | `xtb` | SMILES | 最小化最低构象能量 |
| 012 | `rdkit_chain_end_to_end_max_013` | `rdkit` | SMILES | 最大化最低能构象的六碳链端到端距离 |
| 013 | `rdkit_caffeine_similarity_max_014` | `rdkit` | SMILES | 最大化与咖啡因的 Morgan Tanimoto 相似度 |

task ID 按各 track 当前正式任务的末尾顺延。专家题号保留在设计、测试名称和
release notes 中，不要求写入公共 answer schema。

实现完成后，正式任务数量预期为：

- `rdkit`：11 增至 14；
- `xtb`：18 增至 20；
- `property_calculation`：保持 2；
- 全部正式任务：31 增至 36。

## 3. 通用评价语义

### 3.1 答案与候选

每题只接受一个候选。SMILES 题使用：

```text
FINAL ANSWER: <SMILES>
```

XYZ 题使用：

````text
FINAL ANSWER:
```xyz
<XYZ content>
```
````

SMILES 必须表示一个可被 RDKit sanitize 的单组分分子。XYZ 必须包含一个连通分子、
有限坐标和全部氢原子。点分多组分 SMILES、多个候选、缺失最终答案、无法解析的输入均
按现有 parse/validity 规则拒绝。

### 3.2 执行顺序

统一执行顺序为：

1. 解析答案并确认 cardinality；
2. 验证基本分子有效性和单组分/单连通要求；
3. 验证元素、原子计数、电子态、骨架和取代模式等结构硬约束；
4. 计算题目声明的硬性质并应用严格比较符；
5. 只有全部硬门通过后，计算或读取主评分性质；
6. 使用冻结的 `linear_goal_v2` profile 产生 `[0, 1]` 分数。

同一 backend run 同时产生多个性质时必须复用同一份 verifier evidence。例如题 010 的
dipole 和 gap 必须来自同一次 GFN2-xTB 优化结果。

### 3.3 硬性质约束

当前 evaluator 的 `quality_gate` 是连续分数乘子，不能表达本文的严格门槛。实现前必须
增加显式硬性质约束，推荐 task schema：

```yaml
hard_constraints:
- property: sa_score
  verifier_id: example_verifier_v1
  operator: lt
  threshold: 5.0
```

首版至少支持：

- `lt`：严格小于；
- `le`：小于等于；
- `closed_window`：包含两端的闭区间；
- 结构 verifier 自身返回的 identity/domain 判定。

硬性质未满足时返回候选级 `hard_constraint_failed`，最终分数为 0。该类型必须加入
verifier result、subprocess runner 和公共结果 schema 的 candidate failure allowlist。
结果必须保留已计算的性质值和被违反的比较条件，便于审计。

### 3.4 连续评分

主目标继续使用 `linear_goal_v2`：

```text
target:   score = clip(1 - distance_to_target / width, 0, 1)
maximize: score = 0                         if x <= B
          score = (x - B) / (T - B)         if B < x < T
          score = 1                         if x >= T
minimize: score = 1                         if x <= T
          score = (B - x) / (B - T)         if T < x < B
          score = 0                         if x >= B
```

其中 `T` 为满分目标，`B` 为零分锚点。需要校准的 `T/B` 必须来自独立冻结的候选集、
文献 reference 或同协议 reference，不得从正式模型提交中估计。

### 3.5 可复现性

所有 verifier spec 必须冻结并报告：

- RDKit、xTB 和 CREST 版本；
- canonical reference SMILES；
- 构象生成 seed、构象数、pruning 和优化迭代数；
- xTB/CREST method、charge、UHF、搜索级别和超时；
- fingerprint 参数；
- scoring profile ID、参数、校准证据和 hash；
- verifier image 或等价的不可变环境标识。

## 4. 题 009：SA 硬门下的 LogP target

### 4.1 标识

```yaml
expert_question: 9
task_id: rdkit_sa_logp_target_012
track: rdkit
object_type: small_molecule
answer_type: smiles
task_type: open_generation
```

### 4.2 公开题意

设计一个有机分子，使其满足：

- 单组分；
- 元素只允许 H、C、O、N、S、F、Cl；
- 至少含一个碳原子；
- 加入全部隐式氢后的总原子数不超过 40；
- SA Score 严格低于 5；
- 在满足以上限制后，使 LogP 尽可能接近 3。

这里不要求氧原子占比。现有 `rdkit_logp_target_011` 的氧占比门不得继承到本题。

### 4.3 验证协议

1. 用 RDKit sanitize 输入 SMILES，并拒绝多组分。
2. 用 `Chem.AddHs` 后的分子统计 H 在内的总原子数和元素计数。
3. 使用 `rdkit.Contrib.SA_Score.sascorer.calculateScore` 计算 SA Score。
4. 若 `SA >= 5.0`，返回 `hard_constraint_failed`，不再运行 LogP 主评分。
5. 使用 `rdkit.Chem.Crippen.MolLogP` 计算 LogP。

SA 和 LogP verifier 必须共享完全相同的候选 domain。不能直接组合当前通用
`rdkit_sa_score_v1` 与含氧占比限制的 `rdkit_logp_expert_v1`。

### 4.4 评分

复用现有 profile `rdkit_logp_target_3p0_3p0_v2`：

```text
T = 3.0
lower_width = 3.0
upper_width = 3.0
score = clip(1 - abs(logP - 3.0) / 3.0, 0, 1)
```

SA 只决定候选是否有资格得分，不参与几何平均或其他连续聚合。

### 4.5 必须报告

```text
canonical_smiles
atom_count_including_h
element_counts
sa_score
logp                         # 仅硬门通过后必需
hard_constraint_passed
```

### 4.6 验收用例

- 含禁止元素的分子为 `domain_error`；
- `Chem.AddHs` 后 41 个原子的分子为 `domain_error`；
- `SA == 5.0` 和 `SA > 5.0` 均为 `hard_constraint_failed`；
- `SA < 5.0` 时 LogP 为 3 得 1 分，0 或 6 得 0 分；
- 不含氧但满足其余条件的候选不会因氧占比被拒绝。

## 5. 题 010：奇数元素计数、低偶极和大 gap

### 5.1 标识

```yaml
expert_question: 10
task_id: xtb_odd_element_counts_gap_max_019
track: xtb
object_type: small_molecule_3d
answer_type: xyz
task_type: open_generation
```

### 5.2 公开题意

提交一个全氢显式的中性闭壳层单重态有机分子 XYZ，并满足：

- 恰好一个连通分子；
- 元素只允许 H、C、O、N、S、F、Cl；
- 至少含一个碳原子；
- 总原子数包含氢且不超过 40；
- 重原子数不少于 7；
- 至少出现 3 种不同的非氢元素；
- 每一种实际出现的非氢元素，其原子个数均为奇数；
- 优化后分子偶极矩严格小于 2 Debye；
- 在满足以上限制后，使优化后 HOMO-LUMO gap 尽可能大。

“非氢元素计数为奇数”指各元素的原子个数为奇数，不是原子序数为奇数。

### 5.3 结构和电子态硬门

XYZ parser 和 domain checker 必须确认：

```text
atom_count <= 40
heavy_atom_count >= 7
carbon_count >= 1
heavy_element_diversity >= 3
for each element != H: element_count % 2 == 1
charge = 0
uhf = 0
electron_count parity compatible with closed shell
inferred_components = 1
all hydrogens explicit
```

需要为 xTB structural domain 增加通用 `element_count_parity` 能力，而不是为具体分子
枚举 formula。

### 5.4 计算协议

1. 对提交 XYZ 做上述结构和电子态检查。
2. 使用冻结的 GFN2-xTB、`--chrg 0 --uhf 0 --opt` 优化一次。
3. 从同一次正常收敛的输出解析总偶极矩和 HOMO-LUMO orbital-energy gap。
4. 若 `dipole_moment >= 2.0 D`，返回 `hard_constraint_failed`。
5. 若偶极硬门通过，用该次结果中的 gap 评分。
6. 本题不额外应用 relaxation-energy quality multiplier。

这里的 gap 是冻结 GFN2-xTB 协议的轨道能级差，不是实验光学带隙。题面和 track 文档
必须保持该解释边界。

### 5.5 评分

```text
property: homo_lumo_gap
type: maximize
unit: eV
```

本题受“奇数元素计数 + dipole < 2 D”限制，不能未经证据直接复用现有通用 gap
profile。正式发布前必须在完全相同的结构域和计算协议中冻结：

- `T_gap`：满分目标；
- `B_gap`：零分锚点；
- 独立正例、near-miss 和负例；
- verifier version/hash 和校准报告。

### 5.6 必须报告

```text
formula
atom_count
heavy_atom_count
element_counts
heavy_element_diversity
charge
uhf
electron_count
dipole_moment
homo_lumo_gap
optimization_converged
hard_constraint_passed
```

### 5.7 验收用例

- 少于 3 种非氢元素、少于 7 个重原子或无碳时为 `domain_error`；
- 任一已出现非氢元素计数为偶数时为 `domain_error`；
- H 数量的奇偶不参与 `element_count_parity`；
- dipole 恰为 2.0 D 时硬门失败；
- dipole 与 gap 只触发一次 xTB optimization；
- xTB 环境缺失、超时或未收敛仍为 infrastructure/tool failure，不是候选零分。

## 6. 题 011：芘三取代异构体的 CREST/xTB 最低能量

### 6.1 标识与 track 扩展

```yaml
expert_question: 11
task_id: xtb_pyrene_substituent_energy_min_020
track: xtb
object_type: small_molecule
answer_type: smiles
task_type: open_generation
```

本题仍属于 `xtb` track，不新建 `xtb_crest` track。`xtb` track 的公开定义扩展为：

- direct-XYZ 题：候选直接提交三维结构；
- SMILES-to-conformer 题：候选提交二维分子图，verifier 生成初始几何并运行冻结的
  CREST/xTB 构象搜索。

答案格式由每道任务的 `answer_schema` 决定，不能再把“xTB track 只接受 XYZ”作为全
track 不变量。

### 6.2 公开题意

参考芘骨架：

```text
c1cc2ccc3cccc4ccc(c1)c2c34
```

在芘的三个不同原 C-H 位点上分别连接且只连接：

- 一个 nitro `NO2`；
- 一个 amino `NH2`；
- 一个 carboxyl `COOH`。

不得改变芘的 16 碳骨架、骨架键级或环系，不得引入其他取代基。在满足结构要求后，
使固定 CREST/xTB 协议找到的最低能构象的总电子能量尽可能低。

### 6.3 分子身份硬门

候选必须满足：

```text
formula = C17H10N2O4
allowed elements = H, C, N, O
formal charge = 0
closed-shell singlet
pyrene scaffold atom count = 16 carbon atoms
substituted original C-H sites = 3 distinct sites
remaining pyrene hydrogens = 7
extra substituent multiset = {nitro: 1, amino: 1, carboxyl: 1}
extra atoms or bonds = none
```

身份验证不能只调用 `HasSubstructMatch(pyrene_smarts)`。必须把芘 reference 与候选的
scaffold atom mapping 固定下来，并比较候选相对 reference 的 graph delta：

- 16 个 scaffold carbon 和 scaffold bond graph 完全一致；
- 三条新增 scaffold-substituent bond 起于三个不同的 reference C-H site；
- nitro 接头为 scaffold-C-N，接受等价的 nitro resonance bond 表示，但要求净中性；
- amino 接头为中性 scaffold-C-NH2；
- carboxyl 接头为中性 scaffold-C-C(=O)OH；
- 除上述 graph delta 外无其他重原子和键。

### 6.4 构象和能量协议

1. RDKit sanitize、canonicalize 并完成分子身份硬门。
2. `Chem.AddHs` 后使用冻结的 ETKDGv3 和固定 seed 生成 CREST 初始三维几何。
3. 验证初始几何重建出的图仍与候选 SMILES 一致。
4. 调用环境中冻结版本的 CREST，使用 GFN2-xTB、charge 0、UHF 0 执行构象搜索。
5. 从正常结束的 CREST ensemble 选择最低能成员。
6. 对选中的 CREST 最低能成员重建分子图，再次执行完整身份硬门。
7. 对该几何运行同版本、同 charge/UHF 的 GFN2-xTB single-point，并解析绝对 total energy。
8. 只有 pre-search 和 post-CREST 身份检查都通过时才接受能量。

实现必须冻结 CREST 版本、xTB 版本、搜索级别、seed/确定性设置、资源上限和超时。
当前环境没有 CREST；安装和环境 smoke test 是实现前置条件。

### 6.5 评分

所有有效候选具有相同 formula、charge 和电子态，因此可在同一冻结方法下比较 total
electronic energy：

```text
property: total_energy
type: minimize
unit: hartree
```

`T_energy/B_energy` 必须通过独立枚举或覆盖代表性取代位置异构体的冻结校准集确定。
校准集不得随正式提交扩充后重新定标。分数只代表该 CREST/GFN2-xTB 协议下的代理
能量，不代表实验生成自由能、溶液平衡或合成产率。

### 6.6 必须报告

```text
canonical_smiles
formula
formal_charge
scaffold_match
substitution_site_indices
substituent_counts
crest_version
xtb_version
crest_conformer_count
crest_min_relative_energy
total_energy
pre_search_identity_match
post_crest_identity_match
```

### 6.7 验收用例

- 未取代、少/多一个取代基、两个基团接到同一位置或含额外取代基均为 identity failure；
- 改变芘骨架键或环系为 identity failure；
- nitro 共振等价 SMILES 应 canonicalize 到同一可接受身份；
- carboxylate、质子化 amino 或非中性候选被拒绝；
- CREST 缺失、超时或无 ensemble 为 infrastructure/tool failure；
- CREST/xTB 过程中发生分子图变化时为 candidate identity failure；
- 同一候选在冻结环境中重复运行应落入预先批准的能量重复性容差。

## 7. 题 012：六碳链最低能构象的端到端距离

### 7.1 标识与 track 决策

```yaml
expert_question: 12
task_id: rdkit_chain_end_to_end_max_013
track: rdkit
object_type: small_molecule
answer_type: smiles
task_type: open_generation
```

本题并入正式 `rdkit` track，不建立 `rdkit_forcefield` track。UFF 构象代码可以继续位于
`evaluation/open_generation/verifiers/rdkit_forcefield/` 模块；模块名只表示实现 backend，
不构成公共 track。

实现本题时必须删除：

```text
src/verifier_grounded_benchmark/task/packs/experimental/rdkit_forcefield/
```

旧 experimental pack 的相关测试应删除或改写为正式 RDKit task 测试；仍有价值的 backend
单元测试保留。单独的 `docs/tracks/RDKit-Forcefield.md` 应删除，其仍有效的协议说明合并到
`docs/tracks/RDKit.md`。

### 7.2 公开题意

候选必须保留以下连续六碳骨架：

```text
[C;X4;!R]-[C;X4;!R]-[C;X4;!R]-[C;X4;!R]-[C;X4;!R]-[C;X4;!R]
```

并满足：

- 单组分、中性分子；
- 元素只允许 H、C、N、O、S、F、Cl；
- 恰好包含 6 个碳原子；
- 全部 6 个碳都属于上述非环、四配位、单键相连的连续骨架；
- 不允许任何额外碳原子或额外碳骨架；
- 加入全部隐式氢后的总原子数不超过 40；
- 在固定 RDKit/UFF workflow 找到的最低能构象中，使六碳链端点距离尽可能大。

“最低能构象”只表示固定有限构象采样和 UFF 优化 workflow 找到的最低者，不宣称真实
全局最低能构象。“长度”只指两个端点碳原子核的欧氏距离，不指全分子最大直径、轮廓
长度、回转半径或包含取代基的尺寸。

### 7.3 骨架和 domain 硬门

1. RDKit sanitize 并拒绝多组分。
2. `Chem.AddHs` 后确认总原子数 `<= 40`。
3. 确认 formal charge 为 0，元素属于允许集合。
4. 确认候选碳原子总数恰好为 6。
5. 用上述 SMARTS 获取匹配，并确认一个匹配覆盖全部 6 个碳。
6. 去除反向重复后，所有有效匹配必须给出同一无序端点对；否则以 domain ambiguity 拒绝。
7. 记录按 canonical atom ranking 确定的端点 atom indices，后续所有构象都使用该映射。

“包含六碳子结构”而碳总数大于 6 的候选必须被拒绝，不能通过增加长碳取代基提高分数。

### 7.4 冻结构象协议

首版固定以下参数，与现有 prototype 默认值保持一致，但强制只用 UFF：

```yaml
embedder: ETKDGv3
random_seed: 61453
num_conformers: 20
prune_rms_thresh: 0.5  # angstrom
forcefield: UFF
max_iters: 200
```

流程为：

1. `Chem.AddHs`；
2. `EmbedMultipleConfs` 生成最多 20 个 retained conformers；
3. 若 `UFFHasAllMoleculeParams` 为 false，以 `domain_error` 拒绝该候选；
4. 若一个构象都未生成，返回 verifier tool failure；
5. 对每个构象运行最多 200 iteration 的 UFF optimization；
6. 只保留 optimization status 为 converged 的构象；
7. 若无收敛构象，返回 verifier tool failure，不产生候选性质分数；
8. 对每个收敛构象计算 UFF energy；
9. 按 `(energy, conformer_id)` 升序选择唯一最低者；
10. 在该构象中测量两个映射端点碳原子的欧氏距离，单位 Angstrom。

UFF energy 只用于同一候选内部选择构象，不作为跨候选评分性质。

### 7.5 评分

```text
property: chain_end_to_end_distance
type: maximize
unit: angstrom
```

正式发布前必须在完全相同的 ETKDGv3/UFF 协议和合法 domain 上冻结
`T_length/B_length`。校准至少包含：

- n-hexane reference；
- 容易折叠的合法取代候选；
- 促进伸展的合法取代候选；
- 重复运行确定性检查；
- 构象数敏感性分析，确认 20 个构象足以支持声明，或在发布前统一修改固定参数。

### 7.6 必须报告

```text
canonical_smiles
atom_count_including_h
carbon_count
chain_match_atom_indices
chain_endpoint_atom_indices
requested_conformer_count
retained_conformer_count
converged_conformer_count
selected_conformer_id
selected_uff_energy_kcal_mol
chain_end_to_end_distance
```

### 7.7 验收用例

- 五碳链、七碳链、含碳支链、环碳或不饱和碳骨架被拒绝；
- 合法的非碳取代不会因“额外碳骨架”规则被拒绝；
- 含氢总原子数恰为 40 可接受，41 被拒绝；
- backend 不能回退到 MMFF；
- 被测距离必须来自最低 UFF 能量的收敛构象，而不是第一个嵌入构象；
- 端点索引反向匹配不改变距离；
- 固定 seed 和环境下重复结果一致。

## 8. 题 013：硬性质窗口下的咖啡因相似度

### 8.1 标识

```yaml
expert_question: 13
task_id: rdkit_caffeine_similarity_max_014
track: rdkit
object_type: small_molecule
answer_type: smiles
task_type: open_generation
```

### 8.2 Reference

冻结咖啡因 reference：

```text
input_smiles: Cn1c(=O)c2c(ncn2C)n(C)c1=O
canonical_smiles: Cn1c(=O)c2c(ncn2C)n(C)c1=O
formula: C8H10N4O2
```

在冻结 RDKit 2026.3.2 下的审计值：

```text
logp = -1.0293
qed = 0.5384628262372215
sa_score = 2.29798245679401
sa_upper_bound = reference_sa_score + 0.5 = 2.79798245679401
```

reference 本身不满足 LogP 和 QED 硬窗口，因此不是本题的平凡有效答案。

### 8.3 公开题意

候选必须是可 sanitize 的单组分分子，并满足：

- LogP 位于闭区间 `[-0.5, 1.5]`；
- SA Score 不高于同版本咖啡因 SA Score 加 0.5；
- QED 位于闭区间 `[0.65, 0.75]`；
- 在满足上述全部限制后，使其与咖啡因的 Morgan fingerprint Tanimoto 相似度尽可能高。

“针对咖啡因设计”不表示必须保留黄嘌呤或咖啡因 scaffold。本题不增加 scaffold
hard gate；结构接近程度完全由冻结的 fingerprint 相似度衡量。

### 8.4 验证协议

对同一个 sanitized、canonicalized 候选依次计算：

1. `Crippen.MolLogP`；
2. `SA_Score.sascorer.calculateScore`；
3. `QED.qed`；
4. 只有前三个硬门全部通过后才计算 Morgan fingerprint 和 Tanimoto。

硬门使用：

```text
-0.5 <= logp <= 1.5
sa_score <= reference_sa_score + 0.5
0.65 <= qed <= 0.75
```

边界全部包含。reference SA 必须由同一冻结 RDKit/SA implementation 计算并同时与 spec
中的审计常量核对；不一致属于 verifier environment/spec error，不能改变门槛后继续评分。

### 8.5 Fingerprint 定义

使用 RDKit Morgan bit fingerprint：

```yaml
generator: rdFingerprintGenerator.GetMorganGenerator
radius: 2
fpSize: 2048
includeChirality: false
useBondTypes: true
fingerprint_type: bit_vector
similarity: DataStructs.TanimotoSimilarity
```

候选和 reference 必须使用相同 generator 实例/参数。不接受 count fingerprint、feature
Morgan、不同 bit length 或模型自报 similarity。

### 8.6 评分

Tanimoto 的定义域为 `[0, 1]`，可使用定义域锚点：

```text
property: caffeine_morgan_tanimoto
type: maximize
T = 1.0
B = 0.0
score = caffeine_morgan_tanimoto
```

LogP、SA 和 QED 只作为硬门，不进入几何平均。

### 8.7 必须报告

```text
canonical_smiles
logp
sa_score
reference_sa_score
qed
fingerprint_radius
fingerprint_size
caffeine_morgan_tanimoto
hard_constraint_passed
```

### 8.8 验收用例

- 三个窗口的上下边界按规定包含，越界任意小量均硬门失败；
- candidate SA 恰为 `reference + 0.5` 可接受；
- caffeine reference 因 LogP/QED 失败而不得进入相似度主评分；
- 不含黄嘌呤 scaffold 但满足性质窗口的候选仍可评分；
- 相同 canonical molecule 的不同等价 SMILES 得到相同 fingerprint 和分数；
- 修改 radius、bit size 或 fingerprint 类型会被配置/hash 测试发现。

## 9. 实现变更矩阵

| 组件 | 必需变更 |
|---|---|
| task schema | 增加 `hard_constraints` 及 `lt/le/closed_window` 校验 |
| evaluator | 硬门先于主约束执行；硬门失败短路；复用 verifier evidence |
| failure taxonomy | 增加候选级 `hard_constraint_failed` |
| RDKit descriptor backend | 支持题目专用共同 domain、SA 硬门、Morgan/Tanimoto reference property |
| xTB structural domain | 支持每个已出现非氢元素的计数 parity |
| xTB property backend | 同一 optimization evidence 同时提供 dipole 和 gap |
| xTB track parser/routing | 按 task answer schema 同时支持 XYZ 和 SMILES |
| xTB CREST backend | SMILES 初始几何、CREST ensemble、最低构象、xTB single-point 和搜索前后 identity check |
| RDKit force-field backend | 精确六碳 SMARTS、固定 UFF、最低能构象 endpoint distance |
| formal RDKit pack | 新增题 009、012、013 和对应 specs/profiles |
| formal xTB pack | 新增题 010、011 和对应 specs/profiles |
| experimental pack | 删除 `task/packs/experimental/rdkit_forcefield/` |
| track docs | 更新 `RDKit.md`、`xTB.md`；删除独立 `RDKit-Forcefield.md` |
| package/release | 更新任务清单、样例、release manifest/hash 和正式任务计数 |

## 10. 测试与发布验收

### 10.1 单元测试

- 每个新增 domain key 的正、负、边界测试；
- `hard_constraints` schema、执行顺序、短路和 failure mapping；
- SA、LogP、QED 和 fingerprint 的冻结数值测试；
- odd-count parity 不检查 H 的回归测试；
- pyrene graph delta、官能团计数和 resonance 等价测试；
- UFF 最低能构象选择和 endpoint mapping 测试；
- xTB multi-property evidence 只执行一次 optimization 的测试。

### 10.2 集成测试

- 五道题均能从 raw answer 完成解析、验证和评分；
- verifier subprocess 输出符合公共 result schema；
- `vgb.load_track("rdkit")` 返回 14 题，`vgb.load_track("xtb")` 返回 20 题；
- suite 共返回 36 个唯一 task ID；
- wheel/sdist 包含新增正式资源且不包含 `task/packs/experimental/rdkit_forcefield`；
- xTB track 的 SMILES 和 XYZ 两种 answer schema 均能从安装后的 wheel 工作。

### 10.3 Live smoke

- 检查 `xtb` 和 `crest` executable、版本及最小计算；
- 对题 010 的小型合法候选完成一次联合 gap/dipole run；
- 对题 011 的至少一个合法三取代异构体完成 CREST ensemble 和最终 xTB energy；
- 对题 012 的 n-hexane 完成固定 UFF workflow；
- live smoke 的环境故障必须与 candidate rejection 明确区分。

### 10.4 正式发布门

以下条件全部满足后才能把题目标为 `formal_track: true` 并制作 release：

1. 题 010 gap、题 011 energy、题 012 length 的 `T/B` 有批准的校准报告；
2. CREST/xTB 环境已冻结并通过重复性检查；
3. 五题正例、边界例和负例全部通过 private calibration；
4. 完整测试、lint、build 和安装后 wheel smoke 通过；
5. task、verifier、profile 和 release artifact hash 已更新；
6. 公共 prompt 不暴露内部脚本、verifier ID 或评分实现细节；
7. track 文档准确说明 RDKit/UFF、GFN2-xTB、CREST 和 fingerprint 的代理性质边界。

## 11. 已冻结的决策摘要

- 题 009：SA `<5` 是硬门；LogP 越接近 3 分数越高；评分同 RDKit 011，但不继承氧占比。
- 题 010：每一种非氢元素的原子个数必须为奇数；dipole `<2 D` 是硬门；gap 是唯一主目标。
- 题 011：安装 CREST；答案使用 SMILES；仍属于 `xtb` track；允许 track 内多种答案表示。
- 题 012：长度是六碳链端点碳距离；禁止其他碳骨架；总原子数包含隐式氢；固定 UFF；并入 `rdkit` track；删除旧 experimental pack。
- 题 013：新增固定 Morgan/Tanimoto；不要求保留黄嘌呤 scaffold；三个 RDKit 性质均为硬门。

本文未冻结的只有必须由独立计算证据决定的连续评分锚点和 CREST 部署版本。它们不是题面
约束的歧义，不得在缺少校准证据时随意填入正式 task pack。
