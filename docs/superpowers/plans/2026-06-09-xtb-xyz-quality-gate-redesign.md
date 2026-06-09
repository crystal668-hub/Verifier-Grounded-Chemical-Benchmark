# xTB XYZ Quality Gate Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the xTB direct-XYZ task pack so relaxation energy becomes a universal geometry-quality gate and task 006 becomes a low-gap/high-dipole multi-objective optimization task.

**Architecture:** Keep the existing direct-XYZ contract and local xTB CLI backend. Extend the xTB backend and routing flow so every xTB XYZ task can combine one or more chemistry-property constraints with a relaxation-energy quality multiplier. Update task definitions, sample answers, and regression tests so simple common molecules no longer receive high scores merely by being easy optimized geometries.

**Tech Stack:** Python 3.12, PyYAML, pytest, RDKit periodic-table helpers, local xTB CLI 6.7.x, existing verifier scripts under `verifiers/xtb`.

---

## Design Rationale

### Why relaxation energy becomes a universal gate

For direct XYZ generation, the submitted coordinates are part of the answer. xTB optimization is allowed for measurement, but the benchmark should not reward a rough geometry that only becomes chemically reasonable after xTB repairs it. The relaxation energy

```text
relaxation_energy_eV = max(0, (E_input_Eh - E_optimized_Eh) * 27.211386245988)
```

measures how far the submitted XYZ is from the optimized local xTB structure. A smaller value means the model gave a geometry that is already close to a low-energy structure. Therefore `relaxation_energy` should be a common geometry-quality constraint for every xTB direct-XYZ task, not a standalone target task.

### Threshold basis for `lower: 0.0`, `upper: 0.35`

`lower: 0.0` is the natural lower bound because a successful geometry optimization should not need to lower the energy of an already optimized structure; any negative numerical artifact is clipped by the `max(0, ...)` definition.

`upper: 0.35 eV` is equivalent to:

```text
0.35 eV = 33.8 kJ/mol = 8.07 kcal/mol
```

This is a pragmatic first-version geometry-quality threshold:

- It is wider than the common CREST/xTB low-energy conformer window of about `6 kcal/mol`, so it does not demand perfectly optimized coordinates.
- It is still below broad conformer-generation windows around `10+ kcal/mol`, so it rejects clearly rough or strained input geometries.
- At 298 K, `RT` is about `0.593 kcal/mol`; `8.07 kcal/mol` is about `13.6 RT`, whose Boltzmann weight relative to a minimum is about `1.2e-6`. A structure this high in energy is not meaningfully populated as a low-energy conformer.

Implementation should treat `0.35 eV` as the default first-version gate, not as a universal physical constant. Later versions can add a per-heavy-atom relaxation term for larger and more flexible molecules.

### Scoring rule

Each task keeps its main property score, then multiplies it by a geometry-quality score:

```text
geometry_quality_score = clamp((0.35 - relaxation_energy) / 0.35, 0.0, 1.0)
final_score = property_score * geometry_quality_score
```

For multi-property tasks:

```text
property_score = geometric_mean(main_constraint_scores)
final_score = property_score * geometry_quality_score
```

Do not include relaxation energy as a normal objective in the geometric mean. It is a quality multiplier that can zero out rough geometry.

### Simple/common molecule exclusion

The redesign should prevent simple molecules such as water, methane, ammonia, carbon dioxide, hydrogen cyanide, formaldehyde, ethene, benzene, methanol, acetonitrile, and nitromethane from becoming high-scoring answers in optimization tasks.

Use two mechanisms:

1. Add structural-domain fields computed from the submitted XYZ atoms:
   - `carbon_count`
   - `hetero_atom_count`
   - `heavy_element_diversity`
   - `formula`
2. Add task-level nontriviality constraints:
   - minimum heavy atom count
   - minimum carbon count
   - minimum hetero atom count
   - formula denylist for known easy baselines

The formula denylist is a calibration guardrail, not a chemical-property target.

## File Structure

