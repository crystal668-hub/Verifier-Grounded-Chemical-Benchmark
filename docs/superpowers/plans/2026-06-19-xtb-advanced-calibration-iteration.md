# xTB Advanced Calibration Iteration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make xTB tasks `xtb_lumo_min_008` through `xtb_hessian_thermo_stability_013` reasonable, reliable, and discriminative by replacing weak calibration controls first and adjusting thresholds only when data supports it.

**Architecture:** Keep xTB verifier code, scoring aggregation, answer schema, and universal relaxation-energy quality gate unchanged unless a calibration run proves a verifier bug. Use existing real xTB calibration and real-dataset distribution artifacts to identify candidate controls, then update task YAML, calibration answers, manifest metadata, regression tests, and the calibration reliability report. Generated `artifacts/` outputs are evidence only and must not be committed.

**Tech Stack:** Python 3.12, pytest, PyYAML, JSONL, local xTB CLI 6.7.x via `scripts/run_xtb_calibration.py`, existing `benchmark.evaluate` task loader, and `verifiers.backends.rdkit_descriptors.score_constraint`.

---

## Scope and Evidence

Primary report: `docs/research/2026-06-15-xtb-calibration-reliability-report.md`.

Current status after the first threshold pass:

- `xtb_lumo_min_008`: threshold changed to `[-9.0, -5.0]`; positive scores around `0.860`, near-miss around `0.804`. This no longer saturates, but the near-miss is still too close to the positive control.
- `xtb_polarizability_dipole_opt_009`: report says `needs_more_positive_controls`; current nominal positive scores around `0.055` because its dipole falls outside the 3-8 D window, while the near-miss scores around `0.817`.
- `xtb_solvation_selectivity_alpb_010`: report says `needs_more_positive_controls`; current positive scores around `0.037`, and all nonnegative controls are far below the old `1.5 eV` saturation point.
- `xtb_electrophilicity_max_011`: report says `needs_more_positive_controls`; current positive scores around `0.498`, below the `0.6` promotion bar.
- `xtb_fukui_carbon_site_012`: report says `needs_more_positive_controls`; current nonbaseline candidates have weak or negative `f_plus_contrast`.
- `xtb_hessian_thermo_stability_013`: threshold changed to entropy per heavy atom `[50.0, 80.0]`; the old positive now scores `0.0`, so this task needs a stable high-entropy positive control.

Supporting distribution artifact: `artifacts/xtb_real_distribution/2026-06-15-rerun/`.

- `light_results.json`: 60/60 ok for gap, dipole, LUMO, polarizability, relaxation.
- `medium_results.json`: 60/60 ok for ALPB selectivity, electrophilicity, Fukui properties.
- `expensive_results.json`: 60/60 ok for entropy and imaginary frequency count.
- `sampled_records.jsonl`: source XYZ records for the distribution run.

## Acceptance Criteria

For tasks 8-13, final calibration should satisfy these checks unless the final report explicitly justifies a retained exception:

- Every task has at least one `positive_candidate`, one `near_miss`, and one `negative_baseline`.
- Positive controls are `status: ok` in real xTB calibration.
- Negative baselines remain either expected `domain_error` rows or low-score valid controls.
- No parser, xTB tool, timeout, or unexpected verifier errors appear for nonnegative controls.
- `xtb_lumo_min_008`: positive score should be >= `0.75`; near-miss should be between `0.2` and `0.7`, or the report must explain why a high near-miss remains intentionally challenging.
- `xtb_polarizability_dipole_opt_009`: positive score should be >= `0.6`; near-miss should be below the positive score; positive must satisfy dipole window and have high polarizability per heavy atom.
- `xtb_solvation_selectivity_alpb_010`: positive score should be >= `0.6` after either replacing the positive control or recalibrating the upper threshold from observed real xTB ALPB values; near-miss should stay below the positive score.
- `xtb_electrophilicity_max_011`: positive score should be >= `0.6`; near-miss should stay below the positive score.
- `xtb_fukui_carbon_site_012`: positive score should be >= `0.6` and require both `max_f_plus_on_carbon` and positive `f_plus_contrast`; near-miss should score lower because contrast or carbon-localized f+ is weaker.
- `xtb_hessian_thermo_stability_013`: positive score should be >= `0.6`, `imaginary_frequency_count == 0`, and `relaxation_energy <= 0.35`; near-miss should stay below positive due to entropy, stability, or geometry quality.

