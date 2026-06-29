# Pipeline Package Framework Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Python-first package framework approved in `docs/superpowers/specs/2026-06-29-pipeline-package-framework-design.md`.

**Architecture:** Add a public `verifier_grounded_benchmark` package plus a thin `vgb` alias. The new package exposes registry, track, suite, evaluator, and report objects while reusing the existing `benchmark.evaluate`, `benchmark.answer_extraction`, and verifier script pipeline. Built-in registry entries load only the existing formal `rdkit` and `xtb` task packs.

**Tech Stack:** Python 3.12, dataclasses, pathlib, PyYAML, pytest, existing `benchmark` and `verifiers` modules, Hatchling packaging metadata through `pyproject.toml`.

---

## File Structure

Create these public package modules:

- `verifier_grounded_benchmark/__init__.py`: public facade and global registry helpers.
- `verifier_grounded_benchmark/io.py`: YAML/JSONL loading helpers and minimal schema checks.
- `verifier_grounded_benchmark/resources.py`: project/package resource path resolution and verifier script path materialization.
- `verifier_grounded_benchmark/registry.py`: `TrackDefinition`, `Registry`, built-in `rdkit` and `xtb` registry entries.
- `verifier_grounded_benchmark/evaluator.py`: `EvaluationConfig`, `EvaluationReport`, and `Evaluator`.
- `verifier_grounded_benchmark/track.py`: `Track` and `Suite`.
- `vgb/__init__.py`: thin alias to the public package.

Modify existing files:

- `pyproject.toml`: switch from non-package mode to package mode and include top-level task resources in distributions.
- `scripts/score_answers.py`: add `--track` while preserving `--tasks/--specs`.
- `tests/test_evaluate_routing.py`: extend CLI coverage for `--track`.

Create tests:

- `tests/test_public_api.py`: public import, built-in tracks, default suite, prompt/sample/evaluator behavior.
- `tests/test_registry.py`: registry replacement, external track loading, suite collision checks.

Do not move task packs, verifier scripts, or existing `benchmark/` modules in this implementation.

---

### Task 1: Registry, IO, And Resource Foundation

**Files:**
- Create: `verifier_grounded_benchmark/io.py`
- Create: `verifier_grounded_benchmark/resources.py`
- Create: `verifier_grounded_benchmark/registry.py`
- Create: `verifier_grounded_benchmark/__init__.py`
- Test: `tests/test_registry.py`

- [ ] **Step 1: Write failing registry foundation tests**

Create `tests/test_registry.py` with this content:

```python
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from verifier_grounded_benchmark.registry import Registry, TrackDefinition


ROOT = Path(__file__).resolve().parents[1]


def test_registry_lists_only_formal_tracks_by_default() -> None:
    registry = Registry()
    registry.register_track(
        TrackDefinition(
            name="formal_track",
            version="1",
            display_name="Formal Track",
            task_pack_path=ROOT / "tasks" / "rdkit_baseline" / "tasks.yaml",
            verifier_specs_path=ROOT / "tasks" / "rdkit_baseline" / "verifier_specs.yaml",
            status="formal",
        )
    )
    registry.register_track(
        TrackDefinition(
            name="experimental_track",
            version="1",
            display_name="Experimental Track",
            task_pack_path=ROOT / "tasks" / "xtb_xyz" / "tasks.yaml",
            verifier_specs_path=ROOT / "tasks" / "xtb_xyz" / "verifier_specs.yaml",
            status="experimental",
        )
    )

    assert [definition.name for definition in registry.list_tracks()] == ["formal_track"]
    assert {definition.name for definition in registry.list_tracks(status=None)} == {
        "formal_track",
        "experimental_track",
    }


def test_registry_rejects_duplicate_track_names() -> None:
    registry = Registry()
    definition = TrackDefinition(
        name="rdkit",
        version="1",
        display_name="RDKit",
        task_pack_path=ROOT / "tasks" / "rdkit_baseline" / "tasks.yaml",
        verifier_specs_path=ROOT / "tasks" / "rdkit_baseline" / "verifier_specs.yaml",
        status="formal",
    )
    registry.register_track(definition)

    with pytest.raises(ValueError, match="already registered"):
        registry.register_track(definition)


def test_registry_replace_allows_explicit_override() -> None:
    registry = Registry()
    first = TrackDefinition(
        name="rdkit",
        version="1",
        display_name="First",
        task_pack_path=ROOT / "tasks" / "rdkit_baseline" / "tasks.yaml",
        verifier_specs_path=ROOT / "tasks" / "rdkit_baseline" / "verifier_specs.yaml",
        status="formal",
    )
    second = TrackDefinition(
        name="rdkit",
        version="2",
        display_name="Second",
        task_pack_path=ROOT / "tasks" / "xtb_xyz" / "tasks.yaml",
        verifier_specs_path=ROOT / "tasks" / "xtb_xyz" / "verifier_specs.yaml",
        status="experimental",
    )

    registry.register_track(first)
    registry.register_track(second, replace=True)

    assert registry.get_track_definition("rdkit").version == "2"
    assert registry.get_track_definition("rdkit").status == "experimental"


def test_track_definition_resolves_relative_paths_from_resource_root(tmp_path: Path) -> None:
    task_dir = tmp_path / "custom"
    task_dir.mkdir()
    tasks_path = task_dir / "tasks.yaml"
    specs_path = task_dir / "verifier_specs.yaml"
    tasks_path.write_text(yaml.safe_dump({"tasks": [{"task_id": "custom_task", "prompt": "Prompt", "constraints": []}]}))
    specs_path.write_text(yaml.safe_dump({"verifiers": []}))

    definition = TrackDefinition(
        name="custom",
        version="1",
        display_name="Custom",
        task_pack_path="tasks.yaml",
        verifier_specs_path="verifier_specs.yaml",
        resource_root=task_dir,
        status="experimental",
    )

    assert definition.resolve_path(definition.task_pack_path) == tasks_path
    assert definition.resolve_path(definition.verifier_specs_path) == specs_path
```

