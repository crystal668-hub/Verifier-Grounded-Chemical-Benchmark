# xTB 自动化题目质量评估模块设计

日期：2026-06-23

## 1. 目标与边界

本模块用于对 `tasks/xtb_xyz/` 中的 xTB direct-XYZ 题目做自动化质量评估，核心问题是判断每道题的阈值设定、难度标注和区分能力是否合理。模块第一版定位为审计报告工具，不作为 CI 阻塞门；输出应包含机器可读 JSON、人工可读 Markdown 和必要 CSV 明细，并为后续升级为质量门预留 `severity`、`decision` 和 `blocking` 字段。

评估对象是题目质量，不是重新运行 xTB 计算。模块消费已有结果：

- xTB 真实化学性质抽样统计分布结果；
- curated calibration controls 的已评分结果；
- 模型面板 benchmark run 的已评分结果；
- 正式 task YAML 中声明的 constraints、difficulty 和 structural domain。

非目标：

- 不直接调用 xTB verifier；
- 不重新评分 raw model answers；
- 不复制或提交 repo 外 benchmark run 目录；
- 不把外部 OpenClaw run schema 泄漏到核心评分逻辑中。

## 2. 设计依据

已有本地实现提供了三类可复用证据：

- `scripts/xtb_real_dataset/analyze_xtb_real_dataset_distribution.py` 已能汇总真实数据分布，但当前 task-level recommendation 仍是占位逻辑，没有按正式 task constraints 计算 task score fraction。
- `scripts/xtb_calibration/run_xtb_calibration.py` 和 `scripts/xtb_calibration/analyze_xtb_calibration.py` 已能分析 curated positive、near-miss、negative baseline 和 stress case，但只覆盖控制样本，不覆盖模型面板。
- OpenClaw benchmark run 目录包含模型输出和 verifier-grounded 评分结果，真实评分细节位于 `results[].evaluation.details` 和 `results[].evaluation.details.verifier_result`。

论文和 benchmark 实践给出的方法约束：

- GPQA、SWE-bench Verified 强调题目本身要经验证，并用不同能力水平的参与者或模型表现判断难度。
- MMLU-Pro 强调过滤过易题和噪声题，用模型表现下降、稳定性和区分度证明题目有效。
- Item Response Theory 相关 NLP 评估把题目看作 item，关注 difficulty 与 discrimination，而不是只看平均分。
- GuacaMol、MOSES、PMO、TARTARUS 等分子设计 benchmark 强调真实分布、目标函数、baseline/model panel 和 oracle 成本共同定义任务质量，避免只凭主观阈值构造 trivial target。

本模块采用三条证据链合成题目质量：

1. 真实分布证据：题目阈值在真实化学空间中是否过宽、过窄或明显偏向某一数据域。
2. Calibration 证据：curated positive 是否可达，negative/near-miss 是否能被分开。
3. 模型面板证据：不同模型或运行配置下的实际成功率和分数差异是否符合题目声明难度，并能产生区分度。

## 3. 模块分层

推荐实现分为五层，每层只依赖下层的稳定 schema。

```text
scripts/analyze_xtb_task_quality.py
  CLI orchestration
        |
        v
benchmark/task_quality/adapters.py
  External input adapters
        |
        v
benchmark/task_quality/schema.py
  Normalized schemas
        |
        v
benchmark/task_quality/scoring.py
  Evidence metrics and decision rules
        |
        v
benchmark/task_quality/reporting.py
  JSON, Markdown, CSV writers
```

### 3.1 CLI 层

CLI 只负责解析路径、调用 adapter、汇总输出，不包含评分规则。

建议接口：

