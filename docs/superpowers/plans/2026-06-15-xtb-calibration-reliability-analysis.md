# xTB Calibration Reliability Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reproducible calibration and reliability analysis workflow for the implemented xTB direct-XYZ tasks, covering property distributions, positive/negative controls, failure modes, threshold recommendations, and parser/runtime reliability.

**Architecture:** Add repository-local calibration fixtures, batch scoring scripts, summary analyzers, regression tests, and a dated research report. Keep task thresholds unchanged during this plan; produce data-backed recommendations first, then apply threshold changes in a separate follow-up plan if approved.

**Tech Stack:** Python 3.12, pytest, PyYAML, JSON/JSONL/CSV artifacts, existing `benchmark.evaluate` routing, local xTB CLI when available, fake-runner tests for CI-safe behavior.

---

## Scope

This plan calibrates all xTB direct-XYZ tasks currently registered in `tasks/xtb_xyz/tasks.yaml`:

- First batch: `xtb_gap_window_001` through `xtb_gap_dipole_window_007`.
- Advanced batch: `xtb_lumo_min_008` through `xtb_hessian_thermo_stability_013`.

It does not implement new chemical properties, charged/open-shell schemas, multi-XYZ schemas, or threshold updates. It produces the evidence needed to decide those changes later.

## File Structure

- Create `tasks/xtb_xyz/calibration_answers.jsonl`: curated positive, near-miss, and negative XYZ candidates for all 13 xTB tasks.
- Create `tasks/xtb_xyz/calibration_manifest.yaml`: candidate labels, expected roles, molecule families, source notes, and task coverage metadata.
- Modify `tasks/xtb_xyz/sample_answers.jsonl`: only if Task 5 identifies high-confidence positive controls for tasks 8-13 that score at least `0.6` with real xTB.
- Create `scripts/run_xtb_calibration.py`: real-xTB batch calibration runner that scores a JSONL answer set and writes machine-readable reports.
- Create `scripts/analyze_xtb_calibration.py`: offline analyzer that reads calibration results and produces per-task summary statistics, threshold recommendations, and failure tables.
- Create `docs/research/2026-06-15-xtb-calibration-reliability-report.md`: human-readable calibration report with tables and decisions.
- Create `tests/test_xtb_calibration_inputs.py`: CI-safe tests for calibration JSONL/manifest schema, task coverage, answer extraction, and label consistency.
- Create `tests/test_xtb_calibration_scripts.py`: CI-safe tests for script argument parsing, missing-xTB behavior, analyzer summaries, and report-shape guarantees.

## Calibration Dataset Contract

Use JSONL answer records compatible with `benchmark.evaluate.load_answers_jsonl`:

```json
{"task_id":"xtb_lumo_min_008","candidate_id":"acceptor_nitro_cyano_arene_001","role":"positive_candidate","response":"FINAL ANSWER:\n```xyz\n3\nwater-format-example\nO 0.000000 0.000000 0.000000\nH 0.758602 0.000000 0.504284\nH -0.758602 0.000000 0.504284\n```"}
```

The evaluator ignores `candidate_id` and `role`; scripts preserve them in output rows for analysis.

Use manifest entries keyed by `candidate_id`:

```yaml
candidates:
  acceptor_nitro_cyano_arene_001:
    role: positive_candidate
    molecule_family: push_pull_arene
    target_tasks: [xtb_lumo_min_008, xtb_electrophilicity_max_011]
    expected_behavior:
      xtb_lumo_min_008: high_score
      xtb_electrophilicity_max_011: medium_or_high_score
    source: "Curated XYZ from local xTB optimization"
```

Candidate roles:

- `positive_candidate`: intended to score at least `0.6` for a target task.
- `near_miss`: chemically plausible but outside one key property range.
- `negative_baseline`: simple/common molecule or known undesirable shortcut.
- `stress_case`: valid-domain molecule expected to expose runtime/parser/optimization limits.

## Task 1: Calibration Input Schema Tests

**Files:**
- Create: `tests/test_xtb_calibration_inputs.py`
- Create: `tasks/xtb_xyz/calibration_answers.jsonl`
- Create: `tasks/xtb_xyz/calibration_manifest.yaml`

