# 专家题 14-25 Property Calculation 转换预期

日期：2026-08-20
状态：已获审批并实施；本文件同时记录实际注册结果和保留的解释边界

## 1. 范围与结论

本次审阅对象为：

`/Users/xutao/Documents/bench-task/xutao_task/task14-25/`

其中包含 12 道题的中文题面和 gold answer，题号为 14-25。根据用户要求，12
道题均按 `property_calculation` 方向规划；gold 已由更严谨的科学计算软件或
文献来源验证，因此实现阶段不要求在本机部署对应科学软件，也不把本机 verifier
作为准入条件。

上一轮仅提交本审批文档；本轮根据用户审批开始实施。此前不会：

- 向 `src/verifier_grounded_benchmark/task/packs/property_calculation/` 添加任务；
- 修改 `tasks.yaml`、`verifier_specs.yaml`、`sample_answers.jsonl`、release inventory
  或注册表；
- 把附件复制进仓库；
- 为这些题实现新的本机 verifier。

本轮已按本文件的决定实现题面、输入对象、gold schema、评分 profile 和测试。

## 1.1 已确认的审批决定

1. 16、17、18、24、25 全部进入正式注册。专家提供的 gold answer 作为冻结目标；
   是否能在本机用同一科学软件重算，不作为纳入正式 task 的判断条件。
2. 15 只要求报告 IR intensity 最大的三个模式对应的 frequencies；三个频率按无序
   集合比较，输出顺序不影响正确性。
3. 14、19、21 按本文原定方式冻结：14 使用来源定义的 12 根氢键计数，19 分别报告
   interaction/binding energy，21 报告同一 O-H...O 中的 O-H 与 H...O 两个距离。
4. 12 道题全部正式注册；仍会把题面定义、输入证据和外部 gold 来源写清楚，避免把
   “信任 gold”误写成“题面已经足以从头推导 gold”。
5. 第24题的 `FI...NH3` 按原始题面逐字保留，不擅自规范化为 `F-I...NH3` 或反转原子
   顺序；该字符串歧义已在实现记录中显式保留。

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

附件没有复制到仓库。实现时仅将原题明确要求答题者查看的 CIF/XYZ 或分子对象整理成
任务内的 `input_objects`；Gaussian `.out` 不属于答题者可见输入，不能在正式 prompt 中
依赖 `/Users/...` 路径或不可解析的上传引用。

### 大体量 Gaussian 输出的体积

按附件原始 UTF-8/ASCII 字节统计，若完整逐字放入模型可见 prompt：

| 题目 | 文件 | 字节/字符 | 行数 | 约合 token* |
| --- | --- | ---: | ---: | ---: |
| 15 | `gaussian.out` | 914,119 | 13,608 | 229k |
| 19 | `A.out` + `AB.out` + `BSSE.out` | 1,951,780 | 29,210 | 488k |
| 20 | `homolumo.out` | 425,124 | 6,295 | 106k |
| 21 | `gaussian.out` | 1,069,126 | 16,701 | 267k |
| 合计 | 上述 6 个 Gaussian 文件 | 4,360,149 | 72,206 | 1.09M |

\* token 按约 4 个 ASCII 字符/token 粗略估计，实际值取决于 tokenizer。当前 task v2
这些文件的体积仅用于维护侧容量审计；它们不写入 `input_objects`，也不进入答题者
prompt。CIF/XYZ 等明确可见附件仍按完整内容内联；这不改变 gold 的信任决定。

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
输入，将以 `input_objects` 的文本值和 prompt 内联块同时保存；Gaussian `.out` 只保留
维护侧来源和 hash，不写入正式任务。这样既避免数 MB prompt，也不依赖本地附件路径。

数值 gold 统一使用 `value_type: number` 和 canonical unit，评分采用
`numeric_gold` profile；字符串或离散标签使用 `value_type: string` 和
`exact_string` profile。左右容错宽度、多个字段的 comparison group 和 profile
命名都需要在实现前单独审批，不能把现有两个 profile 的参数直接套用到新性质。