## File Structure

- Modify `tasks/xtb_xyz/tasks.yaml`: only update thresholds or prompt/domain text needed for tasks 8-13.
- Modify `tasks/xtb_xyz/calibration_answers.jsonl`: replace weak positive or near-miss controls for tasks 8-13 with validated XYZ controls.
- Modify `tasks/xtb_xyz/calibration_manifest.yaml`: keep metadata synchronized with calibration answers and document source/provenance for replaced controls.
- Modify `tests/test_xtb_calibration_inputs.py`: add metadata/role checks for task8-13 calibration controls and candidate IDs.
- Modify `tests/test_xtb_xyz_tasks.py`: add or update threshold regression tests for final task8-13 scoring decisions.
- Modify `docs/research/2026-06-15-xtb-calibration-reliability-report.md`: update recommendations, final data, and theoretical rationale.
- Create local generated artifacts under `artifacts/xtb_calibration/2026-06-19-advanced-iteration/`; do not stage or commit them.

## Task 1: Baseline Extraction and Candidate Shortlist

**Files:**
- Read: `artifacts/xtb_calibration/2026-06-17-post-threshold-rerun/results.json`
- Read: `artifacts/xtb_real_distribution/2026-06-15-rerun/*.json`
- Read: `artifacts/xtb_real_distribution/2026-06-15-rerun/sampled_records.jsonl`
- Create generated: `artifacts/xtb_calibration/2026-06-19-advanced-iteration/candidate_shortlist.json`

- [ ] **Step 1: Run xTB environment preflight**

Run:

```bash
uv run python scripts/check_xtb_env.py
```

Expected: exit code `0`, JSON `status: ok`, and `xtb_executable` pointing to a local xTB binary.

- [ ] **Step 2: Generate a candidate shortlist from existing artifacts**

Run this read-only Python extraction command:

```bash
python3 - <<'PY'
import json
from pathlib import Path

base = Path("artifacts/xtb_real_distribution/2026-06-15-rerun")
records = {}
for line in (base / "sampled_records.jsonl").read_text().splitlines():
    if line.strip():
        row = json.loads(line)
        records[row["record_id"]] = row

tiers = {}
for filename in ["light_results.json", "medium_results.json", "expensive_results.json"]:
    payload = json.loads((base / filename).read_text())
    for row in payload["rows"]:
        entry = tiers.setdefault(row["record_id"], {})
        entry.update(row.get("properties") or {})

joined = []
for record_id, record in records.items():
    props = tiers.get(record_id, {})
    joined.append({"record_id": record_id, "record": record, "properties": props})

def domain_ok(record, *, heavy_min=4, heavy_max=40, carbon_min=0, hetero_min=0):
    return (
        heavy_min <= int(record["heavy_atom_count"]) <= heavy_max
        and int(record["carbon_count"]) >= carbon_min
        and int(record["hetero_atom_count"]) >= hetero_min
    )

shortlist = {
    "xtb_lumo_min_008": sorted(
        [
            item for item in joined
            if domain_ok(item["record"], heavy_min=8, heavy_max=40, carbon_min=4, hetero_min=2)
            and "lumo_energy" in item["properties"]
            and float(item["properties"]["relaxation_energy"]) <= 0.35
        ],
        key=lambda item: item["properties"]["lumo_energy"],
    )[:10],
    "xtb_polarizability_dipole_opt_009": sorted(
        [
            item for item in joined
            if domain_ok(item["record"], heavy_min=8, heavy_max=40, carbon_min=4, hetero_min=2)
            and int(item["record"]["heavy_element_diversity"]) >= 2
            and 3.0 <= float(item["properties"].get("dipole_moment", -999)) <= 8.0
            and float(item["properties"].get("relaxation_energy", 999)) <= 0.35
        ],
        key=lambda item: item["properties"].get("polarizability_per_heavy_atom", -999),
        reverse=True,
    )[:10],
    "xtb_solvation_selectivity_alpb_010": sorted(
        [
            item for item in joined
            if domain_ok(item["record"], heavy_min=8, heavy_max=36, carbon_min=3, hetero_min=3)
            and float(item["properties"].get("relaxation_energy", 999)) <= 0.35
        ],
        key=lambda item: item["properties"].get("alpb_water_hexane_selectivity", -999),
        reverse=True,
    )[:10],
    "xtb_electrophilicity_max_011": sorted(
        [
            item for item in joined
            if domain_ok(item["record"], heavy_min=8, heavy_max=40, carbon_min=4, hetero_min=2)
            and float(item["properties"].get("relaxation_energy", 999)) <= 0.35
        ],
        key=lambda item: item["properties"].get("global_electrophilicity", -999),
        reverse=True,
    )[:10],
    "xtb_fukui_carbon_site_012": sorted(
        [
            item for item in joined
            if domain_ok(item["record"], heavy_min=8, heavy_max=32, carbon_min=5, hetero_min=2)
            and float(item["properties"].get("relaxation_energy", 999)) <= 0.35
        ],
        key=lambda item: (
            item["properties"].get("f_plus_contrast", -999),
            item["properties"].get("max_f_plus_on_carbon", -999),
        ),
        reverse=True,
    )[:10],
    "xtb_hessian_thermo_stability_013": sorted(
        [
            item for item in joined
            if domain_ok(item["record"], heavy_min=4, heavy_max=18, carbon_min=2, hetero_min=1)
            and int(item["properties"].get("imaginary_frequency_count", 999)) == 0
            and float(item["properties"].get("relaxation_energy", 999)) <= 0.35
        ],
        key=lambda item: item["properties"].get("entropy_298_per_heavy_atom", -999),
        reverse=True,
    )[:10],
}

out = Path("artifacts/xtb_calibration/2026-06-19-advanced-iteration/candidate_shortlist.json")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(shortlist, indent=2, sort_keys=True))
for task_id, rows in shortlist.items():
    print(task_id, len(rows))
    for row in rows[:5]:
        props = row["properties"]
        print(" ", row["record_id"], row["record"]["formula"], {
            key: props[key]
            for key in sorted(props)
            if key in {
                "lumo_energy",
                "polarizability_per_heavy_atom",
                "dipole_moment",
                "alpb_water_hexane_selectivity",
                "global_electrophilicity",
                "max_f_plus_on_carbon",
                "f_plus_contrast",
                "entropy_298_per_heavy_atom",
                "imaginary_frequency_count",
                "relaxation_energy",
            }
        })
PY
```

Expected: print at least one candidate for each task. If any task has no candidates, keep current calibration answer for that task and document the data gap in the report instead of inventing unsupported values.

- [ ] **Step 3: Inspect candidate shortlist**

Run:

```bash
jq 'to_entries[] | {task_id: .key, candidates: [.value[0:5][] | {record_id, formula: .record.formula, properties}]}' artifacts/xtb_calibration/2026-06-19-advanced-iteration/candidate_shortlist.json
```

Expected: task-level top candidates are visible with the properties needed to choose controls.

## Task 2: Add Calibration Quality Regression Tests

**Files:**
- Modify: `tests/test_xtb_calibration_inputs.py`

- [ ] **Step 1: Add tests that encode final calibration-control requirements**

Append this helper and test to `tests/test_xtb_calibration_inputs.py`:

