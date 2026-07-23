# verifier_grounded_benchmark 使用说明

`verifier_grounded_benchmark` 是 verifier-grounded benchmark pipeline 的
Python package 入口。它负责加载 benchmark task、暴露 prompt、接收外部模型生成的
answer records，并调用内置 verifier pipeline 进行评分。

该 package 不负责模型调用。使用者需要自行调用 LLM、agent 或分子生成程序，然后把输出
按约定格式提交给本框架评分。

## 安装

当前项目可以从本地源码或本地 wheel 安装：

```bash
pip install .
```

或使用 `uv`：

```bash
uv pip install .
```

也可以先构建 wheel 再安装：

```bash
uv build --wheel
pip install dist/verifier_grounded_benchmark-0.3.0-py3-none-any.whl
```

如果后续发布到 PyPI 或私有包索引，才使用下面这种包名安装方式：

```bash
pip install verifier-grounded-benchmark
```

运行环境要求 Python `>=3.12,<3.13`。RDKit track 的依赖随 package 安装。xTB
track 的真实计算评分还需要系统中可执行的 `xtb` 命令，并且该命令在 `PATH` 中。

## 快速开始

推荐使用 Python API：

```python
import verifier_grounded_benchmark as vgb

track = vgb.load_track("rdkit")

prompts = track.prompts()
first_prompt = prompts[0]

# 使用者自行调用模型。本 package 不调用模型。
answer_records = [
    {
        "task_id": first_prompt["task_id"],
        "response": "Reasoning text...\nFINAL ANSWER: CCO",
    }
]

report = track.evaluate_answers(answer_records)
print(report["summary"])
print(report["rows"][0])
```

也可以使用短别名：

```python
import vgb

suite = vgb.load_suite(["rdkit", "xtb", "property_calculation"])
print([track.name for track in suite.tracks()])
```

## 内置 tracks

默认正式 track 有三类：

| track | 内容 | 额外环境要求 |
| --- | --- | --- |
| `rdkit` | RDKit small-molecule descriptor tasks，输入通常是 SMILES | 无额外命令行工具 |
| `xtb` | xTB molecular optimization tasks，按题目接受 explicit-H XYZ 或 SMILES | 真实评分需要 `xtb`；构象搜索题还需要 CREST 2.12 |
| `property_calculation` | 给定完整结构并对照公开 gold 评分的性质计算题 | 无额外命令行工具 |

查看当前可用正式 track：

```python
import verifier_grounded_benchmark as vgb

for definition in vgb.list_tracks():
    print(definition.name, definition.version, definition.display_name)
```

默认 `vgb.list_tracks()` 只返回 `status="formal"` 的 tracks。仓库中可能包含实验性或
开发中的 task resources，但不会自动进入正式公开列表。

## 获取任务和 prompt

加载单个 track：

```python
track = vgb.load_track("rdkit")

tasks = track.tasks()
task = track.task("rdkit_qed_max_001")
prompts = track.prompts()
sample_answers = track.sample_answers()
```

`track.prompts()` 返回面向模型调用的最小视图：

```python
[
    {
        "track": "rdkit",
        "task_id": "rdkit_qed_max_001",
        "prompt": "...",
        "answer_schema": {
            "format": "final_answer_line",
            "final_answer_prefix": "FINAL ANSWER:",
            "value_type": "smiles",
        },
    }
]
```

该视图只公开模型作答所需的 prompt 和 answer schema，不包含 verifier spec、
sample answer 或 gold。评分端应通过同一安装版本的 `track.evaluate_one(...)` 提交答案，
不要从任务目录复制内部评分配置。

加载多个 tracks 组成 suite：

```python
suite = vgb.load_suite(["rdkit", "xtb", "property_calculation"])
all_prompts = suite.prompts()
```

不传参数时，`load_suite()` 会加载所有正式 track：

```python
suite = vgb.load_suite()
```

## Answer record 格式

每条 answer record 必须至少包含 `task_id`。框架支持两种提交方式。

### 原始模型回复

这是最贴近真实测评的方式。框架会根据 task 的 `answer_schema` 从 `response` 中抽取最终答案：

```python
{
    "task_id": "rdkit_qed_max_001",
    "response": "I propose ethanol.\nFINAL ANSWER: CCO",
}
```

RDKit track 的 prompt 通常要求最终答案格式为：

```text
FINAL ANSWER: <SMILES>
```

xTB track 的 prompt 通常要求最终答案格式为：

````text
FINAL ANSWER:
```xyz
<XYZ content>
```
````

### 结构化 candidates

如果使用者已经完成答案抽取，也可以直接提交 verifier-ready candidates：

```python
{
    "task_id": "rdkit_qed_max_001",
    "candidates": [{"smiles": "CCO"}],
}
```

xTB 的结构化输入通常包含 XYZ 字符串：

```python
{
    "task_id": "xtb_gap_window_001",
    "candidates": [
        {
            "xyz": "3\nwater\nO 0.0 0.0 0.0\nH 0.0 0.8 0.6\nH 0.0 -0.8 0.6\n"
        }
    ],
}
```

## 评分

评分单条 answer：

```python
result = track.evaluate_one(
    {"task_id": "rdkit_qed_max_001", "candidates": [{"smiles": "CCO"}]}
)
```

评分一批 answers：

```python
answers = track.sample_answers()
report = track.evaluate_answers(answers)
```

返回的 report 是一个普通 dict：