```bash
uv run python scripts/analyze_xtb_task_quality.py \
  --tasks tasks/xtb_xyz/tasks.yaml \
  --distribution-results artifacts/xtb_real_distribution/2026-06-22-expanded-run/light_results.json \
  --distribution-results artifacts/xtb_real_distribution/2026-06-22-expanded-run/medium_results.json \
  --distribution-results artifacts/xtb_real_distribution/2026-06-22-expanded-run/expensive_results.json \
  --calibration-results artifacts/xtb_calibration/2026-06-19-advanced-iteration/final-results.json \
  --openclaw-run /Users/xutao/.openclaw/workspace/state/benchmark-runs/verifier-grounded-xtb-xyz-gpt55-no-timeout-20260611-004044 \
  --model-result another_panel:/absolute/path/to/repo-native-results.json \
  --output-dir artifacts/xtb_task_quality/2026-06-23
```

输入参数语义：

- `--tasks`：正式 task YAML，作为阈值、difficulty 和 task id 的唯一来源。
- `--distribution-results`：可重复，读取 xTB real-dataset tier result JSON。
- `--calibration-results`：可选，读取 `run_xtb_calibration.py` 输出。
- `--model-result label:path`：可重复，读取 repo-native scored JSON。
- `--openclaw-run PATH`：可重复，读取 OpenClaw run 目录或其中的 `results.json`。
- `--output-dir`：写入报告，默认不覆盖输入。

`--openclaw-run` 的重复参数语义是显式合并多个 benchmark run，而不是只消费一次 run。每个 run 中的每个 `group_id` 都会展开成一个 panel member；为了避免不同 run 复用同一个 `group_id` 时发生冲突，内部 `panel_member_id` 应规范化为 `<run_id>::<group_id>`，同时保留原始 `group_id` 和 `run_id` 字段用于报告展示。第一版不做隐式全盘检索；如果需要从一个 benchmark-run 根目录中自动筛选多个 run，应后续新增显式参数，例如 `--openclaw-run-root`、`--run-name-glob` 和 `--run-generated-after`。

输出文件：

- `task_quality_summary.json`：完整结构化报告；
- `task_quality_summary.md`：面向审阅的结论和表格；
- `task_distribution_scores.csv`：真实分布中每个可评分记录的 task score；
- `model_panel_matrix.csv`：模型面板按 task 和 panel member 的分数矩阵；
- `source_provenance.json`：所有外部输入的路径、大小、mtime 和 sha256。

### 3.2 Adapter 层

Adapter 层把不同来源转换成统一 schema。核心原则是：外部格式差异在 adapter 内消化，后续评分逻辑只消费统一对象。

#### RepoNativeScoredResultAdapter

适配 `vgb-score`、`scripts/xtb_calibration/run_xtb_calibration.py` 和相同结构的 JSON。

识别规则：

- 顶层有 `rows`；
- row 直接包含 `task_id`、`status`、`score`、`properties`、`constraint_scores`，或 `score` 可从 `scores.score` 得到。

字段映射：

- `task_id` <- `row.task_id`
- `score` <- `row.score` 或 `row.scores.score`
- `status` <- `row.status`
- `failure_type` <- `row.failure_type`
- `properties` <- `row.properties`
- `constraint_scores` <- `row.constraint_scores` 或 `row.scores.constraint_scores`
- `role` <- `row.role`，用于 calibration controls
- `panel_member_id` <- CLI label，除非 row 自带 `model`、`model_id` 或 `group_id`

#### OpenClawRunAdapter

适配 repo 外的 OpenClaw benchmark run 目录。默认读取 `PATH/results.json`；如果传入的 `PATH` 本身是 JSON 文件，则直接读取该文件。

已验证的 run 目录示例：

```text
/Users/xutao/.openclaw/workspace/state/benchmark-runs/
  verifier-grounded-xtb-xyz-gpt55-no-timeout-20260611-004044/
    results.json
    runtime-manifest.json
    per-record/<group_id>/<record>.json
    progress/state.json
```

OpenClaw 映射规则：