- [ ] **Step 1: Write failing tests for calibration input contracts**

Create `tests/test_xtb_calibration_inputs.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

import yaml

from benchmark.answer_extraction import normalize_answer_record
from benchmark.evaluate import load_tasks


ROOT = Path(__file__).resolve().parents[1]
TASK_DIR = ROOT / "tasks" / "xtb_xyz"
ANSWERS_PATH = TASK_DIR / "calibration_answers.jsonl"
MANIFEST_PATH = TASK_DIR / "calibration_manifest.yaml"


def _load_answers() -> list[dict]:
    with ANSWERS_PATH.open() as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _load_manifest() -> dict:
    with MANIFEST_PATH.open() as handle:
        return yaml.safe_load(handle)


def test_xtb_calibration_files_exist_and_are_nonempty() -> None:
    assert ANSWERS_PATH.exists()
    assert MANIFEST_PATH.exists()
    assert len(_load_answers()) >= 26
    assert len(_load_manifest()["candidates"]) >= 26


def test_xtb_calibration_answers_have_unique_candidate_ids() -> None:
    answers = _load_answers()
    candidate_ids = [answer["candidate_id"] for answer in answers]
    assert len(candidate_ids) == len(set(candidate_ids))


def test_xtb_calibration_answers_reference_known_tasks_and_extract_xyz() -> None:
    tasks = load_tasks(TASK_DIR / "tasks.yaml")
    answers = _load_answers()
    for answer in answers:
        assert answer["task_id"] in tasks
        assert answer["role"] in {"positive_candidate", "near_miss", "negative_baseline", "stress_case"}
        normalized = normalize_answer_record(answer, tasks[answer["task_id"]])
        assert normalized.ok, answer["candidate_id"]
        candidate = normalized.answer["candidates"][0]
        assert "xyz" in candidate
        xyz_lines = candidate["xyz"].splitlines()
        assert int(xyz_lines[0]) == len(xyz_lines) - 2


def test_xtb_calibration_manifest_matches_answers() -> None:
    answers = _load_answers()
    manifest = _load_manifest()
    manifest_ids = set(manifest["candidates"])
    answer_ids = {answer["candidate_id"] for answer in answers}
    assert answer_ids == manifest_ids
    for answer in answers:
        metadata = manifest["candidates"][answer["candidate_id"]]
        assert metadata["role"] == answer["role"]
        assert answer["task_id"] in metadata["target_tasks"]
        assert answer["task_id"] in metadata["expected_behavior"]


def test_xtb_calibration_covers_every_task_with_positive_and_negative_cases() -> None:
    tasks = load_tasks(TASK_DIR / "tasks.yaml")
    answers = _load_answers()
    for task_id in tasks:
        roles = {answer["role"] for answer in answers if answer["task_id"] == task_id}
        assert "positive_candidate" in roles, task_id
        assert "negative_baseline" in roles, task_id
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
uv run pytest tests/test_xtb_calibration_inputs.py -q
```

Expected: FAIL because `tasks/xtb_xyz/calibration_answers.jsonl` and `tasks/xtb_xyz/calibration_manifest.yaml` do not exist.

- [ ] **Step 3: Add initial calibration files**

Create `tasks/xtb_xyz/calibration_answers.jsonl` with at least two records per task:

- one `positive_candidate`;
- one `negative_baseline`.

For tasks 1-7, seed positives from the existing `tasks/xtb_xyz/sample_answers.jsonl`. For tasks 8-13, use chemically plausible curated candidates from the implementation work or local xTB optimization notes. For every task, include at least one simple/common molecule baseline that either fails structural domain or scores low.

Create `tasks/xtb_xyz/calibration_manifest.yaml` with matching `candidate_id` keys and metadata. Use this top-level structure:

```yaml
version: 1
description: Calibration candidates for xTB direct-XYZ task reliability analysis.
candidates: {}
```

Every manifest candidate must include:

- `role`
- `molecule_family`
- `target_tasks`
- `expected_behavior`
- `source`

