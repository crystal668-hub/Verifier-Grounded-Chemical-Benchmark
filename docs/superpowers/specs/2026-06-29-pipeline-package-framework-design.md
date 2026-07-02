# Pipeline 框架封装设计方案

## 背景

当前仓库已经形成了可运行的 verifier-grounded pipeline：

```text
task -> answer extraction -> verifier spec lookup -> property-level verification_script -> score aggregation
```

真实实现主要分布在：

- `tasks/rdkit_baseline/`：RDKit small-molecule descriptor task pack。
- `tasks/xtb_xyz/`：xTB direct-XYZ task pack。
- `benchmark/answer_extraction.py`：把 raw model response 归一化为 verifier-ready candidate。
- `benchmark/verifier_scripts.py`：构造 verifier script payload 并通过子进程运行 property-level script。
- `benchmark/evaluate.py`：按 task constraint 路由 verifier、聚合多约束分数并输出 report。
- `verifiers/`：property-level verifier scripts 和共享计算后端。

下一阶段目标不是新增 benchmark task，而是把这套 pipeline 封装成使用者可以直接 import 的 Python package。使用者应能枚举任务、拿到 prompt、用自己的模型或 agent 生成答案，再把答案交回 package 评分。

## 设计目标

本次封装只聚焦 package 框架：

- Python API 优先，CLI 只是薄封装。
- 暂时不引入新的 benchmark task，默认正式 track 只包含 `rdkit` 和 `xtb`。
- 模型调用不属于 package 职责；使用者自行调用模型并提交 answer records。
- 保留当前 property-level verifier script I/O 契约，不回退到中心化 Python verifier registry。
- 后续新增 task/verifier 时，应通过显式注册加入框架，不需要修改 evaluator 核心路由。
- 包名设计保持可迁移：正式 import 名先用 `verifier_grounded_benchmark`，同时提供薄别名 `vgb`。

## 非目标

以下内容不纳入本阶段：

- 不新增 RDKit/xTB 之外的新正式 benchmark task。
- 不重新引入已移除的 `matgl_materials`、`mace_materials` 或 `atomisticskills_smoke` prototype task packs。
- 不内置 OpenAI、Anthropic、本地模型或其他 provider adapter。
- 不实现 provider retry、batch generation、prompt templating 或 agent orchestration。
- 不在第一版引入 Python entry-points 插件系统。
- 不改变现有 result schema、failure taxonomy 或 verifier script payload/result 契约。

## 外部 Benchmark 封装调研

高影响力 benchmark 的封装方式大致分为三类。

### Registry + Runner

LM Evaluation Harness 使用任务配置和 task manager 发现/加载任务，适合借鉴“配置可复现 + registry 发现”的模式。OpenAI Evals 也使用 registry 将 eval 名称映射到配置和实现。它们说明 benchmark package 需要稳定的命名、注册和加载入口。

参考：

- LM Evaluation Harness task guide: https://github.com/EleutherAI/lm-evaluation-harness/blob/main/docs/task_guide.md
- OpenAI Evals run docs: https://github.com/openai/evals/blob/main/docs/run-evals.md

### 分层执行框架

HELM 将 benchmark 流程拆成 scenario、adapter、executor、metric 和 runner。这个结构提醒我们应区分 task 数据、模型执行、verifier 执行和 metric 聚合。本项目不负责模型执行，因此只需要保留 task、verifier 和 evaluator/report 分层。

参考：

- HELM code structure: https://crfm-helm.readthedocs.io/en/latest/code/

### 领域 Python Package

TDC、GuacaMol、Matbench 和 TARTARUS 更接近本项目目标：它们把 benchmark 暴露为领域 package，用户在自己的训练、生成或搜索循环中调用 benchmark/oracle/evaluator。它们支持“Python API 优先，不接管模型调用”的设计。

参考：

- TDC quick start: https://tdcommons.ai/start/
- GuacaMol: https://github.com/BenevolentAI/guacamol
- Matbench: https://github.com/materialsproject/matbench
- TARTARUS benchmark: https://github.com/aspuru-guzik-group/Tartarus