- Modify `verifiers/backends/xtb_properties.py`: compute structural-domain properties, evaluate relaxation quality scores for any xTB task, support `role: quality_gate`, and expose quality scores in result JSON.
- Modify `benchmark/evaluate.py`: aggregate main property constraints and relaxation quality gates separately so final score equals `property_score * geometry_quality_score`.
- Modify `tasks/xtb_xyz/tasks.yaml`: remove standalone relaxation task, add universal geometry-quality constraint to all tasks, replace task 006 with low-gap/high-dipole optimization, and add nontrivial structural-domain requirements.
- Modify `tasks/xtb_xyz/verifier_specs.yaml`: keep `xtb_relaxation_energy_gfn2_v1`, mark it as a quality verifier, and document the `0.35 eV` threshold.
- Modify `tasks/xtb_xyz/sample_answers.jsonl`: replace simple samples with nontrivial positive controls that score at least `0.6` after real xTB evaluation.
- Modify `tests/test_xtb_properties_backend.py`: cover structural-domain properties and quality-gate scoring.
- Modify `tests/test_xtb_xyz_tasks.py`: assert every xTB task has a relaxation quality gate, task 006 is low-gap/high-dipole, and no standalone relaxation task remains.
- Modify or create `tests/test_xtb_quality_gate_regression.py`: score fixed simple/common molecule baselines and assert they do not receive high scores.
- Modify `/Users/xutao/.agents/skills/xtb-cli-verifier/SKILL.md`: document relaxation energy as a universal geometry-quality gate and include the real sample-answer scoring command.

## Target Task Redesign

### Task `xtb_gap_window_001`

Keep it as a gap window task, but make it nontrivial.

```yaml
constraints:
  - type: window
    property: homo_lumo_gap
    verifier_id: xtb_gap_gfn2_v1
    min: 3.5
    max: 5.5
    sigma: 0.75
  - type: minimize_bounded
    property: relaxation_energy
    verifier_id: xtb_relaxation_energy_gfn2_v1
    role: quality_gate
    lower: 0.0
    upper: 0.35
structural_domain:
  heavy_atom_count: [6, 40]
  hetero_atom_count_min: 1
  formula_denylist: [H2O, CH4, NH3, CO2, HCN, CH2O, C2H4, C6H6]
```

### Task `xtb_dipole_window_002`

Make the window target a nontrivial polar molecule instead of water/ammonia/HCN.

```yaml
constraints:
  - type: window
    property: dipole_moment
    verifier_id: xtb_dipole_gfn2_v1
    min: 3.0
    max: 5.5
    sigma: 1.0
  - type: minimize_bounded
    property: relaxation_energy
    verifier_id: xtb_relaxation_energy_gfn2_v1
    role: quality_gate
    lower: 0.0
    upper: 0.35
structural_domain:
  heavy_atom_count: [5, 40]
  carbon_count_min: 2
  hetero_atom_count_min: 2
  formula_denylist: [H2O, NH3, HCN, CH2O, CH3NO2]
```

### Task `xtb_gap_max_003`

Raise the saturation point so simple saturated molecules do not automatically score `1.0`.

```yaml
constraints:
  - type: maximize_bounded
    property: homo_lumo_gap
    verifier_id: xtb_gap_gfn2_v1
    lower: 12.0
    upper: 20.0
  - type: minimize_bounded
    property: relaxation_energy
    verifier_id: xtb_relaxation_energy_gfn2_v1
    role: quality_gate
    lower: 0.0
    upper: 0.35
structural_domain:
  atom_count: [12, 80]
  heavy_atom_count: [8, 40]
  hetero_atom_count_min: 1
  heavy_element_diversity_min: 2
  formula_denylist: [H2O, CH4, NH3, CH4O, CH3F]
```

### Task `xtb_gap_min_004`

Keep it as low-gap optimization, but guard against rough-geometry artifacts.

```yaml
constraints:
  - type: minimize_bounded
    property: homo_lumo_gap
    verifier_id: xtb_gap_gfn2_v1
    lower: 0.0
    upper: 5.0
  - type: minimize_bounded
    property: relaxation_energy
    verifier_id: xtb_relaxation_energy_gfn2_v1
    role: quality_gate
    lower: 0.0
    upper: 0.35
structural_domain:
  heavy_atom_count: [8, 40]
  carbon_count_min: 4
  hetero_atom_count_min: 2
  formula_denylist: [CH2O, C2H4, C6H6, CH3NO2]
```

### Task `xtb_dipole_max_005`

Make low and moderate dipoles weak baselines rather than meaningful optimization success.