- [ ] **Step 4: Run the calibration input tests**

Run:

```bash
uv run pytest tests/test_xtb_calibration_inputs.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add tests/test_xtb_calibration_inputs.py tasks/xtb_xyz/calibration_answers.jsonl tasks/xtb_xyz/calibration_manifest.yaml
git commit -m "test: add xtb calibration input fixtures"
```

## Task 2: Real-xTB Calibration Runner

**Files:**
- Create: `scripts/run_xtb_calibration.py`
- Create: `tests/test_xtb_calibration_scripts.py`

- [ ] **Step 1: Write failing tests for runner behavior**

Create `tests/test_xtb_calibration_scripts.py` with these tests:

```python
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_xtb_calibration.py"


def test_run_xtb_calibration_reports_missing_executable(tmp_path) -> None:
    env = {**os.environ, "PATH": str(tmp_path)}
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--answers",
            "tasks/xtb_xyz/calibration_answers.jsonl",
            "--output",
            str(tmp_path / "calibration-results.json"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    assert completed.returncode == 1
    payload = json.loads(completed.stdout)
    assert payload["status"] == "error"
    assert payload["failure_type"] == "verifier_environment_error"
    assert payload["xtb_executable"] is None


def test_run_xtb_calibration_help() -> None:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "--answers" in completed.stdout
    assert "--output" in completed.stdout
    assert "--max-candidates" in completed.stdout
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
uv run pytest tests/test_xtb_calibration_scripts.py -q
```

Expected: FAIL because `scripts/run_xtb_calibration.py` does not exist.

- [ ] **Step 3: Implement the runner**

Create `scripts/run_xtb_calibration.py`:

```python
#!/usr/bin/env python
"""Run real-xTB calibration for xTB direct-XYZ tasks."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmark.evaluate import evaluate_one, load_answers_jsonl, load_tasks, load_verifier_specs


TASK_DIR = ROOT / "tasks" / "xtb_xyz"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--answers", type=Path, default=TASK_DIR / "calibration_answers.jsonl")
    parser.add_argument("--tasks", type=Path, default=TASK_DIR / "tasks.yaml")
    parser.add_argument("--specs", type=Path, default=TASK_DIR / "verifier_specs.yaml")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-candidates", type=int, default=None)
    return parser.parse_args()


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    scores = [float(row.get("score") or 0.0) for row in rows]
    ok_count = sum(row.get("status") == "ok" for row in rows)
    return {
        "num_answers": len(rows),
        "num_ok": ok_count,
        "num_error": len(rows) - ok_count,
        "min_score": min(scores) if scores else None,
        "max_score": max(scores) if scores else None,
        "mean_score": sum(scores) / len(scores) if scores else None,
    }


def main() -> int:
    args = parse_args()
    executable = shutil.which("xtb")
    if executable is None:
        print(
            json.dumps(
                {
                    "status": "error",
                    "failure_type": "verifier_environment_error",
                    "message": "xTB executable not found on PATH",
                    "xtb_executable": None,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 1

    tasks = load_tasks(args.tasks)
    specs = load_verifier_specs(args.specs)
    answers = load_answers_jsonl(args.answers)
    if args.max_candidates is not None:
        answers = answers[: args.max_candidates]

    rows: list[dict[str, Any]] = []
    for answer in answers:
        result = evaluate_one(answer, tasks, specs)
        scores = result.get("scores") or {}
        rows.append(
            {
                "candidate_id": answer.get("candidate_id"),
                "role": answer.get("role"),
                "task_id": result.get("task_id"),
                "status": result.get("status"),
                "failure_type": result.get("failure_type"),
                "score": scores.get("score", 0.0),
                "property_score": scores.get("property_score", 0.0),
                "geometry_quality_score": scores.get("geometry_quality_score"),
                "stability_gate_score": scores.get("stability_gate_score"),
                "properties": result.get("properties", {}),
                "constraint_scores": scores.get("constraint_scores", []),
                "message": result.get("message"),
            }
        )

    payload = {
        "status": "ok",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "xtb_executable": executable,
        "answers_path": str(args.answers),
        "tasks_path": str(args.tasks),
        "specs_path": str(args.specs),
        "summary": summarize(rows),
        "rows": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True))
    print(json.dumps({"status": "ok", "output": str(args.output), "summary": payload["summary"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run runner tests**

Run:

```bash
uv run pytest tests/test_xtb_calibration_scripts.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add scripts/run_xtb_calibration.py tests/test_xtb_calibration_scripts.py
git commit -m "feat: add xtb calibration runner"
```

## Task 3: Calibration Analyzer

**Files:**
- Create: `scripts/analyze_xtb_calibration.py`
- Modify: `tests/test_xtb_calibration_scripts.py`

- [ ] **Step 1: Add failing analyzer tests**

Append these tests to `tests/test_xtb_calibration_scripts.py`:

```python
def test_analyze_xtb_calibration_writes_summary_files(tmp_path) -> None:
    input_path = tmp_path / "results.json"
    output_dir = tmp_path / "analysis"
    input_path.write_text(
        json.dumps(
            {
                "status": "ok",
                "rows": [
                    {
                        "candidate_id": "positive_1",
                        "role": "positive_candidate",
                        "task_id": "xtb_lumo_min_008",
                        "status": "ok",
                        "failure_type": None,
                        "score": 0.8,
                        "properties": {"lumo_energy": -3.0, "relaxation_energy": 0.05},
                    },
                    {
                        "candidate_id": "negative_1",
                        "role": "negative_baseline",
                        "task_id": "xtb_lumo_min_008",
                        "status": "ok",
                        "failure_type": None,
                        "score": 0.1,
                        "properties": {"lumo_energy": 0.5, "relaxation_energy": 0.02},
                    },
                    {
                        "candidate_id": "bad_1",
                        "role": "stress_case",
                        "task_id": "xtb_hessian_thermo_stability_013",
                        "status": "error",
                        "failure_type": "verifier_timeout",
                        "score": 0.0,
                        "properties": {},
                    },
                ],
            }
        )
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_xtb_calibration.py",
            "--input",
            str(input_path),
            "--output-dir",
            str(output_dir),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    summary = json.loads((output_dir / "summary.json").read_text())
    assert summary["tasks"]["xtb_lumo_min_008"]["num_rows"] == 2
    assert summary["tasks"]["xtb_lumo_min_008"]["num_positive_candidates"] == 1
    assert summary["tasks"]["xtb_lumo_min_008"]["num_negative_baselines"] == 1
    assert summary["tasks"]["xtb_hessian_thermo_stability_013"]["failure_types"]["verifier_timeout"] == 1
    assert (output_dir / "summary.md").exists()
```

- [ ] **Step 2: Run the analyzer test to verify it fails**

Run:

```bash
uv run pytest tests/test_xtb_calibration_scripts.py::test_analyze_xtb_calibration_writes_summary_files -q
```

Expected: FAIL because `scripts/analyze_xtb_calibration.py` does not exist.

- [ ] **Step 3: Implement the analyzer**

Create `scripts/analyze_xtb_calibration.py`:

```python
#!/usr/bin/env python
"""Analyze xTB calibration result JSON files."""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser.parse_args()


def score_stats(rows: list[dict[str, Any]]) -> dict[str, float | int | None]:
    scores = [float(row.get("score") or 0.0) for row in rows]
    if not scores:
        return {"count": 0, "min": None, "median": None, "mean": None, "max": None}
    return {
        "count": len(scores),
        "min": min(scores),
        "median": statistics.median(scores),
        "mean": statistics.fmean(scores),
        "max": max(scores),
    }


def analyze(payload: dict[str, Any]) -> dict[str, Any]:
    by_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in payload.get("rows", []):
        by_task[str(row.get("task_id"))].append(row)

    tasks: dict[str, Any] = {}
    for task_id, rows in sorted(by_task.items()):
        roles = Counter(str(row.get("role")) for row in rows)
        failures = Counter(str(row.get("failure_type")) for row in rows if row.get("status") != "ok")
        ok_rows = [row for row in rows if row.get("status") == "ok"]
        positive_rows = [row for row in rows if row.get("role") == "positive_candidate"]
        negative_rows = [row for row in rows if row.get("role") == "negative_baseline"]
        tasks[task_id] = {
            "num_rows": len(rows),
            "num_ok": len(ok_rows),
            "num_error": len(rows) - len(ok_rows),
            "num_positive_candidates": roles.get("positive_candidate", 0),
            "num_negative_baselines": roles.get("negative_baseline", 0),
            "score_stats": score_stats(rows),
            "positive_score_stats": score_stats(positive_rows),
            "negative_score_stats": score_stats(negative_rows),
            "failure_types": dict(failures),
            "needs_attention": attention_flags(rows),
        }
    return {"tasks": tasks}


def attention_flags(rows: list[dict[str, Any]]) -> list[str]:
    flags: list[str] = []
    positive_scores = [float(row.get("score") or 0.0) for row in rows if row.get("role") == "positive_candidate"]
    negative_scores = [float(row.get("score") or 0.0) for row in rows if row.get("role") == "negative_baseline"]
    error_rows = [row for row in rows if row.get("status") != "ok"]
    if positive_scores and max(positive_scores) < 0.6:
        flags.append("no_positive_candidate_above_0.6")
    if negative_scores and max(negative_scores) > 0.35:
        flags.append("negative_baseline_above_0.35")
    if error_rows:
        flags.append("has_verifier_errors")
    return flags


def write_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# xTB Calibration Summary",
        "",
        "| Task | Rows | OK | Errors | Positive max | Negative max | Attention |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for task_id, task in summary["tasks"].items():
        positive_max = task["positive_score_stats"]["max"]
        negative_max = task["negative_score_stats"]["max"]
        lines.append(
            "| {task_id} | {rows} | {ok} | {errors} | {positive} | {negative} | {attention} |".format(
                task_id=task_id,
                rows=task["num_rows"],
                ok=task["num_ok"],
                errors=task["num_error"],
                positive="" if positive_max is None else f"{positive_max:.3f}",
                negative="" if negative_max is None else f"{negative_max:.3f}",
                attention=", ".join(task["needs_attention"]),
            )
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    payload = json.loads(args.input.read_text())
    summary = analyze(payload)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    (args.output_dir / "summary.md").write_text(write_markdown(summary))
    print(json.dumps({"status": "ok", "output_dir": str(args.output_dir)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run analyzer tests**

Run:

```bash
uv run pytest tests/test_xtb_calibration_scripts.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add scripts/analyze_xtb_calibration.py tests/test_xtb_calibration_scripts.py
git commit -m "feat: analyze xtb calibration results"
```

## Task 4: Positive/Negative Reliability Regression

**Files:**
- Modify: `tests/test_xtb_quality_gate_regression.py`
- Modify: `tests/test_xtb_calibration_inputs.py`

- [ ] **Step 1: Extend CI-safe regression tests**

In `tests/test_xtb_quality_gate_regression.py`, extend `OPTIMIZATION_TASK_IDS` to include all optimization-oriented advanced tasks:

```python
OPTIMIZATION_TASK_IDS = [
    "xtb_gap_max_003",
    "xtb_gap_min_004",
    "xtb_dipole_max_005",
    "xtb_low_gap_high_dipole_opt_006",
    "xtb_lumo_min_008",
    "xtb_polarizability_dipole_opt_009",
    "xtb_solvation_selectivity_alpb_010",
    "xtb_electrophilicity_max_011",
    "xtb_fukui_carbon_site_012",
    "xtb_hessian_thermo_stability_013",
]
```

Also add a manifest-level test in `tests/test_xtb_calibration_inputs.py`:

```python
def test_xtb_advanced_tasks_have_at_least_three_calibration_roles() -> None:
    answers = _load_answers()
    advanced_task_ids = {
        "xtb_lumo_min_008",
        "xtb_polarizability_dipole_opt_009",
        "xtb_solvation_selectivity_alpb_010",
        "xtb_electrophilicity_max_011",
        "xtb_fukui_carbon_site_012",
        "xtb_hessian_thermo_stability_013",
    }
    for task_id in advanced_task_ids:
        roles = {answer["role"] for answer in answers if answer["task_id"] == task_id}
        assert {"positive_candidate", "near_miss", "negative_baseline"}.issubset(roles), task_id
```

- [ ] **Step 2: Run regression tests**

Run:

```bash
uv run pytest tests/test_xtb_quality_gate_regression.py tests/test_xtb_calibration_inputs.py -q
```

Expected: FAIL until `calibration_answers.jsonl` contains near-miss cases for tasks 8-13 and simple baselines are covered.

- [ ] **Step 3: Add near-miss and stress cases**

Add at least one `near_miss` for each advanced task:

- `xtb_lumo_min_008`: moderate LUMO but valid acceptor-like structure.
- `xtb_polarizability_dipole_opt_009`: high polarizability but low dipole, or high dipole but low normalized polarizability.
- `xtb_solvation_selectivity_alpb_010`: polar molecule with weak water/hexane selectivity.
- `xtb_electrophilicity_max_011`: low LUMO but modest global electrophilicity.
- `xtb_fukui_carbon_site_012`: high f+ on hetero atom rather than carbon, or low contrast.
- `xtb_hessian_thermo_stability_013`: valid optimized-looking molecule expected to have low entropy per heavy atom or borderline low-frequency behavior.

Add at least two `stress_case` records across the full pack:

- a large but domain-valid molecule near timeout limits;
- a flexible molecule likely to challenge hessian or relaxation gate.

Update the manifest for every new `candidate_id`.

- [ ] **Step 4: Run regression tests**

Run:

```bash
uv run pytest tests/test_xtb_quality_gate_regression.py tests/test_xtb_calibration_inputs.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add tests/test_xtb_quality_gate_regression.py tests/test_xtb_calibration_inputs.py tasks/xtb_xyz/calibration_answers.jsonl tasks/xtb_xyz/calibration_manifest.yaml
git commit -m "test: expand xtb calibration reliability cases"
```

## Task 5: Live Calibration Run and Report

**Files:**
- Create: `docs/research/2026-06-15-xtb-calibration-reliability-report.md`
- Optional modify: `tasks/xtb_xyz/sample_answers.jsonl`
- Optional modify: `tests/test_xtb_xyz_tasks.py`

- [ ] **Step 1: Check local xTB availability**

Run:

```bash
uv run python scripts/check_xtb_env.py
```

Expected when xTB is installed: JSON with `"status": "ok"`.

Expected when xTB is missing: exit code `1` with `"failure_type": "verifier_environment_error"`. If xTB is missing, stop this task and document the blocker in the report; do not fake live calibration results.

- [ ] **Step 2: Run calibration batch**

Run:

```bash
uv run python scripts/run_xtb_calibration.py \
  --answers tasks/xtb_xyz/calibration_answers.jsonl \
  --output artifacts/xtb_calibration/2026-06-15/results.json
```

Expected: exit code `0`, output JSON points to `artifacts/xtb_calibration/2026-06-15/results.json`.

Do not commit `artifacts/xtb_calibration/2026-06-15/results.json` unless the repository later adopts a rule for storing generated raw calibration artifacts. Use the generated JSON to write the research report.

- [ ] **Step 3: Analyze calibration results**

Run:

```bash
uv run python scripts/analyze_xtb_calibration.py \
  --input artifacts/xtb_calibration/2026-06-15/results.json \
  --output-dir artifacts/xtb_calibration/2026-06-15/analysis
```

Expected: exit code `0`; files `summary.json` and `summary.md` appear under `artifacts/xtb_calibration/2026-06-15/analysis`.

- [ ] **Step 4: Write the research report**

Create `docs/research/2026-06-15-xtb-calibration-reliability-report.md` with this structure:

```markdown
# xTB Calibration Reliability Report

## Environment

- Date:
- xTB executable:
- xTB version:
- Python:
- Command:

## Summary

| Task | Positive max | Negative max | Error rate | Recommendation |
| --- | ---: | ---: | ---: | --- |

## Per-Task Findings

### xtb_gap_window_001

- Positive controls:
- Negative baselines:
- Failure modes:
- Threshold recommendation:

### xtb_hessian_thermo_stability_013

- Positive controls:
- Negative baselines:
- Failure modes:
- Threshold recommendation:

## Cross-Task Reliability

- Parser failures:
- Optimization failures:
- Timeout failures:
- Relaxation-energy gate behavior:
- Stability-gate behavior:

## Recommended Follow-Ups

- Threshold changes:
- Sample-answer updates:
- Parser hardening:
- Runtime changes:
```

For each task, explicitly state one of:

- `keep_thresholds`
- `tighten_thresholds`
- `loosen_thresholds`
- `needs_more_positive_controls`
- `needs_parser_or_runtime_fix`

- [ ] **Step 5: Promote high-confidence positive controls if available**

If live results show a task 8-13 `positive_candidate` has `status == "ok"` and `score >= 0.6`, add one such candidate per advanced task to `tasks/xtb_xyz/sample_answers.jsonl`.

Update `tests/test_xtb_xyz_tasks.py`:

```python
def test_xtb_xyz_sample_answers_use_fenced_xyz() -> None:
    tasks = load_tasks(TASK_DIR / "tasks.yaml")
    answers = load_answers_jsonl(TASK_DIR / "sample_answers.jsonl")

    assert len(answers) == 13
    assert {answer["task_id"] for answer in answers} == set(tasks)
    for answer in answers:
        normalized = normalize_answer_record(answer, tasks[answer["task_id"]])
        assert normalized.ok
        assert "xyz" in normalized.answer["candidates"][0]
```

If no high-confidence positive control exists for a task, do not add a weak sample. Record `needs_more_positive_controls` in the report.

- [ ] **Step 6: Run targeted tests**

Run:

```bash
uv run pytest tests/test_xtb_xyz_tasks.py tests/test_xtb_calibration_inputs.py tests/test_xtb_calibration_scripts.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

If only the report changed:

```bash
git add docs/research/2026-06-15-xtb-calibration-reliability-report.md
git commit -m "docs: report xtb calibration reliability"
```

If sample answers changed:

```bash
git add docs/research/2026-06-15-xtb-calibration-reliability-report.md tasks/xtb_xyz/sample_answers.jsonl tests/test_xtb_xyz_tasks.py
git commit -m "docs: report xtb calibration reliability"
```

## Task 6: Full Verification and Handoff

**Files:**
- Read-only verification.

- [ ] **Step 1: Run full test suite**

Run:

```bash
uv run pytest
```

Expected: PASS.

- [ ] **Step 2: Run missing-xTB behavior check**

Run:

```bash
PATH=/usr/bin:/bin uv run python scripts/run_xtb_calibration.py \
  --answers tasks/xtb_xyz/calibration_answers.jsonl \
  --output /tmp/xtb-calibration-missing.json
```

Expected: If `xtb` is not in that restricted PATH, exit code `1` with `verifier_environment_error`. If the machine has `xtb` in `/usr/bin` or `/bin`, use a temporary empty PATH as in the pytest test instead.

- [ ] **Step 3: Check generated artifacts are not accidentally staged**

Run:

```bash
git status --short
```

Expected: no files under `artifacts/xtb_calibration/` are staged unless the repository later explicitly decides to version generated calibration outputs.

- [ ] **Step 4: Summarize calibration decisions**

In the final handoff, include:

- tests run and pass/fail status;
- whether real xTB calibration ran or was blocked by environment;
- path to the report;
- tasks that need threshold changes;
- tasks that need more positive controls;
- parser/runtime fixes found.

## Self-Review

- Spec coverage: This plan covers calibration fixtures, batch scoring, offline analysis, positive/negative controls, reliability regressions, live xTB reporting, and sample-answer promotion.
- Completeness scan: Every task has files, commands, and expected outcomes.
- Type consistency: Task IDs and verifier IDs match `tasks/xtb_xyz/tasks.yaml` and `tasks/xtb_xyz/verifier_specs.yaml` as implemented.
- Scope check: The plan produces evidence and reports only; threshold changes and schema expansion remain follow-up work.