### Task Pack 自包含

BIG-bench 采用每个 task 自包含目录的方式，目录中包含任务定义、说明和程序化评测入口。当前仓库的 `tasks/<track>/tasks.yaml + verifier_specs.yaml + sample_answers.jsonl` 已经接近这种形态，应继续保留 task pack 自包含边界。

参考：

- BIG-bench docs: https://github.com/google/BIG-bench/blob/main/docs/doc.md

## 总体方案

采用“Core object model + registry”方案。

用户入口示例：

```python
import verifier_grounded_benchmark as vgb

suite = vgb.load_suite(["rdkit", "xtb"])
tasks = suite.tasks()

# 用户自行调用模型，生成 answer records:
# [{"task_id": "...", "response": "..."}]
# 或 [{"task_id": "...", "candidates": [...]}]
report = suite.evaluate_answers(answer_records)
```

也支持短别名：

```python
import vgb

track = vgb.load_track("rdkit")
report = track.evaluate_answers(answer_records)
```

框架核心对象：

- `TrackDefinition`：声明一个 track 的资源位置、状态、标签和元数据。
- `Registry`：显式注册和发现 tracks。
- `Track`：加载后的单个 task pack，暴露 tasks、prompts、sample answers 和 evaluator。
- `Suite`：多个 track 的组合，处理 task id/verifier id 冲突。
- `Evaluator`：封装现有 answer extraction、script execution 和 score aggregation。
- `EvaluationReport`：对当前 dict report 的薄包装，提供序列化 helper。

## 公开 API

第一版公开 API 应保持小而稳定：

```python
list_tracks(status: str = "formal") -> list[TrackDefinition]
load_track(name: str) -> Track
load_suite(track_names: list[str] | None = None) -> Suite
register_track(definition: TrackDefinition, *, replace: bool = False) -> None
```

`Track` API：

```python
track.tasks() -> list[dict]
track.task(task_id: str) -> dict
track.prompts() -> list[dict[str, str]]
track.sample_answers() -> list[dict]
track.evaluate_one(answer: dict) -> dict
track.evaluate_answers(answers: list[dict]) -> dict | EvaluationReport
track.evaluator() -> Evaluator
```

`Suite` API：

```python
suite.tracks() -> list[Track]
suite.tasks() -> list[dict]
suite.task(task_id: str) -> dict
suite.prompts() -> list[dict[str, str]]
suite.evaluate_one(answer: dict) -> dict
suite.evaluate_answers(answers: list[dict]) -> dict | EvaluationReport
```

Answer record 支持两种形态：

```python
{"task_id": "rdkit_qed_max_001", "response": "...\nFINAL ANSWER: CCO"}
```

或：

```python
{"task_id": "rdkit_qed_max_001", "candidates": [{"smiles": "CCO"}]}
```

这个设计直接兼容当前 `benchmark/answer_extraction.py` 的 raw response 和 structured candidate 路径。

## Registry 设计

Registry 采用显式注册，不扫描整个 `tasks/` 目录。原因是仓库中仍可能存在非正式/prototype 内容，如果自动扫描会把非正式 task pack 错误暴露给用户。

首批内置注册：

```python
TrackDefinition(
    name="rdkit",
    version="0.1.0",
    display_name="RDKit baseline small-molecule tasks",
    task_pack_path="tasks/rdkit_baseline/tasks.yaml",
    verifier_specs_path="tasks/rdkit_baseline/verifier_specs.yaml",
    sample_answers_path="tasks/rdkit_baseline/sample_answers.jsonl",
    status="formal",
    tags=("small_molecule", "rdkit", "descriptor"),
)
```

```python
TrackDefinition(
    name="xtb",
    version="0.1.0",
    display_name="xTB direct-XYZ small-molecule tasks",
    task_pack_path="tasks/xtb_xyz/tasks.yaml",
    verifier_specs_path="tasks/xtb_xyz/verifier_specs.yaml",
    sample_answers_path="tasks/xtb_xyz/sample_answers.jsonl",
    status="formal",
    tags=("small_molecule_3d", "xtb", "xyz"),
    requirements=("xtb executable for real scoring",),
)
```