```yaml
constraints:
  - type: maximize_bounded
    property: dipole_moment
    verifier_id: xtb_dipole_gfn2_v1
    lower: 3.0
    upper: 10.0
  - type: minimize_bounded
    property: relaxation_energy
    verifier_id: xtb_relaxation_energy_gfn2_v1
    role: quality_gate
    lower: 0.0
    upper: 0.35
structural_domain:
  heavy_atom_count: [6, 40]
  carbon_count_min: 2
  hetero_atom_count_min: 2
  formula_denylist: [HCN, CH3CN, CH2O, CH3NO2]
```

### Task `xtb_low_gap_high_dipole_opt_006`

Replace `xtb_relaxation_energy_min_006` with a true multi-objective optimization task.

```yaml
task_id: xtb_low_gap_high_dipole_opt_006
constraints:
  - type: minimize_bounded
    property: homo_lumo_gap
    verifier_id: xtb_gap_gfn2_v1
    lower: 0.0
    upper: 5.0
  - type: maximize_bounded
    property: dipole_moment
    verifier_id: xtb_dipole_gfn2_v1
    lower: 3.0
    upper: 8.0
  - type: minimize_bounded
    property: relaxation_energy
    verifier_id: xtb_relaxation_energy_gfn2_v1
    role: quality_gate
    lower: 0.0
    upper: 0.35
scoring:
  aggregation: geometric_mean
structural_domain:
  heavy_atom_count: [8, 40]
  carbon_count_min: 4
  hetero_atom_count_min: 2
  formula_denylist: [HCN, CH2O, C2H4, C6H6, CH3CN, CH3NO2]
```

### Task `xtb_gap_dipole_window_007`

Keep it as a windowed multi-objective task, but raise the polarity requirement and narrow the gap window.

```yaml
constraints:
  - type: window
    property: homo_lumo_gap
    verifier_id: xtb_gap_gfn2_v1
    min: 2.5
    max: 4.2
    sigma: 0.75
  - type: window
    property: dipole_moment
    verifier_id: xtb_dipole_gfn2_v1
    min: 3.5
    max: 6.0
    sigma: 1.0
  - type: minimize_bounded
    property: relaxation_energy
    verifier_id: xtb_relaxation_energy_gfn2_v1
    role: quality_gate
    lower: 0.0
    upper: 0.35
structural_domain:
  heavy_atom_count: [8, 40]
  carbon_count_min: 4
  hetero_atom_count_min: 2
  formula_denylist: [HCN, CH2O, C2H4, C6H6, CH3CN, CH3NO2]
```

## Implementation Tasks

### Task 1: Add Structural Domain Properties

**Files:**
- Modify: `verifiers/backends/xtb_properties.py`
- Modify: `tests/test_xtb_properties_backend.py`

- [ ] **Step 1: Write failing tests for formula and structural counts**

Add tests that parse water, formaldehyde, acetonitrile, and a mixed heteroatom molecule. Assert:

```python
assert properties["formula"] == "H2O"
assert properties["carbon_count"] == 0
assert properties["hetero_atom_count"] == 1
assert properties["heavy_element_diversity"] == 1
```

For acetonitrile-like XYZ, assert formula `C2H3N`, carbon count `2`, hetero atom count `1`, and heavy element diversity `2`.

- [ ] **Step 2: Run red test**

Run:

```bash
uv run pytest tests/test_xtb_properties_backend.py::test_inspect_xyz_reports_structural_domain_properties -q
```

Expected: fail because these properties are not computed yet.

- [ ] **Step 3: Implement structural property calculation**

Update `inspect_xyz` to count atoms and return:

```python
"formula": hill_formula(counts),
"carbon_count": counts.get("C", 0),
"hetero_atom_count": sum(count for element, count in counts.items() if element not in {"H", "C"}),
"heavy_element_diversity": len({element for element in counts if element != "H"}),
```

Add `hill_formula(counts: dict[str, int]) -> str` using Hill ordering: `C`, `H`, then remaining elements alphabetically. Omit count when count is `1`.

- [ ] **Step 4: Run green test**

Run:

```bash
uv run pytest tests/test_xtb_properties_backend.py -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add verifiers/backends/xtb_properties.py tests/test_xtb_properties_backend.py
git commit -m "feat: add xtb xyz structural domain properties"
```

