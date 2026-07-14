# Expert Open-Generation Tasks Implementation Plan

> **For implementers:** Execute one task at a time. Keep tests red-green, run
> the full suite before each commit, and do not register an xTB task until its
> live-calibration gate passes.

**Goal:** Add expert Tasks 1-6 to the existing RDKit and xTB open-generation
tracks with exactly the approved constraints, scoring contracts, molecular
identity checks, and calibration gates.

**Architecture:** Extend shared scoring only for the new target-distance mode,
add a dedicated RDKit verifier domain for Task 1, and extend the existing xTB
backend with explicit electronic-state, exact-composition, total-energy, graph,
and stereochemistry capabilities. Build Tasks 2-6 first in an unregistered,
distribution-excluded calibration pack. Promote each task to the formal xTB
pack only after recorded live xTB evidence establishes its score bounds and
operational limits.

**Tech Stack:** Python 3.12, pytest, PyYAML, RDKit 2026.3.2, local xTB 6.7.1,
the existing verifier-script runner, and the existing task/answer schemas.

---

## Fixed Task Ids

| Expert task | Task id | Formal destination |
|---|---|---|
| 1 | `rdkit_logp_target_011` | `tasks/rdkit_baseline/tasks.yaml` |
| 2 | `xtb_formula_dipole_min_014` | `tasks/xtb_xyz/tasks.yaml` after calibration |
| 3 | `xtb_two_fluorine_gap_min_015` | `tasks/xtb_xyz/tasks.yaml` after calibration |
| 4 | `xtb_c10_f2_gap_min_016` | `tasks/xtb_xyz/tasks.yaml` after calibration |
| 5 | `xtb_roy_singlepoint_energy_min_017` | `tasks/xtb_xyz/tasks.yaml` after calibration |
| 6 | `xtb_ritonavir_optimized_energy_min_018` | `tasks/xtb_xyz/tasks.yaml` after calibration |

Tasks 2-6 must not be appended to the built-in formal pack with
`formal_track: false`. Current coverage counts every row in a registered task
pack, so candidate definitions live in a separate unregistered file until they
pass.

## Task 1: Add Target-Distance Scoring

**Files:**

- Modify: `src/verifiers/common/scoring.py`
- Modify: `src/benchmark/evaluate.py`
- Modify: `tests/test_small_molecule_rdkit.py`
- Modify: `tests/test_evaluate_routing.py`

- [ ] **Step 1: Write failing scoring tests**

Add tests for:

```python
constraint = {
    "type": "target_distance",
    "property": "logp",
    "target": 3.0,
    "scale": 0.5,
}
```

Assert scores of `1.0` at `3.0`, `exp(-1)` at `2.5` and `3.5`, symmetry
around the target, and `ValueError` for a non-positive scale. Add a routing
test proving a repeated verifier result can be reused for this constraint
type.

- [ ] **Step 2: Run the red tests**

```bash
uv run pytest tests/test_small_molecule_rdkit.py tests/test_evaluate_routing.py -q
```

Expected: FAIL because `target_distance` is unsupported.

- [ ] **Step 3: Implement the scoring mode**

In `score_constraint`, implement exactly:

```text
exp(-abs(value - target) / scale)
```

Reject `scale <= 0` and keep the return value clamped to `[0, 1]`. Add
`target_distance` to `REUSABLE_CONSTRAINT_TYPES`; do not change the behavior
of the existing three modes.

- [ ] **Step 4: Run focused and full tests**

```bash
uv run pytest tests/test_small_molecule_rdkit.py tests/test_evaluate_routing.py -q
uv run pytest
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/verifiers/common/scoring.py src/benchmark/evaluate.py \
  tests/test_small_molecule_rdkit.py tests/test_evaluate_routing.py
git commit -m "feat: add target-distance constraint scoring"
```

## Task 2: Support the Task 1 RDKit Domain

**Files:**

- Modify: `src/verifiers/rdkit_descriptors/backend.py`
- Modify: `tests/test_rdkit_descriptor_backend.py`

- [ ] **Step 1: Write failing domain tests**

Test a dedicated spec whose domain contains only:

```yaml
allowed_elements: [H, C, O, N, S, F, Cl]
atom_count: [1, 40]
element_fraction_min:
  O: 0.10
```

Cover implicit-H expansion, exactly 40 versus 41 total atoms, oxygen fraction
exactly 0.10, a value just below 0.10, disallowed elements, and a charged
molecule. The charged molecule must not fail merely because it is charged.
Assert returned diagnostic properties include total atom count, per-element
counts, and oxygen fraction.

