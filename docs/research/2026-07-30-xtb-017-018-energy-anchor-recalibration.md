# xTB-017/018 能量满分锚点复校报告

日期：2026-07-30  
状态：批准用于当前正式 task pack  
取代：`docs/research/2026-07-21-xtb-total-energy-linear-goal-dossier.md` 中 017/018 的满分目标

## 1. 目标与冻结协议

本次复校只调整两个任务的满分锚点，不调整零分锚点。初始候选 XYZ 来自已执行的
正式 task run，记录在
`docs/research/2026-07-28-vgb-13-task-raw-model-responses.md`；随后又以独立
RDKit/CREST 构象搜索扩展候选集合。复核时不信任答案中自报的能量，而是将每个 XYZ
重新交给当前正式 evaluator。

两项均使用 xTB 6.7.1、GFN2-xTB、`charge=0`、`uhf=0` 和既有结构身份硬门：

- xtb-017（ROY）：提交坐标的 single-point total energy，不先优化；
- xtb-018（Ritonavir）：优化提交坐标后读取 total energy，并在优化前后检查图结构和
  四个指定立体中心。

## 2. 独立 evaluator 结果

所有下表记录均为 `status=scored`，结构身份、显式氢和收敛检查均通过。数值单位为
Hartree。

| task | run candidate | evaluator total energy |
| --- | --- | ---: |
| xtb-017 | gpt-5.5 / skills-on | -50.289476555109 |
| xtb-017 | gpt-5.5 / skills-off | -50.289476346983 |
| xtb-017 | gpt-5.6-terra / skills-on | -50.302550641450 |
| xtb-017 | gpt-5.6-terra / skills-off | -50.302551918742 |
| xtb-017 | gpt-5.6-sol / skills-on | -50.302552185765 |
| xtb-017 | gpt-5.6-sol / skills-off | **-50.302552312418** |
| xtb-018 | gpt-5.5 / skills-on | -148.195251205626 |
| xtb-018 | gpt-5.5 / skills-off | -148.205533111640 |
| xtb-018 | gpt-5.6-terra / skills-on | -148.199583213355 |
| xtb-018 | gpt-5.6-terra / skills-off | -148.202624787938 |
| xtb-018 | gpt-5.6-sol / skills-on | -148.210476869589 |
| xtb-018 | gpt-5.6-sol / skills-off | -148.205916723848 |
| xtb-018 | independent CREST `METADYN1`, frame 625 | **-148.213721794168** |

对两条加粗的最佳候选各独立重复 evaluator 3 次，三次均逐位得到同一能量。因而本
报告将它们定义为当前冻结方法、电子态、身份策略和计算模式下已复核的最低可达值；
这不是对连续势能面的数学全局最小性证明。

## 3. 新的 profile 值

| profile | full-score target `T` | zero-score anchor `B` | unit |
| --- | ---: | ---: | --- |
| `xtb_total_energy_minimize_neg_50p3_neg_50p25_v2` | `-50.302552312418` | `-50.287905192962` | Hartree |
| `xtb_total_energy_minimize_neg_148p2_neg_148p15_v2` | `-148.213721794168` | `-148.183476873812` | Hartree |

只更新 `T`；两个 `B` 与原正式 task pack 完全一致。评分仍使用
`linear_goal_v2` 的 minimize 定义，能量达到或低于 `T` 时得满分。

## 4. 独立构象搜索

为避免锚点只反映现有回答，本次额外进行了与 model run 无关的搜索。RDKit
ETKDGv3/MMFF 预优化后接 xTB 搜索得到的最低值没有超过本报告的最终锚点：ROY 为
`-50.302533412858 Eh`，Ritonavir 为 `-148.203199255607 Eh`。ROY 的完整 CREST
搜索输出 49 个唯一构象，最低 CREST 值约为 `-50.30255230 Eh`，也没有低于
`xtb-017` 的锚点。

Ritonavir 以 ETKDGv3 `randomSeed=424242`、`useRandomCoords=True` 生成独立初始
几何，并以 CREST 2.12 / xTB 6.7.1、GFN2-xTB、`charge=0`、`uhf=0`、`-mquick -T 2`
采样。完整 CREST 聚类在 3600 秒上限前超时，但 `METADYN1` 与 `METADYN6` 两条
67 ps 元动力学轨迹已完整保存。对每条轨迹先选取 6 个低势能且时间分散的快照，再每
约 5 ps 均匀抽取 13 个快照，共 38 个候选；37 个通过正式 evaluator 的优化、图和
立体化学检查，1 个未收敛。最低候选为 `METADYN1` 第 625 帧。

由于未固定线程时该局部优化在末位出现数值差异，最终重复验证固定
`OMP_NUM_THREADS=1`、`OPENBLAS_NUM_THREADS=1` 和 `MKL_NUM_THREADS=1`；对该
精确 XYZ 进行三次独立正式评测均逐位得到 `-148.213721794168 Eh`。该值因此取代
原 run 候选的 Ritonavir 满分锚点。

## 5. 复校后的边界

这些值只可在各自分子、GFN2-xTB、neutral closed-shell、固定 verifier mode 和身份
策略内解释。ROY 与 Ritonavir 的绝对能量不可互比；该复校也不把有限 run 中发现的
候选宣称为实验构象能、晶格能或完整势能面的全局最小值。