### Task 2: Enforce Structural Domain Constraints

**Files:**
- Modify: `verifiers/backends/xtb_properties.py`
- Modify: `tests/test_xtb_properties_backend.py`

- [ ] **Step 1: Write failing domain tests**

Add tests for:

- `carbon_count_min`
- `hetero_atom_count_min`
- `heavy_element_diversity_min`
- `formula_denylist`

Each failing molecule should return `domain_error` and include the violated field in `message`.

- [ ] **Step 2: Run red tests**

Run:

```bash
uv run pytest tests/test_xtb_properties_backend.py::test_xtb_property_enforces_nontrivial_structural_domain -q
```

Expected: fail because structural-domain keys are ignored.

- [ ] **Step 3: Implement domain checks**

Extend `check_domain`:

```python
if "carbon_count_min" in domain and properties["carbon_count"] < int(domain["carbon_count_min"]):
    return f"carbon_count below minimum {domain['carbon_count_min']}"
if "hetero_atom_count_min" in domain and properties["hetero_atom_count"] < int(domain["hetero_atom_count_min"]):
    return f"hetero_atom_count below minimum {domain['hetero_atom_count_min']}"
if "heavy_element_diversity_min" in domain and properties["heavy_element_diversity"] < int(domain["heavy_element_diversity_min"]):
    return f"heavy_element_diversity below minimum {domain['heavy_element_diversity_min']}"
if properties["formula"] in set(domain.get("formula_denylist", [])):
    return f"formula is denied: {properties['formula']}"
```

- [ ] **Step 4: Run green tests**

Run:

```bash
uv run pytest tests/test_xtb_properties_backend.py -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add verifiers/backends/xtb_properties.py tests/test_xtb_properties_backend.py
git commit -m "feat: enforce xtb xyz structural domain constraints"
```

### Task 3: Add Quality Gate Scoring Semantics

**Files:**
- Modify: `benchmark/evaluate.py`
- Modify: `verifiers/backends/xtb_properties.py`
- Modify: `tests/test_evaluate_routing.py`
- Modify: `tests/test_xtb_properties_backend.py`

- [ ] **Step 1: Write failing aggregation test**

Add a routing-level test with three fake verifier results:

```python
gap_score = 0.8
dipole_score = 0.5
quality_score = 0.5
expected = geometric_mean([0.8, 0.5]) * 0.5
```

Mark the relaxation constraint with:

```yaml
role: quality_gate
```

Assert final `scores.score` equals the expected value and `scores.geometry_quality_score == 0.5`.

- [ ] **Step 2: Run red test**

Run:

```bash
uv run pytest tests/test_evaluate_routing.py::test_aggregate_constraint_results_applies_quality_gate_multiplier -q
```

Expected: fail because quality gates are currently included as normal constraints or not distinguished.

- [ ] **Step 3: Implement quality-gate aggregation**

Update `aggregate_constraint_results` so constraint scores are split:

```python
quality_scores = [item["score"] for item in constraint_scores if item.get("role") == "quality_gate"]
main_scores = [item["score"] for item in constraint_scores if item.get("role") != "quality_gate"]
property_score = aggregate_scores(main_scores, aggregation)
geometry_quality_score = min(quality_scores) if quality_scores else 1.0
score = property_score * geometry_quality_score
```

Keep all constraint scores in the JSON output for transparency.

- [ ] **Step 4: Preserve quality role in verifier result**

In `evaluate_xtb_property_constraint`, include role when present:

```python
constraint_score = {
    "property": constraint["property"],
    "type": constraint["type"],
    "score": score_constraint(merged_properties, constraint),
}
if "role" in constraint:
    constraint_score["role"] = constraint["role"]
```

- [ ] **Step 5: Run green tests**

Run:

```bash
uv run pytest tests/test_evaluate_routing.py tests/test_xtb_properties_backend.py -q
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add benchmark/evaluate.py verifiers/backends/xtb_properties.py tests/test_evaluate_routing.py tests/test_xtb_properties_backend.py
git commit -m "feat: add verifier quality gate scoring"
```

### Task 4: Redesign xTB XYZ Task Pack

