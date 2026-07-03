# Src Layout Reorganization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move importable Python packages under `src/` while preserving current public import names, CLI behavior, benchmark resources, tests, scripts, and package installation behavior.

**Architecture:** Keep the package names unchanged: `verifier_grounded_benchmark`, `vgb`, `benchmark`, and `verifiers`. Only their physical location changes from repository root to `src/`; repository data directories such as `tasks/`, `scripts/`, `tests/`, `docs/`, `data/`, `artifacts/`, and `dist/` remain at the root. Update resource resolution so package APIs can still find root-level benchmark task files both from a checkout and from an installed wheel.

**Tech Stack:** Python 3.12, Hatchling, uv, pytest, existing package modules and scripts.

---

## File Structure

Files and directories to move:
- Move `benchmark/` to `src/benchmark/`.
- Move `verifier_grounded_benchmark/` to `src/verifier_grounded_benchmark/`.
- Move `verifiers/` to `src/verifiers/`.
- Move `vgb/` to `src/vgb/`.

Files to modify:
- `pyproject.toml`: point Hatchling wheel packages at `src/...`, include the package README at its new path, and set pytest `pythonpath` to `src`.
- `src/verifier_grounded_benchmark/resources.py`: make repository-root resolution work after moving the package under `src/`.
- `src/verifier_grounded_benchmark/registry.py`: keep built-in task definitions resolving to root-level `tasks/`.
- `src/benchmark/verifier_scripts.py`: keep subprocess `PYTHONPATH` pointing at `src` when running verifier scripts from the checkout.
- Tests only if they assert exact old filesystem locations.

Files and directories to keep in place:
- `src/verifier_grounded_benchmark/README.md`: remains package user documentation, not a root README.
- `tests/`: remains root-level test suite.
- `tasks/`: remains root-level benchmark task data.
- `scripts/`: remains root-level maintenance and analysis scripts.
- `docs/`: remains the only top-level documentation tree.
- `data/`, `artifacts/`, and `dist/`: remain root-level data, generated artifacts, and distribution output.

Compatibility requirements:
- `import verifier_grounded_benchmark as vgb` continues to work.
- `import vgb` continues to work.
- Existing tests that import `benchmark` and `verifiers` continue to work.
- `vgb-score` console script continues to work from an installed wheel.
- `scripts/score_answers.py` continues to delegate to the package CLI.
- Built-in tracks still resolve `tasks/rdkit_baseline` and `tasks/xtb_xyz`.
- The package README stays under `src/verifier_grounded_benchmark/README.md`.

## Task 1: Move Packages Under `src/`

**Files:**
- Move: `benchmark/` to `src/benchmark/`
- Move: `verifier_grounded_benchmark/` to `src/verifier_grounded_benchmark/`
- Move: `verifiers/` to `src/verifiers/`
- Move: `vgb/` to `src/vgb/`

- [ ] **Step 1: Confirm a clean starting state**

Run:
```bash
git status --short
```

Expected: no output except the committed plan is already in history.

- [ ] **Step 2: Create `src/`**

Run:
```bash
mkdir -p src
```

Expected: `src/` exists.

- [ ] **Step 3: Move each importable package**

Run:
```bash
git mv benchmark src/benchmark
git mv verifier_grounded_benchmark src/verifier_grounded_benchmark
git mv verifiers src/verifiers
git mv vgb src/vgb
```

Expected: `git status --short` shows four directory renames.

- [ ] **Step 4: Verify the package README stayed with the package**

Run:
```bash
test -f src/verifier_grounded_benchmark/README.md
test ! -f README.md
```

Expected: both commands exit with status 0.

- [ ] **Step 5: Run tests before committing**

Run:
```bash
uv run pytest
```

Expected: failures are likely at this intermediate point because `pyproject.toml` still points pytest and Hatchling at root-level packages. Do not commit if failures are caused by anything other than the expected missing import path. Continue directly to Task 2.

## Task 2: Update Packaging and Test Import Paths

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Update Hatchling package paths**

Change:
```toml
[tool.hatch.build.targets.wheel]
packages = ["benchmark", "verifiers", "verifier_grounded_benchmark", "vgb"]
```

To:
```toml
[tool.hatch.build.targets.wheel]
packages = [
    "src/benchmark",
    "src/verifiers",
    "src/verifier_grounded_benchmark",
    "src/vgb",
]
```

- [ ] **Step 2: Update pytest import path**

