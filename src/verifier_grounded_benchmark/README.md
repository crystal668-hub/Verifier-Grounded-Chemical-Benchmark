# Verifier-Grounded Benchmark (v0.10.0)

`verifier_grounded_benchmark` 提供可复现的化学 benchmark task pack、verifier 和评分工具。
模型调用由用户或 agent runner 负责；本包负责提供题目、解析答案并生成评分报告。

v0.10.0 采用逐题独立容差，不再加载或校验 `family-policy.yaml`。
Basic 013 的容差为 ±3 kcal/mol；Advanced 008、010、013 分别为
±10 kcal/mol、±0.1 Å、±5 kcal/mol，并先对答案与 gold 取绝对值再比较。
容差仍表示线性评分降至零的误差宽度，gold 和字段权重不变。
Advanced 011 使用半径 1.2 Å 的球形探针。
RDKit 和 xTB 的 task-id 分别标准化为 `rdkit_001_qed_max`–`rdkit_014_caffeine_similarity_max`、
`xtb_001_gap_window`–`xtb_020_pyrene_substituent_energy_min`；已有答案记录需同步更新 task-id。

## QuickStart

```python
import verifier_grounded_benchmark as vgb

print([x.name for x in vgb.list_tracks()])
track = vgb.load_track("property_calculation_advanced")
prompt = track.prompts()[0]
answer = {"task_id": prompt["task_id"], "answer": 0.0, "unit": "kJ/mol"}
result = track.evaluate_one(answer)
print(result["scores"]["score"])
```

## Tracks

| Canonical name | 内容 |
| --- | --- |
| `open_generation_rdkit` | 开放分子生成与 RDKit descriptor/force-field 评分 |
| `open_generation_xtb` | 开放分子或 XYZ 结构生成与 xTB 评分 |
| `property_calculation_basic` | 51 道 basic 固定输入性质计算题 |
| `property_calculation_advanced` | 20 道 advanced 固定输入性质计算题 |

v0.10.0 仅支持上述 canonical names；旧的 `rdkit`、`xtb`、
`property_calculation` 和 `property_calculation_easy` 名称已移除。
开放生成任务通过 verifier 计算候选分子的性质；性质计算任务依据 gold answer
和逐题 scoring profile 评分，不调用 verifier，也不需要 verifier 配置文件。

## Public API

- `vgb.list_tracks(status="formal")`：列出 tracks。
- `vgb.load_track(name)`：加载单个 `Track`。
- `vgb.load_suite(names)`：组合多个 tracks 为 `Suite`。
- `vgb.register_track(definition)`：注册外部 track。
- `track.tasks()` / `track.task(task_id)`：读取不含评分和答案的公开任务定义。
- `track.prompts()`：返回模型 runner 使用的最小 `{track, task_id, prompt, answer_schema}` 视图。
- `track.task(task_id, include_gold=True)`：唯一受支持的 gold 读取接口。
- `track.evaluate_one(answer)`：评分单条 answer record。
- `track.evaluate_answers(answers)`：批量评分并返回 report dict。

`Evaluator.tasks`、`Suite.tasks()`、`EvaluationReport` 和评分结果都不会返回
`gold_answers`、评分 profile 或 failure policy。

Property calculation tracks 不提供内置 `sample_answers()`；RDKit 和 xTB 仍提供 showcase samples。

## Answer format

```json
{"task_id":"property_calculation_advanced_001_free_energy","answer":0.258031679,"unit":"kJ/mol"}
```

也可以提交包含 `FINAL ANSWER:` 行的原始模型 response。

## CLI

```bash
vgb-score --track open_generation_rdkit --answers answers.jsonl --require-complete
```

开发态自定义开放生成 pack：

```bash
vgb-score --tasks tasks.yaml --specs verifier_specs.yaml \
  --scoring scoring.yaml --answers answers.jsonl
```

开发态自定义性质计算 pack：

```bash
vgb-score --tasks tasks.yaml --scoring scoring.yaml --answers answers.jsonl
```

## Pack layout

```text
<track>/
  tasks.yaml          # 题目、输入、prompt、answer schema
  scoring.yaml        # gold、scoring profiles、聚合和失败策略
  verifier_specs.yaml # 仅开放生成 track：verifier 实现与运行环境
```

`tasks.yaml` 与 `scoring.yaml` 在发行包中均可用于离线审计；公共 API 不会在普通任务视图
或评分结果中重复暴露评分配置。正式防止测试集调参需要不携带 scoring config 的 server-side pack。

性质计算 track 仅需要 `tasks.yaml` 和 `scoring.yaml`，不提供空 verifier 占位文件。
`task/calibration/` 为源码维护用校准数据，整个目录均不进入 wheel 或 sdist。