- [ ] **Step 2: Run the red tests**

```bash
uv run pytest tests/test_rdkit_descriptor_backend.py -q
```

Expected: FAIL because the backend assumes heavy-atom, MW, and charge ranges.

- [ ] **Step 3: Generalize optional domain checks narrowly**

Build element counts from `Chem.AddHs(mol)` and expose:

- `atom_count`
- `element_counts`
- `element_fractions`
- existing heavy-atom, MW, and charge values

Make each domain key optional. Implement `atom_count` and
`element_fraction_min` checks without injecting missing baseline keys. Keep
existing RDKit tasks unchanged under their current specs.

- [ ] **Step 4: Run focused and full tests**

```bash
uv run pytest tests/test_rdkit_descriptor_backend.py tests/test_small_molecule_rdkit.py -q
uv run pytest
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/verifiers/rdkit_descriptors/backend.py \
  tests/test_rdkit_descriptor_backend.py
git commit -m "feat: support total-atom rdkit domains"
```

## Task 3: Add Expert Task 1 to the RDKit Track

**Files:**

- Modify: `tasks/rdkit_baseline/tasks.yaml`
- Modify: `tasks/rdkit_baseline/verifier_specs.yaml`
- Modify: `tests/test_small_molecule_rdkit.py`
- Modify: `docs/tracks/RDKit.md`

- [ ] **Step 1: Write failing task-pack tests**

Assert `rdkit_logp_target_011` uses the shared SMILES answer schema, contains
only the approved element/total-atom/oxygen-fraction gates, and uses:

```yaml
type: target_distance
property: logp
target: 3.0
scale: 0.5
```

Assert the English prompt defines the denominator as all atoms after adding
implicit hydrogen and does not mention RDKit, verifier internals, neutrality,
closed shell, MW, or heavy-atom limits.

- [ ] **Step 2: Run the red test**

```bash
uv run pytest tests/test_small_molecule_rdkit.py -q
```

Expected: FAIL because the task and dedicated verifier spec are absent.

- [ ] **Step 3: Add the task and dedicated verifier spec**

Add `rdkit_logp_expert_v1`, reusing the existing logP script but using only the
approved domain. Do not alter `rdkit_logp_v1`, because its baseline domain is
still required by existing tasks.

- [ ] **Step 4: Update track documentation and verify**

```bash
uv run pytest tests/test_small_molecule_rdkit.py tests/test_rdkit_task_scripts.py -q
uv run pytest
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tasks/rdkit_baseline/tasks.yaml \
  tasks/rdkit_baseline/verifier_specs.yaml tests/test_small_molecule_rdkit.py \
  docs/tracks/RDKit.md
git commit -m "feat: add expert logp target task"
```

## Task 4: Add Exact xTB Composition and Electronic-State Validation

**Files:**

- Modify: `src/verifiers/xtb/backend.py`
- Modify: `tests/test_xtb_properties_backend.py`

- [ ] **Step 1: Write failing composition tests**

Cover these domain keys without changing existing keys:

```yaml
formula: C12H16N3O8
element_count_exact: {F: 2}
element_count_max: {C: 10}
```

Test exact matches, off-by-one failures, elements absent from the submitted
XYZ, and error messages that identify the failed field. Add `element_counts`
to `inspect_xyz` rather than reparsing the formula string.

- [ ] **Step 2: Write failing charge/spin tests**

Add tests for the exact XYZ comment syntax `charge=<integer>`. Reject extra
tokens, missing values, non-integers, and that syntax on tasks not configured
for candidate-declared charge. Test:

- fixed Task 2 state: charge 0, UHF 1, 173 electrons;
- candidate-declared Tasks 3-4 charge with fixed UHF 0;
- even electron count accepted for UHF 0;
- odd electron count rejected for UHF 0;
- the resolved charge reaches both `--chrg` and the result properties.

- [ ] **Step 3: Run the red tests**

```bash
uv run pytest tests/test_xtb_properties_backend.py -q
```

Expected: FAIL because exact counts and dynamic charge are unsupported.

- [ ] **Step 4: Implement explicit state resolution**

Add focused helpers such as:

```python
parse_xyz_charge(comment: str) -> int
resolve_electronic_state(molecule, task, spec) -> ElectronicState
electron_count(molecule, charge: int) -> int
```

