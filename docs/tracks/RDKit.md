# RDKit 题目设计与实现同步

更新日期：2026-06-11

## 1. 设计来源

RDKit 题目来自以下本地设计与计划文档：

- `docs/design/INITIAL-DESIGN.md`：把 RDKit 小分子 descriptor 题定位为首批最稳定、成本最低、可本地确定性验证的 open-generation benchmark。
- `docs/research/2026-05-26-verifier-grounded-chemical-benchmark-target-properties.md`：将 QED、logP、TPSA、MW、HBD/HBA、rotatable bonds、SA score 等列为 P0 小分子基础性质。
- `docs/superpowers/plans/2026-06-02-task-level-verifier-script-migration.md`：废弃 task-level verifier script，明确采用 descriptor-level verifier 设计。

当前真实实现已按如下边界落地：

```text
task constraint/property -> verifier_id -> verification_script -> shared RDKit descriptor backend
```

## 2. 题目类型

当前 RDKit 题目是 `small_molecule` 的 open-generation property-satisfaction 任务。模型需要生成一个单组分小分子，并在最终答案中给出一条 SMILES：

```text
FINAL ANSWER: <SMILES>
```

统一 domain gate：

- 单组分 SMILES，不接受 dot-separated multi-component SMILES。
- 允许元素：H、B、C、N、O、F、P、S、Cl、Br、I。
- heavy atom count：5 到 60。
- RDKit molecular weight：不超过 600 dalton。
- formal charge：-1 到 1。

这些 gate 使题目保持在典型小分子/药物样化学空间内，并避免多盐、多组分、过大分子或异常价态成为高分答案。

## 3. 当前题目数量

当前 task pack：`tasks/rdkit_baseline/`

- 题目数量：10。
- verifier specs：8。
- 当前正式评分用到的性质：7 个。
- 当前存在但只作为 spec/backend 能力保留、未被 task 直接评分的 verifier：`rdkit_mw_v1`。

| task_id | 目标性质 | 约束类型 |
|---|---|---|
| `rdkit_qed_max_001` | QED | maximize bounded `[0.0, 1.0]` |
| `rdkit_sa_min_002` | SA score | minimize bounded `[1.0, 10.0]` |
| `rdkit_logp_window_003` | logP | window `[1.0, 3.0]`, `sigma=0.5` |
| `rdkit_tpsa_window_004` | TPSA | window `[35.0, 75.0]`, `sigma=10.0` |
| `rdkit_hba_window_006` | HBA | window `[2, 4]`, `sigma=1.0` |
| `rdkit_hbd_window_007` | HBD | window `[1, 2]`, `sigma=1.0` |
| `rdkit_fsp3_max_008` | fraction Csp3 | maximize bounded `[0.0, 1.0]` |
| `rdkit_qed_sa_009` | QED + SA score | multi-objective |
| `rdkit_logp_tpsa_010` | logP + TPSA | multi-objective |
| `rdkit_hba_hbd_012` | HBA + HBD | multi-objective |

## 4. 涉及的可验证化学性质

| 性质 | 当前用途 | 实现入口 | 化学含义 |
|---|---|---|---|
| QED | 评分目标 | `rdkit.Chem.QED.qed` | 综合 drug-likeness desirability 分数，范围 0 到 1。 |
| SA score | 评分目标 | `rdkit.Contrib.SA_Score.sascorer.calculateScore` | 合成可及性 heuristic，当前按 1 易到 10 难处理。 |
| logP | 评分目标 | `rdkit.Chem.Crippen.MolLogP` | 脂溶性/疏水性 proxy。 |
| TPSA | 评分目标 | `rdkit.Chem.rdMolDescriptors.CalcTPSA` | 极性表面积 proxy，关联转运、渗透和 oral exposure。 |
| HBA | 评分目标 | `rdkit.Chem.rdMolDescriptors.CalcNumHBA` | 氢键受体数量。 |
| HBD | 评分目标 | `rdkit.Chem.rdMolDescriptors.CalcNumHBD` | 氢键供体数量。 |
| fraction Csp3 | 评分目标 | `rdkit.Chem.rdMolDescriptors.CalcFractionCSP3` | 碳骨架饱和度/三维复杂度 proxy。 |
| MW | domain gate；spec 保留 | `rdkit.Chem.Descriptors.MolWt` | 分子大小与 drug-like domain 控制。 |
| heavy atom count / formal charge | domain gate | RDKit Mol API | 结构规模、离子态和适用域控制。 |

## 5. 对应 verifier

当前 RDKit verifier 都通过 `verifiers/rdkit_descriptors/cli.py` 进入共享后端 `verifiers/rdkit_descriptors/backend.py`。