- [ ] **Step 2: Run registry tests and verify they fail for missing package**

Run:

```bash
uv run pytest tests/test_registry.py -q
```

Expected: fail with `ModuleNotFoundError: No module named 'verifier_grounded_benchmark'`.

- [ ] **Step 3: Add IO helpers**

Create `verifier_grounded_benchmark/io.py`:

```python
"""File loading helpers for task packs, verifier specs, and answer records."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


def load_tasks_file(path: str | Path) -> dict[str, dict[str, Any]]:
    resolved = Path(path)
    with resolved.open() as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict) or not isinstance(payload.get("tasks"), list):
        raise ValueError(f"task file must contain a tasks list: {resolved}")
    tasks: dict[str, dict[str, Any]] = {}
    for task in payload["tasks"]:
        if not isinstance(task, dict):
            raise ValueError(f"task entries must be objects: {resolved}")
        task_id = task.get("task_id")
        if not isinstance(task_id, str) or not task_id:
            raise ValueError(f"task entries must include a task_id string: {resolved}")
        if task_id in tasks:
            raise ValueError(f"duplicate task_id {task_id!r} in {resolved}")
        tasks[task_id] = task
    return tasks


def load_verifier_specs_file(path: str | Path) -> dict[str, dict[str, Any]]:
    resolved = Path(path)
    with resolved.open() as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict) or not isinstance(payload.get("verifiers"), list):
        raise ValueError(f"verifier spec file must contain a verifiers list: {resolved}")
    specs: dict[str, dict[str, Any]] = {}
    for spec in payload["verifiers"]:
        if not isinstance(spec, dict):
            raise ValueError(f"verifier entries must be objects: {resolved}")
        verifier_id = spec.get("verifier_id")
        if not isinstance(verifier_id, str) or not verifier_id:
            raise ValueError(f"verifier entries must include a verifier_id string: {resolved}")
        if verifier_id in specs:
            raise ValueError(f"duplicate verifier_id {verifier_id!r} in {resolved}")
        specs[verifier_id] = spec
    return specs


def load_answers_jsonl_file(path: str | Path) -> list[dict[str, Any]]:
    resolved = Path(path)
    answers: list[dict[str, Any]] = []
    with resolved.open() as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            if not isinstance(record, dict):
                raise ValueError(f"answer JSONL line {line_number} must be an object: {resolved}")
            answers.append(record)
    return answers
```

- [ ] **Step 4: Add resource helpers**

Create `verifier_grounded_benchmark/resources.py`:

```python
"""Resource path helpers for built-in and external task packs."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any


def package_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_path(path: str | Path, *, base: str | Path | None = None) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    root = Path(base) if base is not None else package_root()
    return (root / candidate).resolve()


def materialize_verifier_specs(
    specs: dict[str, dict[str, Any]],
    *,
    script_root: str | Path,
) -> dict[str, dict[str, Any]]:
    materialized = deepcopy(specs)
    root = Path(script_root)
    for spec in materialized.values():
        script = spec.get("verification_script")
        if isinstance(script, str) and script:
            spec["verification_script"] = str(resolve_path(script, base=root))
    return materialized
```

- [ ] **Step 5: Add registry types and built-in entries**

Create `verifier_grounded_benchmark/registry.py`:

```python
"""Track registry for verifier-grounded benchmark task packs."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from verifier_grounded_benchmark.resources import package_root, resolve_path


@dataclass(frozen=True)
class TrackDefinition:
    name: str
    version: str
    display_name: str
    task_pack_path: str | Path
    verifier_specs_path: str | Path
    sample_answers_path: str | Path | None = None
    status: str = "formal"
    tags: tuple[str, ...] = field(default_factory=tuple)
    requirements: tuple[str, ...] = field(default_factory=tuple)
    resource_root: str | Path | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("track name must be non-empty")
        if not self.version:
            raise ValueError(f"track {self.name!r} must include a version")
        if not self.display_name:
            raise ValueError(f"track {self.name!r} must include a display_name")
        if not self.status:
            raise ValueError(f"track {self.name!r} must include a status")
        object.__setattr__(self, "tags", tuple(self.tags))
        object.__setattr__(self, "requirements", tuple(self.requirements))

    @property
    def root(self) -> Path:
        return Path(self.resource_root).resolve() if self.resource_root is not None else package_root()

    def resolve_path(self, path: str | Path) -> Path:
        return resolve_path(path, base=self.root)


class Registry:
    def __init__(self, definitions: Iterable[TrackDefinition] = ()) -> None:
        self._definitions: dict[str, TrackDefinition] = {}
        for definition in definitions:
            self.register_track(definition)

    def register_track(self, definition: TrackDefinition, *, replace: bool = False) -> None:
        if definition.name in self._definitions and not replace:
            raise ValueError(f"track {definition.name!r} is already registered")
        self._definitions[definition.name] = definition

    def get_track_definition(self, name: str) -> TrackDefinition:
        try:
            return self._definitions[name]
        except KeyError as exc:
            raise KeyError(f"unknown track: {name}") from exc

    def list_tracks(self, status: str | None = "formal") -> list[TrackDefinition]:
        definitions = list(self._definitions.values())
        if status is not None:
            definitions = [definition for definition in definitions if definition.status == status]
        return sorted(definitions, key=lambda definition: definition.name)


def builtin_definitions() -> list[TrackDefinition]:
    return [
        TrackDefinition(
            name="rdkit",
            version="0.1.0",
            display_name="RDKit baseline small-molecule tasks",
            task_pack_path="tasks/rdkit_baseline/tasks.yaml",
            verifier_specs_path="tasks/rdkit_baseline/verifier_specs.yaml",
            sample_answers_path="tasks/rdkit_baseline/sample_answers.jsonl",
            status="formal",
            tags=("small_molecule", "rdkit", "descriptor"),
            resource_root=package_root(),
        ),
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
            resource_root=package_root(),
        ),
    ]


DEFAULT_REGISTRY = Registry(builtin_definitions())
```

- [ ] **Step 6: Add initial public facade**

Create `verifier_grounded_benchmark/__init__.py`:

```python
"""Python API for the verifier-grounded benchmark pipeline."""

from __future__ import annotations

from verifier_grounded_benchmark.registry import DEFAULT_REGISTRY, Registry, TrackDefinition


def list_tracks(status: str | None = "formal") -> list[TrackDefinition]:
    return DEFAULT_REGISTRY.list_tracks(status=status)


def register_track(definition: TrackDefinition, *, replace: bool = False) -> None:
    DEFAULT_REGISTRY.register_track(definition, replace=replace)


__all__ = [
    "Registry",
    "TrackDefinition",
    "list_tracks",
    "register_track",
]
```

- [ ] **Step 7: Run registry foundation tests**

Run:

```bash
uv run pytest tests/test_registry.py -q
```

Expected: `4 passed`.

- [ ] **Step 8: Commit registry foundation**

Run:

```bash
git add verifier_grounded_benchmark/__init__.py verifier_grounded_benchmark/io.py verifier_grounded_benchmark/resources.py verifier_grounded_benchmark/registry.py tests/test_registry.py
git commit -m "feat: add benchmark track registry foundation"
```

---

### Task 2: Track And Suite Loading

**Files:**
- Create: `verifier_grounded_benchmark/track.py`
- Modify: `verifier_grounded_benchmark/__init__.py`
- Test: `tests/test_public_api.py`
- Test: `tests/test_registry.py`

- [ ] **Step 1: Write failing public API and suite tests**

Create `tests/test_public_api.py`:

```python
from __future__ import annotations

from pathlib import Path

import pytest

import verifier_grounded_benchmark as vgb


ROOT = Path(__file__).resolve().parents[1]


def test_public_api_lists_only_rdkit_and_xtb_formal_tracks() -> None:
    assert [definition.name for definition in vgb.list_tracks()] == ["rdkit", "xtb"]


def test_load_track_exposes_tasks_prompts_and_samples() -> None:
    track = vgb.load_track("rdkit")

    task_ids = [task["task_id"] for task in track.tasks()]
    prompts = track.prompts()
    sample_answers = track.sample_answers()

    assert "rdkit_qed_max_001" in task_ids
    assert prompts[0]["track"] == "rdkit"
    assert prompts[0]["task_id"] == "rdkit_qed_max_001"
    assert prompts[0]["prompt"].startswith("Propose one valid single-component molecule")
    assert len(sample_answers) == 10


def test_default_suite_loads_only_formal_builtin_tracks() -> None:
    suite = vgb.load_suite()
    task_ids = {task["task_id"] for task in suite.tasks()}

    assert "rdkit_qed_max_001" in task_ids
    assert "xtb_gap_window_001" in task_ids
    assert all(not task_id.startswith("matgl_") for task_id in task_ids)
    assert all(not task_id.startswith("mace_") for task_id in task_ids)


def test_load_unknown_track_raises_key_error() -> None:
    with pytest.raises(KeyError, match="unknown track"):
        vgb.load_track("missing")
```