- `task_id`：优先 `evaluation.details.task_id`，否则 `record_id`。
- `score`：优先 `evaluation.normalized_score`，否则 `evaluation.score`，否则 `evaluation.details.verifier_result.scores.score`。
- `status`：优先 `evaluation.details.status`，否则 `evaluation.details.verifier_result.status`。
- `failure_type`：优先 `evaluation.details.failure_type`，否则 `evaluation.details.verifier_result.failure_type`。
- `properties`：`evaluation.details.properties`。
- `constraint_scores`：`evaluation.details.constraint_scores`。
- `property_score`、`geometry_quality_score`、`stability_gate_score`：从 `evaluation.details.verifier_result.scores` 读取。
- `panel_member_id`：`group_id`。
- `raw_group_id`：`group_id`。
- `run_id`：OpenClaw run 目录名，或 `results.json` 父目录名。
- `panel_member_label`：`group_label`。
- `model`：优先 `runner_meta.agentMeta.provider + "/" + runner_meta.agentMeta.model`；缺失时从 `runtime-manifest.json` 的 `groups.<group_id>.single_agent_model` 读取。
- `answer_availability`、`answer_reliability`、`evaluable`、`scored`、`skills_enabled`、`websearch`、`elapsed_seconds`：从同名顶层字段读取。

必须明确避免的误读：

- `raw.result` 在 OpenClaw run 中是模型 payload/meta，不是 verifier result。
- `per-record/` 中的 JSON 可作为 debug fallback，但默认应以顶层 `results.json` 为准。

#### DistributionResultAdapter

适配 `scripts/xtb_real_dataset/run_xtb_real_dataset_distribution.py` 的 tier result JSON。

每个 row 转换为 `PropertyObservation`。同一个真实分子可能在 light、medium、expensive 三个 tier 中分别出现，模块按 `(dataset_name, record_id)` 合并 property values 和 property statuses，形成 `DistributionCandidate`。

合并规则：

- `properties` 字典做并集，后读入的同名 property 值必须与已有值一致；若不一致，记录 `conflicting_property_value` 并跳过相关 task scoring。
- `property_statuses` 按 property 记录 `ok`、`error`、`skipped`。
- `runtime_seconds` 和 `versions` 只用于 provenance 和 runtime diagnostics，不参与 task score。

### 3.3 Schema 层

#### SourceProvenance

```python
{
    "source_id": "openclaw:verifier-grounded-xtb-xyz-gpt55-no-timeout-20260611-004044",
    "source_type": "openclaw_run",
    "path": "/absolute/path/to/results.json",
    "resolved_path": "/absolute/path/to/results.json",
    "size_bytes": 1123456,
    "mtime": "2026-06-11T01:32:42+08:00",
    "sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
    "schema_version": 2,
}
```

#### ScoredAttempt

用于 calibration controls 和模型面板。

```python
{
    "source_id": "openclaw:verifier-grounded-xtb-xyz-gpt55-no-timeout-20260611-004044",
    "source_type": "openclaw_run",
    "run_id": "verifier-grounded-xtb-xyz-gpt55-no-timeout-20260611-004044",
    "panel_member_id": "single_llm_skills_on",
    "panel_member_label": "单一 LLM + benchmark skills allowlist",
    "model": "openai/gpt-5.5",
    "task_id": "xtb_gap_window_001",
    "role": None,
    "status": "ok",
    "failure_type": None,
    "score": 0.9999999158779223,
    "property_score": 1.0,
    "geometry_quality_score": 0.9999999158779223,
    "stability_gate_score": None,
    "properties": {
        "homo_lumo_gap": 4.647621712273,
        "relaxation_energy": 2.944272718797379e-08
    },
    "constraint_scores": [
        {"property": "homo_lumo_gap", "type": "window", "score": 1.0},
        {"property": "relaxation_energy", "type": "minimize_bounded", "role": "quality_gate", "score": 0.9999999158779223}
    ],
    "evaluable": True,
    "scored": True,
    "answer_availability": "native_final",
    "answer_reliability": "native",
    "elapsed_seconds": 147.30561208724976,
    "skills_enabled": True,
    "websearch": False,
}
```

#### DistributionCandidate