```python
{
    "summary": {
        "num_answers": 10,
        "num_ok": 10,
        "num_error": 0,
        "mean_score": 0.95,
        "evaluated_mean_score": 0.95,
        "coverage": {
            "num_tasks_total": 10,
            "num_rows_submitted": 10,
            "missing_task_ids": [],
            "duplicate_task_ids": [],
            "unknown_task_ids": [],
            "complete": True,
        },
        "benchmark_score": 0.95,
    },
    "rows": [
        {
            "task_id": "rdkit_qed_max_001",
            "status": "ok",
            "failure_type": None,
            "score": 0.88,
            "properties": {},
            "constraint_scores": [],
        }
    ],
}
```

`coverage.complete` 只有在所有任务都被提交且没有重复或未知 `task_id` 时才为 `True`。
当提交不完整时，`benchmark_score` 为 `None`；此时 `mean_score` 或
`evaluated_mean_score` 只代表已提交任务的平均分，不应作为正式 benchmark 总分。

如果需要序列化 helper，可以请求 `EvaluationReport` 包装对象：

```python
report = track.evaluate_answers(track.sample_answers(), as_report=True)

print(report.to_json())
print(report.to_jsonl_rows())
```

需要遇到第一条评分错误就中断时：

```python
config = vgb.EvaluationConfig(fail_fast=True)
evaluator = track.evaluator(config=config)
report = evaluator.evaluate_many(track.sample_answers())
```

## CLI

安装 package 后会提供 `vgb-score` 命令。

使用内置 track 评分 JSONL answer 文件：

```bash
vgb-score --track rdkit --answers answers.jsonl
```

要求提交完整覆盖整个 track：

```bash
vgb-score --track rdkit --answers answers.jsonl --require-complete
```

`answers.jsonl` 每行是一条 answer record：

```jsonl
{"task_id":"rdkit_qed_max_001","response":"FINAL ANSWER: CCO"}
{"task_id":"rdkit_sa_min_002","candidates":[{"smiles":"O=C(O)c1ccccc1"}]}
```

维护 task pack 时，也可以显式传入 tasks 和 verifier specs。这个路径主要用于开发：

```bash
vgb-score \
  --tasks path/to/tasks.yaml \
  --specs path/to/verifier_specs.yaml \
  --answers answers.jsonl
```

`--track` 不能和 `--tasks` 或 `--specs` 同时使用。

## 注册新 track

后续新增 task 和 verifier 时，不需要修改 evaluator 核心逻辑。把 task pack 和
verifier specs 准备好后，通过 `TrackDefinition` 注册即可。

推荐目录结构：

```text
my_track/
  tasks.yaml
  verifier_specs.yaml
  sample_answers.jsonl
  verifiers/
    my_property.py
```

注册示例：

```python
from pathlib import Path

import verifier_grounded_benchmark as vgb

root = Path("my_track").resolve()

vgb.register_track(
    vgb.TrackDefinition(
        name="my_track",
        version="0.1.0",
        display_name="My experimental track",
        task_pack_path="tasks.yaml",
        verifier_specs_path="verifier_specs.yaml",
        sample_answers_path="sample_answers.jsonl",
        status="experimental",
        tags=("custom",),
        requirements=("describe extra runtime requirements here",),
        resource_root=root,
    )
)

track = vgb.load_track("my_track")
report = track.evaluate_answers(track.sample_answers())
```

`resource_root` 用于解析相对路径。`verifier_specs.yaml` 中的
`verification_script` 也会被 materialize 为绝对路径，便于 verifier 子进程执行。

如果同名 track 已经注册，默认会报错。只有明确希望覆盖时才使用：

```python
vgb.register_track(definition, replace=True)
```

## API 速查

| API | 用途 |
| --- | --- |
| `vgb.list_tracks(status="formal")` | 列出已注册 tracks，默认只列正式 tracks |
| `vgb.load_track(name)` | 加载单个 track |
| `vgb.load_suite(track_names=None)` | 加载多个 tracks；默认加载正式 tracks |
| `vgb.register_track(definition, replace=False)` | 注册外部 track |
| `Track.tasks()` / `Suite.tasks()` | 返回完整 task dict 列表 |
| `Track.task(task_id)` / `Suite.task(task_id)` | 按 `task_id` 获取单个 task |
| `Track.prompts()` / `Suite.prompts()` | 返回模型调用所需的 prompt 列表 |
| `Track.sample_answers()` | 返回 track 自带样例答案 |
| `evaluate_one(answer)` | 评分单条 answer record |
| `evaluate_answers(answers, as_report=False)` | 批量评分 answer records |
| `EvaluationReport.to_json()` | 将 report 序列化为 JSON 字符串 |
| `EvaluationReport.to_jsonl_rows()` | 将每条评分 row 序列化为 JSONL 文本 |

## 常见问题

### `pip install verifier-grounded-benchmark` 找不到包

说明该 package 尚未发布到你使用的包索引。请先使用本地源码安装：

```bash
pip install .
```

或安装本地构建出的 wheel。

### xTB track 报 `verifier_environment_error`

通常表示 `xtb` executable 不在 `PATH` 中，或运行环境缺少 xTB 所需依赖。先确认：

```bash
xtb --version
```

### `benchmark_score` 是 `None`

这通常表示提交不完整，或存在重复/未知 `task_id`。检查：

```python
report["summary"]["coverage"]
```

只有 `coverage.complete == True` 时，`benchmark_score` 才代表正式整套任务得分。

### 我应该把模型调用接在哪里？

模型调用应放在本 package 外部。典型流程是：

1. 使用 `track.prompts()` 或 `suite.prompts()` 取出任务 prompt。
2. 使用自己的模型、agent 或搜索程序生成 response。
3. 组装成 answer records。
4. 调用 `evaluate_answers()` 或 `vgb-score` 评分。