Append these tests to `tests/test_registry.py`:

```python
from verifier_grounded_benchmark.track import Suite, Track


def test_suite_rejects_duplicate_task_ids(tmp_path: Path) -> None:
    tasks_path = tmp_path / "tasks.yaml"
    specs_path = tmp_path / "verifier_specs.yaml"
    tasks_path.write_text(yaml.safe_dump({"tasks": [{"task_id": "duplicate", "prompt": "Prompt", "constraints": []}]}))
    specs_path.write_text(yaml.safe_dump({"verifiers": []}))
    first = Track(
        TrackDefinition(
            name="first",
            version="1",
            display_name="First",
            task_pack_path=tasks_path,
            verifier_specs_path=specs_path,
            status="experimental",
            resource_root=tmp_path,
        )
    )
    second = Track(
        TrackDefinition(
            name="second",
            version="1",
            display_name="Second",
            task_pack_path=tasks_path,
            verifier_specs_path=specs_path,
            status="experimental",
            resource_root=tmp_path,
        )
    )

    with pytest.raises(ValueError, match="duplicate task_id"):
        Suite([first, second])


def test_suite_rejects_conflicting_verifier_specs(tmp_path: Path) -> None:
    tasks_path = tmp_path / "tasks.yaml"
    specs_a_path = tmp_path / "verifier_specs_a.yaml"
    specs_b_path = tmp_path / "verifier_specs_b.yaml"
    tasks_path.write_text(yaml.safe_dump({"tasks": [{"task_id": "task_a", "prompt": "Prompt", "constraints": []}]}))
    specs_a_path.write_text(
        yaml.safe_dump({"verifiers": [{"verifier_id": "shared_v1", "verification_script": "a.py"}]})
    )
    specs_b_path.write_text(
        yaml.safe_dump({"verifiers": [{"verifier_id": "shared_v1", "verification_script": "b.py"}]})
    )
    first = Track(
        TrackDefinition(
            name="first",
            version="1",
            display_name="First",
            task_pack_path=tasks_path,
            verifier_specs_path=specs_a_path,
            status="experimental",
            resource_root=tmp_path,
        )
    )
    second_tasks_path = tmp_path / "tasks_b.yaml"
    second_tasks_path.write_text(yaml.safe_dump({"tasks": [{"task_id": "task_b", "prompt": "Prompt", "constraints": []}]}))
    second = Track(
        TrackDefinition(
            name="second",
            version="1",
            display_name="Second",
            task_pack_path=second_tasks_path,
            verifier_specs_path=specs_b_path,
            status="experimental",
            resource_root=tmp_path,
        )
    )

    with pytest.raises(ValueError, match="conflicting verifier spec"):
        Suite([first, second])
```

- [ ] **Step 2: Run track tests and verify they fail for missing load functions**

Run:

```bash
uv run pytest tests/test_public_api.py tests/test_registry.py -q
```

Expected: fail with `AttributeError: module 'verifier_grounded_benchmark' has no attribute 'load_track'` or `ModuleNotFoundError` for `verifier_grounded_benchmark.track`.

- [ ] **Step 3: Implement Track and Suite**

Create `verifier_grounded_benchmark/track.py`:

```python
"""Loaded track and suite objects for benchmark users."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable

from verifier_grounded_benchmark.io import load_answers_jsonl_file, load_tasks_file, load_verifier_specs_file
from verifier_grounded_benchmark.registry import TrackDefinition
from verifier_grounded_benchmark.resources import materialize_verifier_specs


class Track:
    def __init__(self, definition: TrackDefinition) -> None:
        self.definition = definition
        self.tasks_by_id = load_tasks_file(definition.resolve_path(definition.task_pack_path))
        specs = load_verifier_specs_file(definition.resolve_path(definition.verifier_specs_path))
        self.verifier_specs_by_id = materialize_verifier_specs(specs, script_root=definition.root)

    @property
    def name(self) -> str:
        return self.definition.name

    def tasks(self) -> list[dict[str, Any]]:
        return [deepcopy(task) for task in self.tasks_by_id.values()]

    def task(self, task_id: str) -> dict[str, Any]:
        try:
            return deepcopy(self.tasks_by_id[task_id])
        except KeyError as exc:
            raise KeyError(f"unknown task_id for track {self.name!r}: {task_id}") from exc

    def prompts(self) -> list[dict[str, str]]:
        prompts: list[dict[str, str]] = []
        for task in self.tasks_by_id.values():
            prompt = task.get("prompt")
            if isinstance(prompt, str):
                prompts.append({"track": self.name, "task_id": str(task["task_id"]), "prompt": prompt})
        return prompts

    def sample_answers(self) -> list[dict[str, Any]]:
        if self.definition.sample_answers_path is None:
            return []
        return load_answers_jsonl_file(self.definition.resolve_path(self.definition.sample_answers_path))


class Suite:
    def __init__(self, tracks: Iterable[Track]) -> None:
        self._tracks = list(tracks)
        self.tasks_by_id: dict[str, dict[str, Any]] = {}
        self.verifier_specs_by_id: dict[str, dict[str, Any]] = {}
        for track in self._tracks:
            for task_id, task in track.tasks_by_id.items():
                if task_id in self.tasks_by_id:
                    raise ValueError(f"duplicate task_id across suite tracks: {task_id}")
                self.tasks_by_id[task_id] = deepcopy(task)
            for verifier_id, spec in track.verifier_specs_by_id.items():
                if verifier_id in self.verifier_specs_by_id and self.verifier_specs_by_id[verifier_id] != spec:
                    raise ValueError(f"conflicting verifier spec across suite tracks: {verifier_id}")
                self.verifier_specs_by_id[verifier_id] = deepcopy(spec)

    def tracks(self) -> list[Track]:
        return list(self._tracks)

    def tasks(self) -> list[dict[str, Any]]:
        return [deepcopy(task) for task in self.tasks_by_id.values()]

    def task(self, task_id: str) -> dict[str, Any]:
        try:
            return deepcopy(self.tasks_by_id[task_id])
        except KeyError as exc:
            raise KeyError(f"unknown task_id for suite: {task_id}") from exc

    def prompts(self) -> list[dict[str, str]]:
        prompts: list[dict[str, str]] = []
        for track in self._tracks:
            prompts.extend(track.prompts())
        return prompts
```