Change:
```toml
[tool.pytest.ini_options]
pythonpath = ["."]
```

To:
```toml
[tool.pytest.ini_options]
pythonpath = ["src"]
```

- [ ] **Step 3: Run focused import smoke tests**

Run:
```bash
uv run python - <<'PY'
import benchmark
import verifier_grounded_benchmark
import verifiers
import vgb

print(benchmark.__file__)
print(verifier_grounded_benchmark.__file__)
print(verifiers.__file__)
print(vgb.__file__)
PY
```

Expected: all printed paths are under `/Users/xutao/verifier-grounded-benchmark/src/`.

- [ ] **Step 4: Run tests before committing**

Run:
```bash
uv run pytest
```

Expected: tests may now reveal resource path assumptions, subprocess `PYTHONPATH` assumptions, or packaging assumptions. Fix those in Tasks 3 and 4 before committing.

## Task 3: Preserve Root-Level Resource Resolution

**Files:**
- Modify: `src/verifier_grounded_benchmark/resources.py`
- Modify if needed: `src/verifier_grounded_benchmark/registry.py`

- [ ] **Step 1: Inspect current failing resource tests**

Run:
```bash
uv run pytest tests/test_registry.py tests/test_public_api.py tests/test_packaging.py -q
```

Expected before the fix: failures, if any, point to task files resolving under `src/tasks` instead of root-level `tasks`.

- [ ] **Step 2: Replace repository-root discovery in `resources.py`**

Use this implementation in `src/verifier_grounded_benchmark/resources.py`:
```python
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any


def package_root() -> Path:
    return Path(__file__).resolve().parents[1]


def repository_root() -> Path:
    package_parent = package_root().parent
    if package_parent.name == "src":
        return package_parent.parent
    return package_root()


def resolve_path(path: str | Path, base: str | Path | None = None) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate.resolve()

    root = Path(base) if base is not None else repository_root()
    return (root / candidate).resolve()


def materialize_verifier_specs(
    specs: dict[str, dict[str, Any]],
    script_root: str | Path,
) -> dict[str, dict[str, Any]]:
    materialized = deepcopy(specs)
    for spec in materialized.values():
        verification_script = spec.get("verification_script")
        if isinstance(verification_script, str) and verification_script:
            spec["verification_script"] = str(
                resolve_path(verification_script, base=script_root)
            )
    return materialized
```

- [ ] **Step 3: Update `registry.py` imports and built-in resource root**

If built-in track paths still resolve under `src/`, change `src/verifier_grounded_benchmark/registry.py` from:
```python
from verifier_grounded_benchmark.resources import package_root, resolve_path
```

To:
```python
from verifier_grounded_benchmark.resources import repository_root, resolve_path
```

Then change both built-in definitions from:
```python
resource_root=package_root(),
```

To:
```python
resource_root=repository_root(),
```

- [ ] **Step 4: Run focused resource tests**

Run:
```bash
uv run pytest tests/test_registry.py tests/test_public_api.py tests/test_packaging.py -q
```

Expected: all selected tests pass.

- [ ] **Step 5: Run full tests before committing**

Run:
```bash
uv run pytest
```

Expected: all tests pass or remaining failures are limited to subprocess verifier path assumptions handled in Task 4. Do not commit until the full suite passes or the only failures are explicitly diagnosed and fixed.

## Task 4: Preserve Verifier Script Subprocess Behavior

**Files:**
- Modify: `src/benchmark/verifier_scripts.py`
- Test: `tests/test_verifier_script_runner.py`
- Test: `tests/test_rdkit_task_scripts.py`
- Test: `tests/test_xtb_task_scripts.py`
- Test: `tests/test_admet_ai_task_scripts.py`
- Test: `tests/test_matgl_task_scripts.py`

- [ ] **Step 1: Inspect subprocess path handling**

Run:
```bash
sed -n '1,120p' src/benchmark/verifier_scripts.py
```

Expected: the file defines a root path from the module location and injects it into `PYTHONPATH`.

- [ ] **Step 2: Make subprocess `PYTHONPATH` point at `src` in a checkout**

If the file still computes `ROOT = Path(__file__).resolve().parents[1]`, change it to:
```python
MODULE_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = MODULE_ROOT.parent if MODULE_ROOT.name == "src" else MODULE_ROOT
PYTHONPATH_ROOT = MODULE_ROOT if MODULE_ROOT.name == "src" else REPOSITORY_ROOT
```

