# Task-Level Verifier Script Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate the current verifier pipeline from Python registry-dispatched verifier functions to per-task `verification_script` entries that consume a standard `{task, verifier_spec, candidate}` JSON payload and emit a standard result JSON.

**Architecture:** Keep Docker image packaging as a future release step. In the current repo, implement the contract locally with subprocess-executed task scripts. Each task has one script entry point; scripts may call shared backend modules for reusable RDKit, scoring, and future chemistry tooling. The runner dispatches by `verifier_spec.verification_script`, not by a Python function registry.

**Tech Stack:** Python 3.12, PyYAML, pytest, subprocess JSON I/O, RDKit 2026.3.2, existing benchmark answer extraction.

---

## Scope And Boundaries

This plan implements the verifier shape needed for current development. It does not build or publish the final Docker image.

In scope:

- Add a local script execution layer that sends `{task, verifier_spec, candidate}` to a task-level script over stdin.
- Split the current RDKit verifier logic into shared backend code and task-level scripts.
- Update RDKit baseline verifier specs so every task points to a unique `verification_script`.
- Update the runner to dispatch by script path and preserve the existing report shape.
- Keep RDKit baseline tasks passing through the new script path.
- Mark AtomisticSkills smoke verifiers as experimental/non-formal so they are not mistaken for the final property-satisfaction track.

Out of scope:

- No Dockerfile, image build, image push, or container runtime integration.
- No xTB, ADMET, CHGNet, MACE, docking, or other new scientific backend implementation.
- No conversion of AtomisticSkills MCP tasks into formal production verifiers.
- No database-query verifier path.
- No new benchmark task families beyond restructuring existing RDKit baseline verifiers.

## Target Interfaces

### Verifier Spec Shape

Every formal verifier spec must include a task-level script path:

```yaml
verifier_id: rdkit_logp_window_003_v1
name: RDKit LogP Window Verifier
version: 1
verifier_image: verifier-grounded:dev
verification_script: verifiers/tasks/rdkit_logp_window_003.py
timeout_seconds: 60
resources:
  cpu: 1
  memory_mb: 1024
backend:
  type: rdkit_descriptors
package_versions:
  rdkit: "2026.3.2"
domain:
  allowed_elements: [H, B, C, N, O, F, P, S, Cl, Br, I]
  heavy_atom_count: [5, 60]
  mw: [80.0, 600.0]
  formal_charge: [-1, 1]
```

`verifier_image: verifier-grounded:dev` is metadata in this phase. It documents the future runtime target but is not used to run Docker.

### Script Input

Runner sends this JSON to the script stdin:

```json
{
  "task": {
    "task_id": "rdkit_logp_window_003",
    "constraints": [
      {
        "type": "window",
        "property": "logp",
        "min": 1.0,
        "max": 3.0,
        "sigma": 0.5
      }
    ],
    "answer_schema": {
      "format": "final_answer_line",
      "value_type": "smiles"
    },
    "failure_policy": {
      "invalid_smiles": "parse_error"
    }
  },
  "verifier_spec": {
    "verifier_id": "rdkit_logp_window_003_v1",
    "verification_script": "verifiers/tasks/rdkit_logp_window_003.py",
    "backend": {
      "type": "rdkit_descriptors"
    },
    "domain": {
      "allowed_elements": ["H", "B", "C", "N", "O", "F", "P", "S", "Cl", "Br", "I"],
      "heavy_atom_count": [5, 60],
      "mw": [80.0, 600.0],
      "formal_charge": [-1, 1]
    }
  },
  "candidate": {
    "smiles": "CC(=O)Oc1ccccc1C(=O)O"
  }
}
```

### Script Output

Script stdout must contain one JSON object:

```json
{
  "task_id": "rdkit_logp_window_003",
  "status": "ok",
  "failure_type": null,
  "canonical_smiles": "CC(=O)Oc1ccccc1C(=O)O",
  "properties": {
    "logp": 1.3101,
    "mw": 180.159
  },
  "scores": {
    "validity_gate": 1.0,
    "domain_gate": 1.0,
    "constraint_scores": [
      {
        "property": "logp",
        "type": "window",
        "score": 1.0
      }
    ],
    "property_score": 1.0,
    "score": 1.0
  },
  "versions": {
    "verifier_image": "verifier-grounded:dev",
    "rdkit": "2026.3.2"
  }
}
```