```python
ADVANCED_TASK_IDS = {
    "xtb_lumo_min_008",
    "xtb_polarizability_dipole_opt_009",
    "xtb_solvation_selectivity_alpb_010",
    "xtb_electrophilicity_max_011",
    "xtb_fukui_carbon_site_012",
    "xtb_hessian_thermo_stability_013",
}


def test_xtb_advanced_calibration_manifest_records_curated_controls() -> None:
    answers = _load_answers()
    manifest = _load_manifest()

    for task_id in ADVANCED_TASK_IDS:
        task_answers = [answer for answer in answers if answer["task_id"] == task_id]
        roles = {answer["role"] for answer in task_answers}
        assert {"positive_candidate", "near_miss", "negative_baseline"}.issubset(roles), task_id

        positive_ids = [answer["candidate_id"] for answer in task_answers if answer["role"] == "positive_candidate"]
        assert len(positive_ids) >= 1, task_id
        for candidate_id in positive_ids:
            metadata = manifest["candidates"][candidate_id]
            assert metadata["expected_behavior"][task_id] in {"high_score", "medium_or_high_score"}
            assert metadata["source"]
            assert metadata["molecule_family"]

    curated_ids = {
        answer["candidate_id"]
        for answer in answers
        if answer["task_id"] in ADVANCED_TASK_IDS and answer["role"] in {"positive_candidate", "near_miss"}
    }
    assert any("qm9" in manifest["candidates"][candidate_id]["source"].lower() for candidate_id in curated_ids)
```

- [ ] **Step 2: Run the new test and verify RED**

Run:

```bash
uv run pytest tests/test_xtb_calibration_inputs.py::test_xtb_advanced_calibration_manifest_records_curated_controls -q
```

Expected: FAIL before calibration manifest sources are updated with at least one QM9-derived curated control.

## Task 3: Replace or Add Validated Calibration Controls

**Files:**
- Modify: `tasks/xtb_xyz/calibration_answers.jsonl`
- Modify: `tasks/xtb_xyz/calibration_manifest.yaml`
- Read: `artifacts/xtb_calibration/2026-06-19-advanced-iteration/candidate_shortlist.json`

- [ ] **Step 1: Choose controls from candidate shortlist**

For each task, select controls using these rules:

- Keep existing `negative_baseline` entries unless they stopped producing expected `domain_error`.
- Prefer QM9-derived candidates for task13 if they satisfy zero imaginary modes and relaxation quality.
- Prefer existing hand-curated high-performing controls over QM9 when QM9 distribution lacks enough advanced chemistry.
- For task9, select a positive candidate with dipole in `[3.0, 8.0]` and high polarizability per heavy atom.
- For task10, if observed ALPB selectivity values are all below `0.5 eV`, plan to recalibrate the upper threshold rather than pretending the old `1.5 eV` target is validated.
- For task12, select a positive candidate with both positive `f_plus_contrast` and high `max_f_plus_on_carbon`.

- [ ] **Step 2: Update calibration answers JSONL**

For every chosen replacement or added nonbaseline control, write one JSONL object with:

```json
{"task_id":"<task-id>","candidate_id":"<unique-id>","role":"positive_candidate","response":"<short rationale>\\nFINAL ANSWER:\\n```xyz\\n<XYZ>\\n```"}
```

Use exact XYZ from the chosen source record or a real xTB-optimized existing local sample. Preserve valid JSON escaping by using a small script or structured editor, not manual comma editing.

- [ ] **Step 3: Update calibration manifest**

For every changed or added control, add synchronized manifest metadata:

```yaml
  <candidate_id>:
    role: positive_candidate
    molecule_family: <specific_family>
    target_tasks: [<task-id>]
    expected_behavior:
      <task-id>: high_score
    source: "QM9 rerun record <record_id> from artifacts/xtb_real_distribution/2026-06-15-rerun, selected by 2026-06-19 advanced calibration iteration"
```

For retained hand-curated controls, keep the current source text unless the role or expectation changes.

- [ ] **Step 4: Run calibration input tests**

Run:

```bash
uv run pytest tests/test_xtb_calibration_inputs.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit calibration-control updates**

Run:

```bash
git add tests/test_xtb_calibration_inputs.py tasks/xtb_xyz/calibration_answers.jsonl tasks/xtb_xyz/calibration_manifest.yaml
git commit -m "test: curate xtb advanced calibration controls"
```

## Task 4: Calibrate Thresholds Against Validated Controls

**Files:**
- Modify: `tasks/xtb_xyz/tasks.yaml`
- Modify: `tests/test_xtb_xyz_tasks.py`
- Generated: `artifacts/xtb_calibration/2026-06-19-advanced-iteration/results-before-thresholds.json`
- Generated: `artifacts/xtb_calibration/2026-06-19-advanced-iteration/analysis-before-thresholds/`

- [ ] **Step 1: Run real calibration with curated controls**

Run:

```bash
uv run python scripts/run_xtb_calibration.py \
  --answers tasks/xtb_xyz/calibration_answers.jsonl \
  --output artifacts/xtb_calibration/2026-06-19-advanced-iteration/results-before-thresholds.json