| verifier_id | property / descriptor | verification_script |
|---|---|---|
| `rdkit_qed_v1` | `qed` | `verifiers/rdkit_descriptors/rdkit_qed.py` |
| `rdkit_logp_v1` | `logp` | `verifiers/rdkit_descriptors/rdkit_logp.py` |
| `rdkit_tpsa_v1` | `tpsa` | `verifiers/rdkit_descriptors/rdkit_tpsa.py` |
| `rdkit_mw_v1` | `mw` | `verifiers/rdkit_descriptors/rdkit_mw.py` |
| `rdkit_hba_v1` | `hba` | `verifiers/rdkit_descriptors/rdkit_hba.py` |
| `rdkit_hbd_v1` | `hbd` | `verifiers/rdkit_descriptors/rdkit_hbd.py` |
| `rdkit_sa_score_v1` | `sa_score` | `verifiers/rdkit_descriptors/rdkit_sa_score.py` |
| `rdkit_fraction_csp3_v1` | `fraction_csp3` | `verifiers/rdkit_descriptors/rdkit_fraction_csp3.py` |

真实执行流程：

1. `benchmark/answer_extraction.py` 从 raw response 抽取 SMILES。
2. `benchmark/evaluate.py` 按 task constraint 的 `verifier_id` 找到 spec。
3. `benchmark/verifier_scripts.py` 构造 JSON payload 并子进程执行 `verification_script`。
4. RDKit backend 重新解析 SMILES、canonicalize、做 domain gate、计算 descriptor、返回标准 result JSON。

模型自报的性质值不会被信任；评分只使用 verifier 重新计算的性质。

## 6. 打分计算方式

RDKit 题目使用统一 scoring helper `score_constraint`。

### 6.1 Window constraint

性质落在 `[min, max]` 内得 1.0。落在窗口外时按距离指数衰减：

```text
score = exp(-distance_to_window / sigma)
```

结果裁剪到 `[0.0, 1.0]`。

### 6.2 Maximize bounded

```text
score = clamp((value - lower) / (upper - lower), 0.0, 1.0)
```

### 6.3 Minimize bounded

```text
score = clamp((upper - value) / (upper - lower), 0.0, 1.0)
```

### 6.4 多目标聚合

多目标任务由 runner 对多个 constraint score 做 geometric mean：

```text
property_score = geometric_mean(main_constraint_scores)
final_score = property_score
```

任一 verifier 发生 parse、validity 或 domain error 时，最终 score 为 0。RDKit 题目当前没有额外 quality gate。

## 7. 实际化学意义

RDKit track 的实际目标不是证明某个分子真实可成药，而是构造一个低成本、确定性、可复现的小分子生成 sanity layer：

- QED 将多种 oral drug-like 分布压缩为 0 到 1 的 desirability 分数，适合做基础药物样目标。
- logP、TPSA、HBA、HBD 和 MW 是经典 early-stage medicinal chemistry 过滤指标，关联溶解性、渗透性、口服吸收和 ADME 风险。
- SA score 防止模型只优化 QED/logP 而生成明显复杂或不易合成的结构。
- fraction Csp3 鼓励更饱和、更立体的分子骨架，用于避免过度平面化的芳香结构偏置。
- 多目标题目用于模拟真实 lead optimization 中“同时满足多个基础性质”的压力，而不是单一 descriptor maximization。

这类题目的工程意义同样重要：它验证 answer schema、SMILES parsing、property-level verifier script、shared backend、multi-objective aggregation 和 failure taxonomy 是否稳定。

## 8. 文献与资料支撑

- RDKit QED 文档说明 QED 来源于 Bickerton 等人的 quantitative estimate of drug-likeness，并由 MW、logP、TPSA、HBD/HBA、aromatic rings、rotatable bonds 和 alerts 等性质构成：https://www.rdkit.org/docs/source/rdkit.Chem.QED.html
- Bickerton et al., "Quantifying the chemical beauty of drugs", Nature Chemistry 2012；论文提出 QED 作为 drug-likeness desirability 度量：https://pubmed.ncbi.nlm.nih.gov/22270643/
- Ertl and Schuffenhauer, "Estimation of synthetic accessibility score of drug-like molecules", Journal of Cheminformatics 2009；SA score 范围按 1 易合成到 10 难合成解释：https://pubmed.ncbi.nlm.nih.gov/20298526/
- Ertl, Rohde and Selzer, "Fast calculation of molecular polar surface area as a sum of fragment-based contributions", Journal of Medicinal Chemistry 2000；支撑 TPSA 作为快速 fragment-based polar surface area 估计：https://pubmed.ncbi.nlm.nih.gov/11020286/
- RDKit Crippen 文档说明 `MolLogP` 使用 Wildman-Crippen atom-based scheme：https://www.rdkit.org/docs/source/rdkit.Chem.Crippen.html
- Wildman and Crippen, "Prediction of Physicochemical Parameters by Atomic Contributions", JCICS 1999；支撑 atom contribution logP/MR：https://www.semanticscholar.org/paper/Prediction-of-Physicochemical-Parameters-by-Atomic-Wildman-Crippen/1f8a30b17d363c04feab4adb02654c33c0ae1e5b
- Lipinski Rule of Five 相关性质包括 MW、logP、HBD、HBA，用于 oral absorption/permeation 风险判断：https://pubmed.ncbi.nlm.nih.gov/11259830/
- Lovering et al., "Escape from Flatland", Journal of Medicinal Chemistry 2009；提出 Fsp3/饱和度与临床阶段成功率相关的观察：https://pubmed.ncbi.nlm.nih.gov/19827778/