用于真实分布打分。

```python
{
    "candidate_id": "qmugs:CHEMBL123",
    "dataset_name": "qmugs",
    "record_id": "CHEMBL123",
    "properties": {
        "homo_lumo_gap": 2.78,
        "dipole_moment": 4.10,
        "lumo_energy": -7.13,
        "relaxation_energy": 0.00001
    },
    "property_statuses": {
        "homo_lumo_gap": {"status": "ok", "failure_type": None},
        "global_electrophilicity": {"status": "error", "failure_type": "verifier_tool_error"}
    },
    "source_rows": ["light_results.json", "medium_results.json"]
}
```

#### DistributionTaskScore

```python
{
    "task_id": "xtb_gap_dipole_window_007",
    "candidate_id": "qm9:gdb9_000001",
    "dataset_name": "qm9",
    "score": 0.82,
    "property_score": 0.91,
    "geometry_quality_score": 0.90,
    "stability_gate_score": 1.0,
    "constraint_scores": [
        {"property": "homo_lumo_gap", "score": 1.0},
        {"property": "dipole_moment", "score": 0.84},
        {"property": "relaxation_energy", "role": "quality_gate", "score": 0.90}
    ],
    "status": "scored",
    "missing_properties": []
}
```

#### TaskQualityReport

```python
{
    "generated_at": "2026-06-23T00:00:00+08:00",
    "tasks_path": "/absolute/path/tasks/xtb_xyz/tasks.yaml",
    "sources": [
        {
            "source_id": "openclaw:verifier-grounded-xtb-xyz-gpt55-no-timeout-20260611-004044",
            "source_type": "openclaw_run",
            "resolved_path": "/Users/xutao/.openclaw/workspace/state/benchmark-runs/verifier-grounded-xtb-xyz-gpt55-no-timeout-20260611-004044/results.json"
        }
    ],
    "tasks": {
        "xtb_gap_window_001": {
            "declared_difficulty": "basic",
            "decision": "keep_thresholds",
            "severity": "info",
            "blocking": False,
            "distribution": {"scorable_count": 10000, "fraction_score_gte_0_8": 0.012},
            "calibration": {"positive_max_score": 1.0, "negative_max_score": 0.0},
            "model_panel": {"panel_member_count": 2, "success_rate": 0.5},
            "rationale": ["real-distribution high-score fraction is within the target range"]
        }
    }
}
```

## 4. 题目质量评分方法

每道题的质量评分不是单个数字直接决定，而是由三类 evidence score 和一组 decision rules 组合。建议报告同时输出连续分数和离散建议。

### 4.1 真实分布证据

真实分布证据回答：“这个阈值在真实化学空间中是不是太容易或太难？”

流程：

1. 从 task YAML 读取 constraints。
2. 从 tiered distribution rows 合并每个真实分子的 properties。
3. 对每个 task，检查该 task 所需 properties 是否齐全。
4. 用正式 scoring function 计算每个真实分子的 task score。
5. 按全体和 dataset slice 统计 score fractions。

统计指标：

- `scorable_count`；
- `missing_property_count`；
- `property_error_rate`；
- `score_mean`、`score_p50`、`score_p90`、`score_p95`；
- `fraction_score_gte_0_2`；
- `fraction_score_gte_0_5`；
- `fraction_score_gte_0_8`；
- `fraction_score_gte_0_95`；
- `fraction_failing_quality_gate`；
- `fraction_failing_stability_gate`；
- per-dataset versions of the same metrics。

阈值判断：

- `needs_more_data`：light task 可评分记录少于 200，medium 少于 100，expensive 少于 50。
- `needs_runtime_fix`：任一主性质的 property/runtime error rate 超过 5%。
- `tighten_thresholds`：`score>=0.8` 超过 5%，或 `score>=0.95` 超过 1%。
- `loosen_thresholds`：`score>=0.5` 低于 0.1%，且 calibration positive 也低于 0.6。
- `split_by_domain`：不同 dataset 的 `score>=0.8` 或 `score>=0.5` 比例相差超过 3 倍，且两侧样本数都足够。

