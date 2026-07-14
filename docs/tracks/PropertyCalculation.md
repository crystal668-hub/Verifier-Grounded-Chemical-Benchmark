# Property Calculation Track

更新日期：2026-07-13

## 1. 定位

`property_calculation` 是独立于 open-generation 的正式 track。题面给出完整化学或材料结构，模型报告计算结果；评分器只比较最终答案与公开 gold，不运行性质 verifier，也不检查模型的工具调用或中间推理。

当前正式题目：

| task_id | 输入 | 输出 |
|---|---|---|
| `property_calc_free_energy_001` | 两个完整内嵌 CIF | 300 K 自由能绝对差，`kJ/mol` |
| `property_calc_crystal_phase_002` | alpha/beta 两个完整内嵌 CIF | 势能绝对差、常压相和高压相 |

所有模型输入都在英文 `prompt` 中。运行时不读取附件、文件路径或外部结构数据库。

## 2. Task Schema

该 track 复用公共 task envelope，并通过以下字段表达固定输入和公开答案：

```yaml
task_type: property_calculation
input_objects: [mapping]
requested_properties: [mapping]
gold_answers: [mapping]
gold_provenance:
  disclosure: withheld_initial_release
```

它不创建伪 `constraints`。为了兼容现有 `TrackDefinition`，`verifier_specs.yaml` 内容为：

```yaml
verifiers: []
```

缺失 `task_type` 的既有任务仍默认按 `open_generation` 路由。

## 3. Answer Contract

Task 7 的规范化 JSONL：

```json
{"task_id":"property_calc_free_energy_001","answer":0.258031679,"unit":"kJ/mol"}
```

Task 8 的规范化 JSONL：

```json
{"task_id":"property_calc_crystal_phase_002","answers":[{"property":"potential_energy_difference","value":0.079,"unit":"eV"},{"property":"ambient_pressure_phase","value":"alpha"},{"property":"high_pressure_phase","value":"beta"}]}
```

原始模型回复使用相同 JSON 内容，并放在单行 `FINAL ANSWER:` 之后。答案归一化支持原始回复和结构化 JSONL；重复属性或非法列表结构是 `parse_error`。

## 4. Scoring

Task 7 的公开 gold 为 `0.258031679 kJ/mol`，绝对容差为 `0.001 kJ/mol`。版本 1 只接受精确单位字符串 `kJ/mol`，不进行 meV 或其他单位换算。

Task 8 有两个等权比较组：

1. `potential_energy_difference`：gold `0.079 eV`，绝对容差 `0.001 eV`。
2. `pressure_phase_assignment`：常压相必须为 `alpha` 且高压相必须为 `beta`，两项全对时该组才得 1。

最终分数是比较组的算术平均，因此 Task 8 只可能得到 `0`、`0.5` 或 `1`。

格式正确但数值、单位或相位错误的答案返回 `status: ok` 和相应低分；它不是 evaluator 故障。

## 5. Result Contract

结果复用其他 tracks 的外层字段：

```yaml
task_id: string
status: ok | error
canonical_smiles: null
properties:
  submitted_answers: mapping
  gold_answers: mapping
scores:
  validity_gate: number
  domain_gate: number
  constraint_scores: [mapping]
  property_score: number
  score: number
failure_type: string | null
message: string | null
versions: mapping
```

`constraint_scores` 在这里记录比较组结果，不代表运行了 verifier script。

## 6. Gold Policy

gold 数值随 task data 和公开 sample answers 发布，用于本地 sanity check、agent 计算能力评估和模型回归。初版只记录 `withheld_initial_release`，不公布 gold 生成协议，也不把协议写入 prompt。