`Registry` 职责：

- `list_tracks(status="formal")`：列出正式公开 track。
- `get_track_definition(name)`：按名字取 track definition。
- `register_track(definition, replace=False)`：显式注册外部 track。

重复注册同名 track 默认报错；只有显式 `replace=True` 才允许覆盖。

外部扩展示例：

```python
vgb.register_track(
    vgb.TrackDefinition(
        name="my_track",
        version="0.1.0",
        display_name="My experimental track",
        task_pack_path="path/to/tasks.yaml",
        verifier_specs_path="path/to/verifier_specs.yaml",
        sample_answers_path="path/to/sample_answers.jsonl",
        status="experimental",
        tags=("custom",),
    )
)
```

## Track 与 Suite 行为

`Track` 加载 YAML 后维护：

- `tasks_by_id`
- `verifier_specs_by_id`
- `definition`
- `resource_root`

`Track.prompts()` 返回最小任务视图：

```python
[
    {
        "track": "rdkit",
        "task_id": "rdkit_qed_max_001",
        "prompt": "...",
    }
]
```

`Suite` 组合多个 track 时做保护：

- task id 不能冲突；冲突应抛出 API usage error。
- verifier id 可以共享，但同名 verifier spec 必须内容一致；不一致应抛出 API usage error。
- 默认 `load_suite()` 只加载 status 为 `formal` 的内置 track，即 `rdkit` 和 `xtb`。

这个行为能防止后续扩展时同名 task/verifier 含义漂移。

## Evaluator 与 Report

`Evaluator` 不保存模型状态，只保存 tasks、specs 和执行配置：

```python
evaluator = vgb.load_track("rdkit").evaluator()
result = evaluator.evaluate_one({"task_id": "...", "response": "..."})
report = evaluator.evaluate_many(answer_records)
```

`evaluate_one` 行为保持当前流程：

1. 检查 `task_id`。
2. 根据 task 的 `answer_schema` 从 `response/raw_answer` 抽取候选，或直接接受 `candidates`。
3. 按 constraints 找 verifier spec。
4. 构造 script payload。
5. 子进程执行 property-level verifier script。
6. 聚合多约束结果。

默认返回仍使用当前 dict schema：

```python
{
    "summary": {...},
    "rows": [...],
}
```

可额外提供薄包装：

```python
EvaluationReport(summary: dict, rows: list[dict])
```

helper：

- `to_dict()`
- `to_json(indent=2)`
- `to_jsonl_rows()`

底层 schema 仍以 dict 为准，避免过早把所有 task/spec/result 字段类型化。

## 错误处理策略

保持“结果内结构化错误优先，不让整批评测轻易崩掉”：

- 用户答案问题返回 result：`parse_error`、`validity_error`、`domain_error`、`task_error`。
- verifier 环境问题返回 result：`verifier_environment_error`、`verifier_tool_error`、`verifier_timeout`。
- API 使用错误才抛异常：不存在的 track、非法注册、YAML 结构无效、suite task id 冲突、同名 verifier spec 不一致。

这个策略与现有 `benchmark.evaluate` 行为一致，也便于用户批量评测模型。

## 资源和脚本路径

当前 verifier spec 中的 `verification_script` 是 repo-relative 路径，例如：

```yaml
verification_script: verifiers/descriptors/rdkit_qed.py
```

package 化后不能假设当前工作目录就是 repo root，因此需要明确资源解析规则：

- 内置 track 的 task/spec/sample 路径由 package 自己解析。
- 内置 verifier script 路径从 package/resource root 解析。
- 外部 track 的相对路径从注册时的 `resource_root` 或 `task_pack_path` 所在目录解析。
- 第一版不移动 `tasks/`，但 `pyproject.toml` 必须确保 wheel/sdist 包含 task yaml、sample answers 和 verifier scripts。

实现时可以先保留现有顶层资源布局，降低迁移风险。

## 建议代码结构

新增公开包目录：

