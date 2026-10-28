# 标准任务难度等级

生效日期：2026-10-28。

正式 benchmark 任务统一使用两档 difficulty：

- basic：基础级。
- advanced：进阶级。

Open-generation 与 property-calculation tracks 使用相同的等级词表。
正式任务不再使用 simple、intermediate 或 expert 标签。
该分类是任务元数据，不改变题目、可行域、验证流程、评分曲线或通过阈值，
也不自动对应某个模型成功率区间。

## 当前任务分类

| Track | basic | advanced |
| --- | --- | --- |
| open_generation_rdkit | rdkit_001–rdkit_010（10 题） | rdkit_011–rdkit_014（4 题） |
| open_generation_xtb | xtb_001–xtb_013（13 题） | xtb_014–xtb_020（7 题） |
| property_calculation_basic | 全部任务 | — |
| property_calculation_advanced | — | 全部任务 |

Open-generation 合计 23 道 basic、11 道 advanced，共 34 道题。
正式标签以 src/verifier_grounded_benchmark/task/packs/ 下各 tasks.yaml 为准。
上表的编号范围是当前任务清单的显式分类，不是新任务按编号自动分级的规则。

## 历史资料与后续校准

历史 release 快照、校准资料及研究报告保留当时的难度标签；
其旧标签不作为当前正式任务分类依据。
xtb-task-quality-evaluation.md 中原四档模型成功率区间属于旧设计，
不能直接套用到新的两档分类；若需要经验难度校准，应另行确定模型面板、
工具权限、搜索预算和成功标准，再制定两档的校准区间。
