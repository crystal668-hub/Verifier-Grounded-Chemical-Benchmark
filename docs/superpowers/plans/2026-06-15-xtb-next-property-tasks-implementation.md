# xTB Next Property Tasks Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the approved advanced xTB direct-XYZ property tasks, verifier specs, scripts, backend run plans, parsers, and schema tests.

**Architecture:** Keep the current property-level verifier pattern. Add thin scripts under `verifiers/xtb/`, extend `verifiers/backends/xtb_properties.py` with property-specific xTB run plans and conservative parsers, and register the new tasks/specs in `tasks/xtb_xyz/`.

**Tech Stack:** Python, pytest, PyYAML task/spec files, local xTB CLI with fake-runner unit tests.

---

### Task 1: Backend Parser and Run-Plan Tests

**Files:**
- Modify: `tests/test_xtb_properties_backend.py`
- Modify: `verifiers/backends/xtb_properties.py`

- [ ] **Step 1: Write failing parser/run-plan tests**

Add tests for:
- LUMO orbital energy parsing from xTB orbital output.
- Molecular polarizability parsing and per-heavy-atom normalization.
- ALPB `Gsolv` parsing and water/hexane selectivity.
- `--vomega` global electrophilicity parsing.
- `--vfukui` carbon max and f+ contrast parsing.
- hessian imaginary frequency count and 298 K entropy parsing.
- xTB command generation for `property_command`, method selection, solvent runs, and hessian flags.

Run: `uv run pytest tests/test_xtb_properties_backend.py -q`
Expected: FAIL because the backend does not support the new properties.

- [ ] **Step 2: Implement backend support**

In `verifiers/backends/xtb_properties.py`:
- Add parser patterns/helpers for `lumo_energy`, `molecular_polarizability`, `Gsolv`, `global_electrophilicity`, Fukui f+ tables, hessian frequencies, and entropy.
- Extend `XTBRunner.command()` to honor backend keys `method`, `property_command`, `solvent_model`, `solvent`, and explicit optimize/singlepoint/property modes while retaining current default GFN2 behavior.
- Extend `run_property_calculation()` with property-specific plans:
  - optimize then parse for `lumo_energy`, `polarizability_per_heavy_atom`;
  - optimize then run ALPB water and hexane single-points for `alpb_water_hexane_selectivity`;
  - optimize then run `--vomega` for `global_electrophilicity`;
  - optimize then run `--vfukui` for `max_f_plus_on_carbon` and `f_plus_contrast`;
  - optimize/hessian run for `imaginary_frequency_count` and `entropy_298_per_heavy_atom`.

Run: `uv run pytest tests/test_xtb_properties_backend.py -q`
Expected: PASS.

- [ ] **Step 3: Commit**

Run:
```bash
git add tests/test_xtb_properties_backend.py verifiers/backends/xtb_properties.py
git commit -m "feat: extend xtb property backend"
```

### Task 2: Verifier Scripts and Specs

**Files:**
- Create: `verifiers/xtb/xtb_lumo.py`
- Create: `verifiers/xtb/xtb_polarizability.py`
- Create: `verifiers/xtb/xtb_solvation_selectivity.py`
- Create: `verifiers/xtb/xtb_electrophilicity.py`
- Create: `verifiers/xtb/xtb_fukui.py`
- Create: `verifiers/xtb/xtb_hessian_thermo.py`
- Modify: `tasks/xtb_xyz/verifier_specs.yaml`
- Modify: `tests/test_xtb_task_scripts.py`

- [ ] **Step 1: Write failing script/spec tests**

Update `tests/test_xtb_task_scripts.py` to require all six new script wrappers reject property mismatches with the shared script helper.

Run: `uv run pytest tests/test_xtb_task_scripts.py -q`
Expected: FAIL because scripts/specs are missing.

- [ ] **Step 2: Add scripts and verifier specs**

Add each script as a thin wrapper around `main("<property_name>")`. Add six verifier entries to `tasks/xtb_xyz/verifier_specs.yaml` with the approved IDs, property names, timeout values, backend methods/commands, domain, package versions, scoring, and failure policy.

Run: `uv run pytest tests/test_xtb_task_scripts.py tests/test_xtb_xyz_tasks.py -q`
Expected: existing task tests may still fail until Task 3 adds task cards, but script mismatch tests should pass.

- [ ] **Step 3: Commit**

Run:
```bash
git add verifiers/xtb/xtb_lumo.py verifiers/xtb/xtb_polarizability.py verifiers/xtb/xtb_solvation_selectivity.py verifiers/xtb/xtb_electrophilicity.py verifiers/xtb/xtb_fukui.py verifiers/xtb/xtb_hessian_thermo.py tasks/xtb_xyz/verifier_specs.yaml tests/test_xtb_task_scripts.py
git commit -m "feat: add advanced xtb verifier specs"
```

### Task 3: Task Cards and Schema Tests

**Files:**
- Modify: `tasks/xtb_xyz/tasks.yaml`
- Modify: `tests/test_xtb_xyz_tasks.py`

- [ ] **Step 1: Write failing task schema tests**

Update `tests/test_xtb_xyz_tasks.py` to expect task IDs `xtb_lumo_min_008` through `xtb_hessian_thermo_stability_013`, all new verifier IDs, the universal relaxation quality gate, and the hessian stability gate.

Run: `uv run pytest tests/test_xtb_xyz_tasks.py -q`
Expected: FAIL because the task cards are not yet present.

- [ ] **Step 2: Add task cards**

Append six task cards to `tasks/xtb_xyz/tasks.yaml` using the approved prompts, constraints, structural domains, scoring aggregation, and failure-policy anchor.

Run: `uv run pytest tests/test_xtb_xyz_tasks.py -q`
Expected: PASS.

- [ ] **Step 3: Commit**

Run:
```bash
git add tasks/xtb_xyz/tasks.yaml tests/test_xtb_xyz_tasks.py
git commit -m "feat: add advanced xtb task cards"
```

### Task 4: Full Verification

**Files:**
- Read-only verification.

- [ ] **Step 1: Run targeted tests**

Run:
```bash
uv run pytest tests/test_xtb_properties_backend.py tests/test_xtb_task_scripts.py tests/test_xtb_xyz_tasks.py -q
```
Expected: PASS.

- [ ] **Step 2: Run full suite**

Run:
```bash
uv run pytest -q
```
Expected: PASS.

- [ ] **Step 3: Optional xTB environment check**

Run:
```bash
uv run python scripts/check_xtb_env.py
```
Expected: `status` is `ok` when local xTB is installed, otherwise the documented `verifier_environment_error` JSON.