连续分数建议：

```text
distribution_quality_score = coverage_score
                           * runtime_reliability_score
                           * threshold_balance_score
                           * domain_balance_score
```

其中：

- `coverage_score`：样本数达到 tier 下限为 1，否则按 `scorable_count / required_count` 截断。
- `runtime_reliability_score`：`1 - min(error_rate / 0.05, 1)`。
- `threshold_balance_score`：以声明难度对应的目标高分率区间为中心，过高或过低都扣分。
- `domain_balance_score`：不同数据源差异在 3 倍以内为 1，差异越大越低。

### 4.2 Calibration 证据

Calibration 证据回答：“人工挑选的 positive、near-miss、negative 是否符合预期？”

输入为已评分 calibration result rows。角色来自 `row.role`：

- `positive_candidate`：应该能达到高分；
- `near_miss`：应该接近但不饱和；
- `negative_baseline`：应该低分或因预期 domain error 失败；
- `stress_case`：用于暴露 parser/runtime/quality gate 问题，不一定要求高分。

统计指标：

- `positive_max_score`、`positive_mean_score`；
- `near_miss_max_score`、`near_miss_mean_score`；
- `negative_max_score`；
- `stress_error_types`；
- `expected_domain_error_count`；
- `unexpected_runtime_error_count`。

判断规则：

- positive max 低于 0.6：`weak_positive_controls`。
- negative max 高于 0.35：`negative_baseline_too_easy`。
- near-miss max 高于 0.95：`near_miss_saturates`。
- near-miss max 高于 positive max：`control_order_inverted`。
- stress case 出现 parser/tool/timeout failure 且非预期：`runtime_fragility`。

连续分数建议：

```text
calibration_quality_score = positive_reachability_score
                          * negative_separation_score
                          * near_miss_gradient_score
                          * runtime_stress_score
```

其中：

- `positive_reachability_score = clamp(positive_max / 0.8)`；
- `negative_separation_score = 1` if `negative_max <= 0.35` else linearly decays to 0 at 0.8；
- `near_miss_gradient_score` 在 near-miss 低于 positive 且不饱和时最高；
- `runtime_stress_score` 在无非预期 runtime/parser failure 时为 1。

### 4.3 模型面板证据

模型面板证据回答：“题目对真实模型是否有合适难度和区分度？”

输入可以来自 repo-native scored JSON，也可以来自一个或多个 OpenClaw run。OpenClaw run 中每个 `group_id` 被视为一个 panel member；当同时传入多个 run 时，panel member 的唯一键使用 `<run_id>::<group_id>`。例如：

- `single_llm_skills_on`：`openai/gpt-5.5`，skills enabled；
- `single_llm_skills_off`：`openai/gpt-5.5`，skills disabled。

统计指标：

- `attempt_count`；
- `panel_member_count`；
- `success_rate`：`score >= 0.8` 的比例；
- `partial_rate`：`score >= 0.5` 的比例；
- `mean_score`；
- `best_score`；
- `score_stddev`；
- `score_range`；
- `evaluable_rate`；
- `degraded_execution_rate`；
- `failure_type_counts`；
- per-panel-member score matrix。

声明难度的目标 success rate：

| Declared difficulty | 目标 success rate |
| --- | ---: |
| `basic` | 35%-80% |
| `intermediate` | 15%-60% |
| `advanced` | 5%-35% |
| `expert` | 1%-20% |

判断规则：

- success rate 高于目标区间上限：`difficulty_too_easy`。
- success rate 低于目标区间下限，且 calibration positives 可达：`difficulty_too_hard_for_panel`。
- success rate 低且 calibration positives 也不可达：优先归因 `threshold_or_control_problem`。
- `score_stddev` 和 `score_range` 都很低：`low_discrimination`。
- 至少 3 个 panel members 时，计算近似 item discrimination：把每个 panel member 的全局平均分作为能力 proxy，计算 task score 与能力 proxy 的相关性；相关性低或为负时标记 `poor_item_discrimination`。