On error, `status` is `"error"`, `failure_type` is a known failure type, and score fields are zeroed as today.

## File Structure

- Create `benchmark/verifier_scripts.py`: subprocess runner for task-level scripts and payload construction.
- Modify `benchmark/evaluate.py`: dispatch to `verification_script`; keep legacy registry only for explicitly experimental specs during transition.
- Create `verifiers/backends/rdkit_descriptors.py`: shared RDKit parsing, canonicalization, property, domain, and scoring helpers.
- Create `verifiers/tasks/rdkit_common.py`: thin script helper that reads stdin, calls the RDKit backend, and writes JSON.
- Create `verifiers/tasks/rdkit_<task_id>.py` for each current RDKit baseline task; each file is the unique task entry point and delegates to `rdkit_common`.
- Modify `tasks/rdkit_baseline/verifier_specs.yaml`: give each RDKit task its own verifier spec with `verification_script`.
- Modify `tasks/rdkit_baseline/tasks.yaml`: update each task's `verifier_id` to the task-specific spec id.
- Modify `tasks/atomisticskills_smoke/tasks.yaml` and `tasks/atomisticskills_smoke/verifier_specs.yaml`: add clear experimental/smoke metadata and keep them out of formal script migration.
- Create or modify tests listed per task below.

## Task 1: Add Script Execution Contract

**Files:**
- Create: `benchmark/verifier_scripts.py`
- Test: `tests/test_verifier_script_runner.py`

- [ ] **Step 1: Write failing tests for payload construction and script execution**

Create `tests/test_verifier_script_runner.py` with:

```python
from __future__ import annotations

import json
import sys
from pathlib import Path

from benchmark.verifier_scripts import build_script_payload, run_verification_script


def test_build_script_payload_uses_first_candidate() -> None:
    task = {"task_id": "task_1", "constraints": []}
    spec = {"verifier_id": "verifier_1", "verification_script": "verifiers/tasks/example.py"}
    answer = {"task_id": "task_1", "candidates": [{"smiles": "CCO"}]}

    payload = build_script_payload(answer, task, spec)

    assert payload == {
        "task": task,
        "verifier_spec": spec,
        "candidate": {"smiles": "CCO"},
    }


def test_run_verification_script_round_trips_json(tmp_path: Path) -> None:
    script = tmp_path / "echo_verifier.py"
    script.write_text(
        "import json, sys\n"
        "payload = json.load(sys.stdin)\n"
        "json.dump({'task_id': payload['task']['task_id'], 'status': 'ok', 'failure_type': None, 'properties': {}, 'scores': {'score': 1.0}, 'versions': {}}, sys.stdout)\n"
    )

    result = run_verification_script(
        script,
        {"task": {"task_id": "task_1"}, "verifier_spec": {}, "candidate": {"smiles": "CCO"}},
        timeout_seconds=5,
        python_executable=sys.executable,
    )

    assert result["task_id"] == "task_1"
    assert result["status"] == "ok"
    assert result["scores"]["score"] == 1.0
```

Run: `uv run pytest tests/test_verifier_script_runner.py -v`

Expected: fail because `benchmark.verifier_scripts` does not exist.

- [ ] **Step 2: Implement script runner**

Create `benchmark/verifier_scripts.py`:

```python
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def build_script_payload(answer: dict[str, Any], task: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    candidates = answer.get("candidates")
    candidate = candidates[0] if isinstance(candidates, list) and candidates and isinstance(candidates[0], dict) else {}
    return {"task": task, "verifier_spec": spec, "candidate": candidate}


def run_verification_script(
    script_path: str | Path,
    payload: dict[str, Any],
    *,
    timeout_seconds: float,
    python_executable: str = sys.executable,
) -> dict[str, Any]:
    script = Path(script_path)
    completed = subprocess.run(
        [python_executable, str(script)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    if completed.returncode != 0:
        return {
            "task_id": payload.get("task", {}).get("task_id"),
            "status": "error",
            "failure_type": "verifier_tool_error",
            "message": completed.stderr.strip() or completed.stdout.strip() or f"{script} exited {completed.returncode}",
            "properties": {},
            "scores": {
                "validity_gate": 0.0,
                "domain_gate": 0.0,
                "constraint_scores": [],
                "property_score": 0.0,
                "score": 0.0,
            },
            "versions": {},
        }
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        return {
            "task_id": payload.get("task", {}).get("task_id"),
            "status": "error",
            "failure_type": "verifier_tool_error",
            "message": f"verification script produced invalid JSON: {exc.msg}",
            "properties": {},
            "scores": {
                "validity_gate": 0.0,
                "domain_gate": 0.0,
                "constraint_scores": [],
                "property_score": 0.0,
                "score": 0.0,
            },
            "versions": {},
        }
    return result
```

- [ ] **Step 3: Verify runner tests pass**

Run: `uv run pytest tests/test_verifier_script_runner.py -v`

Expected: pass.

- [ ] **Step 4: Commit Task 1**

Run:

```bash
git add benchmark/verifier_scripts.py tests/test_verifier_script_runner.py
git commit -m "Add verifier script execution contract"
```

## Task 2: Extract Shared RDKit Backend

**Files:**
- Create: `verifiers/backends/__init__.py`
- Create: `verifiers/backends/rdkit_descriptors.py`
- Modify: `verifiers/small_molecule_rdkit.py`
- Test: `tests/test_rdkit_descriptor_backend.py`, `tests/test_small_molecule_rdkit.py`

- [ ] **Step 1: Write failing backend tests**

Create `tests/test_rdkit_descriptor_backend.py`:

```python
from __future__ import annotations

import pytest

from verifiers.backends.rdkit_descriptors import evaluate_candidate


SPEC = {
    "verifier_id": "rdkit_backend_test_v1",
    "verifier_image": "verifier-grounded:dev",
    "domain": {
        "allowed_elements": ["H", "B", "C", "N", "O", "F", "P", "S", "Cl", "Br", "I"],
        "heavy_atom_count": [5, 60],
        "mw": [80.0, 600.0],
        "formal_charge": [-1, 1],
    },
}


TASK = {
    "task_id": "rdkit_logp_window_003",
    "constraints": [{"type": "window", "property": "logp", "min": 1.0, "max": 3.0, "sigma": 0.5}],
}


def test_evaluate_candidate_scores_valid_smiles() -> None:
    result = evaluate_candidate({"smiles": "CC(=O)Oc1ccccc1C(=O)O"}, TASK, SPEC)

    assert result["status"] == "ok"
    assert result["task_id"] == "rdkit_logp_window_003"
    assert result["canonical_smiles"] == "CC(=O)Oc1ccccc1C(=O)O"
    assert result["properties"]["logp"] == pytest.approx(1.3101, abs=1e-4)
    assert result["scores"]["score"] == 1.0
    assert result["versions"]["verifier_image"] == "verifier-grounded:dev"


def test_evaluate_candidate_rejects_invalid_smiles() -> None:
    result = evaluate_candidate({"smiles": "not a smiles"}, TASK, SPEC)

    assert result["status"] == "error"
    assert result["failure_type"] == "parse_error"
    assert result["scores"]["score"] == 0.0
```

Run: `uv run pytest tests/test_rdkit_descriptor_backend.py -v`

Expected: fail because backend module does not exist.

- [ ] **Step 2: Move reusable RDKit logic into backend**

Create `verifiers/backends/__init__.py`.

Create `verifiers/backends/rdkit_descriptors.py` by moving reusable logic from `verifiers/small_molecule_rdkit.py`:

- `clamp`
- `score_constraint`
- `compute_properties`
- `check_domain`
- `geometric_mean`
- `base_result`
- `error_result`
- new `evaluate_candidate(candidate, task, spec)`

`evaluate_candidate` must accept a single candidate dict, not a full answer record. It must read `candidate["smiles"]`.

The result shape must match current RDKit verifier output and include:

```python
"versions": {
    "verifier_image": spec.get("verifier_image"),
    "rdkit": metadata.version("rdkit"),
}
```

- [ ] **Step 3: Make legacy RDKit callable delegate to backend**

Modify `verifiers/small_molecule_rdkit.py` so `evaluate_answer(answer, task, spec)` extracts the first candidate and calls `verifiers.backends.rdkit_descriptors.evaluate_candidate(candidate, task, spec)`. Re-export `clamp`, `geometric_mean`, and `score_constraint` from the backend so existing tests and AtomisticSkills smoke code keep working.

- [ ] **Step 4: Verify backend and legacy tests pass**

Run:

```bash
uv run pytest tests/test_rdkit_descriptor_backend.py tests/test_small_molecule_rdkit.py -v
```

Expected: pass.

- [ ] **Step 5: Commit Task 2**

Run:

```bash
git add verifiers/backends/__init__.py verifiers/backends/rdkit_descriptors.py verifiers/small_molecule_rdkit.py tests/test_rdkit_descriptor_backend.py
git commit -m "Extract shared RDKit descriptor backend"
```

## Task 3: Add Task-Level RDKit Scripts

**Files:**
- Create: `verifiers/tasks/__init__.py`
- Create: `verifiers/tasks/rdkit_common.py`
- Create: one task script per RDKit baseline task:
  - `verifiers/tasks/rdkit_qed_max_001.py`
  - `verifiers/tasks/rdkit_sa_min_002.py`
  - `verifiers/tasks/rdkit_logp_window_003.py`
  - `verifiers/tasks/rdkit_tpsa_window_004.py`
  - `verifiers/tasks/rdkit_mw_window_005.py`
  - `verifiers/tasks/rdkit_hba_window_006.py`
  - `verifiers/tasks/rdkit_hbd_window_007.py`
  - `verifiers/tasks/rdkit_fsp3_max_008.py`
  - `verifiers/tasks/rdkit_qed_sa_009.py`
  - `verifiers/tasks/rdkit_logp_tpsa_010.py`
  - `verifiers/tasks/rdkit_mw_qed_011.py`
  - `verifiers/tasks/rdkit_hba_hbd_012.py`
- Test: `tests/test_rdkit_task_scripts.py`

- [ ] **Step 1: Write failing script tests**

Create `tests/test_rdkit_task_scripts.py`:

```python
from __future__ import annotations

from pathlib import Path

import yaml

from benchmark.verifier_scripts import run_verification_script


ROOT = Path(__file__).resolve().parents[1]
TASKS_PATH = ROOT / "tasks" / "rdkit_baseline" / "tasks.yaml"


def load_tasks() -> list[dict]:
    with TASKS_PATH.open() as handle:
        return yaml.safe_load(handle)["tasks"]


def test_rdkit_task_script_outputs_result_json() -> None:
    task = next(task for task in load_tasks() if task["task_id"] == "rdkit_logp_window_003")
    spec = {
        "verifier_id": "rdkit_logp_window_003_v1",
        "verifier_image": "verifier-grounded:dev",
        "verification_script": "verifiers/tasks/rdkit_logp_window_003.py",
        "timeout_seconds": 60,
        "domain": {
            "allowed_elements": ["H", "B", "C", "N", "O", "F", "P", "S", "Cl", "Br", "I"],
            "heavy_atom_count": [5, 60],
            "mw": [80.0, 600.0],
            "formal_charge": [-1, 1],
        },
    }
    payload = {"task": task, "verifier_spec": spec, "candidate": {"smiles": "CC(=O)Oc1ccccc1C(=O)O"}}

    result = run_verification_script(ROOT / spec["verification_script"], payload, timeout_seconds=60)

    assert result["status"] == "ok"
    assert result["task_id"] == "rdkit_logp_window_003"
    assert result["canonical_smiles"] == "CC(=O)Oc1ccccc1C(=O)O"
    assert result["scores"]["score"] == 1.0
```

Run: `uv run pytest tests/test_rdkit_task_scripts.py -v`

Expected: fail because script files do not exist.

- [ ] **Step 2: Implement common script helper**

