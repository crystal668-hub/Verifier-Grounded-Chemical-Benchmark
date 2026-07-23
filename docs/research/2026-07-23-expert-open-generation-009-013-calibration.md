# 专家开放生成题 009-013 校准报告

日期：2026-07-23  
状态：批准用于正式 task pack  
规格：`docs/design/expert-open-generation-tasks-009-013.md`

## 1. 范围与冻结原则

本报告只冻结规格中尚待独立计算决定的三组连续评分锚点和 CREST 部署版本。候选在写入正式 task pack 前固定，未使用正式模型提交反向定标。题 009 复用已批准的 LogP profile；题 013 使用 Tanimoto 定义域 `[0, 1]`，二者不需要额外经验锚点。

所有新增 profile 使用 `linear_goal_v2`。下表中的 `T` 是满分目标，`B` 是零分锚点：

| task_id | property | direction | T | B |
|---|---|---|---:|---:|
| `xtb_odd_element_counts_gap_max_019` | `homo_lumo_gap` (eV) | maximize | 11.9 | 3.6 |
| `xtb_pyrene_substituent_energy_min_020` | `total_energy` (Hartree) | minimize | -63.56975 | -63.5669 |
| `rdkit_chain_end_to_end_max_013` | `chain_end_to_end_distance` (Angstrom) | maximize | 6.49 | 6.36 |

## 2. 冻结环境和协议

- RDKit：2026.3.2。
- xTB：6.7.1，GFN2-xTB，显式 `charge=0`、`uhf=0`。
- CREST：2.12，单线程，`-mquick`；环境定义在 `envs/crest-xtb.yml`。
- CREST 初始几何：RDKit ETKDGv3，seed `61453`。
- 六碳链：ETKDGv3，seed `61453`，20 个请求构象，pruning `0.5 Angstrom`，UFF，最多 200 次优化迭代。

CREST 3.0.2 在本机 smoke 中于内部 tblite 初始优化失败，而相同几何可由 xTB 6.7.1 正常处理。因此没有把 3.0.2 标为可发布环境；冻结组合为已完成 ensemble 和最终 single-point 的 CREST 2.12 / xTB 6.7.1。

## 3. 题 010：奇数元素计数下的 gap

校准候选均通过元素计数、显式氢、连通性、中性闭壳层和 `dipole < 2 D` 硬门。偶极和 gap 来自同一次收敛的 xTB optimization。

| candidate SMILES（用于生成校准 XYZ） | dipole (D) | gap (eV) | 角色 |
|---|---:|---:|---|
| `COC(F)CCC` | 1.851 | 11.893113997256 | 高端正例 |
| `COC(C)C(F)C` | 1.650 | 10.787301647553 | 正例 |
| `Cc1c(F)cccc1Cl` | 1.223 | 4.268465907006 | 低端对照 |
| `Cc1cc(O)ccc1S` | 1.369 | 3.629911216719 | 零分锚点 near-miss |

高端值向一位小数取整为 `T=11.9 eV`，低端 near-miss 向一位小数取整为 `B=3.6 eV`。`COC(F)CCC` 通过正式 evaluator 的 live score 为 `0.9991703611151806`。偶极达到或超过 2 D 的候选只用于硬门负例，不进入 gap 锚点估计。

## 4. 题 011：芘三取代异构体能量

三个候选分别覆盖相邻、分散和相对取代位点。全部通过搜索前后 graph-delta identity 检查；能量来自 CREST ensemble 最低成员的 xTB single-point。

| reference site indices | conformers | total energy (Hartree) | 角色 |
|---|---:|---:|---|
| `[0, 1, 3]` | 2 | -63.569741808302 | 高端正例 |
| `[0, 3, 6]` | 7 | -63.567042166436 | 中间对照 |
| `[0, 6, 8]` | 4 | -63.566923860259 | 零分锚点 near-miss |

冻结 `T=-63.56975 Eh`、`B=-63.5669 Eh`。对 `[0, 1, 3]` 候选的独立端到端 smoke 得到 2 个构象和 `-63.569739738933 Eh`，与校准值相差约 `2.07e-6 Eh`，落在批准的重复性范围内。该分数仅比较同 formula、charge、电子态和冻结协议下的代理能量，不解释为实验生成自由能、平衡丰度或合成产率。

## 5. 题 012：六碳链端到端距离

以下结果来自完全相同的 ETKDGv3/UFF workflow；候选在正式 task pack 冻结前选定。

| candidate | distance (Angstrom) | 角色 |
|---|---:|---|
| `CCCCCC` | 6.368444271088 | n-hexane reference / 低端对照 |
| `FCCCCCCF` | 6.375545548051 | 合法取代对照 |
| `NCCCCCCN` | 6.388652406996 | 合法取代对照 |
| `OCCCCCCO` | 6.376836213144 | 合法取代对照 |
| `FC(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)F` | 6.492878991220 | 伸展正例 |
| `ClCCCCCCCl` | 6.384482193199 | 合法取代对照 |

冻结 `B=6.36 Angstrom`、`T=6.49 Angstrom`。固定 seed 的重复运行逐值一致。5/10/20/40 个请求构象的敏感性检查表明，部分候选在更大 ensemble 中会选到不同的更低 UFF 能量构象；因此这里明确冻结的是“20 个请求构象的有限 workflow”，不是全局最低能构象。20 构象结果可重现，且 n-hexane 与全氟候选分别稳定支撑冻结锚点。

## 6. 配置哈希

哈希算法与 release builder 的 scoring-profile 算法一致：对解析后的对象执行 sorted-key、compact-separator canonical JSON，再取 SHA-256。

| object | SHA-256 |
|---|---|
| profile `xtb_odd_element_gap_maximize_3p6_11p9_v2` | `8cf86edef7aa2d6dc92e6a366af719f280a9d41dd22cb62d25a01076d91fb091` |
| verifier `xtb_odd_element_gap_dipole_gfn2_v1` | `b341ac58634cde19812fd240146db190fb082c0f94cc6579e6f2cb18ef284188` |
| profile `xtb_pyrene_total_energy_minimize_neg_63p56975_neg_63p5669_v2` | `ba4bec5068abe3daa0c0dbcd90eb93d110402492f521d0e6be04a9abf7cc0ded` |
| verifier `xtb_pyrene_crest_energy_v1` | `b19c091dd8818792fcf67f9688b9154ca274df7969e116754e005fd74caed36c` |
| profile `rdkit_chain_end_to_end_maximize_6p36_6p49_v2` | `d5a8a4ac6d1b84619a5659c5999e144058c5fef5dcea98018fa9d2e772c61b91` |
| verifier `rdkit_chain_end_to_end_uff_v1` | `3a75a5ee89bf71799282a5e6207edb25ff9a4f57a31ec40c23cd9fb426ee13ef` |

任务文件、全部 scoring profiles 和构建产物的最终哈希由 `scripts/release/build_release.py` 在 release 构建时生成；本报告不修改历史 release artifact。