- [ ] **Step 4: Expose load_track and load_suite**

Update `verifier_grounded_benchmark/__init__.py` to:

```python
"""Python API for the verifier-grounded benchmark pipeline."""

from __future__ import annotations

from verifier_grounded_benchmark.registry import DEFAULT_REGISTRY, Registry, TrackDefinition
from verifier_grounded_benchmark.track import Suite, Track


def list_tracks(status: str | None = "formal") -> list[TrackDefinition]:
    return DEFAULT_REGISTRY.list_tracks(status=status)


def register_track(definition: TrackDefinition, *, replace: bool = False) -> None:
    DEFAULT_REGISTRY.register_track(definition, replace=replace)


def load_track(name: str) -> Track:
    return Track(DEFAULT_REGISTRY.get_track_definition(name))


def load_suite(track_names: list[str] | tuple[str, ...] | None = None) -> Suite:
    names = list(track_names) if track_names is not None else [definition.name for definition in list_tracks()]
    return Suite([load_track(name) for name in names])


__all__ = [
    "Registry",
    "Suite",
    "Track",
    "TrackDefinition",
    "list_tracks",
    "load_suite",
    "load_track",
    "register_track",
]
```

- [ ] **Step 5: Run track and suite tests**

Run:

```bash
uv run pytest tests/test_public_api.py tests/test_registry.py -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit Track and Suite loading**

Run:

```bash
git add verifier_grounded_benchmark/__init__.py verifier_grounded_benchmark/track.py tests/test_public_api.py tests/test_registry.py
git commit -m "feat: add benchmark track and suite loading"
```

---

### Task 3: Evaluator And Report API

**Files:**
- Create: `verifier_grounded_benchmark/evaluator.py`
- Modify: `verifier_grounded_benchmark/__init__.py`
- Modify: `verifier_grounded_benchmark/track.py`
- Test: `tests/test_public_api.py`

- [ ] **Step 1: Add failing evaluator tests**

Append these tests to `tests/test_public_api.py`:

```python
from benchmark.evaluate import evaluate_many, load_answers_jsonl, load_tasks, load_verifier_specs


def test_track_evaluate_answers_matches_existing_rdkit_summary() -> None:
    track = vgb.load_track("rdkit")
    answers = track.sample_answers()

    public_report = track.evaluate_answers(answers)
    legacy_report = evaluate_many(
        load_answers_jsonl(ROOT / "tasks" / "rdkit_baseline" / "sample_answers.jsonl"),
        load_tasks(ROOT / "tasks" / "rdkit_baseline" / "tasks.yaml"),
        load_verifier_specs(ROOT / "tasks" / "rdkit_baseline" / "verifier_specs.yaml"),
    )

    assert public_report["summary"] == legacy_report["summary"]
    assert public_report["rows"] == legacy_report["rows"]


def test_track_evaluate_one_returns_structured_xtb_parse_error() -> None:
    track = vgb.load_track("xtb")

    result = track.evaluate_one({"task_id": "xtb_gap_window_001", "candidates": [{}]})

    assert result["status"] == "error"
    assert result["task_id"] == "xtb_gap_window_001"
    assert result["failure_type"] == "parse_error"
    assert result["message"] == "candidate must include an XYZ string"


def test_suite_evaluate_one_routes_by_task_id() -> None:
    suite = vgb.load_suite(["rdkit", "xtb"])

    result = suite.evaluate_one({"task_id": "rdkit_qed_max_001", "candidates": [{"smiles": "CCO"}]})

    assert result["task_id"] == "rdkit_qed_max_001"
    assert result["status"] == "error"
    assert result["failure_type"] == "domain_error"
    assert result["scores"]["score"] == 0.0