## 4. 逐题转换预期

下表中的 task id 是**暂定名**，仅用于审批和后续测试命名，不代表已经注册。

### 14. DEBXIT06 氢键数量

- 暂定 task id：`property_calc_003_hbond_count`
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

- 暂定 task id：`property_calc_004_ir_top3_frequencies`
- 题型：三个数值字段；建议 `frequency_1`、`frequency_2`、`frequency_3`，unit
  `cm^-1`，同属一个 comparison group。
- 拟题面：说明 M06-2X/cc-pVTZ 优化与频率计算背景，要求报告 IR intensity 最大的三个
  模式对应的 harmonic frequencies。
- 输入对象：无 Gaussian 输出输入对象；`gaussian.out` 仅作为维护侧证据留存，不进入
  答题者可见 prompt。
- Gold 数值集合：`1208.1036`、`1674.0688`、`1685.5562 cm^-1`。
- 评分预期：三个 numeric gold 字段；comparison group 使用 `all`，要求三项都在
  各自容错内。
- 已冻结：不比较输出顺序。答案解析后将三个频率作为无序集合与三个 gold 数值比较；
  prompt 只要求报告这三个频率，不声明排序规则。

### 16. 咖啡因一水合物晶体密度

- 暂定 task id：`property_calc_005_crystal_density`
- 题型：单个数值；property `crystal_density`，unit `g/cm^3`。
- 原 gold：`1.44728`。
- 现状：没有 CIF、晶胞参数、空间群、Z 值或可由题面重建的晶体结构。仅凭
  `Cn1cnc2c1c(=O)n(C)c(=O)n2C` 和“1:1 水合物”不能唯一得到晶体密度。
- 正式注册决定：按专家 gold `1.44728 g/cm^3` 注册。由于当前没有晶胞/空间群输入，
  prompt 将明确这是基于 1:1 caffeine monohydrate crystal 的参考值计算题，并在
  `gold_provenance`/维护文档中标注外部 CCDC 数据来源；不声称仅凭裸 SMILES 可以唯一
  重建该密度。

### 17. Cannabinol–tetramethylpyrazine 共晶比例

- 暂定 task id：`property_calc_006_cocrystal_ratio`
- 题型：单个字符串；property `cocrystal_molar_ratio`，gold `1:1`。
- 拟题面方向：明确询问最终共晶中的组分摩尔比，不把投料质量比当作答案。
- 现状：题面只有投料质量、溶剂和来源，没有最终晶体结构、化学分析或文献摘录。
  投料质量本身不能推出选择性结晶后的共晶化学计量；按分子量换算也只是投料摩尔比，
  不是最终晶体比例。
- 正式注册决定：按专家 gold `1:1` 注册。prompt 将保留投料与结晶条件，并明确答案
  是最终共晶的摩尔比；维护文档标注该比例来自 blind-test 来源，而不是由投料质量比
  直接推导。

### 18. Radiprodil FormA/FormC 自由能反转

- 暂定 task id：`property_calc_007_polymorph_free_energy_crossover`
- 题型：一个离散标签加一个温度数值；建议 properties `lower_free_energy_at_0k`
  （exact string，gold `FormC`）和 `crossover_temperature`（numeric，unit `K`，
  gold `343.15`）。
- 输入对象：两个完整 CIF：`Radiprodil_FormA_mi_ucfr.cif`、
  `Radiprodil_FormC_mi_ucfr.cif`。
- 现状：CIF 只能给出结构和晶胞，不能唯一给出自由能随温度的曲线或交叉温度。
  题面没有能量、熵、热容或计算协议。
- 正式注册决定：按专家 gold `FormC`、`343.15 K` 注册。prompt 将明确任务要求报告
  0 K 较低者和自由能反转温度；CIF 作为结构上下文，外部自由能曲线/计算来源记录在
  gold provenance 中，不把本机能量重算作为前置条件。