**Files:**
- Modify: `tasks/xtb_xyz/tasks.yaml`
- Modify: `tasks/xtb_xyz/verifier_specs.yaml`
- Modify: `tests/test_xtb_xyz_tasks.py`

- [ ] **Step 1: Write failing task-pack tests**

Update tests to assert:

- No task id contains `relaxation_energy_min`.
- `xtb_low_gap_high_dipole_opt_006` exists.
- Every task has exactly one `relaxation_energy` constraint with `role: quality_gate`, `lower: 0.0`, `upper: 0.35`.
- Optimization tasks include nontrivial structural-domain keys.
- Task 006 has both `homo_lumo_gap` minimize and `dipole_moment` maximize constraints.

- [ ] **Step 2: Run red tests**

Run:

```bash
uv run pytest tests/test_xtb_xyz_tasks.py -q
```

Expected: fail against the current task pack.

- [ ] **Step 3: Update verifier specs**

Keep `xtb_relaxation_energy_gfn2_v1`, but change the property notes to:

```yaml
property:
  role: geometry_quality_gate
  source: xTB input single-point energy minus optimized total energy
  units: eV
  notes: Used as a universal direct-XYZ geometry quality multiplier, not as a standalone chemistry target.
```

- [ ] **Step 4: Update tasks**

Apply the target redesign in the "Target Task Redesign" section above. Prompts must state the geometry-quality requirement in user-facing terms:

```text
The submitted XYZ should already be close to a low-energy xTB geometry; rough geometries that relax by more than about 0.35 eV will receive little or no credit.
```

Do not expose verifier IDs or scoring internals in prompts.

- [ ] **Step 5: Run green task tests**

Run:

```bash
uv run pytest tests/test_xtb_xyz_tasks.py -q
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add tasks/xtb_xyz/tasks.yaml tasks/xtb_xyz/verifier_specs.yaml tests/test_xtb_xyz_tasks.py
git commit -m "feat: redesign xtb xyz tasks with relaxation quality gate"
```

### Task 5: Replace Sample Answers With Nontrivial Positives

**Files:**
- Modify: `tasks/xtb_xyz/sample_answers.jsonl`
- Create: `scripts/check_xtb_xyz_samples.py`
- Modify: `tests/test_xtb_xyz_tasks.py`

- [ ] **Step 1: Create sample-check script test**

Add a test that runs:

```bash
uv run python scripts/check_xtb_xyz_samples.py
```

The script should exit `0` only when all sample answers score at least `0.6` with real xTB available. If xTB is missing, it should report `verifier_environment_error` and exit `1`.

- [ ] **Step 2: Implement sample-check script**

Create `scripts/check_xtb_xyz_samples.py` that loads `tasks/xtb_xyz/sample_answers.jsonl`, evaluates with `benchmark.evaluate.evaluate_many`, prints summary JSON, and fails if any row has `status != "ok"` or `score < 0.6`.

- [ ] **Step 3: Generate candidate positive XYZ files manually**

Use direct XYZ only. Do not generate 3D coordinates from SMILES for this track. Candidate families to try:

- substituted conjugated nitriles
- carbonyl nitriles
- nitro aromatics
- cyano-substituted heterocycles
- compact fluorinated carbonyls

For each candidate, run the real xTB harness:

```bash
uv run python scripts/score_answers.py --tasks tasks/xtb_xyz/tasks.yaml --specs tasks/xtb_xyz/verifier_specs.yaml --answers tasks/xtb_xyz/sample_answers.jsonl
```

- [ ] **Step 4: Replace sample answers**

Replace water, methane, HCN, formaldehyde, and ethene samples. Every sample should:

- be a fenced XYZ final answer
- satisfy structural-domain constraints
- have `relaxation_energy <= 0.35 eV`
- score at least `0.6`

- [ ] **Step 5: Run sample check**

Run:

```bash
uv run python scripts/check_xtb_xyz_samples.py
```

Expected: exit `0`; all rows `status: ok`; every score `>= 0.6`.

- [ ] **Step 6: Commit**

```bash
git add tasks/xtb_xyz/sample_answers.jsonl scripts/check_xtb_xyz_samples.py tests/test_xtb_xyz_tasks.py
git commit -m "test: add nontrivial xtb xyz sample checks"
```

### Task 6: Add Negative Baseline Regression

