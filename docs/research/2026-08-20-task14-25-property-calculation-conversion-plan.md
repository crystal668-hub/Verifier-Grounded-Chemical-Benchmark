# 专家题 14-25 Property Calculation 转换预期

日期：2026-08-20  
状态：待审批；本文件只描述预期改动，不注册任务、不修改现有 task pack

## 1. 范围与结论

本次审阅对象为：

`/Users/xutao/Documents/bench-task/xutao_task/task14-25/`

其中包含 12 道题的中文题面和 gold answer，题号为 14-25。根据用户要求，12
道题均按 `property_calculation` 方向规划；gold 已由更严谨的科学计算软件或
文献来源验证，因此实现阶段不要求在本机部署对应科学软件，也不把本机 verifier
作为准入条件。

本轮仅提交本审批文档。审批前不会：

- 向 `src/verifier_grounded_benchmark/task/packs/property_calculation/` 添加任务；
- 修改 `tasks.yaml`、`verifier_specs.yaml`、`sample_answers.jsonl`、release inventory
  或注册表；
- 把附件复制进仓库；
- 为这些题实现新的本机 verifier。

审批后，才按本文件的决定实现题面、输入对象、gold schema、评分 profile 和测试。

## 2. 附件可读性审计

附件目录中的文件均可读取，未发现权限、编码损坏或二进制格式阻塞。文本文件均为
ASCII/UTF-8 可读格式；CIF、XYZ 和 Gaussian 输出均可作为普通文本检查。

在当前环境中做了作者侧结构化解析（这不是任务运行时 verifier）：

| 题号 | 附件 | 读取/解析结果 |
| --- | --- | --- |
| 14 | `DEBXIT06.cif` | CIF 可解析；92 atoms，formula `H28 C46 N12 O6`，volume 1793.7802 A^3 |
| 15 | `gaussian.out` | cclib 可解析；Gaussian 16 normal termination；含完整频率和 IR intensity 表 |
| 16 | 无 | 无附件；只有咖啡因-水合物题面和 density gold |
| 17 | 无 | 无附件；只有投料质量、溶剂、来源和 1:1 gold |
| 18 | `Radiprodil_FormA_mi_ucfr.cif`、`Radiprodil_FormC_mi_ucfr.cif` | 两个 CIF 均可解析；各 196 atoms；FormA volume 1848.0008 A^3，FormC volume 1845.7507 A^3 |
| 19 | `A.out`、`AB.out`、`BSSE.out` | 三个 Gaussian 输出均可解析且 normal termination；`BSSE.out` 含 counterpoise corrected energy 和 BSSE energy |
| 20 | `homolumo.out` | cclib 可解析；含 occupied/virtual orbital eigenvalues；normal termination |
| 21 | `conformer.xyz`、`gaussian.out` | XYZ 为 16 atoms；Gaussian 输出含优化完成、最终 Standard orientation 和 normal termination |
| 22 | `NOGCOE.cif` | CIF 可解析；192 atoms，formula `H72 C108 N12`，volume 2430.2272 A^3 |
| 23 | `crest_conformers.xyz` | XYZ 含 3 个 30-atom conformer；可读取每一帧及其坐标 |
| 24 | 无 | 无附件；题面中的 `FI。。。NH3` 表达需确认 |
| 25 | 无 | 无附件；只有分子 SMILES、文献来源和 pKa gold |

附件没有复制到仓库。实现前应将需要公开给参评模型的内容整理成任务内的
`input_objects`；不能在正式 prompt 中依赖 `/Users/...` 路径或不可解析的上传引用。

## 3. 统一任务写法预期

每道题拟采用当前 v2 Property Calculation 公共 envelope：

```yaml
task_type: property_calculation
version: 1
formal_track: true
answer_schema:
  format: final_answer_line
  final_answer_prefix: "FINAL ANSWER:"
  value_type: json
  cardinality: one
gold_provenance:
  disclosure: withheld_initial_release
scoring:
  aggregation: arithmetic_mean
  version: linear_goal_v2
```

题面拟改写为英文、工具中立、可独立阅读的科学问题：不出现 verifier、脚本路径、
本 benchmark、gold 或“请使用某个内部后端”等实现信息。附件若是题目求解所必需的
输入，将以 `input_objects` 的文本值和 prompt 内联块同时保存；大体量 Gaussian
输出不直接整份塞进 YAML，而是保留与答案直接相关的、带上下文的结果片段，并在
维护文档中记录原文件 hash。这样既避免数 MB prompt，也不依赖本地附件路径。