### 19. 两分子相互作用能与结合能

- 暂定 task id：`property_calc_008_interaction_binding_energy`
- 题型：两个数值字段 `interaction_energy`、`binding_energy`，unit `kcal/mol`，
  同属一个 comparison group。
- 拟题面：给出二聚体分子对象，要求报告专家验证的相互作用能与结合能，并保留负号。
- 输入对象：仅保留二聚体分子式参考；`A.out`、`AB.out`、`BSSE.out` 是维护侧证据，
  不进入答题者可见 prompt。
- Gold：interaction energy `-69.04 kcal/mol`；binding energy `-58.15 kcal/mol`。
- 评分预期：两个 numeric gold 字段，comparison group `all`；需在任务说明中冻结
  interaction/binding 的公式和是否采用 BSSE 修正，避免只凭字段名猜公式。
- 可复核性：三个输出均可解析且 normal termination；它们只用于维护侧证据和 gold 来源
  追踪，本机不需要重跑 Gaussian。

### 20. HOMO-LUMO gap

- 暂定 task id：`property_calc_009_homo_lumo_gap`
- 题型：单个数值；property `homo_lumo_gap`，unit `eV`。
- 拟题面：给出分子 SMILES，要求报告专家验证的 HOMO-LUMO gap。
- 输入对象：分子 SMILES；`homolumo.out` 仅作为维护侧证据留存，不进入答题者可见 prompt。
- Gold：`7.26 eV`。作者侧从最后一组 alpha orbital energies 得到约 `7.263807 eV`，
  与题面四舍五入值一致。
- 评分预期：numeric gold；需要审批报告精度和容错（建议 prompt 明确报告到 2 位小数，
  profile 仍按未公开 gold 评分）。

### 21. 尿素–磷酸氢键距离

- 暂定 task id：`property_calc_010_hbond_distances`
- 题型：两个数值字段，unit `angstrom`，同属一个 comparison group。
- 拟题面：给出优化后的代表性相互作用单元，要求报告同一个 O-H...O 相互作用中
  covalent O-H 距离和 H...O 接触距离。
- 输入对象：原题明确提到的 `conformer.xyz`，完整内联；Gaussian 最终几何只作为维护侧
  证据，不进入答题者可见 prompt。
- Gold：`1.029 angstrom` 和 `1.485 angstrom`。
- 重要澄清：原题“两个 H 原子到两边 O 的距离”与附件几何不一致；作者侧最终几何显示
  是一个 H 到两个 O 的距离约 1.0293 和 1.4851 A。实现前必须按 atom label/元素关系
  明确字段，避免把问题写成两个不同 H 原子之间的距离。

### 22. CIF 孔隙可接近/不可接近体积比

- 暂定 task id：`property_calc_011_accessible_pore_volume_ratio`
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

- 暂定 task id：`property_calc_012_carboxyl_hydrogen_distance`
- 题型：单个数值；property `carboxyl_hydrogen_distance`，unit `angstrom`。
- 拟题面：给出多构象 XYZ 及每帧能量，先选择能量最低构象，再报告两个羧基氢原子间
  的距离。
- 输入对象：完整三帧 `crest_conformers.xyz`，`type: xyz_multiframe`；维护侧记录
  原文件 hash `fa82b1ee...36fefc`。三帧能量约为 -49.04209475、-49.04188658、
  -49.04182689，第一帧为最低能构象。
- Gold：`2.521 angstrom`；作者侧第一帧坐标计算为约 `2.52125 A`。
- 评分预期：numeric gold；prompt 必须明确能量排序和“羧基氢”的原子识别规则。

### 24. 卤键相互作用能

- 暂定 task id：`property_calc_013_halogen_bond_energy`
- 题型：单个数值；property `halogen_bond_interaction_energy`，unit `kcal/mol`。
- 原 gold：`-17.11 kcal/mol`。
- 现状：题面中的 `FI。。。NH3` 存在字符/化学式歧义，且没有结构、计算输出、理论
  级别或文献摘录。无法确认是 I-F...NH3、F-I...NH3，还是原题中被截断的其他对象。