Use a copied per-candidate spec/backend mapping when invoking xTB; never mutate
the registry-loaded spec. A task configured with `charge_source: xyz_comment`
must use the exact comment syntax and fixed `uhf: 0`. Other existing tasks keep
their fixed spec charge and may use arbitrary comments.

- [ ] **Step 5: Run focused and full tests**

```bash
uv run pytest tests/test_xtb_properties_backend.py tests/test_xtb_quality_gate_regression.py -q
uv run pytest
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/verifiers/xtb/backend.py tests/test_xtb_properties_backend.py
git commit -m "feat: validate xtb composition and electronic state"
```

## Task 5: Add Molecular Identity and Stereochemistry Gates

**Files:**

- Create: `src/verifiers/xtb/structure_identity.py`
- Modify: `src/verifiers/xtb/backend.py`
- Create: `tests/test_xtb_structure_identity.py`
- Modify: `tests/test_xtb_properties_backend.py`

- [ ] **Step 1: Write failing ROY identity tests**

Generate deterministic explicit-H conformers from:

```text
Cc1cc(c(s1)Nc2ccccc2[N+](=O)[O-])C#N
```

Test acceptance of an equivalent atom ordering and rejection of wrong formula,
disconnected fragments, and a same-formula connectivity change.

- [ ] **Step 2: Write failing Ritonavir identity tests**

Use the approved isomeric SMILES. Assert formula `C37H48N6O5S2`, 50 heavy
atoms, 98 total atoms, charge 0, and four specified stereocenters. Test
acceptance of the reference stereoisomer and rejection of one inverted center,
unspecified stereochemistry, a graph change, and a post-optimization structure
that no longer matches.

- [ ] **Step 3: Run the red tests**

```bash
uv run pytest tests/test_xtb_structure_identity.py \
  tests/test_xtb_properties_backend.py -q
```

Expected: FAIL because the identity module is absent.

- [ ] **Step 4: Implement graph reconstruction and comparison**

Keep the RDKit-specific reconstruction in `structure_identity.py`. Reconstruct
bonds from explicit-H XYZ coordinates with the task's declared total charge,
sanitize, remove H only for graph comparison, and compare against a reference
SMILES-derived graph. Compare assigned tetrahedral stereochemistry only when
the task supplies reference stereocenters. Return structured diagnostics for
formula, graph, charge, and stereochemistry.

Do not compare canonical SMILES strings without atom mapping as the sole graph
test. Add permutation tests to prove atom-order independence.

- [ ] **Step 5: Wire pre/post-calculation gates**

Run the identity gate before all calculations when `reference_smiles` exists.
For Task 6, load `xtbopt.xyz` and repeat identity/stereochemistry validation
before returning a score. Map identity failures to `domain_error`; malformed or
disconnected coordinates retain the existing parse/validity taxonomy.

- [ ] **Step 6: Run focused and full tests**

```bash
uv run pytest tests/test_xtb_structure_identity.py \
  tests/test_xtb_properties_backend.py tests/test_xtb_quality_gate_regression.py -q
uv run pytest
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/verifiers/xtb/structure_identity.py src/verifiers/xtb/backend.py \
  tests/test_xtb_structure_identity.py tests/test_xtb_properties_backend.py
git commit -m "feat: verify xtb molecular identity"
```

## Task 6: Add Submitted and Optimized Total-Energy Modes

**Files:**

- Modify: `src/verifiers/xtb/backend.py`
- Create: `src/verifiers/xtb/xtb_total_energy.py`
- Modify: `tests/test_xtb_properties_backend.py`
- Modify: `tests/test_xtb_task_scripts.py`

- [ ] **Step 1: Write failing calculation-mode tests**

Test `total_energy` with explicit `calculation_mode` values:

- `submitted_singlepoint`: exactly one single-point call, no optimization;
- `optimized`: exactly one optimization call, converged energy from that run;
- missing total energy or convergence marker: `verifier_tool_error`;
- unknown calculation mode: `verifier_spec_error`.

Return total energy in Hartree and record the unit. Do not convert or compare
energies across molecules.

- [ ] **Step 2: Run the red tests**

```bash
uv run pytest tests/test_xtb_properties_backend.py tests/test_xtb_task_scripts.py -q
```

Expected: FAIL because `total_energy` and its script are absent.

- [ ] **Step 3: Implement total-energy dispatch and script**

The single script fixes `property_name: total_energy`; separate verifier specs
later select submitted versus optimized mode. Preserve current optimized
property behavior for gap and dipole.

