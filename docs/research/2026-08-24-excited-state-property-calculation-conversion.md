# 激发态动力学专家题 Property Calculation 转换记录

日期：2026-08-24
状态：已实施

## 1. 范围

本次将 `题目-batch2/进阶题目/补充题目.txt` 中的 6 道专家题注册为
`property_calculation`。题目覆盖 SOCME、系间窜越、磷光、Herzberg-Teller 贡献和
内转换速率。原始计算结果文件只作为维护侧证据，不进入参评模型可见的 prompt，也不
复制进发布包。

统一转换原则：

- 保留分子、跃迁、温度、溶剂模型、电子结构方法、能隙和需加和的自旋子能级；
- 将 `DoHT`、`UseJ`、`NACME`、`ETF` 等程序选项改写为对应的科学协议描述；
- 不在 prompt 中出现 ORCA 名称、输出文件名、附件路径、gold 或评分实现；
- 所有答案使用单行 `FINAL ANSWER:` JSON 和 `numeric_gold` 评分。

## 2. 逐题理解与标准化

| task_id | 出题核心 | 冻结答案与单位 | 数值容错宽度 |
|---|---|---:|---:|
| `property_calc_015_formaldehyde_socme` | 固定 B3LYP/def2-SVP 气相 SOC-TD-DFT 协议，读取 T1-S0 SOCME 并由 `cm^-1` 换算为 `eV` | `0.00734 eV` | `0.0001 eV` |
| `property_calc_016_anthracene_isc_rate` | Kasha 规则下，从 S1 出发汇总 S1-to-T1、S1-to-T2 及各自三个三重态自旋子能级的 ISC 速率 | `1.17e8 s^-1` | `1e7 s^-1` |
| `property_calc_017_biacetyl_phosphorescence_rate` | 固定乙醇 CPCM、298 K、RI-SOMF(1X) 与 HT 协议下的磷光速率 | `98 s^-1` | `1 s^-1` |
| `property_calc_018_anthracene_ht_contribution` | 固定 S1-to-T1 ISC 协议下，区分 Franck-Condon 与 Herzberg-Teller 两项并报告 HT 百分比 | `100 percent` | `1 percent` |
| `property_calc_019_acetophenone_isc_rate` | 对 T1 的 `-1/0/+1` 三个自旋子能级速率求和，且保留 HT 效应 | `2.84e10 s^-1` | `1e8 s^-1` |
| `property_calc_020_azulene_internal_conversion_rate` | 固定甲醇 CPCM、298.15 K、NACME、ETF 与 J-correlation 协议下的 S1-to-S0 IC 速率 | `3.82e8 s^-1` | `1e7 s^-1` |

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
`.hess` 文件内联进 task。`input_objects` 只记录题面中的 SMILES；计算协议直接写入
prompt，使任务在不依赖本地附件路径的情况下保持可独立阅读。