连续分数建议：

```text
model_panel_quality_score = difficulty_alignment_score
                          * discrimination_score
                          * evaluability_score
```

其中：

- `difficulty_alignment_score` 根据 success rate 与声明难度目标区间的距离计算；
- `discrimination_score` 由 score range、stddev 和 item discrimination 组合；
- `evaluability_score = evaluable_count / attempt_count`。

### 4.4 综合决策

每道题最终输出一个 `decision`，同时保留所有 evidence flags。

优先级：

1. 如果 runtime/parser/tool error rate 高，输出 `needs_runtime_fix`。
2. 如果样本不足，输出 `needs_more_data`。
3. 如果 positive controls 不可达，输出 `repair_controls_or_loosen_thresholds`。
4. 如果真实分布或 near-miss 显示阈值过宽，输出 `tighten_thresholds`。
5. 如果真实分布和模型面板都显示题目过难，输出 `loosen_thresholds`。
6. 如果数据域差异显著，输出 `split_by_domain`。
7. 如果模型面板区分度低但阈值分布正常，输出 `revise_prompt_or_objective`。
8. 否则输出 `keep_thresholds`。

综合分数建议：

```text
task_quality_score = 0.40 * distribution_quality_score
                   + 0.30 * calibration_quality_score
                   + 0.30 * model_panel_quality_score
```

当某证据链缺失时，不强行补零；报告应标记 `evidence_missing`，并按剩余证据重归一化权重。例如没有模型面板时，distribution 和 calibration 权重归一化为 0.571 和 0.429。

## 5. OpenClaw run 的消费方式

OpenClaw run 目录应通过 `--openclaw-run` 直接传入，不需要复制到 repo。

示例：

```bash
uv run python scripts/analyze_xtb_task_quality.py \
  --tasks tasks/xtb_xyz/tasks.yaml \
  --distribution-results artifacts/xtb_real_distribution/2026-06-22-expanded-run/light_results.json \
  --distribution-results artifacts/xtb_real_distribution/2026-06-22-expanded-run/medium_results.json \
  --distribution-results artifacts/xtb_real_distribution/2026-06-22-expanded-run/expensive_results.json \
  --calibration-results artifacts/xtb_calibration/2026-06-19-advanced-iteration/final-results.json \
  --openclaw-run /Users/xutao/.openclaw/workspace/state/benchmark-runs/verifier-grounded-xtb-xyz-gpt55-no-timeout-20260611-004044 \
  --output-dir artifacts/xtb_task_quality/2026-06-23
```

如果有多个 benchmark run，应重复传入：

```bash
uv run python scripts/analyze_xtb_task_quality.py \
  --tasks tasks/xtb_xyz/tasks.yaml \
  --distribution-results artifacts/xtb_real_distribution/2026-06-22-expanded-run/light_results.json \
  --distribution-results artifacts/xtb_real_distribution/2026-06-22-expanded-run/medium_results.json \
  --distribution-results artifacts/xtb_real_distribution/2026-06-22-expanded-run/expensive_results.json \
  --openclaw-run /Users/xutao/.openclaw/workspace/state/benchmark-runs/run-a \
  --openclaw-run /Users/xutao/.openclaw/workspace/state/benchmark-runs/run-b \
  --output-dir artifacts/xtb_task_quality/2026-06-23
```

多 run 合并规则：

- 每个 run 独立生成 `SourceProvenance`。
- 每条 attempt 的唯一 panel key 是 `<run_id>::<group_id>`。
- 报告中同时展示 `run_id`、原始 `group_id`、`group_label`、`model`、`skills_enabled` 和 `websearch`。
- 如果多个 run 表示同一模型和同一配置的重复实验，默认仍作为多个 panel members 参与分布统计；后续可以增加 `--collapse-repeated-panel-members` 选项，将同一 `(model, skills_enabled, websearch, task_id)` 的重复 attempts 聚合为 mean/best。
- 模块不应从 `~/.openclaw/workspace/state/benchmark-runs` 自动扫描所有目录，除非用户显式提供后续扩展参数。这样可以避免把过期、失败或不同 task pack 的 run 混入当前质量评估。