uv run python scripts/analyze_xtb_calibration.py \
  --input artifacts/xtb_calibration/2026-06-19-advanced-iteration/results-before-thresholds.json \
  --output-dir artifacts/xtb_calibration/2026-06-19-advanced-iteration/analysis-before-thresholds
```

Expected: exit code `0` for both commands.

- [ ] **Step 2: Extract task8-13 scores and properties**

Run:

```bash
jq -r '.rows[] | select(.task_id|test("xtb_(lumo_min_008|polarizability_dipole_opt_009|solvation_selectivity_alpb_010|electrophilicity_max_011|fukui_carbon_site_012|hessian_thermo_stability_013)")) | [.task_id, .candidate_id, .role, .status, (.score|tostring), (.property_score|tostring), (.stability_gate_score|tostring), (.geometry_quality_score|tostring), (.properties.lumo_energy // ""), (.properties.polarizability_per_heavy_atom // ""), (.properties.dipole_moment // ""), (.properties.alpb_water_hexane_selectivity // ""), (.properties.global_electrophilicity // ""), (.properties.max_f_plus_on_carbon // ""), (.properties.f_plus_contrast // ""), (.properties.entropy_298_per_heavy_atom // ""), (.properties.imaginary_frequency_count // ""), (.properties.relaxation_energy // ""), (.failure_type // "")] | @tsv' \
  artifacts/xtb_calibration/2026-06-19-advanced-iteration/results-before-thresholds.json
```

Expected: nonnegative controls show concrete property values and no unexpected failures.

- [ ] **Step 3: Decide final thresholds**

Use this decision table:

- If positive and near-miss ordering is correct and positive score >= `0.6`, keep thresholds.
- If positive is valid but all scores are compressed below `0.6`, adjust bounded `lower`/`upper` to observed real xTB scale from calibration controls and QM9 distribution quantiles.
- If positive is below near-miss, replace controls before changing thresholds.
- If all available controls for a task remain weak, leave thresholds conservative and document the remaining data gap rather than overfitting.

- [ ] **Step 4: Write threshold regression test first**

Update `test_xtb_advanced_tasks_use_calibrated_tightened_thresholds` or add a new test in `tests/test_xtb_xyz_tasks.py` that asserts final threshold values for task8-13. Include `score_constraint` examples for every changed bounded constraint.

- [ ] **Step 5: Run threshold test and verify RED if thresholds changed**

Run:

```bash
uv run pytest tests/test_xtb_xyz_tasks.py::test_xtb_advanced_tasks_use_calibrated_tightened_thresholds -q
```

Expected: FAIL if tests assert new thresholds that are not yet present. If no thresholds changed, the existing test can remain green and this step documents that no YAML threshold edit is required.

- [ ] **Step 6: Update task thresholds**

Edit only the relevant constraints under task8-13 in `tasks/xtb_xyz/tasks.yaml`. Do not change verifier IDs, answer schema, or relaxation-energy gate.

- [ ] **Step 7: Run task tests**

Run:

```bash
uv run pytest tests/test_xtb_xyz_tasks.py tests/test_xtb_calibration_inputs.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit threshold updates**

Run:

```bash
git add tasks/xtb_xyz/tasks.yaml tests/test_xtb_xyz_tasks.py
git commit -m "test: recalibrate xtb advanced task thresholds"
```

If no threshold changes were needed, skip this commit and note that in the final report.

## Task 5: Final Real xTB Calibration and Report Update

**Files:**
- Modify: `docs/research/2026-06-15-xtb-calibration-reliability-report.md`
- Generated: `artifacts/xtb_calibration/2026-06-19-advanced-iteration/final-results.json`
- Generated: `artifacts/xtb_calibration/2026-06-19-advanced-iteration/final-analysis/`

