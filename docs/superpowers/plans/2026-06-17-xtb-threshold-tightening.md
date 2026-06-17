# xTB Threshold Tightening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tighten only the xTB task thresholds that the calibration reliability report identified as saturated: `xtb_lumo_min_008` and `xtb_hessian_thermo_stability_013`.

**Architecture:** Keep verifier code, answer schemas, prompts, calibration fixtures, and sample answers unchanged. Add regression tests that encode the calibrated threshold decisions, then update `tasks/xtb_xyz/tasks.yaml` values. Do not adjust tasks 9-12 in this plan because the report classifies them as needing stronger positive controls rather than threshold changes.

**Tech Stack:** Python 3.12, pytest, PyYAML, existing `benchmark.evaluate.load_tasks`, shared bounded scorer from `verifiers.backends.rdkit_descriptors.score_constraint`.

---

## Evidence Summary

Use `docs/research/2026-06-15-xtb-calibration-reliability-report.md` as the primary scope source:

- `xtb_lumo_min_008`: recommendation `tighten_thresholds`; both the positive control LUMO `-8.442 eV` and intended near miss `-8.217 eV` saturated at score `1.000` under `lower: -4.0`, `upper: 1.0`.
- `xtb_hessian_thermo_stability_013`: recommendation `tighten_thresholds`; stable controls with entropy per heavy atom around `40-43 J mol-1 K-1` saturated under `lower: 5.0`, `upper: 18.0`.
- `xtb_polarizability_dipole_opt_009`, `xtb_solvation_selectivity_alpb_010`, `xtb_electrophilicity_max_011`, and `xtb_fukui_carbon_site_012`: recommendation `needs_more_positive_controls`; leave thresholds unchanged.

Use `docs/research/2026-06-15-xtb-real-dataset-property-distributions.md` only as supporting scale evidence for numeric choices:

- QM9 smoke `lumo_energy`: P5 `-8.698`, P50 `-5.607`, P95 `1.428`.
- QM9 smoke `entropy_298_per_heavy_atom`: P5 `54.515`, P50 `65.298`, P95 `75.229`.

## Threshold Decisions

- `xtb_lumo_min_008`:
  - Change `lower` from `-4.0` to `-9.0`.
  - Change `upper` from `1.0` to `-5.0`.
  - Expected effect: common median-like LUMO values around `-5.6 eV` score low, while strongly electron-accepting values around `-8.4 eV` remain high but no longer saturate.

- `xtb_hessian_thermo_stability_013`:
  - Change `entropy_298_per_heavy_atom` `lower` from `5.0` to `50.0`.
  - Change `entropy_298_per_heavy_atom` `upper` from `18.0` to `80.0`.
  - Expected effect: the current stable compact controls no longer saturate solely from being stable; high entropy per heavy atom remains a real optimization objective. The existing imaginary-frequency stability gate and relaxation-energy quality gate remain unchanged.

## File Structure

- Modify `tests/test_xtb_xyz_tasks.py`: add a calibration-threshold regression test for task 8 and task 13, and assert tasks 9-12 remain at their current thresholds.
- Modify `tasks/xtb_xyz/tasks.yaml`: update only the `lumo_energy` bounded scoring values for task 8 and the `entropy_298_per_heavy_atom` bounded scoring values for task 13.
- Do not modify `tasks/xtb_xyz/sample_answers.jsonl`.
- Do not modify `tasks/xtb_xyz/calibration_answers.jsonl` or `tasks/xtb_xyz/calibration_manifest.yaml` in this plan.
- Do not commit generated `artifacts/` outputs.

## Task 1: Add Threshold Regression Tests

**Files:**
- Modify: `tests/test_xtb_xyz_tasks.py`

- [ ] **Step 1: Write the failing threshold regression test**

Append this test after `test_xtb_gap_max_task_uses_calibrated_high_gap_thresholds`:

```python
def test_xtb_advanced_tasks_use_calibrated_tightened_thresholds() -> None:
    from verifiers.backends.rdkit_descriptors import score_constraint

    tasks = load_tasks(TASK_DIR / "tasks.yaml")

    lumo = next(item for item in tasks["xtb_lumo_min_008"]["constraints"] if item["property"] == "lumo_energy")
    assert lumo["type"] == "minimize_bounded"
    assert lumo["lower"] == -9.0
    assert lumo["upper"] == -5.0
    assert score_constraint({"lumo_energy": -8.442}, lumo) == pytest.approx(0.8605, rel=1e-4)
    assert score_constraint({"lumo_energy": -8.217}, lumo) == pytest.approx(0.80425, rel=1e-4)
    assert score_constraint({"lumo_energy": -5.607}, lumo) == pytest.approx(0.15175, rel=1e-4)

    hessian_constraints = tasks["xtb_hessian_thermo_stability_013"]["constraints"]
    entropy = next(item for item in hessian_constraints if item["property"] == "entropy_298_per_heavy_atom")
    imaginary = next(item for item in hessian_constraints if item["property"] == "imaginary_frequency_count")
    assert imaginary["role"] == "stability_gate"
    assert imaginary["min"] == 0
    assert imaginary["max"] == 0
    assert entropy["type"] == "maximize_bounded"
    assert entropy["lower"] == 50.0
    assert entropy["upper"] == 80.0
    assert score_constraint({"entropy_298_per_heavy_atom": 43.397}, entropy) == 0.0
    assert score_constraint({"entropy_298_per_heavy_atom": 65.298}, entropy) == pytest.approx(0.509933, rel=1e-4)
    assert score_constraint({"entropy_298_per_heavy_atom": 75.229}, entropy) == pytest.approx(0.840967, rel=1e-4)

    polarizability = next(
        item
        for item in tasks["xtb_polarizability_dipole_opt_009"]["constraints"]
        if item["property"] == "polarizability_per_heavy_atom"
    )
    solvation = next(
        item
        for item in tasks["xtb_solvation_selectivity_alpb_010"]["constraints"]
        if item["property"] == "alpb_water_hexane_selectivity"
    )
    electrophilicity = next(
        item
        for item in tasks["xtb_electrophilicity_max_011"]["constraints"]
        if item["property"] == "global_electrophilicity"
    )
    fukui = next(
        item
        for item in tasks["xtb_fukui_carbon_site_012"]["constraints"]
        if item["property"] == "max_f_plus_on_carbon"
    )
    assert polarizability["lower"] == 4.0
    assert polarizability["upper"] == 12.0
    assert solvation["lower"] == 0.0
    assert solvation["upper"] == 1.5
    assert electrophilicity["lower"] == 0.5
    assert electrophilicity["upper"] == 4.0
    assert fukui["lower"] == 0.05
    assert fukui["upper"] == 0.35
```

- [ ] **Step 2: Add the missing pytest import**

At the top of `tests/test_xtb_xyz_tasks.py`, add:

```python
import pytest
```

- [ ] **Step 3: Run the new test to verify it fails**

Run:

```bash
uv run pytest tests/test_xtb_xyz_tasks.py::test_xtb_advanced_tasks_use_calibrated_tightened_thresholds -q
```

Expected: FAIL because `xtb_lumo_min_008` still has `lower: -4.0`, `upper: 1.0`, and `xtb_hessian_thermo_stability_013` still has `lower: 5.0`, `upper: 18.0`.

## Task 2: Update Task Thresholds

**Files:**
- Modify: `tasks/xtb_xyz/tasks.yaml`
- Modify: `tests/test_xtb_xyz_tasks.py`

- [ ] **Step 1: Update `xtb_lumo_min_008` thresholds**

In `tasks/xtb_xyz/tasks.yaml`, update the `lumo_energy` constraint under `xtb_lumo_min_008`:

```yaml
      - type: minimize_bounded
        property: lumo_energy
        verifier_id: xtb_lumo_gfn2_v1
        lower: -9.0
        upper: -5.0
```

- [ ] **Step 2: Update `xtb_hessian_thermo_stability_013` entropy thresholds**

In `tasks/xtb_xyz/tasks.yaml`, update the `entropy_298_per_heavy_atom` constraint under `xtb_hessian_thermo_stability_013`:

```yaml
      - type: maximize_bounded
        property: entropy_298_per_heavy_atom
        verifier_id: xtb_hessian_thermo_gfn2_v1
        lower: 50.0
        upper: 80.0
```

- [ ] **Step 3: Run the threshold regression test**

Run:

```bash
uv run pytest tests/test_xtb_xyz_tasks.py::test_xtb_advanced_tasks_use_calibrated_tightened_thresholds -q
```

Expected: PASS.

- [ ] **Step 4: Run xTB task metadata tests**

Run:

```bash
uv run pytest tests/test_xtb_xyz_tasks.py tests/test_xtb_calibration_inputs.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit threshold changes**

Run:

```bash
git add tests/test_xtb_xyz_tasks.py tasks/xtb_xyz/tasks.yaml
git commit -m "test: tighten calibrated xtb thresholds"
```

## Task 3: Verification and Handoff

**Files:**
- Read-only verification.

- [ ] **Step 1: Run the full test suite**

Run:

```bash
uv run pytest
```

Expected: PASS.

- [ ] **Step 2: Run optional live calibration spot check**

Run:

```bash
uv run python scripts/run_xtb_calibration.py \
  --answers tasks/xtb_xyz/calibration_answers.jsonl \
  --output artifacts/xtb_calibration/2026-06-17-thresholds/results.json
```

Expected: exit code `0` when xTB is installed. Do not commit generated files under `artifacts/`.

- [ ] **Step 3: Confirm generated artifacts are not staged**

Run:

```bash
git status --short
git diff --cached --name-only
```

Expected: no staged files under `artifacts/`.

## Self-Review

- Spec coverage: The plan implements threshold changes only for tasks explicitly marked `tighten_thresholds` in the calibration reliability report.
- Scope check: Tasks 9-12 stay unchanged because the report says they need stronger positive controls, not threshold changes.
- Type consistency: The test values use existing task property names: `lumo_energy`, `entropy_298_per_heavy_atom`, `imaginary_frequency_count`, `polarizability_per_heavy_atom`, `alpb_water_hexane_selectivity`, `global_electrophilicity`, and `max_f_plus_on_carbon`.
- Verification: The plan uses TDD for task threshold changes and keeps raw calibration artifacts uncommitted.