- [ ] **Step 4: Run focused and full tests**

```bash
uv run pytest tests/test_xtb_properties_backend.py tests/test_xtb_task_scripts.py -q
uv run pytest
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/verifiers/xtb/backend.py src/verifiers/xtb/xtb_total_energy.py \
  tests/test_xtb_properties_backend.py tests/test_xtb_task_scripts.py
git commit -m "feat: add xtb total-energy modes"
```

## Task 7: Build the Unregistered Expert xTB Calibration Pack

**Files:**

- Create: `tasks/xtb_xyz/expert_calibration/tasks.yaml`
- Create: `tasks/xtb_xyz/expert_calibration/verifier_specs.yaml`
- Create: `tasks/xtb_xyz/expert_calibration/answers.jsonl`
- Create: `tasks/xtb_xyz/expert_calibration/manifest.yaml`
- Modify: `pyproject.toml`
- Create: `tests/test_xtb_expert_calibration_inputs.py`
- Modify: `tests/test_packaging.py`

- [ ] **Step 1: Write failing pack tests**

Assert the five candidate tasks use the existing fenced explicit-H XYZ schema
and only the approved restrictions:

- Task 2: exact `C12H16N3O8`, charge 0, UHF 1;
- Task 3: at most 40 atoms, exactly two F, at most ten C, approved elements,
  comment-declared charge, UHF 0;
- Task 4: at most 40 atoms, exactly ten C and two F, approved elements,
  comment-declared charge, UHF 0;
- Task 5: ROY identity, charge 0, UHF 0, submitted-geometry single-point
  energy;
- Task 6: Ritonavir identity/stereochemistry, charge 0, UHF 0, optimized
  energy and post-check.

Assert no relaxation-energy gate, neutral restriction on Tasks 3-4, formula
denylist, extra heavy-atom bound, or neighboring-task domain is present.

- [ ] **Step 2: Run the red test**

```bash
uv run pytest tests/test_xtb_expert_calibration_inputs.py -q
```

Expected: FAIL because the calibration pack is absent.

- [ ] **Step 3: Add candidate verifier specs and inputs**

Keep candidate definitions and verifier specs together in the calibration
directory or allow the calibration runner to merge them with the formal specs.
Include multiple valid conformers and explicit negative controls for each task.
For Ritonavir include enough diverse conformers to exercise convergence and
stereochemical retention; do not publish those conformers as sample answers.

- [ ] **Step 4: Exclude the calibration directory from artifacts**

Add `/tasks/xtb_xyz/expert_calibration/` to Hatch exclusions and extend
packaging tests to prove no candidate task, answer, or manifest reaches wheels
or sdists.

- [ ] **Step 5: Run focused and full tests**

```bash
uv run pytest tests/test_xtb_expert_calibration_inputs.py tests/test_packaging.py -q
uv run pytest
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add tasks/xtb_xyz/expert_calibration pyproject.toml \
  tests/test_xtb_expert_calibration_inputs.py tests/test_packaging.py
git commit -m "test: add expert xtb calibration pack"
```

## Task 8: Extend Calibration Diagnostics and Run Live xTB

**Files:**

- Modify: `scripts/xtb_calibration/run_xtb_calibration.py`
- Modify: `scripts/xtb_calibration/analyze_xtb_calibration.py`
- Modify: `tests/test_xtb_calibration_scripts.py`
- Modify after calibration: `tasks/xtb_xyz/expert_calibration/tasks.yaml`
- Modify after calibration: `tasks/xtb_xyz/expert_calibration/verifier_specs.yaml`
- Create after the run: `docs/research/2026-07-13-expert-open-generation-xtb-calibration.md`

- [ ] **Step 1: Add failing diagnostic tests**

Require each row to record calculation mode, resolved charge/UHF, wall time,
convergence, identity before/after when applicable, and property value. Require
the summary to report per-task success rate, timeout count, runtime quantiles,
score/property ranges, and structure-retention failures. Record peak memory
when the platform runner can measure it; otherwise record it explicitly as
unavailable rather than silently omitting it.

- [ ] **Step 2: Implement diagnostics and verify scripts**

```bash
uv run pytest tests/test_xtb_calibration_scripts.py -q
uv run pytest
```

Expected: PASS.

- [ ] **Step 3: Commit the calibration tooling**

```bash
git add scripts/xtb_calibration tests/test_xtb_calibration_scripts.py
git commit -m "feat: report expert xtb calibration diagnostics"
```

- [ ] **Step 4: Run the local live calibration**

