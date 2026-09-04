# 激发态动力学专家题 Property Calculation 转换记录

日期：2026-08-24
状态：已实施

## 1. 范围

本次将 `题目-batch2/进阶题目/补充题目.txt` 中的 6 道专家题注册为
`property_calculation`。题目覆盖 SOCME、系间窜越、磷光、Herzberg-Teller 贡献和
内转换速率。原始计算结果文件只作为维护侧证据，不进入参评模型可见的 prompt，也不
复制进发布包。

统一转换原则：

- prompt 只保留原始“问题”中的分子、跃迁、温度、气相/溶剂、Kasha 规则和明确要求的
  Herzberg-Teller 条件；
- 电子结构方法、基组、能隙、程序选项和自旋子能级加和方式只作为 gold provenance，
  不写入 prompt；
- 不在 prompt 中出现 ORCA 名称、输出文件名、附件路径、gold 或评分实现；
- 所有答案使用单行 `FINAL ANSWER:` JSON 和 `numeric_gold` 评分。

## 2. 逐题理解与标准化

| task_id | 出题核心 | 冻结答案与单位 | 数值容错宽度 |
|---|---|---:|---:|
| `property_calculation_advanced_015_formaldehyde_socme` | 气相 formaldehyde 的 T1-S0 SOCME，并以 `eV` 报告 | `0.00734 eV` | `0.0001 eV` |
| `property_calculation_advanced_016_anthracene_isc_rate` | Kasha 规则下气相 anthracene 在 77 K 的 S1 ISC 速率 | `1.17e8 s^-1` | `1e7 s^-1` |
| `property_calculation_advanced_017_biacetyl_phosphorescence_rate` | biacetyl 在乙醇 CPCM 模型和 298 K 下的磷光速率 | `98 s^-1` | `1 s^-1` |
| `property_calculation_advanced_018_anthracene_ht_contribution` | 气相 anthracene 在 77 K 的 S1-to-T1 ISC 速率中 HT 项占比 | `100 percent` | `1 percent` |
| `property_calculation_advanced_019_acetophenone_isc_rate` | 气相 acetophenone 在 77 K、包含 HT 效应的 S1-to-T1 ISC 速率 | `2.84e10 s^-1` | `1e8 s^-1` |
| `property_calculation_advanced_020_azulene_internal_conversion_rate` | azulene 在甲醇 CPCM 模型和 298.15 K 下的 S1-to-S0 IC 速率 | `3.82e8 s^-1` | `1e7 s^-1` |

容错宽度按专家答案的报告精度冻结，是 `linear_goal_v2` 中从 gold 线性衰减到零分的
宽度，不是满分区间。

## 3. 维护侧结果复核

原始文件哈希：

| 文件 | SHA-256 |
|---|---|
| `补充题目.txt` | `b0c5852f5aa69fc857e4a417daf57f47d817ee0c42354187156fd13a354c26ea` |
| `ISC_anthracene/kISC_S1-T1_HT.out` | `fdad7106526d05acde2140f9d4b57a285e3d9cc4feb8d0c104bbad86f8fb23e0` |
| `ISC_acetophenone/kISC_S1-T1_HT.out` | `b5cc0907c77b9fd5cba24445ecd0567b30ca79bc0d32989d6218ca55e5a725d8` |

Anthracene 输出的三个 T1 自旋子能级速率分别为 `2.249924e-1`、`9.916970e-5` 和
`2.245086e-1 s^-1`；每一项均明确写为 `0.00 from FC and 100.00 from HT`，因此加和后
HT 占比仍为 `100 percent`。

Acetophenone 输出的三个 T1 自旋子能级速率分别为 `1.386943e10`、`7.028204e8` 和
`1.381656e10 s^-1`。加和得到 `2.83888104e10 s^-1`，按专家题面精度为
`2.84e10 s^-1`。

Formaldehyde 来源同时给出 `59.19 cm^-1`；使用
`1 cm^-1 = 1.239841984e-4 eV` 换算为约 `0.00733862 eV`，与冻结答案 `0.00734 eV`
一致。其余三题以所引 ORCA 6.1.1 手册示例结果作为 gold 来源。

## 4. 注册边界

本次不新增运行时 verifier，不要求本机部署量化计算软件，也不把 `.out`、`.inp` 或
`.hess` 文件内联进 task。`input_objects` 只记录题面中的 SMILES；gold 生成和复核协议
仅保留在本维护记录及 `gold_provenance` 中，不进入 prompt。