Then change subprocess environment injection to use:
```python
env["PYTHONPATH"] = (
    str(PYTHONPATH_ROOT) if not pythonpath else f"{PYTHONPATH_ROOT}{os.pathsep}{pythonpath}"
)
```

- [ ] **Step 3: Run verifier script tests**

Run:
```bash
uv run pytest \
  tests/test_verifier_script_runner.py \
  tests/test_rdkit_task_scripts.py \
  tests/test_xtb_task_scripts.py \
  tests/test_admet_ai_task_scripts.py \
  tests/test_matgl_task_scripts.py \
  -q
```

Expected: all selected tests pass.

- [ ] **Step 4: Run full tests before committing**

Run:
```bash
uv run pytest
```

Expected: all tests pass. If failures remain, diagnose the concrete failing path or import and fix before committing.

## Task 5: Verify Installed Package Behavior

**Files:**
- Modify if needed: `pyproject.toml`
- Modify if needed: `src/verifier_grounded_benchmark/resources.py`
- Test: `tests/test_installed_wheel.py`

- [ ] **Step 1: Build package artifacts**

Run:
```bash
uv build
```

Expected: `dist/verifier_grounded_benchmark-0.1.0-py3-none-any.whl` and `dist/verifier_grounded_benchmark-0.1.0.tar.gz` are created or refreshed.

- [ ] **Step 2: Inspect wheel contents**

Run:
```bash
python - <<'PY'
from pathlib import Path
from zipfile import ZipFile

wheel = next(Path("dist").glob("verifier_grounded_benchmark-0.1.0-py3-none-any.whl"))
with ZipFile(wheel) as zf:
    names = set(zf.namelist())

required = {
    "benchmark/__init__.py",
    "verifiers/__init__.py",
    "verifier_grounded_benchmark/__init__.py",
    "verifier_grounded_benchmark/README.md",
    "vgb/__init__.py",
    "tasks/rdkit_baseline/tasks.yaml",
    "tasks/xtb_xyz/tasks.yaml",
}

missing = sorted(required - names)
if missing:
    raise SystemExit(f"missing from wheel: {missing}")
print("wheel contents ok")
PY
```

Expected: `wheel contents ok`.

- [ ] **Step 3: Run installed-wheel tests**

Run:
```bash
uv run pytest tests/test_installed_wheel.py -q
```

Expected: selected tests pass.

- [ ] **Step 4: Run CLI smoke test from checkout**

Run:
```bash
uv run vgb-score --help
```

Expected: command exits 0 and prints usage text.

- [ ] **Step 5: Run full tests before committing**

Run:
```bash
uv run pytest
```

Expected: all tests pass.

## Task 6: Final Commit and Cleanliness Check

**Files:**
- Stage all moved and modified files.
- Commit the migration.

- [ ] **Step 1: Review status**

Run:
```bash
git status --short
```

Expected: only planned moves, `pyproject.toml`, code path fixes, and refreshed `dist/` outputs if `uv build` changed them.

- [ ] **Step 2: Review diff summary**

Run:
```bash
git diff --stat
```

Expected: mostly renames into `src/`, plus small edits to `pyproject.toml`, `resources.py`, `registry.py`, and possibly `verifier_scripts.py`.

- [ ] **Step 3: Run final tests before committing**

Run:
```bash
uv run pytest
```

Expected: all tests pass.

- [ ] **Step 4: Create commit**

Run:
```bash
git add pyproject.toml src tests dist
git add -A benchmark verifier_grounded_benchmark verifiers vgb
git commit -m "refactor: move packages under src layout"
```

Expected: commit succeeds.

- [ ] **Step 5: Confirm clean tree**

Run:
```bash
git status --short
```

Expected: no output.

## Self-Review

Spec coverage:
- The approved structure is covered by Tasks 1 and 2.
- The instruction not to move package README to the repository root is covered by Task 1 Step 4 and the file-structure section.
- Compatibility protection is covered by Tasks 2 through 5.
- The repository rule to run tests before every commit is covered by Tasks 1 through 6.

Placeholder scan:
- No `TBD`, `TODO`, or deferred implementation language remains.
- Each command has a concrete expected result.

Type consistency:
- `repository_root()` is introduced in `resources.py` and imported by `registry.py`.
- `PYTHONPATH_ROOT` is introduced in `benchmark/verifier_scripts.py` and used by subprocess environment injection.
