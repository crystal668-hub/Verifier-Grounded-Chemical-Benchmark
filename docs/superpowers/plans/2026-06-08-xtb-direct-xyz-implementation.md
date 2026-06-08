# xTB Direct XYZ Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the first xTB direct-XYZ verifier track and create a reusable Codex skill that guides harness agents to operate xTB through the official CLI-oriented workflow.

**Architecture:** Add an `xtb_xyz` task pack, XYZ answer extraction support, property-level xTB verifier scripts, and a shared local-CLI backend. The backend validates XYZ geometry, maps failure modes, shells out to the `xtb` executable when present, and remains fully testable with fake runners when xTB is absent.

**Tech Stack:** Python 3.12, PyYAML, pytest, RDKit covalent radii/periodic table helpers, local xTB CLI, Codex personal skill files under `~/.agents/skills`.

---

## File Structure

- Modify `benchmark/answer_extraction.py`: support `final_answer_block` with `value_type: xyz`.
- Create `verifiers/backends/xtb_properties.py`: shared XYZ parser, domain checks, local xTB command runner, output parsers, scoring, and result shaping.
- Create `verifiers/xtb/xtb_property_script.py`: shared CLI wrapper for property scripts.
- Create `verifiers/xtb/xtb_gap.py`, `verifiers/xtb/xtb_dipole.py`, `verifiers/xtb/xtb_relaxation_energy.py`, `verifiers/xtb/__init__.py`: property-level scripts.
- Create `tasks/xtb_xyz/tasks.yaml`, `tasks/xtb_xyz/verifier_specs.yaml`, `tasks/xtb_xyz/sample_answers.jsonl`: formal task pack.
- Create `scripts/check_xtb_env.py`: manually runnable environment smoke check.
- Create tests:
  - `tests/test_xtb_answer_extraction.py`
  - `tests/test_xtb_xyz_tasks.py`
  - `tests/test_xtb_properties_backend.py`
  - `tests/test_xtb_task_scripts.py`
  - `tests/test_xtb_check_script.py`
- Create `~/.agents/skills/xtb-cli-verifier/SKILL.md` plus optional `agents/openai.yaml`: reusable harness skill.

## Implementation Tasks

### Task 1: XYZ Answer Extraction

**Files:**
- Modify: `benchmark/answer_extraction.py`
- Create: `tests/test_xtb_answer_extraction.py`

- [ ] **Step 1: Write failing extraction tests**

Create `tests/test_xtb_answer_extraction.py` with tests for `value_type: xyz`: successful extraction, last block wins, missing block, empty block, and structured `candidates` passthrough.

- [ ] **Step 2: Run red test**

Run: `uv run pytest tests/test_xtb_answer_extraction.py -q`
Expected: fail because `value_type: xyz` is unsupported.

- [ ] **Step 3: Implement extraction**

Modify `normalize_final_answer_block` so `value_type == "xyz"` accepts `fence_language: xyz` and returns `{"xyz": extracted}` while preserving existing CIF behavior.

- [ ] **Step 4: Run green test**

Run: `uv run pytest tests/test_xtb_answer_extraction.py tests/test_answer_extraction.py -q`
Expected: pass.

- [ ] **Step 5: Commit**

Commit message: `feat: extract fenced xyz answers`

### Task 2: xTB Task Pack

**Files:**
- Create: `tasks/xtb_xyz/tasks.yaml`
- Create: `tasks/xtb_xyz/verifier_specs.yaml`
- Create: `tasks/xtb_xyz/sample_answers.jsonl`
- Create: `tests/test_xtb_xyz_tasks.py`

- [ ] **Step 1: Write failing task tests**

Tests should assert task IDs, verifier IDs, `answer_schema.format: final_answer_block`, `value_type: xyz`, every constraint has `verifier_id`, prompts expose domain gates, prompts do not expose verifier IDs/script paths/`sigma`, sample answers normalize, and relaxation upper is `0.5`.

- [ ] **Step 2: Run red test**

Run: `uv run pytest tests/test_xtb_xyz_tasks.py -q`
Expected: fail because `tasks/xtb_xyz` does not exist.

- [ ] **Step 3: Add task pack**

Create the three verifier specs and seven task cards from the approved design. Use broad but explicit sample answers in fenced XYZ blocks.

- [ ] **Step 4: Run green test**

Run: `uv run pytest tests/test_xtb_xyz_tasks.py -q`
Expected: pass.

- [ ] **Step 5: Commit**

Commit message: `feat: add xtb xyz task pack`

### Task 3: xTB Backend Validation And Fake Runner Scoring

**Files:**
- Create: `verifiers/backends/xtb_properties.py`
- Create: `tests/test_xtb_properties_backend.py`

- [ ] **Step 1: Write failing backend tests**

Tests should cover XYZ parsing, atom-count mismatch, disallowed elements, atom overlap, disconnected geometry, score calculation for gap/dipole/relaxation with fake runner outputs, property mismatch, missing executable, runner nonzero exit, timeout, missing property, and xTB command construction.

- [ ] **Step 2: Run red test**

Run: `uv run pytest tests/test_xtb_properties_backend.py -q`
Expected: fail because backend module does not exist.

- [ ] **Step 3: Implement backend**

Implement focused helpers:

- `parse_xyz(xyz: str) -> XYZMolecule`
- `inspect_xyz(molecule, domain) -> dict`
- `check_domain(properties, domain) -> str | None`
- `evaluate_xtb_property_constraint(candidate, task, constraint, spec, runner=None) -> dict`
- `XTBRunner` using `subprocess.run`
- output parsers for total energy, HOMO-LUMO gap, dipole moment, optimization convergence, and optimized energy

- [ ] **Step 4: Run green test**

Run: `uv run pytest tests/test_xtb_properties_backend.py -q`
Expected: pass.

- [ ] **Step 5: Commit**

Commit message: `feat: add xtb xyz verifier backend`

### Task 4: xTB Property Scripts And Routing

**Files:**
- Create: `verifiers/xtb/__init__.py`
- Create: `verifiers/xtb/xtb_property_script.py`
- Create: `verifiers/xtb/xtb_gap.py`
- Create: `verifiers/xtb/xtb_dipole.py`
- Create: `verifiers/xtb/xtb_relaxation_energy.py`
- Create: `tests/test_xtb_task_scripts.py`

- [ ] **Step 1: Write failing script tests**

Tests should assert property mismatch returns `verifier_spec_error`, missing candidate returns `parse_error`, and each script returns standard JSON shape through `run_verification_script`.

- [ ] **Step 2: Run red test**

Run: `uv run pytest tests/test_xtb_task_scripts.py -q`
Expected: fail because scripts do not exist.

- [ ] **Step 3: Implement scripts**

Mirror existing RDKit/MatGL property script shape. Each script imports `main` and passes a fixed property name.

- [ ] **Step 4: Run green test**

Run: `uv run pytest tests/test_xtb_task_scripts.py tests/test_evaluate_routing.py -q`
Expected: pass.

- [ ] **Step 5: Commit**

Commit message: `feat: add xtb property verifier scripts`

### Task 5: xTB Environment Check Script

**Files:**
- Create: `scripts/check_xtb_env.py`
- Create: `tests/test_xtb_check_script.py`

- [ ] **Step 1: Write failing environment script tests**

Tests should assert the script imports project modules, reports `xtb_executable`, exits 1 with a clear message when `xtb` is absent, and can run in a missing-xTB environment without crashing.

- [ ] **Step 2: Run red test**

Run: `uv run pytest tests/test_xtb_check_script.py -q`
Expected: fail because script does not exist.

- [ ] **Step 3: Implement script**

Implement a JSON-printing smoke check. If xTB is present, run `xtb --version` and a water optimization/property parse; if absent, exit 1 and print a structured missing-executable report.

- [ ] **Step 4: Run green test**

Run: `uv run pytest tests/test_xtb_check_script.py -q`
Expected: pass.

- [ ] **Step 5: Commit**

Commit message: `feat: add xtb environment check script`

### Task 6: Full Integration Verification

**Files:**
- Modify tests only if integration reveals a mismatch.

- [ ] **Step 1: Run full test suite**

Run: `uv run pytest`
Expected: all tests pass.

- [ ] **Step 2: Run manual environment check**

Run: `uv run python scripts/check_xtb_env.py`
Expected on current machine: exit 1 with `verifier_environment_error` because `xtb` is not installed.

- [ ] **Step 3: Commit any integration fixes**

Commit only if files changed. Use a focused message such as `fix: align xtb integration tests`.

### Task 7: Create xTB CLI Verifier Skill

**Files:**
- Create: `/Users/xutao/.agents/skills/xtb-cli-verifier/SKILL.md`
- Optionally create: `/Users/xutao/.agents/skills/xtb-cli-verifier/agents/openai.yaml`

- [ ] **Step 1: Draft skill**

Create a concise skill named `xtb-cli-verifier`. It should trigger when an agent needs to run, verify, or debug xTB CLI verifier workflows, xTB XYZ scoring, xTB installation checks, failure mapping, or harness integration.

- [ ] **Step 2: Validate skill file**

Run a lightweight metadata check that parses YAML frontmatter and confirms required `name` and `description` fields.

- [ ] **Step 3: Verify skill in this Codex environment**

Use the skill instructions manually against the real machine:

- Run `command -v xtb`.
- Run `uv run python scripts/check_xtb_env.py`.
- Confirm the skill correctly predicts and explains the missing-xTB behavior.

- [ ] **Step 4: Commit repo-side note if needed**

The skill lives outside the repo. Do not commit personal skill files unless the user asks to vendor them. Include verification evidence in the final response.

### Task 8: Final Verification And Cleanup

**Files:**
- Any modified repo files.

- [ ] **Step 1: Run full tests**

Run: `uv run pytest`
Expected: all tests pass.

- [ ] **Step 2: Check git status**

Run: `git status --short`
Expected: clean or only intentional personal skill files outside repo.

- [ ] **Step 3: Summarize commits and known environment limitation**

Report that xTB is not installed locally, so live xTB chemistry execution is guarded by the environment check and fake-runner tests.

## Self-Review

- Spec coverage: answer schema, task cards, verifier specs, backend, scripts, failure policy, tests, env smoke check, and skill are covered.
- Placeholder scan: no task uses TBD/TODO/fill-in instructions.
- Type consistency: property names are `homo_lumo_gap`, `dipole_moment`, and `relaxation_energy`; verifier IDs match the Chinese design spec.