数值 gold 统一使用 `value_type: number` 和 canonical unit，评分采用
`numeric_gold` profile；字符串或离散标签使用 `value_type: string` 和
`exact_string` profile。左右容错宽度、多个字段的 comparison group 和 profile
命名都需要在实现前单独审批，不能把现有两个 profile 的参数直接套用到新性质。

## 4. 逐题转换预期

下表中的 task id 是**暂定名**，仅用于审批和后续测试命名，不代表已经注册。

### 14. DEBXIT06 氢键数量

- 暂定 task id：`property_calc_014_hbond_count`
- 题型：单个整数数值；建议 property `hydrogen_bond_count`，unit `count`。
- 拟题面：给出 `DEBXIT06.cif`，要求统计晶体中每个分子与其他分子形成的氢键总数，
  同时计入该分子作为供体和受体的氢键。
- 输入对象：完整 `DEBXIT06.cif`，`type: cif`，建议 `presentation: prompt_inline`。
- Gold：`12`。
- 评分预期：numeric gold；需要审批整数答案的容错语义（建议只有 12 为满分，
  相邻整数不应意外获得高分）。
- 待确认：CIF 没有 `_geom_hbond` 记录，题面也没有 donor/acceptor、距离和角度阈值。
  如果这是按来源论文的已确定统计结果，应在维护说明中固定计数口径；否则题面需补充
  氢键判据，避免不同模型按不同几何阈值计数。

### 15. Resveratrol 频率和 IR 强度前三

- 暂定 task id：`property_calc_015_ir_top3_frequencies`
- 题型：三个数值字段；建议 `frequency_1`、`frequency_2`、`frequency_3`，unit
  `cm^-1`，同属一个 comparison group。
- 拟题面：提供 M06-2X/cc-pVTZ 优化与频率计算结果片段，要求找出 IR intensity
  最大的三个模式，并报告它们的 harmonic frequencies。
- 输入对象：从 `gaussian.out` 提取 route、三组相关 `Frequencies --`/`IR Inten --`
  行及 normal termination；维护侧保留完整文件 hash `5323390f...ab220d7`。
- Gold 数值集合：`1208.1036`、`1674.0688`、`1685.5562 cm^-1`。
- 评分预期：三个 numeric gold 字段；comparison group 使用 `all`，要求三项都在
  各自容错内。
- 待确认：按 IR intensity 降序应为 1208.1036、1685.5562、1674.0688，但原题答案
  按频率升序列出 1208.1036、1674.0688、1685.5562。实现前必须冻结输出顺序；本计划
  建议按频率升序，并在 prompt 中明确排序规则。

### 16. 咖啡因一水合物晶体密度

- 暂定 task id：`property_calc_016_crystal_density`
- 题型：单个数值；property `crystal_density`，unit `g/cm^3`。
- 原 gold：`1.44728`。
- 现状：没有 CIF、晶胞参数、空间群、Z 值或可由题面重建的晶体结构。仅凭
  `Cn1cnc2c1c(=O)n(C)c(=O)n2C` 和“1:1 水合物”不能唯一得到晶体密度。
- 预期处理：**暂缓实现**。需要补充 CCDC CIF 或至少完整晶胞/组成数据；补齐后再
  采用完整 CIF 内联的标准题面。不能把“CCDC 咖啡因数据”作为不可解析的外部引用。

### 17. Cannabinol–tetramethylpyrazine 共晶比例

- 暂定 task id：`property_calc_017_cocrystal_ratio`
- 题型：单个字符串；property `cocrystal_molar_ratio`，gold `1:1`。
- 拟题面方向：明确询问最终共晶中的组分摩尔比，不把投料质量比当作答案。
- 现状：题面只有投料质量、溶剂和来源，没有最终晶体结构、化学分析或文献摘录。
  投料质量本身不能推出选择性结晶后的共晶化学计量；按分子量换算也只是投料摩尔比，
  不是最终晶体比例。
- 预期处理：**暂缓实现**。需要补充 blind-test 论文中对应结构/组成证据，或将任务
  明确改为“从给定文献摘录读取比例”并把摘录作为输入对象。否则属于外部知识问答，
  不是自洽的固定输入 property calculation。

### 18. Radiprodil FormA/FormC 自由能反转

- 暂定 task id：`property_calc_018_polymorph_free_energy_crossover`
- 题型：一个离散标签加一个温度数值；建议 properties `lower_free_energy_at_0k`
  （exact string，gold `FormC`）和 `crossover_temperature`（numeric，unit `K`，
  gold `343.15`）。
- 输入对象：两个完整 CIF：`Radiprodil_FormA_mi_ucfr.cif`、
  `Radiprodil_FormC_mi_ucfr.cif`。