- [ ] **Step 1: Run final real xTB calibration**

Run:

```bash
uv run python scripts/run_xtb_calibration.py \
  --answers tasks/xtb_xyz/calibration_answers.jsonl \
  --output artifacts/xtb_calibration/2026-06-19-advanced-iteration/final-results.json
uv run python scripts/analyze_xtb_calibration.py \
  --input artifacts/xtb_calibration/2026-06-19-advanced-iteration/final-results.json \
  --output-dir artifacts/xtb_calibration/2026-06-19-advanced-iteration/final-analysis
```

Expected: exit code `0` for both commands.

- [ ] **Step 2: Confirm task8-13 acceptance criteria**

Run:

```bash
jq -r '.rows[] | select(.task_id|test("xtb_(lumo_min_008|polarizability_dipole_opt_009|solvation_selectivity_alpb_010|electrophilicity_max_011|fukui_carbon_site_012|hessian_thermo_stability_013)")) | [.task_id, .candidate_id, .role, .status, (.score|tostring), (.property_score|tostring), (.stability_gate_score|tostring), (.geometry_quality_score|tostring), (.properties.lumo_energy // ""), (.properties.polarizability_per_heavy_atom // ""), (.properties.dipole_moment // ""), (.properties.alpb_water_hexane_selectivity // ""), (.properties.global_electrophilicity // ""), (.properties.max_f_plus_on_carbon // ""), (.properties.f_plus_contrast // ""), (.properties.entropy_298_per_heavy_atom // ""), (.properties.imaginary_frequency_count // ""), (.properties.relaxation_energy // ""), (.failure_type // "")] | @tsv' \
  artifacts/xtb_calibration/2026-06-19-advanced-iteration/final-results.json
cat artifacts/xtb_calibration/2026-06-19-advanced-iteration/final-analysis/summary.md
```

Expected: task8-13 show positive controls promoted above the target bar or have a report-justified exception.

- [ ] **Step 3: Update calibration reliability report**

Update `docs/research/2026-06-15-xtb-calibration-reliability-report.md` with:

- A new dated section for the 2026-06-19 advanced iteration.
- Commands used and artifact paths.
- A task8-13 before/after table with candidate IDs, roles, properties, and scores.
- Threshold changes and why they are chemically/data justified.
- Replaced or retained calibration-control rationale.
- Remaining limitations, especially if any task is still data-limited.

- [ ] **Step 4: Run documentation and targeted tests**

Run:

```bash
uv run pytest tests/test_xtb_xyz_tasks.py tests/test_xtb_calibration_inputs.py tests/test_xtb_calibration_scripts.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit report update**

Run:

```bash
git add docs/research/2026-06-15-xtb-calibration-reliability-report.md
git commit -m "docs: update xtb advanced calibration report"
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

- [ ] **Step 2: Confirm generated artifacts are not staged**

Run:

```bash
git status --short
git diff --cached --name-only
```

Expected: no staged files and no untracked non-ignored files. `artifacts/` may appear only as ignored output if checked with `--ignored`.

- [ ] **Step 3: Summarize final state**

Report:

- Plan path.
- Candidate-control changes by task.
- Threshold changes by task.
- Final calibration summary and task8-13 scores.
- Tests run and results.
- Commits created.
- Any remaining caveats that were intentionally retained.

## Self-Review

- Spec coverage: The plan covers task8-13, including threshold adjustment, positive-control replacement, final calibration, and report update.
- Scope control: Verifier code changes are intentionally out of scope unless real calibration reveals a verifier bug.
- Type consistency: Property names match existing specs: `lumo_energy`, `polarizability_per_heavy_atom`, `dipole_moment`, `alpb_water_hexane_selectivity`, `global_electrophilicity`, `max_f_plus_on_carbon`, `f_plus_contrast`, `entropy_298_per_heavy_atom`, `imaginary_frequency_count`, and `relaxation_energy`.
- TDD coverage: New calibration manifest quality requirements are tested before changing calibration controls; threshold tests are updated before YAML threshold edits.
- Artifact hygiene: Generated calibration outputs remain under ignored `artifacts/` and are not staged.