def test_evaluation_report_wrapper_serializes_rows() -> None:
    report = vgb.EvaluationReport(summary={"num_answers": 1}, rows=[{"task_id": "task_1", "score": 0.5}])

    assert report.to_dict() == {"summary": {"num_answers": 1}, "rows": [{"task_id": "task_1", "score": 0.5}]}
    assert '"num_answers": 1' in report.to_json()
    assert report.to_jsonl_rows() == '{"score": 0.5, "task_id": "task_1"}\n'
```

- [ ] **Step 2: Run evaluator tests and verify they fail for missing methods**

Run:

```bash
uv run pytest tests/test_public_api.py -q
```

Expected: fail because `Track` has no `evaluate_answers` or `EvaluationReport` is not exported.

- [ ] **Step 3: Implement Evaluator and EvaluationReport**

Create `verifier_grounded_benchmark/evaluator.py`:

```python
"""Evaluator facade over the existing task/verifier pipeline."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from benchmark.evaluate import evaluate_many, evaluate_one


@dataclass(frozen=True)
class EvaluationConfig:
    fail_fast: bool = False


@dataclass(frozen=True)
class EvaluationReport:
    summary: dict[str, Any]
    rows: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {"summary": deepcopy(self.summary), "rows": deepcopy(self.rows)}

    def to_json(self, *, indent: int = 2, sort_keys: bool = True) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=sort_keys)

    def to_jsonl_rows(self, *, sort_keys: bool = True) -> str:
        return "".join(json.dumps(row, sort_keys=sort_keys) + "\n" for row in self.rows)


class Evaluator:
    def __init__(
        self,
        tasks: dict[str, dict[str, Any]],
        verifier_specs: dict[str, dict[str, Any]],
        *,
        config: EvaluationConfig | None = None,
    ) -> None:
        self.tasks = deepcopy(tasks)
        self.verifier_specs = deepcopy(verifier_specs)
        self.config = config or EvaluationConfig()

    def evaluate_one(self, answer: dict[str, Any]) -> dict[str, Any]:
        return evaluate_one(answer, self.tasks, self.verifier_specs)

    def evaluate_many(self, answers: list[dict[str, Any]], *, as_report: bool = False) -> dict[str, Any] | EvaluationReport:
        if not self.config.fail_fast:
            report = evaluate_many(answers, self.tasks, self.verifier_specs)
        else:
            rows = []
            for answer in answers:
                result = self.evaluate_one(answer)
                if result.get("status") != "ok":
                    raise RuntimeError(result.get("message") or result.get("failure_type") or "evaluation failed")
                from benchmark.evaluate import summarize_row, summarize_rows

                rows.append(summarize_row(result))
            report = {"summary": summarize_rows(rows), "rows": rows}
        if as_report:
            return EvaluationReport(summary=report["summary"], rows=report["rows"])
        return report
```

- [ ] **Step 4: Add evaluator methods to Track and Suite**

Update `verifier_grounded_benchmark/track.py`:

```python
"""Loaded track and suite objects for benchmark users."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable

from verifier_grounded_benchmark.evaluator import EvaluationConfig, Evaluator
from verifier_grounded_benchmark.io import load_answers_jsonl_file, load_tasks_file, load_verifier_specs_file
from verifier_grounded_benchmark.registry import TrackDefinition
from verifier_grounded_benchmark.resources import materialize_verifier_specs


class Track:
    def __init__(self, definition: TrackDefinition) -> None:
        self.definition = definition
        self.tasks_by_id = load_tasks_file(definition.resolve_path(definition.task_pack_path))
        specs = load_verifier_specs_file(definition.resolve_path(definition.verifier_specs_path))
        self.verifier_specs_by_id = materialize_verifier_specs(specs, script_root=definition.root)

    @property
    def name(self) -> str:
        return self.definition.name

    def tasks(self) -> list[dict[str, Any]]:
        return [deepcopy(task) for task in self.tasks_by_id.values()]

    def task(self, task_id: str) -> dict[str, Any]:
        try:
            return deepcopy(self.tasks_by_id[task_id])
        except KeyError as exc:
            raise KeyError(f"unknown task_id for track {self.name!r}: {task_id}") from exc

    def prompts(self) -> list[dict[str, str]]:
        prompts: list[dict[str, str]] = []
        for task in self.tasks_by_id.values():
            prompt = task.get("prompt")
            if isinstance(prompt, str):
                prompts.append({"track": self.name, "task_id": str(task["task_id"]), "prompt": prompt})
        return prompts

    def sample_answers(self) -> list[dict[str, Any]]:
        if self.definition.sample_answers_path is None:
            return []
        return load_answers_jsonl_file(self.definition.resolve_path(self.definition.sample_answers_path))

    def evaluator(self, *, config: EvaluationConfig | None = None) -> Evaluator:
        return Evaluator(self.tasks_by_id, self.verifier_specs_by_id, config=config)

    def evaluate_one(self, answer: dict[str, Any]) -> dict[str, Any]:
        return self.evaluator().evaluate_one(answer)

    def evaluate_answers(self, answers: list[dict[str, Any]], *, as_report: bool = False) -> dict[str, Any] | EvaluationReport:
        return self.evaluator().evaluate_many(answers, as_report=as_report)