**Files:**
- Create: `tests/test_xtb_quality_gate_regression.py`

- [ ] **Step 1: Write baseline regression tests**

Add fixed XYZ baselines:

```text
water, methane, ammonia, carbon dioxide, HCN, formaldehyde, ethene, benzene, methanol, acetonitrile, nitromethane
```

For every optimization task, assert:

```python
assert result["status"] != "ok" or result["scores"]["score"] <= 0.35
```

For malformed and disconnected inputs, keep existing failure-type expectations.

- [ ] **Step 2: Run red test**

Run:

```bash
uv run pytest tests/test_xtb_quality_gate_regression.py -q
```

Expected: fail until task pack and scoring semantics are fully updated.

- [ ] **Step 3: Run green regression**

After Tasks 3-5, run:

```bash
uv run pytest tests/test_xtb_quality_gate_regression.py -q
```

Expected: pass.

- [ ] **Step 4: Commit**

```bash
git add tests/test_xtb_quality_gate_regression.py
git commit -m "test: guard xtb xyz tasks against simple baselines"
```

### Task 7: Update xTB CLI Skill

**Files:**
- Modify: `/Users/xutao/.agents/skills/xtb-cli-verifier/SKILL.md`

- [ ] **Step 1: Update skill body**

Add a section:

```markdown
## Direct-XYZ Geometry Quality Gate

For this benchmark, relaxation energy is a universal geometry-quality multiplier, not a standalone task objective. Run a single-point calculation on the submitted XYZ and an optimized calculation with `--opt`; compute:

relaxation_energy_eV = max(0, (E_input_Eh - E_optimized_Eh) * 27.211386245988)

Use lower 0.0 and upper 0.35 eV by default. Values above 0.35 eV should sharply reduce final score because the submitted XYZ was too rough.
```

Add the real sample validation command:

```bash
uv run python scripts/check_xtb_xyz_samples.py
```

- [ ] **Step 2: Validate skill frontmatter**

Run:

```bash
uv run python - <<'PY'
from pathlib import Path
import yaml
text = Path('/Users/xutao/.agents/skills/xtb-cli-verifier/SKILL.md').read_text()
data = yaml.safe_load(text.split('---\n', 2)[1])
assert data['name'] == 'xtb-cli-verifier'
assert 'xTB CLI verifier' in data['description']
assert 'Geometry Quality Gate' in text
PY
```

Expected: exit `0`.

### Task 8: Full Verification

**Files:**
- Modify only if failures reveal implementation mistakes.

- [ ] **Step 1: Run unit and routing tests**

Run:

```bash
uv run pytest
```

Expected: all tests pass.

- [ ] **Step 2: Run xTB environment check**

Run:

```bash
uv run python scripts/check_xtb_env.py
```

Expected on this machine: `status: ok`, `xtb_executable: /opt/homebrew/bin/xtb`, and parsed water smoke properties.

- [ ] **Step 3: Run real sample check**

Run:

```bash
uv run python scripts/check_xtb_xyz_samples.py
```

Expected: all sample answers `status: ok`, every score `>= 0.6`.

- [ ] **Step 4: Run simple-baseline regression**

Run:

```bash
uv run pytest tests/test_xtb_quality_gate_regression.py -q
```

Expected: pass; simple common molecules do not score above `0.35` on optimization tasks.

- [ ] **Step 5: Check git status**

Run:

```bash
git status --short --branch
```

Expected: only intended files are modified before final commit.

- [ ] **Step 6: Commit integration fixes**

If any integration fixes were required:

```bash
git add <changed-files>
git commit -m "fix: align xtb xyz quality gate integration"
```

## Acceptance Criteria

- `xtb_relaxation_energy_min_006` no longer exists.
- `xtb_low_gap_high_dipole_opt_006` exists and uses both low gap and high dipole main constraints.
- Every xTB XYZ task has a relaxation-energy quality gate with `lower: 0.0`, `upper: 0.35`, and `role: quality_gate`.
- Final scoring separates main property score from geometry quality score.
- Simple/common baselines do not score above `0.35` on optimization tasks.
- Every sample answer is nontrivial and scores at least `0.6` with real xTB CLI installed.
- `uv run pytest` passes.
- `uv run python scripts/check_xtb_env.py` passes on this machine.

