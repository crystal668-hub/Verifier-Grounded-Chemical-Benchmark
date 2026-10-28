# Verifier-Grounded Benchmark (v1.0.0-rc)

Python package version: `1.0.0rc1`; Git tag: `v1.0.0-rc`.

`verifier_grounded_benchmark` 提供可复现的化学 benchmark task pack、verifier 和评分工具。
模型调用由用户或 agent runner 负责；本包负责提供题目、解析答案并生成评分报告。

v0.10.0 采用逐题独立容差，不再加载或校验 `family-policy.yaml`。
四个正式 track 的评分 profile 已移除开发记录 `provenance`，运行时仅使用评分参数。
Basic 013 的容差为 ±3 kcal/mol；Advanced 007、009、012 分别为
±10 kcal/mol、±0.1 Å、±5 kcal/mol，并先对答案与 gold 取绝对值再比较。
容差仍表示线性评分降至零的误差宽度，gold 和字段权重不变。
Advanced 010 使用半径 1.2 Å 的球形探针。
RDKit 和 xTB 的 task-id 分别标准化为 `rdkit_001_qed_max`–`rdkit_010_caffeine_similarity_max`、
`xtb_001_gap_window`–`xtb_020_pyrene_substituent_energy_min`；已有答案记录需同步更新 task-id。

2026-10-28 源码题集删减后共 100 题：RDKit 10、xTB 20、Basic 51、Advanced 19。
保留任务已按原相对顺序连续编号；旧答案记录必须按完整 task ID 映射迁移，
不能只按数字编号匹配。退役备份不进入 wheel/sdist；历史 release 快照保持原样。

## QuickStart

### Installation

Requires Python **3.12** (`>=3.12,<3.13`). The following commands target macOS/Linux.
On Windows, activate `.venv\Scripts\activate` instead. Use the actual absolute
path of the local RC wheel; it is not assumed to be published on PyPI.

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install /absolute/path/to/verifier_grounded_benchmark-1.0.0rc1-py3-none-any.whl
```

For a source checkout with uv installed, use `uv sync --frozen` and run commands
through `uv run --no-sync`. Optional backend groups are not needed for the
RDKit and Property Calculation examples below.

### Complete RDKit example

Run these commands in a writable experiment directory after installation:

```bash
python - <<'PY'
import json
from pathlib import Path
import verifier_grounded_benchmark as vgb

track = vgb.load_track("open_generation_rdkit")
Path("rdkit-answers.jsonl").write_text(
    "\n".join(json.dumps(answer) for answer in track.sample_answers()) + "\n",
    encoding="utf-8",
)
print(f"Prepared {len(track.tasks())} sample answers")
PY
vgb-score --track open_generation_rdkit --answers rdkit-answers.jsonl --require-complete > rdkit-report.json
python - <<'PY'
import json
from pathlib import Path
report = json.loads(Path("rdkit-report.json").read_text())
print(report["summary"])
assert report["summary"]["coverage"]["complete"] is True
assert report["summary"]["num_error"] == 0
assert report["summary"]["benchmark_score"] is not None
PY
```

These are bundled showcase answers, not model-performance measurements.
For a real run, pass `track.prompts()` to your model runner and save one JSON
object per task containing `task_id` and either `response` (the full model text)
or the documented structured answer. Keep the original answers and model/tool
configuration together with the report.

### Single property answer

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
| `property_calculation_advanced` | 19 道 advanced 固定输入性质计算题 |

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

`list_tracks(status="formal")` accepts a status string or `None` to list every
registered track. `load_suite(track_names=None)` defaults to the formal tracks.
`register_track(definition, replace=False)` rejects duplicate names unless
replacement is explicit. Unknown track/task names raise `KeyError`; malformed
packs raise `ValueError`. `TrackDefinition` is the typed registration input.
`evaluate_one(answer: dict)` returns the detailed result with `scores.score`;
`evaluate_answers(answers: list[dict], as_report=False)` returns `{summary, rows}`
with flattened `rows[*].score`. Set `as_report=True` for an `EvaluationReport`.

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

### Report and error interpretation

- `score` is in `[0, 1]` for scored answers. Invalid candidates, wrong units and
  invalid numeric values may legitimately receive zero. They are not tool errors.
- `status: error` and `score: null` identify submission-ID, evaluator or
  infrastructure errors. `failure_scope`, `failure_type` and `message` explain them.
- `evaluated_mean_score` summarizes scored rows only. `benchmark_score` is
  populated only for complete, duplicate-free, known-task coverage with no errors.
- Exit **0**: evaluation completed without error rows; a partial run can still
  exit 0 unless `--require-complete` was requested.
- Exit **2**: argument, dependency, required-coverage or evaluation error.
  Evaluation errors retain the JSON report on stdout; dependency and coverage
  failures produce structured diagnostics on stderr. Invalid input files may
  terminate with exit 1. Never interpret a missing report as a zero score.

Property numeric units must match exactly; no unit conversion is performed.
Tolerance widths are the distance from gold to zero credit, not full-credit
acceptance intervals. Advanced 002 averages two groups: energy and phase. The
phase group scores 1 only when both phases are correct. Field scores `[1,1,0]`
therefore give total **0.5**, not 2/3. Other ungrouped property tasks average fields.

### xTB and environment checks

xTB tasks require xTB **6.7.1**; task 020 additionally requires CREST **2.12**.
The source checkout includes `envs/crest-xtb.yml`: create it with
`conda env create -f envs/crest-xtb.yml`. Verifier preflight can discover the
`vgb-crest` environment. No executable environment is bundled in the wheel.
The nine xTB showcase answers cover only nine of the twenty tasks.

From the source checkout, `uv run --no-sync python scripts/env/check_core_env.py`
checks only declared core packages. `--include-optional` additionally checks the
`future-backends` and `materials` groups, which must first be installed with
`uv sync --group future-backends --group materials`. Dedicated backend check
scripts remain available under `scripts/env/`.

If an executable is missing or has the wrong version, fix the environment and
rerun the original answers. If coverage fails, inspect missing/duplicate/unknown
task IDs and apply the RC ID migration; do not match tasks by numeric suffix alone.

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

Separate scoring configs must match the task-pack ID and version. Duplicate
mapping keys in task, scoring and verifier YAML are errors rather than overrides.

## RC scope and migration

The `v1.0.0-rc` Git label maps explicitly to Python version `1.0.0rc1`. Historical
`v0.10.0` artifacts remain unchanged. Five tasks were retired, and 25 retained
task IDs changed; the new suite has 100 tasks instead of 105. Difficulty accepts
only `basic` or `advanced`. Old/new whole-suite scores use different inventories
and must not be treated as directly comparable. Result schema 3 and
`linear_goal_v2` are unchanged.

Full RC changes, the retained-ID mapping and acceptance materials accompany the
local release directory `releases/v1.0.0-rc/`. The source release notes are in
`docs/research/2026-10-28-v1.0.0-rc-release-notes.md`. This is a local artifact
delivery, with no remote publication or license grant implied. The review-system
development tool, retirement backups and private calibration inputs are excluded.
