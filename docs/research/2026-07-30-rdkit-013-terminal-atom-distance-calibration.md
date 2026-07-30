# RDKit-013 末端原子距离校准报告

日期：2026-07-30  
状态：批准用于正式 task pack  
取代：`2026-07-23-expert-open-generation-009-013-calibration.md` 中题 012 的端点碳校准

## 1. 性质定义

`rdkit_chain_end_to_end_max_013` 保留原有六碳非环饱和链 domain 和冻结构象协议，但主性质从两个六碳链端点碳的距离改为 `terminal_atom_distance`。

末端重原子定义为重原子图中恰好只有一个重原子邻居的非氢原子。对最低 UFF 能量的已收敛构象枚举所有末端重原子对，主性质取最大的原子核欧氏距离。显式或隐式氢均不参与。verifier 同时报告 `terminal_atom_indices` 和实际最大距离对应的 `terminal_atom_pair_indices`。

这个定义使 `CCCCCC` 仍测量两个末端 C，而 `FCCCCCCCl` 测量 F-Cl。它不是轮廓长度，也不宣称找到真实全局最低能构象。

## 2. 冻结协议

- RDKit `2026.3.2`；
- `Chem.AddHs` 后总原子数不超过 40；
- ETKDGv3，seed `61453`，请求 20 个构象，`pruneRmsThresh=0.5 Angstrom`；
- UFF，最多 200 次优化，只保留返回收敛状态的构象；
- 按 `(UFF energy, conformer_id)` 选择最低构象；
- 单组分、中性，允许 H、C、N、O、S、F、Cl，且恰有 6 个碳并匹配冻结六碳链 SMARTS。

## 3. 候选调研

调研覆盖未取代正己烷、两端 F/N/O/S/Cl 对照、全氟六碳链、对称多硫端基系列，以及不同端基长度、端帽和碳链卤代方式的非对称候选。所有表中结果均由当前正式 evaluator 和上述冻结协议重算。

| candidate | 含氢总原子数 | retained / converged | distance (Angstrom) | score | 角色 |
|---|---:|---:|---:|---:|---|
| `CCCCCC` | 20 | 7 / 7 | 6.368444271088 | 0.000551 | 零分低端对照 |
| `FCCCCCCF` | 20 | 16 / 16 | 7.652357465444 | 0.084358 | 双氟对照 |
| `NCCCCCCN` | 24 | 16 / 16 | 7.784393292066 | 0.092976 | 双氨基对照 |
| `ClCCCCCCCl` | 20 | 14 / 14 | 8.197082673019 | 0.119914 | 双氯对照 |
| `OCCCCCCO` | 22 | 18 / 18 | 8.636791004936 | 0.148616 | 双羟基对照 |
| `FC(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)F` | 20 | 13 / 13 | 8.683478444126 | 0.151663 | 全氟碳链对照 |
| `SCCCCCCS` | 22 | 16 / 16 | 9.363790052755 | 0.196070 | 双硫醇对照 |
| `FSSSSSCCCCCCSSSSSF` | 30 | 20 / 20 | 16.361776284225 | 0.652857 | 中高端多硫对照 |
| `FSSSSSSSSC(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)SSSSSSSF` | 35 | 20 / 16 | 21.686562287507 | 1.000000 | 高端正例 |

旧高端候选全氟六碳链的端点碳距离为 `6.492878991220 Angstrom`；按新性质计量时，最远末端 F-F 距离为 `8.683478444126 Angstrom`。这直接证明旧 `T=6.49` 不可沿用。

## 4. 构象数敏感性与确定性

| candidate | 请求构象数 | retained / converged | selected conformer | distance (Angstrom) |
|---|---:|---:|---:|---:|
| `CCCCCC` | 5 | 4 / 4 | 1 | 5.556656017522 |
| `CCCCCC` | 10 | 5 / 5 | 4 | 6.368444271088 |
| `CCCCCC` | 20 | 7 / 7 | 4 | 6.368444271088 |
| `CCCCCC` | 40 | 8 / 8 | 4 | 6.368444271088 |
| 高端正例 | 5 | 5 / 4 | 0 | 21.686562287507 |
| 高端正例 | 10 | 10 / 7 | 0 | 21.686562287507 |
| 高端正例 | 20 | 20 / 16 | 0 | 21.686562287507 |
| 高端正例 | 40 | 40 / 26 | 0 | 21.686562287507 |

两次独立的 20 构象运行逐值一致。高端正例从 5 到 40 个请求构象均选择同一构象和值；正己烷从 10 到 40 个请求构象也保持不变。正式协议仍冻结为 20 个请求构象，表中的敏感性结果不把性质解释为全局构象搜索。

## 5. 评分锚点

冻结 maximize profile：

```text
property: terminal_atom_distance
unit: angstrom
B = 6.36
T = 21.68
score = clip((distance - 6.36) / 15.32, 0, 1)
```

`B=6.36 Angstrom` 由正己烷低端对照继续支撑。`T=21.68 Angstrom` 取高端正例的可复现值 `21.686562287507 Angstrom` 向下保留两位小数，使该批准正例达到满分。锚点来自预先列出的合法校准候选和冻结 verifier，不使用正式模型提交反向定标。

当前 profile ID 为 `rdkit_terminal_atom_distance_maximize_6p36_21p68_v2`，verifier ID 为 `rdkit_terminal_atom_distance_uff_v2`。历史 release 工件保留旧 profile 和 verifier，不做回写。

## 6. 配置哈希

对 YAML 解析后的对象执行 sorted-key、compact-separator canonical JSON，再取 SHA-256：

| object | SHA-256 |
|---|---|
| profile `rdkit_terminal_atom_distance_maximize_6p36_21p68_v2` | `47f165a21382256bd2cdd20792b07d719ec868d0bc91a2c19beff1be6f13b50b` |
| verifier `rdkit_terminal_atom_distance_uff_v2` | `1531ce0674ee8df15ab5be8f9e1d8a97482652142af70e23f0d700e242b5a39b` |
| task `rdkit_chain_end_to_end_max_013` version 2 | `44d6e51d8716c6de1b4a772748cacdcc8d29d4a91341589e0d3991b50bde33b2` |