```text
verifier_grounded_benchmark/
  __init__.py
  registry.py
  track.py
  evaluator.py
  io.py
  resources.py
vgb/
  __init__.py
```

职责：

- `verifier_grounded_benchmark/__init__.py`：公开 facade。
- `registry.py`：`TrackDefinition`、`Registry` 和内置 registry。
- `track.py`：`Track`、`Suite`、prompt/sample helper。
- `evaluator.py`：`Evaluator`、`EvaluationConfig`、`EvaluationReport`。
- `io.py`：YAML/JSONL loader 和基本 schema validation。
- `resources.py`：package/resource root 和 script path resolution。
- `vgb/__init__.py`：`from verifier_grounded_benchmark import *` 的薄别名。

现有目录保留：

```text
benchmark/
  answer_extraction.py
  verifier_scripts.py
  evaluate.py
verifiers/
tasks/
```

`benchmark.evaluate` 第一阶段可以保持原实现，或逐步委托到新 evaluator core。为了降低风险，建议先让新 `Evaluator` 复用现有 `benchmark.evaluate` 函数，确保公开 API 与旧结果完全一致；后续再决定是否把旧模块变成 shim。

## 迁移步骤

1. 添加 `TrackDefinition`、`Registry` 和内置 `rdkit/xtb` 注册，不改变评分逻辑。
2. 添加 `Track` 与 `Suite`，支持 `list_tracks/load_track/load_suite/tasks/prompts/sample_answers`。
3. 添加 `Evaluator`，内部复用现有 `benchmark.evaluate.evaluate_one/evaluate_many`。
4. 添加 `vgb` alias package。
5. 调整 `pyproject.toml`，让项目可作为 package 安装，并包含 task/spec/verifier script 资源。
6. 更新 `scripts/score_answers.py`，支持 `--track rdkit` 或 `--track xtb`，同时保留传统 `--tasks/--specs` 路径参数。
7. 保持现有 result schema 和 verifier script I/O 不变。
8. 编写公开 API 和 registry 测试。
9. 运行全量测试后提交。

## 测试计划

新增 `tests/test_public_api.py`：

- `import verifier_grounded_benchmark as vgb_long` 成功。
- `import vgb` 成功。
- `vgb.list_tracks()` 只包含 `rdkit` 和 `xtb`。
- `vgb.load_track("rdkit").tasks()` 返回 RDKit tasks。
- `vgb.load_suite()` 默认包含 rdkit/xtb，不包含 matgl/mace/atomisticskills prototype tasks。
- `vgb.load_track("rdkit").evaluate_answers(sample_answers)` 与当前 `benchmark.evaluate.evaluate_many` summary 一致。
- `vgb.load_track("xtb").evaluate_one(...)` 对缺失 XYZ candidate 返回结构化 `parse_error`。

新增 `tests/test_registry.py`：

- 重复注册同名 track 抛异常。
- `replace=True` 时允许覆盖。
- 外部 track 路径可注册并加载。
- suite task id 冲突抛异常。
- suite 同名 verifier spec 不一致抛异常。

扩展 CLI 测试：

- `scripts/score_answers.py --track rdkit --answers tasks/rdkit_baseline/sample_answers.jsonl` 输出与旧路径参数相同的 summary。
- 旧参数 `--tasks/--specs/--answers` 继续可用。

执行要求：

- 每次代码或文档变更后先运行测试。
- 测试通过后再按仓库要求创建 git commit。

## 验收标准

本阶段完成后应满足：

- 用户能通过 `import verifier_grounded_benchmark as vgb` 或 `import vgb` 使用 package。
- 默认公开 track 只有 `rdkit` 和 `xtb`。
- 用户无需知道内部 YAML 路径即可加载 tasks、prompts 和 sample answers。
- 用户能把 raw model responses 或 structured candidates 交给 package 评分。
- RDKit 和 xTB 的评分结果与现有 pipeline 保持一致。
- 新 task/verifier 的接入路径是显式注册新 track，而不是修改 evaluator 分发表。
- 现有 `benchmark.evaluate`、verifier scripts 和 task pack 不被破坏。