OpenClaw provenance 必须写入报告：

- run directory；
- `results.json` resolved path；
- `runtime-manifest.json` resolved path；
- schema version；
- group ids；
- model ids；
- sha256；
- mtime；
- run generated time。

该 run 的 `results.json` schema 已确认：

- 顶层 `results` 是 scored attempts 列表；
- 每条 result 有 `group_id`、`group_label`、`record_id`、`evaluation`、`runner_meta`、`answer_availability`、`evaluable`、`scored` 等字段；
- verifier-grounded 分数在 `evaluation.normalized_score`；
- verifier 细节在 `evaluation.details`；
- 质量门、性质分数等在 `evaluation.details.verifier_result.scores`。

## 6. 错误处理与兼容性

输入 schema 不匹配时，adapter 不应抛出未结构化异常。建议输出 source-level diagnostic：

```python
{
    "source_id": "openclaw:verifier-grounded-xtb-xyz-gpt55-no-timeout-20260611-004044",
    "status": "error",
    "failure_type": "unsupported_schema",
    "message": "expected top-level results or rows",
}
```

常见问题处理：

- 缺少 `evaluation.details.verifier_result`：仍可使用 `evaluation.details` 和 `evaluation.score` 做面板难度统计，但 `property_score` 和 gate scores 标为缺失。
- `score` 缺失：该 attempt 标为 `scored=False`，不进入 success rate 分母，但进入 evaluability diagnostics。
- task id 不存在于当前 task YAML：标记 `unknown_task_id`，不参与正式质量评估。
- 外部路径不存在：CLI 返回非零，报告不生成。
- 外部路径存在但个别 rows 损坏：保留 source diagnostic，跳过损坏 row。

## 7. 报告解释方式

Markdown 报告应先给总览，再给每题明细。

总览表字段：

| Task | Difficulty | Decision | Quality | Distribution | Calibration | Model panel | Main flags |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |

每题明细包括：

- 当前 constraints 摘要；
- 真实分布 score fractions；
- calibration controls 的 positive/near-miss/negative 分离情况；
- 模型面板每个 panel member 的 score；
- 最终 decision 和 rationale；
- 若建议调整阈值，给出应优先检查的 constraint，而不是自动改 YAML。

## 8. 测试策略

单元测试：

- repo-native scored JSON adapter；
- OpenClaw run adapter，使用最小 fixture 覆盖 `evaluation.details.verifier_result`；
- distribution tier join；
- task scoring，覆盖 window、maximize_bounded、minimize_bounded、quality_gate 和 stability_gate；
- missing property 与 conflicting property diagnostics；
- calibration flag rules；
- model-panel difficulty alignment 和 discrimination。

CLI 测试：

- `--help` 正常；
- 使用小型 fixture 生成 JSON、Markdown、CSV；
- repo 外临时目录可作为 `--openclaw-run` 输入；
- 不依赖本机 xTB executable。

验收标准：

- 能从 OpenClaw run 目录读取 `single_llm_skills_on` 和 `single_llm_skills_off` 两个 panel members；
- 能同时读取多个显式传入的 OpenClaw run，并用 `<run_id>::<group_id>` 避免 panel member id 冲突；
- 能把 OpenClaw scored attempts 和 repo-native calibration results 合并到同一模型面板/控制样本 schema；
- 能对当前 13 个 xTB tasks 输出 task-level decision；如果某个 run 只覆盖其中一部分 task，报告应对缺失 task 标记 `missing_model_panel_attempts`，而不是降低当前正式 task 数；
- 不修改或复制 repo 外输入文件；
- 所有报告都包含 source provenance。