- 正式注册决定：按专家 gold `-17.11 kcal/mol` 注册。prompt 保留原题对象为
  `FI...NH3`，不擅自猜测化学式或原子顺序；若后续需要化学规范化，应作为单独的题面
  修订处理。

### 25. BAY-069 pKa

- 暂定 task id：`property_calc_014_bay069_pka`
- 题型：单个数值；property `pka`，unit `pKa`，gold `5.7`。
- 拟题面方向：给出完整 SMILES 和明确的 pKa 定义（酸性/碱性位点、溶剂、温度和报告
  约定），要求报告 pKa。
- 现状：当前只有一个复杂分子 SMILES 和论文引用；没有说明测量的是哪个可电离位点，
  也没有 pH/溶剂/温度或文献数据摘录。复杂杂环可能存在多个可讨论的 protonation site。
- 正式注册决定：按专家 gold `5.7` 注册。prompt 将保留给定 SMILES，并在可确认范围内
  写明 pKa 是文献报告值；若无法从附件确认酸碱位点、溶剂或温度，则在任务 metadata
  中标记这些定义来自专家来源，不把本机 pKa 预测当作注册前置条件。

## 5. 实际修改面

本轮实际修改范围如下：

1. `src/verifier_grounded_benchmark/task/packs/property_calculation/tasks.yaml`：注册
   12 个 `property_calculation` task；删除 Gaussian `.out` 摘录输入，仅保留题面明确要求
   可见的 CIF/XYZ/分子对象输入。
2. `src/verifier_grounded_benchmark/task/packs/property_calculation/verifier_specs.yaml`：
   保持空列表；这些题使用 gold comparison，不新增本机 verifier。
3. `src/verifier_grounded_benchmark/task/packs/property_calculation/sample_answers.jsonl`：
   增加公开格式样例，但不泄漏 gold（具体做法按现有发布策略审批）。
4. 评分 profile：为新单位/性质增加经过审批的 numeric gold 或 exact string profile；
   不复用不匹配的旧 profile 参数。
5. `tests/test_property_calculation_tasks.py`：新增 task id、输入对象、结构化附件摘要、
   answer schema、gold 隔离和 prompt 语言约束测试；另更新公共 API、发布清单和安装包
   smoke test 对正式任务总数的断言。
6. 必要时新增 `docs/tracks/` 的 property calculation 能力说明，记录外部 gold 来源、
   输入摘要、精度与不可复核边界；不把用户附件路径写入任务 prompt。

不会修改 evaluator 算法、通用 parser 或其他 track，除非审批后发现新字段确实超出当前
schema；若需要扩展 `input_objects` 的类型或多字段答案契约，会先单独提交 schema 设计，
不在新增题目的实现提交中隐式改变公共接口。

## 6. 已决事项与保留边界

以下决定已获确认并已落实：

1. 16、17、18、24、25 信任专家 gold，均正式注册，不以本机重算作为准入条件。
2. 15 的三个频率使用 `unordered_numeric` comparison group，输出顺序不计对错。
3. 14、19、21 按本文冻结的字段定义注册。
4. Gaussian `.out` 文件不进入答题者可见 prompt；原始文件仅作为开发和维护阶段的证据
   留存，原始体积审计仍保留在本文件。
5. 14-25 全部进入正式 property-calculation pack；本轮没有新增本机 verifier。

仍保留的边界：第24题的 `FI...NH3` 是原题保留字符串，化学式/原子顺序未被推断；数值
容错采用 tasks.yaml 中记录的 profile 参数，后续若要改变需单独修订评分版本或 profile。

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

本轮完整测试结果：`530 passed, 7 skipped`。测试只验证仓库当前行为，不会验证外部
Gaussian、Zeo++、CREST 或 pKa 计算结果。