class Suite:
    def __init__(self, tracks: Iterable[Track]) -> None:
        self._tracks = list(tracks)
        self.tasks_by_id: dict[str, dict[str, Any]] = {}
        self.verifier_specs_by_id: dict[str, dict[str, Any]] = {}
        for track in self._tracks:
            for task_id, task in track.tasks_by_id.items():
                if task_id in self.tasks_by_id:
                    raise ValueError(f"duplicate task_id across suite tracks: {task_id}")
                self.tasks_by_id[task_id] = deepcopy(task)
            for verifier_id, spec in track.verifier_specs_by_id.items():
                if verifier_id in self.verifier_specs_by_id and self.verifier_specs_by_id[verifier_id] != spec:
                    raise ValueError(f"conflicting verifier spec across suite tracks: {verifier_id}")
                self.verifier_specs_by_id[verifier_id] = deepcopy(spec)

    def tracks(self) -> list[Track]:
        return list(self._tracks)

    def tasks(self) -> list[dict[str, Any]]:
        return [deepcopy(task) for task in self.tasks_by_id.values()]

    def task(self, task_id: str) -> dict[str, Any]:
        try:
            return deepcopy(self.tasks_by_id[task_id])
        except KeyError as exc:
            raise KeyError(f"unknown task_id for suite: {task_id}") from exc

    def prompts(self) -> list[dict[str, str]]:
        prompts: list[dict[str, str]] = []
        for track in self._tracks:
            prompts.extend(track.prompts())
        return prompts

    def evaluator(self, *, config: EvaluationConfig | None = None) -> Evaluator:
        return Evaluator(self.tasks_by_id, self.verifier_specs_by_id, config=config)

    def evaluate_one(self, answer: dict[str, Any]) -> dict[str, Any]:
        return self.evaluator().evaluate_one(answer)

    def evaluate_answers(self, answers: list[dict[str, Any]], *, as_report: bool = False) -> dict[str, Any] | EvaluationReport:
        return self.evaluator().evaluate_many(answers, as_report=as_report)
```

- [ ] **Step 5: Export evaluator types**

Update `verifier_grounded_benchmark/__init__.py` to include:

```python
from verifier_grounded_benchmark.evaluator import EvaluationConfig, EvaluationReport, Evaluator
```

and add `"EvaluationConfig"`, `"EvaluationReport"`, and `"Evaluator"` to `__all__`.

- [ ] **Step 6: Run public API evaluator tests**

Run:

```bash
uv run pytest tests/test_public_api.py tests/test_registry.py -q
```

Expected: all tests pass.

- [ ] **Step 7: Commit evaluator API**

Run:

```bash
git add verifier_grounded_benchmark/__init__.py verifier_grounded_benchmark/evaluator.py verifier_grounded_benchmark/track.py tests/test_public_api.py
git commit -m "feat: add public benchmark evaluator API"
```

---

### Task 4: Alias Package And Packaging Metadata

**Files:**
- Create: `vgb/__init__.py`
- Modify: `pyproject.toml`
- Test: `tests/test_public_api.py`

- [ ] **Step 1: Add failing alias import test**

Append this test to `tests/test_public_api.py`:

```python
def test_vgb_alias_exposes_same_public_api() -> None:
    import vgb as short_vgb

    assert [definition.name for definition in short_vgb.list_tracks()] == ["rdkit", "xtb"]
    assert short_vgb.load_track("rdkit").name == "rdkit"
```

- [ ] **Step 2: Run alias test and verify it fails**

Run:

```bash
uv run pytest tests/test_public_api.py::test_vgb_alias_exposes_same_public_api -q
```

Expected: fail with `ModuleNotFoundError: No module named 'vgb'`.

- [ ] **Step 3: Add thin alias package**

Create `vgb/__init__.py`:

```python
"""Short import alias for verifier_grounded_benchmark."""

from verifier_grounded_benchmark import *  # noqa: F403
```

- [ ] **Step 4: Update package metadata**

Modify `pyproject.toml` from:

```toml
[tool.uv]
package = false
```

to:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.uv]
package = true

[tool.hatch.build.targets.wheel]
packages = ["benchmark", "verifiers", "verifier_grounded_benchmark", "vgb"]

[tool.hatch.build.targets.wheel.force-include]
"tasks" = "tasks"
```

Keep the existing `[project]`, `[dependency-groups]`, and `[tool.pytest.ini_options]` sections.

- [ ] **Step 5: Run package import and public API tests**

Run:

```bash
uv run python -c "import verifier_grounded_benchmark as vgb; import vgb as short; print([d.name for d in vgb.list_tracks()]); print(short.load_track('rdkit').name)"
uv build --wheel
uv run pytest tests/test_public_api.py tests/test_registry.py -q
```

Expected first command prints:

```text
['rdkit', 'xtb']
rdkit
```

Expected pytest result: all tests pass.

Expected build result: a wheel is created under `dist/`.

- [ ] **Step 6: Commit alias and package metadata**

Run:

```bash
rm -rf dist
git add pyproject.toml vgb/__init__.py tests/test_public_api.py
git commit -m "feat: add vgb alias package"
```

---

### Task 5: Track-Aware CLI Wrapper

**Files:**
- Modify: `scripts/score_answers.py`
- Modify: `tests/test_evaluate_routing.py`

- [ ] **Step 1: Add failing CLI track test**

Append this test to `tests/test_evaluate_routing.py`:

```python
def test_score_answers_cli_accepts_track_name() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/score_answers.py",
            "--track",
            "rdkit",
            "--answers",
            str(ANSWERS_PATH),
        ],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )

    report = json.loads(completed.stdout)
    assert report["summary"]["num_answers"] == 10
    assert report["summary"]["num_ok"] == 10
    assert report["summary"]["num_error"] == 0
    assert len(report["rows"]) == 10
```

- [ ] **Step 2: Run CLI track test and verify it fails**

Run:

```bash
uv run pytest tests/test_evaluate_routing.py::test_score_answers_cli_accepts_track_name -q
```

Expected: fail because `scripts/score_answers.py` does not recognize `--track`.

- [ ] **Step 3: Update score_answers CLI**

Replace `scripts/score_answers.py` with:

```python
#!/usr/bin/env python
"""Score answer JSONL files through configured verifier scripts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import verifier_grounded_benchmark as vgb
from benchmark.evaluate import evaluate_many, load_answers_jsonl, load_tasks, load_verifier_specs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--track", help="Registered track name, such as rdkit or xtb.")
    parser.add_argument("--tasks", default=None, type=Path)
    parser.add_argument("--specs", default=None, type=Path)
    parser.add_argument("--answers", required=True, type=Path)
    args = parser.parse_args()
    if args.track and (args.tasks is not None or args.specs is not None):
        parser.error("--track cannot be combined with --tasks or --specs")
    return args


def main() -> None:
    args = parse_args()
    answers = load_answers_jsonl(args.answers)
    if args.track:
        report = vgb.load_track(args.track).evaluate_answers(answers)
    else:
        tasks_path = args.tasks or Path("tasks/rdkit_baseline/tasks.yaml")
        specs_path = args.specs or Path("tasks/rdkit_baseline/verifier_specs.yaml")
        report = evaluate_many(
            answers,
            load_tasks(tasks_path),
            load_verifier_specs(specs_path),
        )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run CLI tests**

Run:

```bash
uv run pytest tests/test_evaluate_routing.py::test_score_answers_cli_outputs_summary_json tests/test_evaluate_routing.py::test_score_answers_cli_accepts_track_name -q
```

Expected: both tests pass.

- [ ] **Step 5: Commit CLI track support**

Run:

```bash
git add scripts/score_answers.py tests/test_evaluate_routing.py
git commit -m "feat: add track-aware scoring CLI"
```

---

### Task 6: Full Regression And Packaging Smoke Test

**Files:**
- Modify only if earlier tasks revealed a concrete issue.

- [ ] **Step 1: Run focused package tests**

Run:

```bash
uv run pytest tests/test_public_api.py tests/test_registry.py tests/test_evaluate_routing.py -q
```

Expected: all selected tests pass.

- [ ] **Step 2: Run full test suite**

Run:

```bash
uv run pytest -q
```

Expected: all tests pass.

- [ ] **Step 3: Run import and CLI smoke commands**

Run:

```bash
uv run python -c "import verifier_grounded_benchmark as vgb; suite = vgb.load_suite(); print(len(suite.tasks()))"
uv run python scripts/score_answers.py --track rdkit --answers tasks/rdkit_baseline/sample_answers.jsonl
```

Expected first command prints a positive integer. Expected second command prints a JSON report with:

```json
"num_answers": 10
```

- [ ] **Step 4: Check git status**

Run:

```bash
git status --short
```

Expected: no uncommitted changes if every task was committed independently. If there are changes from test cache or generated build files, remove ignored/generated files only when they are not user work.

---

## Self-Review Checklist

- Spec coverage: Tasks 1-5 cover registry, Track/Suite, Evaluator/Report, `vgb` alias, packaging metadata, and CLI `--track`.
- Formal track boundary: built-in registry exposes only `rdkit` and `xtb`.
- No model-provider coupling: no OpenAI, Anthropic, local model, retry, or generation API is added.
- Existing pipeline preserved: evaluator delegates to `benchmark.evaluate` and existing verifier scripts.
- Script path safety: `materialize_verifier_specs` resolves relative `verification_script` paths before evaluation.
- Test discipline: every task starts with failing tests and commits only after tests pass.