```bash
uv run python scripts/xtb_calibration/run_xtb_calibration.py \
  --tasks tasks/xtb_xyz/expert_calibration/tasks.yaml \
  --specs tasks/xtb_xyz/expert_calibration/verifier_specs.yaml \
  --answers tasks/xtb_xyz/expert_calibration/answers.jsonl \
  --output build/expert-xtb-calibration/results.json
uv run python scripts/xtb_calibration/analyze_xtb_calibration.py \
  --input build/expert-xtb-calibration/results.json \
  --output-dir build/expert-xtb-calibration/analysis
```

- [ ] **Step 5: Freeze bounds and operational gates**

For each task, record the observed property distribution, chosen
`minimize_bounded` lower/upper bounds, timeout, resource envelope, convergence
rate, and known limitations. Task 6 additionally needs a multi-conformer result
showing acceptable runtime, memory evidence, optimization convergence, graph
retention, and stereochemical retention.

Write the research report with aggregated evidence only. Do not publish the
candidate geometries or a gold-generation protocol.

- [ ] **Step 6: Run tests and commit the report/bounds**

```bash
uv run pytest
git add tasks/xtb_xyz/expert_calibration/tasks.yaml \
  tasks/xtb_xyz/expert_calibration/verifier_specs.yaml \
  docs/research/2026-07-13-expert-open-generation-xtb-calibration.md
git commit -m "docs: record expert xtb calibration"
```

## Task 9: Promote Passing xTB Tasks to the Formal Track

**Files:**

- Modify: `tasks/xtb_xyz/tasks.yaml`
- Modify: `tasks/xtb_xyz/verifier_specs.yaml`
- Modify: `tests/test_xtb_xyz_tasks.py`
- Modify: `docs/tracks/xTB.md`

- [ ] **Step 1: Apply the formalization decision explicitly**

For each Task 2-6, check the research report. Append only tasks whose gates are
marked passed. A failed Task 6 remains in the calibration pack and is reported
as deferred; do not weaken identity or resource gates merely to register it.

- [ ] **Step 2: Write failing formal-pack tests**

For promoted tasks, assert exact prompt wording, schema, constraints, frozen
bounds, verifier binding, charge/spin policy, and absence of extra restrictions.
Update existing tests that assumed every xTB task has a relaxation quality gate
so they distinguish legacy tasks from the expert tasks by contract.

- [ ] **Step 3: Add the task cards and verifier specs**

Promote by copying the reviewed candidate definitions and frozen values. Do
not hand-edit a second divergent version. Every prompt is English and
tool-neutral.

- [ ] **Step 4: Verify track, routing, coverage, and packaging**

```bash
uv run pytest tests/test_xtb_xyz_tasks.py tests/test_xtb_task_scripts.py \
  tests/test_evaluate_routing.py tests/test_registry.py tests/test_packaging.py -q
uv run pytest
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tasks/xtb_xyz/tasks.yaml tasks/xtb_xyz/verifier_specs.yaml \
  tests/test_xtb_xyz_tasks.py docs/tracks/xTB.md
git commit -m "feat: add calibrated expert xtb tasks"
```

## Task 10: Final End-to-End Verification

- [ ] Run `uv run pytest`.
- [ ] Run `uv build` and inspect the wheel/sdist exclusions.
- [ ] Run the existing RDKit sample answers through the `rdkit` track.
- [ ] Run public xTB showcase answers plus one accepted calibration candidate
  for every promoted expert task.
- [ ] Confirm `vgb list-tracks`, prompts, Suite coverage, result JSON, and CLI
  summaries remain compatible.
- [ ] Confirm `git status --short` contains only intended changes.
- [ ] Commit any integration fix separately after rerunning the full suite.

## Completion Criteria

- Task 1 is machine-scored in the formal RDKit track with all-atom oxygen
  fraction and the approved target-distance formula.
- Tasks 2-6 have the required backend capabilities and live calibration
  evidence.
- Every xTB task that passes calibration is in the formal xTB track with frozen
  bounds; every task that does not pass remains unregistered and explicitly
  documented.
- Tasks 3-4 accept charged closed-shell candidates through exact XYZ comment
  syntax and do not impose neutrality.
- Task 5 scores submitted-geometry single-point energy only.
- Task 6 optimizes before scoring and preserves Ritonavir graph and all four
  specified stereocenters.
- Existing RDKit/xTB task behavior, schemas, CLI output, coverage, and package
  contents remain regression-tested.