Create `verifiers/tasks/__init__.py`.

Create `verifiers/tasks/rdkit_common.py`:

```python
from __future__ import annotations

import json
import sys
from typing import Any

from verifiers.backends.rdkit_descriptors import evaluate_candidate


def main() -> None:
    payload: dict[str, Any] = json.load(sys.stdin)
    result = evaluate_candidate(payload.get("candidate", {}), payload.get("task", {}), payload.get("verifier_spec", {}))
    json.dump(result, sys.stdout, sort_keys=True)
```

- [ ] **Step 3: Create task scripts**

Each `verifiers/tasks/rdkit_<task_id>.py` must contain exactly this shape:

```python
from __future__ import annotations

from verifiers.tasks.rdkit_common import main


if __name__ == "__main__":
    main()
```

Create one file for each of the 12 RDKit baseline task ids listed in this task's file section.

- [ ] **Step 4: Verify task script test passes**

Run: `uv run pytest tests/test_rdkit_task_scripts.py -v`

Expected: pass.

- [ ] **Step 5: Commit Task 3**

Run:

```bash
git add verifiers/tasks tests/test_rdkit_task_scripts.py
git commit -m "Add RDKit task-level verifier scripts"
```

## Task 4: Migrate RDKit Specs And Runner To Script Dispatch

**Files:**
- Modify: `tasks/rdkit_baseline/tasks.yaml`
- Modify: `tasks/rdkit_baseline/verifier_specs.yaml`
- Modify: `benchmark/evaluate.py`
- Test: `tests/test_evaluate_routing.py`, `tests/test_small_molecule_rdkit.py`

- [ ] **Step 1: Write failing spec tests**

Modify `tests/test_small_molecule_rdkit.py::test_task_cards_bind_to_verifier_spec` to assert:

```python
assert task["verifier_id"] in specs
spec = specs[task["verifier_id"]]
assert spec["verifier_image"] == "verifier-grounded:dev"
assert spec["verification_script"].endswith(f"{task['task_id']}.py")
assert (ROOT / spec["verification_script"]).exists()
assert spec["backend"]["type"] == "rdkit_descriptors"
```

Run: `uv run pytest tests/test_small_molecule_rdkit.py::test_task_cards_bind_to_verifier_spec -v`

Expected: fail because current RDKit spec has one shared `small_molecule_rdkit_v1` verifier and no `verification_script`.

- [ ] **Step 2: Update RDKit task verifier ids**

In `tasks/rdkit_baseline/tasks.yaml`, set each task's `verifier_id` to the task id plus `_v1`. Examples:

```yaml
task_id: rdkit_qed_max_001
verifier_id: rdkit_qed_max_001_v1
```

```yaml
task_id: rdkit_logp_window_003
verifier_id: rdkit_logp_window_003_v1
```

Apply this to all 12 RDKit tasks.

- [ ] **Step 3: Replace RDKit verifier specs with task-specific specs**

In `tasks/rdkit_baseline/verifier_specs.yaml`, replace the single `small_molecule_rdkit_v1` spec with 12 specs. The naming pattern is:

- `verifier_id`: task id plus `_v1`, for example `rdkit_logp_window_003_v1`.
- `name`: `RDKit ` plus the task id converted to title words plus ` Verifier`, for example `RDKit Logp Window 003 Verifier`.
- `verification_script`: `verifiers/tasks/` plus the task id plus `.py`, for example `verifiers/tasks/rdkit_logp_window_003.py`.

Each spec must include this complete structure:

```yaml
verifier_id: rdkit_logp_window_003_v1
name: RDKit Logp Window 003 Verifier
version: 1
verifier_image: verifier-grounded:dev
verification_script: verifiers/tasks/rdkit_logp_window_003.py
timeout_seconds: 60
resources:
  cpu: 1
  memory_mb: 1024
backend:
  type: rdkit_descriptors
package_versions:
  rdkit: "2026.3.2"
domain:
  allowed_elements: [H, B, C, N, O, F, P, S, Cl, Br, I]
  heavy_atom_count: [5, 60]
  mw: [80.0, 600.0]
  formal_charge: [-1, 1]
properties:
  qed:
    source: rdkit.Chem.QED.qed
    range: [0.0, 1.0]
  logp:
    source: rdkit.Chem.Crippen.MolLogP
  tpsa:
    source: rdkit.Chem.rdMolDescriptors.CalcTPSA
    units: angstrom_squared
  mw:
    source: rdkit.Chem.Descriptors.MolWt
    units: dalton
  hbd:
    source: rdkit.Chem.rdMolDescriptors.CalcNumHBD
  hba:
    source: rdkit.Chem.rdMolDescriptors.CalcNumHBA
  rotatable_bonds:
    source: rdkit.Chem.rdMolDescriptors.CalcNumRotatableBonds
  sa_score:
    source: rdkit.Contrib.SA_Score.sascorer.calculateScore
    scoring_range: [1.0, 10.0]
  fraction_csp3:
    source: rdkit.Chem.rdMolDescriptors.CalcFractionCSP3
    range: [0.0, 1.0]
scoring:
  supported_modes:
    - window
    - maximize_bounded
    - minimize_bounded
  aggregation: geometric_mean
  bounded_modes:
    good_at_or_baseline: forbidden
  final_score_range: [0.0, 1.0]
failure_policy:
  parse_error: invalid answer JSON shape, missing SMILES, or unparseable SMILES
  validity_error: multi-component SMILES or unsanitizable molecule
  domain_error: outside element, heavy atom, MW, or formal charge domain
```

The `properties`, `scoring`, `domain`, and `failure_policy` blocks may be repeated verbatim across the 12 specs. Do not introduce a shared registry spec for the formal RDKit baseline.

- [ ] **Step 4: Update `evaluate_one` to prefer script dispatch**

Modify `benchmark/evaluate.py`:

1. After `spec` lookup, if `spec` has `verification_script`, build payload with `build_script_payload(normalized_answer, task, spec)`.
2. Resolve script path relative to repo root.
3. Call `run_verification_script(script_path, payload, timeout_seconds=float(spec.get("timeout_seconds", 60.0)))`.
4. Preserve `raw_answer` and `extracted_answer` on the result as today.
5. If `verification_script` is missing, fall back to current registry flow only for legacy/experimental specs.

- [ ] **Step 5: Update routing tests**

In `tests/test_evaluate_routing.py`:

- Change registry-specific RDKit assertions so they no longer expect `small_molecule_rdkit_v1`.
- Keep `test_evaluate_one_routes_by_task_and_verifier_id`, but verify script dispatch returns the same score for `rdkit_qed_max_001`.
- Keep unknown registry verifier tests for legacy fallback by using a spec without `verification_script`.

Run:

```bash
uv run pytest tests/test_evaluate_routing.py tests/test_small_molecule_rdkit.py -v
```

Expected: pass.

- [ ] **Step 6: Commit Task 4**

Run:

```bash
git add benchmark/evaluate.py tasks/rdkit_baseline/tasks.yaml tasks/rdkit_baseline/verifier_specs.yaml tests/test_evaluate_routing.py tests/test_small_molecule_rdkit.py
git commit -m "Route RDKit baseline through task verifier scripts"
```

## Task 5: Isolate AtomisticSkills Smoke Verifiers

**Files:**
- Modify: `tasks/atomisticskills_smoke/tasks.yaml`
- Modify: `tasks/atomisticskills_smoke/verifier_specs.yaml`
- Modify: `tests/test_atomisticskills_verifiers.py`

- [ ] **Step 1: Write/update tests for experimental classification**

Update `tests/test_atomisticskills_verifiers.py` to assert every AtomisticSkills smoke task has:

```python
assert "experimental_smoke" in task["capability_tags"]
assert task["formal_track"] is False
```

And every AtomisticSkills smoke spec has:

```python
assert spec["formal_track"] is False
assert spec["backend"]["type"] in {"mcp", "script"}
```

Run: `uv run pytest tests/test_atomisticskills_verifiers.py -v`

Expected: fail until YAML is updated.

- [ ] **Step 2: Update AtomisticSkills task cards**

In `tasks/atomisticskills_smoke/tasks.yaml`, add to each task:

```yaml
formal_track: false
```

Add `experimental_smoke` to each `capability_tags` list.

For `atomisticskills_xrd_peak_001`, add a clear note field:

```yaml
notes: "Smoke test for script adapter only; not a formal open-generation property-satisfaction task because the model reports a numeric peak rather than a candidate structure."
```

For `atomisticskills_base_supercell_001`, add:

```yaml
notes: "Smoke test for structure operation adapter only; not a formal open-generation property-satisfaction task."
```

- [ ] **Step 3: Update AtomisticSkills specs**

In `tasks/atomisticskills_smoke/verifier_specs.yaml`, add to each spec:

```yaml
formal_track: false
verifier_image: null
verification_script: null
```

This makes the boundary explicit: these specs are intentionally retained as legacy/experimental adapter smoke tests and are not part of the formal script migration.

- [ ] **Step 4: Verify AtomisticSkills tests pass**

Run: `uv run pytest tests/test_atomisticskills_verifiers.py tests/test_atomisticskills_adapters.py -v`

Expected: pass.

- [ ] **Step 5: Commit Task 5**

Run:

```bash
git add tasks/atomisticskills_smoke/tasks.yaml tasks/atomisticskills_smoke/verifier_specs.yaml tests/test_atomisticskills_verifiers.py
git commit -m "Mark AtomisticSkills verifiers as experimental smoke tests"
```

## Task 6: Full Verification And Final Cleanup

**Files:**
- Modify as needed: `verifiers/registry.py`, `scripts/score_answers.py`, `scripts/check_core_env.py`, tests.
- Do not create Docker image files.

- [ ] **Step 1: Decide whether registry can be reduced**

Inspect whether `verifiers/registry.py` is now only needed for AtomisticSkills legacy fallback tests. If so, leave it in place and add a module docstring sentence:

```python
"""Legacy verifier registry used only for experimental specs that do not yet define verification_script."""
```

Do not add new RDKit registry entries.

- [ ] **Step 2: Verify CLI still scores sample RDKit answers**

Run:

```bash
uv run python scripts/score_answers.py --answers tasks/rdkit_baseline/sample_answers.jsonl
```

Expected: JSON summary with:

```json
"num_answers": 12,
"num_ok": 12,
"num_error": 0
```

- [ ] **Step 3: Verify full test suite**

Run:

```bash
uv run pytest
```

Expected: all tests pass.

- [ ] **Step 4: Check final diff and no whitespace errors**

Run:

```bash
git diff --stat
git diff --check
git status --short
```

Expected:

- no whitespace errors;
- no Dockerfile or image build files added;
- RDKit formal path uses `verification_script`;
- AtomisticSkills remains clearly experimental.

- [ ] **Step 5: Commit final cleanup if any**

If Task 6 changed files, commit:

```bash
git add verifiers/registry.py scripts/score_answers.py scripts/check_core_env.py tests
git commit -m "Finalize verifier script migration cleanup"
```

If no files changed, do not create an empty commit.

## Acceptance Criteria

- RDKit baseline tasks are formal task-level verifier script tasks.
- Each formal RDKit task has a unique `verification_script`.
- Runner dispatches formal specs by `verification_script`, not by Python registry.
- Script payload is exactly `{task, verifier_spec, candidate}`.
- Script result is valid JSON and preserves the current scoring/report fields.
- Shared RDKit backend is reusable by all RDKit task scripts.
- AtomisticSkills smoke tasks are explicitly non-formal experimental adapter tests.
- No Docker image work is implemented in this plan.
- `uv run pytest` passes.
- `scripts/score_answers.py` scores all 12 RDKit sample answers successfully.

## Implementation Notes

- Keep task scripts intentionally thin. They exist to provide a per-task executable entry point, not to duplicate chemistry logic.
- Do not expose shared backend names to users as the verification target. Users should see and execute task-level scripts.
- Keep `verifier_image: verifier-grounded:dev` as metadata only until the later image packaging phase.
- Do not add database clients or query paths as verifier backends.
- Preserve `raw_answer` and `extracted_answer` in runner summaries.