- 现状：CIF 只能给出结构和晶胞，不能唯一给出自由能随温度的曲线或交叉温度。
  题面没有能量、熵、热容或计算协议。
- 预期处理：**暂缓实现**。需要补充已验证的自由能/温度数据表或计算输出，并明确
  0 K 的比较量（electronic energy、Helmholtz free energy 或其他定义）。补齐后可将
  两个 CIF 与数据摘录一起内联；gold 为 FormC、343.15 K。

### 19. 两分子相互作用能与结合能

- 暂定 task id：`property_calc_019_interaction_binding_energy`
- 题型：两个数值字段 `interaction_energy`、`binding_energy`，unit `kcal/mol`，
  同属一个 comparison group。
- 拟题面：给出二聚体和单体计算结果，要求报告相互作用能与结合能，并保留负号。
- 输入对象：`A.out`、`AB.out`、`BSSE.out` 的相关 SCF/thermal/counterpoise 结果片段；
  不把整份约 1.8 MB Gaussian 文本直接嵌入 prompt。维护侧保留三个原文件 hash。
- Gold：interaction energy `-69.04 kcal/mol`；binding energy `-58.15 kcal/mol`。
- 评分预期：两个 numeric gold 字段，comparison group `all`；需在任务说明中冻结
  interaction/binding 的公式和是否采用 BSSE 修正，避免只凭字段名猜公式。
- 可复核性：三个输出均可解析且 normal termination，BSSE 输出含
  `Counterpoise corrected energy = -1096.945654791773` 和 BSSE energy 行；本机不需要
  重跑 Gaussian。

### 20. HOMO-LUMO gap

- 暂定 task id：`property_calc_020_homo_lumo_gap`
- 题型：单个数值；property `homo_lumo_gap`，unit `eV`。
- 拟题面：给出分子的计算输出或明确的 HOMO/LUMO orbital energies，要求计算能隙。
- 输入对象：`homolumo.out` 中 route、最后一组 occupied/virtual eigenvalue 的相关
  行和 normal termination；维护侧保留原文件 hash `8c42061b...9344ff3`。
- Gold：`7.26 eV`。作者侧从最后一组 alpha orbital energies 得到约 `7.263807 eV`，
  与题面四舍五入值一致。
- 评分预期：numeric gold；需要审批报告精度和容错（建议 prompt 明确报告到 2 位小数，
  profile 仍按未公开 gold 评分）。

### 21. 尿素–磷酸氢键距离

- 暂定 task id：`property_calc_021_hbond_distances`
- 题型：两个数值字段，unit `angstrom`，同属一个 comparison group。
- 拟题面：给出优化后的代表性相互作用单元，要求报告同一个 O-H...O 相互作用中
  covalent O-H 距离和 H...O 接触距离。
- 输入对象：`conformer.xyz` 与 Gaussian 最终几何的相关片段；`conformer.xyz` 仅 16
  atoms，适合完整内联。
- Gold：`1.029 angstrom` 和 `1.485 angstrom`。
- 重要澄清：原题“两个 H 原子到两边 O 的距离”与附件几何不一致；作者侧最终几何显示
  是一个 H 到两个 O 的距离约 1.0293 和 1.4851 A。实现前必须按 atom label/元素关系
  明确字段，避免把问题写成两个不同 H 原子之间的距离。

### 22. CIF 孔隙可接近/不可接近体积比

- 暂定 task id：`property_calc_022_accessible_pore_volume_ratio`
- 题型：单个无量纲数值；property `accessible_to_inaccessible_volume_ratio`，unit
  `ratio`。
- 拟题面：给出 `NOGCOE.cif`，使用半径 1.2 A 球形探针，报告晶胞内可接近体积与不可
  接近体积之比。
- 输入对象：完整 `NOGCOE.cif`，`type: cif`，建议 `presentation: prompt_inline`。
- Gold：`1.713`，来源数值为 `114.008/66.5548`。
- 评分预期：numeric gold；需要在维护文档中记录 accessible/inaccessible 的定义、
  周期边界处理和体积单位。Zeo++ 是 gold 来源，但不作为模型必须调用的工具，也不在
  本机 verifier 中重跑。

### 23. 最低能构象羧基氢间距离

- 暂定 task id：`property_calc_023_carboxyl_hydrogen_distance`
- 题型：单个数值；property `carboxyl_hydrogen_distance`，unit `angstrom`。
- 拟题面：给出多构象 XYZ 及每帧能量，先选择能量最低构象，再报告两个羧基氢原子间
  的距离。
- 输入对象：完整三帧 `crest_conformers.xyz`，`type: xyz_multiframe`；维护侧记录
  原文件 hash `fa82b1ee...36fefc`。三帧能量约为 -49.04209475、-49.04188658、
  -49.04182689，第一帧为最低能构象。
