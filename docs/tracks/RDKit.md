# RDKit 题目设计与实现同步

更新日期：2026-07-23

## 1. Track 边界

RDKit track 是输入为单个 SMILES 的 open-generation track。verifier 始终重新 sanitize、canonicalize 并计算性质，不使用模型自报数值。正式任务资源位于 `src/verifier_grounded_benchmark/task/packs/rdkit/`。

基线题共享 drug-like domain：单组分；允许 H、B、C、N、O、F、P、S、Cl、Br、I；重原子 5 到 60；分子量不超过 600 Da；formal charge 在 `[-1, 1]`。专家题 011-014 只应用各自公开题面中的 domain，不继承未公开的基线限制。

任务 013 虽调用 RDKit ETKDGv3/UFF 生成和优化构象，仍属于 RDKit track。`rdkit_forcefield` 是实现 backend 名称，不是独立公开 track。

## 2. 当前任务

- 正式题目：14。
- verifier specs：14。
- 所有题目均使用 `linear_goal_v2` scoring profile。

| task_id | 主目标 | 关键约束 |
|---|---|---|
| `rdkit_qed_max_001` | maximize QED | 基线 domain |
| `rdkit_sa_min_002` | minimize SA score | 基线 domain |
| `rdkit_logp_window_003` | LogP window `[1, 3]` | 基线 domain |
| `rdkit_tpsa_window_004` | TPSA window `[35, 75]` | 基线 domain |
| `rdkit_hba_window_005` | HBA window `[2, 4]` | 基线 domain |
| `rdkit_hbd_window_006` | HBD window `[1, 2]` | 基线 domain |
| `rdkit_fsp3_max_007` | maximize fraction Csp3 | 基线 domain |
| `rdkit_qed_sa_008` | QED + SA | multi-objective |
| `rdkit_logp_tpsa_009` | LogP + TPSA | multi-objective |
| `rdkit_hba_hbd_010` | HBA + HBD | multi-objective |
| `rdkit_logp_target_011` | LogP 接近 3 | 含氢总原子数和氧比例 domain |
| `rdkit_sa_logp_target_012` | LogP 接近 3 | SA `< 5` 硬门，无氧比例门 |
| `rdkit_chain_end_to_end_max_013` | maximize 六碳链端距 | 精确六碳饱和链；固定 UFF workflow |
| `rdkit_caffeine_similarity_max_014` | maximize caffeine Morgan Tanimoto | LogP、SA、QED 三个硬门 |

## 3. 性质与 verifier

descriptor backend 计算 QED、SA score、LogP、TPSA、HBA、HBD、fraction Csp3 和 MW。新增专家协议包括：

- `rdkit_sa_logp_domain_sa_v1` 与 `rdkit_sa_logp_domain_logp_v1`：共享同一题目专用 domain，先执行 SA 严格硬门，再计算 LogP 主目标。
- `rdkit_chain_end_to_end_uff_v1`：验证精确六碳非环饱和链，ETKDGv3 生成有限构象集，只使用 UFF，按 `(energy, conformer_id)` 选择最低收敛构象并测量两个端点碳核距离。
- `rdkit_caffeine_properties_v1`：在同一 candidate evidence 中计算 LogP、SA 和 QED，并核对冻结 reference SA。
- `rdkit_caffeine_similarity_v1`：Morgan bit fingerprint，radius 2、2048 bit、不含 chirality、使用 bond types，按 Tanimoto 与冻结 caffeine reference 比较。

任务 013 的冻结参数为 seed `61453`、20 个请求构象、pruning `0.5 Angstrom`、UFF、最多 200 次迭代。只保留收敛构象，不回退到 MMFF；没有嵌入或没有收敛构象属于 verifier tool failure。该距离是固定有限采样 workflow 的结果，不是全局最低能构象、分子最大直径或轮廓长度。UFF 能量只用于同一候选内部选构象，不能跨分子解释。

## 4. 硬门与评分

`hard_constraints` 在主评分前运行，支持严格小于、`<=` 和闭区间。硬门失败返回 `hard_constraint_failed` 和已计算 evidence；verifier 环境或工具故障不转成候选零分。同一 verifier 同时提供多个性质时复用 evidence。

连续目标统一使用 `linear_goal_v2`：maximize/minimize 在满分目标 `T` 与零分锚点 `B` 间线性插值；target/window 在冻结目标或窗口与两侧 width 间线性衰减并裁剪到 `[0, 1]`。多主目标取 geometric mean，硬门不参与平均。

任务 012 复用 LogP target 3、宽度 3 的 profile。任务 013 使用独立校准的 `B=6.36`、`T=6.49 Angstrom`。任务 014 的 Tanimoto 使用定义域锚点 `B=0`、`T=1`。校准证据见 `docs/research/2026-07-23-expert-open-generation-009-013-calibration.md`。

## 5. 化学解释边界

QED、SA、LogP、TPSA、HBA/HBD 和 fraction Csp3 是低成本、确定性的 molecular-design proxies，不证明候选真实可成药、可合成或具有目标 ADME。Morgan Tanimoto 只表示冻结 fingerprint 表示下的拓扑相似度，不等同 scaffold identity、药理相似性或生物活性。UFF/ETKDG workflow 是经典力场下的有限构象代理，不等同高精度量子能量或实验构象分布。

## 6. 资料

- RDKit QED：https://www.rdkit.org/docs/source/rdkit.Chem.QED.html
- RDKit Crippen LogP：https://www.rdkit.org/docs/source/rdkit.Chem.Crippen.html
- RDKit fingerprint generator：https://www.rdkit.org/docs/source/rdkit.Chem.rdFingerprintGenerator.html
- Bickerton et al., QED, Nature Chemistry 2012：https://pubmed.ncbi.nlm.nih.gov/22270643/
- Ertl and Schuffenhauer, SA score, Journal of Cheminformatics 2009：https://pubmed.ncbi.nlm.nih.gov/20298526/