- Gold：`2.521 angstrom`；作者侧第一帧坐标计算为约 `2.52125 A`。
- 评分预期：numeric gold；prompt 必须明确能量排序和“羧基氢”的原子识别规则。

### 24. 卤键相互作用能

- 暂定 task id：`property_calc_024_halogen_bond_energy`
- 题型：单个数值；property `halogen_bond_interaction_energy`，unit `kcal/mol`。
- 原 gold：`-17.11 kcal/mol`。
- 现状：题面中的 `FI。。。NH3` 存在字符/化学式歧义，且没有结构、计算输出、理论
  级别或文献摘录。无法确认是 I-F...NH3、F-I...NH3，还是原题中被截断的其他对象。
- 预期处理：**暂缓实现**。需要确认精确的卤键复合物、能量定义（interaction/binding）、
  计算条件和公开输入证据；确认后再采用单值 numeric gold。

### 25. BAY-069 pKa

- 暂定 task id：`property_calc_025_bay069_pka`
- 题型：单个数值；property `pka`，unit `pKa`，gold `5.7`。
- 拟题面方向：给出完整 SMILES 和明确的 pKa 定义（酸性/碱性位点、溶剂、温度和报告
  约定），要求报告 pKa。
- 现状：当前只有一个复杂分子 SMILES 和论文引用；没有说明测量的是哪个可电离位点，
  也没有 pH/溶剂/温度或文献数据摘录。复杂杂环可能存在多个可讨论的 protonation site。
- 预期处理：**暂缓实现**。需要补充论文中对应 pKa 的实验/计算条件和位点；补齐后可
  使用 exact property definition + numeric gold `5.7`，但不能把裸文献 DOI 当成输入。

## 5. 审批后预计修改面

若审批通过且所有“暂缓实现”项补齐证据，预计只会修改以下范围：

1. `src/verifier_grounded_benchmark/task/packs/property_calculation/tasks.yaml`：新增
   12 个 `property_calculation` task、相应内联输入对象、请求字段和 withheld gold。
2. `src/verifier_grounded_benchmark/task/packs/property_calculation/verifier_specs.yaml`：
   保持空列表；这些题使用 gold comparison，不新增本机 verifier。
3. `src/verifier_grounded_benchmark/task/packs/property_calculation/sample_answers.jsonl`：
   增加公开格式样例，但不泄漏 gold（具体做法按现有发布策略审批）。
4. 评分 profile：为新单位/性质增加经过审批的 numeric gold 或 exact string profile；
   不复用不匹配的旧 profile 参数。
5. `tests/test_property_calculation_tasks.py`：新增 task id、输入对象、结构化附件摘要、
   answer schema、gold 隔离和 prompt 语言约束测试。
6. 必要时新增 `docs/tracks/` 的 property calculation 能力说明，记录外部 gold 来源、
   输入摘要、精度与不可复核边界；不把用户附件路径写入任务 prompt。

不会修改 evaluator 算法、通用 parser 或其他 track，除非审批后发现新字段确实超出当前
schema；若需要扩展 `input_objects` 的类型或多字段答案契约，会先单独提交 schema 设计，
不在新增题目的实现提交中隐式改变公共接口。

## 6. 需要审批的决定

请在实施前确认以下事项：

1. 是否同意 16、17、18、24、25 在补齐自洽输入/方法定义前保持暂缓，而不是用外部引用
   或不可复核 gold 强行注册。
2. 15 的三个频率输出顺序是否冻结为按频率升序；若按 IR intensity 降序，gold 顺序需
   改为 1208.1036、1685.5562、1674.0688。
3. 14 的氢键计数判据、21 的两个距离字段定义、19 的 interaction/binding 公式是否按
   本文所述方式冻结。
4. 是否接受对大体量 Gaussian 输出使用“相关结果片段 + 原文件 hash”的输入策略；如果
   必须逐字提供完整输出，需要另行评估 prompt 体积和发布格式。
5. 是否接受 14、15、19、20、21、22、23 先进入实现准备，待 profile 容错和字段顺序
   审批后再一次性注册；本轮文档本身不做注册。

## 7. 审计命令与结果

本轮已执行只读检查：

```text
git status --short --branch
find .../task14-25 -type f -print
file <all attachments>
wc -lc <all attachments>
uv run --extra materials python ...  # pymatgen/ASE/cclib author-side parsing
uv run pytest                         # approval document change verification
```

在本文件提交前会运行完整测试；测试只验证仓库当前行为，不会验证外部 Gaussian、Zeo++、
CREST 或 pKa 计算结果。
