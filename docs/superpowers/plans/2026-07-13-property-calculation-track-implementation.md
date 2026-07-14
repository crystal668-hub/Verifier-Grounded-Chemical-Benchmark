# Property-Calculation Track Implementation Plan

> **For implementers:** Execute one task at a time, use red-green tests, run
> the full suite before every commit, and preserve the existing
> open-generation path byte-for-byte unless a step explicitly changes a shared
> contract.

**Goal:** Implement the independent `property_calculation` track and add expert
Tasks 7-8 as self-contained English text tasks with public gold answers,
machine scoring, and the existing benchmark envelope/result/CLI contracts.

**Architecture:** Dispatch on `task_type` after common answer normalization and
before open-generation constraint validation. A dedicated pure-Python gold
comparison module validates property answer shapes, exact canonical units,
absolute tolerances, categorical mappings, and comparison groups. The track
uses the existing registry and `Track` APIs with an empty `verifiers: []` file;
no verifier script runs while model answers are scored.

**Tech Stack:** Python 3.12, pytest, PyYAML, JSONL, the current benchmark
package APIs, and optional pymatgen only for authoring-time CIF validation.

---

## Fixed Task and Track Contract

| Expert task | Task id | Answer shape |
|---|---|---|
| 7 | `property_calc_free_energy_001` | top-level `answer` and `unit` |
| 8 | `property_calc_crystal_phase_002` | top-level `answers` list |

Track files:

```text
tasks/property_calculation/
  tasks.yaml
  verifier_specs.yaml
  sample_answers.jsonl
```

Both tasks use:

```yaml
task_type: property_calculation
answer_schema:
  format: final_answer_line
  final_answer_prefix: "FINAL ANSWER:"
  value_type: json
  cardinality: one
```

The missing `task_type` default remains `open_generation`; no existing task
pack needs a migration.

## Task 1: Normalize Property-Calculation Answers

**Files:**

- Modify: `src/benchmark/answer_extraction.py`
- Create: `tests/test_property_answer_extraction.py`
- Modify: `tests/test_answer_extraction.py`

- [ ] **Step 1: Write failing Task 7 extraction tests**

For a raw response such as:

```text
FINAL ANSWER: {"answer":0.258031679,"unit":"kJ/mol"}
```

assert the normalized record is:

```json
{"task_id":"property_calc_free_energy_001","answer":0.258031679,"unit":"kJ/mol"}
```

while retaining `raw_answer` and `extracted_answer`. Test equivalent already
structured JSONL input, invalid JSON, non-object JSON, and a missing final
answer marker.

- [ ] **Step 2: Write failing Task 8 extraction tests**

Test the approved `answers` list shape, structured JSONL passthrough, and
malformed list entries. Missing named properties remain representable so the
evaluator can award the other comparison group; duplicate property names or
entries that are not mappings are parse errors.

- [ ] **Step 3: Run the red tests**

```bash
uv run pytest tests/test_property_answer_extraction.py \
  tests/test_answer_extraction.py -q
```

Expected: FAIL because raw JSON is still wrapped as `candidates[0].json` and
structured property records are unsupported.

- [ ] **Step 4: Add task-type-specific normalization**

At the start of `normalize_answer_record`, resolve:

```python
task_type = task.get("task_type", "open_generation")
```

Keep the current code path unchanged for `open_generation`. For
`property_calculation`, parse `value_type: json`, require a JSON mapping, and
unwrap it into canonical top-level `answer`/`unit` or `answers` fields. Preserve
the task id from the submission rather than trusting a nested JSON value.

Do not validate tolerances, units, completeness, or correctness in the
extractor; those belong to evaluation.

- [ ] **Step 5: Run focused and full tests**

```bash
uv run pytest tests/test_property_answer_extraction.py \
  tests/test_answer_extraction.py tests/test_xtb_answer_extraction.py -q
uv run pytest
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/benchmark/answer_extraction.py \
  tests/test_property_answer_extraction.py tests/test_answer_extraction.py
git commit -m "feat: normalize property calculation answers"
```

## Task 2: Implement Gold-Answer Comparison

**Files:**

- Create: `src/benchmark/property_calculation.py`
- Create: `tests/test_property_calculation_evaluator.py`

- [ ] **Step 1: Write failing single-property tests**

Construct in-memory Task 7 records and test:

- exact gold value;
- values exactly at both `0.001 kJ/mol` tolerance boundaries;
- values immediately outside both boundaries;
- wrong and missing units;
- missing answer;
- booleans, strings, NaN, and infinity as numeric values;
- wrong values return `status: ok` and score 0, not evaluator errors.

Canonical unit matching is exact and case-sensitive in version 1. Do not
convert meV, eV, joules, or alternate spellings.

- [ ] **Step 2: Write failing multi-property/group tests**

For Task 8, define two equal comparison groups:

```yaml
scoring:
  aggregation: arithmetic_mean
  comparison_groups:
    - id: numeric
      mode: all
    - id: phase_mapping
      mode: all
```

Each requested property names its `comparison_group`. Test all final scores:

- numeric and both phases correct: `1.0`;
- numeric only correct: `0.5`;
- both phases only correct: `0.5`;
- one phase wrong or missing: phase group `0`, even if the other is correct;
- neither group correct: `0.0`.

Test `0.079 +/- 0.001 eV` inclusively and require exact lowercase `alpha` and
`beta` values.

- [ ] **Step 3: Write failing task-schema tests**

Reject malformed maintainer task data with a structured `task_error`:

- requested/gold property names do not match;
- duplicate requested or gold properties;
- missing or non-positive numeric tolerance;
- unknown comparison group;
- duplicate group ids;
- an aggregation other than the implemented `arithmetic_mean`;
- missing gold value or canonical unit for a numeric property.

- [ ] **Step 4: Run the red tests**

```bash
uv run pytest tests/test_property_calculation_evaluator.py -q
```

Expected: FAIL because the comparison module is absent.

- [ ] **Step 5: Implement a pure comparison module**

Expose one entry point:

```python
evaluate_property_calculation(answer: dict, task: dict) -> dict
```

Normalize submitted values by property name, compare each property, reduce
properties within a group using all-or-nothing semantics, then take the
arithmetic mean of the group scores. Keep helpers small and deterministic;
this module must not import or execute verifier scripts.

Return the standard result envelope:

```yaml
task_id: string
status: ok | error
canonical_smiles: null
properties:
  submitted_answers: mapping
  gold_answers: mapping
scores:
  validity_gate: 1.0
  domain_gate: 1.0
  constraint_scores: [group comparison mappings]
  property_score: number
  score: number
failure_type: null
message: null
versions:
  property_calculation_evaluator: 1
```

For a successfully parsed but incorrect answer, both gates remain 1 and the
comparison score is 0 or 0.5. Error envelopes keep the existing zero-gate
behavior.

- [ ] **Step 6: Run focused and full tests**

```bash
uv run pytest tests/test_property_calculation_evaluator.py -q
uv run pytest
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/benchmark/property_calculation.py \
  tests/test_property_calculation_evaluator.py
git commit -m "feat: compare property calculation answers"
```

## Task 3: Route Property Tasks Before Verifier Constraints

**Files:**

- Modify: `src/benchmark/evaluate.py`
- Modify: `tests/test_evaluate_routing.py`
- Modify: `tests/test_public_api.py`

- [ ] **Step 1: Write failing routing tests**

Assert:

- missing `task_type` follows the existing open-generation path;
- explicit `task_type: open_generation` follows the same path;
- `task_type: property_calculation` succeeds without `constraints` or specs;
- property tasks never call `run_verification_script`;
- unknown task types return `task_error`;
- raw-answer and already structured forms produce identical results;
- `evaluate_many`, summaries, coverage, Suite, and `EvaluationReport` work for
  property rows without special outer schemas.

- [ ] **Step 2: Add failing arithmetic-mean regression tests**

Extend `aggregate_scores` to support `arithmetic_mean` while preserving
`geometric_mean` as the default. Cover empty values, zero values, clamping, and
unknown aggregation errors. Even though the property module reduces comparison
groups directly, the common evaluator must recognize the schema's declared
aggregation consistently.

- [ ] **Step 3: Run the red tests**

```bash
uv run pytest tests/test_evaluate_routing.py tests/test_public_api.py -q
```

Expected: FAIL because constraints are required before task-type routing.

- [ ] **Step 4: Implement early dispatch**

After task lookup and common extraction, dispatch by `task_type` before reading
`constraints`:

```text
missing/open_generation -> current constraint and verifier-script path
property_calculation    -> evaluate_property_calculation
anything else           -> task_error
```

Preserve `raw_answer` and `extracted_answer` in both full results and summary
rows.

- [ ] **Step 5: Run focused and full tests**

```bash
uv run pytest tests/test_evaluate_routing.py tests/test_public_api.py \
  tests/test_verifier_script_runner.py -q
uv run pytest
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/benchmark/evaluate.py tests/test_evaluate_routing.py \
  tests/test_public_api.py
git commit -m "feat: route property calculation evaluation"
```

## Task 4: Add the Self-Contained Task 7 Record

**Files:**

- Create: `tasks/property_calculation/tasks.yaml`
- Create: `tasks/property_calculation/verifier_specs.yaml`
- Create: `tests/test_property_calculation_tasks.py`

**Authoring sources, never runtime inputs:**

- `/Users/xutao/Documents/bench-task/题目/7/ETDIAM01.cif`
- `/Users/xutao/Documents/bench-task/题目/7/ETDIAM18.cif`

- [ ] **Step 1: Write failing Task 7 data tests**

Assert the common envelope, `task_type`, answer schema, input objects,
requested property, public gold, tolerance, scoring group, failure policy, and
withheld provenance marker. Assert:

- object ids are `ETDIAM01` and `ETDIAM18`;
- each `input_objects[].value` is nonempty CIF text and appears verbatim in the
  English prompt;
- the prompt contains no file path, upload, attachment, tool name, gold value,
  or gold-generation protocol;
- the prompt requests the absolute 300 K difference in `kJ/mol`;
- gold is exactly `0.258031679 kJ/mol` with absolute tolerance `0.001`;
- neither the prompt nor accepted-answer contract offers meV as a final unit.

- [ ] **Step 2: Run the red test**

```bash
uv run pytest tests/test_property_calculation_tasks.py -q
```

Expected: FAIL because the task pack is absent.

- [ ] **Step 3: Copy complete CIF text into task data and prompt**

Normalize source line endings to LF once. Copy all 43 lines of each source CIF
into its `input_objects[].value` block scalar and again into the labeled fenced
`cif` blocks in `prompt`. Do not use paths, YAML placeholders, runtime string
substitution, or an attachment loader.

Create `verifier_specs.yaml` with exactly:

```yaml
verifiers: []
```

- [ ] **Step 4: Validate the available CIFs with the materials test group**

Use pymatgen in the authoring test to parse both Task 7 CIF values and check
labels, atom counts, compositions, and finite positive cell volumes. Extend the
same test to all four values when Task 8 is added. Keep pymatgen out of the
scoring runtime imports.

```bash
uv run --group materials pytest tests/test_property_calculation_tasks.py -q
uv run pytest
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tasks/property_calculation/tasks.yaml \
  tasks/property_calculation/verifier_specs.yaml \
  tests/test_property_calculation_tasks.py
git commit -m "feat: add crystal free-energy task"
```

## Task 5: Add the Self-Contained Task 8 Record

**Files:**

- Modify: `tasks/property_calculation/tasks.yaml`
- Modify: `tests/test_property_calculation_tasks.py`

**Authoring sources, never runtime inputs:**

- `/Users/xutao/Documents/bench-task/题目/8/alpha_CONTCAR.cif`
- `/Users/xutao/Documents/bench-task/题目/8/beta_CONTCAR.cif`

- [ ] **Step 1: Write failing Task 8 data tests**

Assert:

- both complete structure-bearing CIF values occur verbatim in the English
  prompt under stable outer labels `alpha_CONTCAR` and `beta_CONTCAR`;
- the prompt contains no external paths or attachment instructions;
- requested properties are numeric difference, ambient phase, and high-pressure
  phase, assigned to the approved two comparison groups;
- public gold is `0.079 eV`, ambient `alpha`, and high-pressure `beta`;
- numeric absolute tolerance is `0.001 eV`;
- the numeric and all-or-nothing phase groups are equally aggregated;
- neither public gold values nor gold-generation details occur in the prompt.

- [ ] **Step 2: Run the red test**

```bash
uv run --group materials pytest tests/test_property_calculation_tasks.py -q
```

Expected: FAIL because Task 8 is absent.

- [ ] **Step 3: Add Task 8 with complete inline structure CIFs**

Normalize line endings to LF and copy the 132 structure-bearing lines from each
source. Omit the 15-line CCDC boilerplate comment header because it carries no
crystal structure data. Preserve the CIF data block even though both internal
blocks use `data_VESTA_phase_1`; the outer object ids and prompt labels
disambiguate them. Keep Task 8 as one task and use the approved `answers` list
example.

- [ ] **Step 4: Run focused and full tests**

```bash
uv run --group materials pytest tests/test_property_calculation_tasks.py -q
uv run pytest
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tasks/property_calculation/tasks.yaml \
  tests/test_property_calculation_tasks.py
git commit -m "feat: add crystal phase calculation task"
```

## Task 6: Register and Package the Track

**Files:**

- Modify: `src/verifier_grounded_benchmark/registry.py`
- Modify: `pyproject.toml`
- Create: `tasks/property_calculation/sample_answers.jsonl`
- Modify: `tests/test_registry.py`
- Modify: `tests/test_public_api.py`
- Modify: `tests/test_packaging.py`
- Modify: `tests/test_installed_wheel.py`

- [ ] **Step 1: Write failing registry tests**

Expect a third formal built-in definition:

```python
TrackDefinition(
    name="property_calculation",
    version="0.1.0",
    display_name="Fixed-input property calculation tasks",
    task_pack_path="tasks/property_calculation/tasks.yaml",
    verifier_specs_path="tasks/property_calculation/verifier_specs.yaml",
    sample_answers_path="tasks/property_calculation/sample_answers.jsonl",
    status="formal",
    tags=("property_calculation", "fixed_input", "crystal"),
)
```

Assert loading an empty verifier-spec mapping succeeds and does not weaken the
existing conflict checks for nonempty verifier specs. Explicitly assert
`vgb.load_track("property_calculation").verifier_specs_by_id == {}` rather than
requiring this track to expose a script.

- [ ] **Step 2: Write failing package and installed-wheel tests**

Require all three property track files in wheel and sdist. In an isolated
installed wheel, run:

```bash
vgb-score --track property_calculation \
  --answers <installed-or-test sample_answers.jsonl> --require-complete
```

and assert two correct rows, complete coverage, and benchmark score `1.0`.
The scoring smoke test must succeed without xTB, pymatgen, or a verifier script.

- [ ] **Step 3: Run the red tests**

```bash
uv run pytest tests/test_registry.py tests/test_public_api.py \
  tests/test_packaging.py tests/test_installed_wheel.py -q
```

Expected: FAIL because the track is not registered or packaged.

- [ ] **Step 4: Register, package, and add public sample answers**

Add the registry entry after RDKit and xTB. Force-include the entire
`tasks/property_calculation` directory. The two sample answers use the public
gold values and canonical structured JSONL shapes; they are public correctness
fixtures, not hidden evaluation data.

Update tests that hard-code the two-track list. Keep the existing API order
stable as `rdkit`, `xtb`, `property_calculation`.

- [ ] **Step 5: Run focused and full tests**

```bash
uv run pytest tests/test_registry.py tests/test_public_api.py \
  tests/test_packaging.py tests/test_installed_wheel.py -q
uv run pytest
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/verifier_grounded_benchmark/registry.py pyproject.toml \
  tasks/property_calculation/sample_answers.jsonl tests/test_registry.py \
  tests/test_public_api.py tests/test_packaging.py tests/test_installed_wheel.py
git commit -m "feat: register property calculation track"
```

## Task 7: Document the Track and Verify CLI Behavior

**Files:**

- Create: `docs/tracks/PropertyCalculation.md`
- Modify: `src/verifier_grounded_benchmark/README.md`
- Modify: `tests/test_evaluate_routing.py`

- [ ] **Step 1: Document the public contract**

Cover task position, fixed-input versus open-generation routing, canonical
answer shapes, exact-unit version-1 policy, binary absolute-tolerance behavior,
comparison groups, result fields, public gold policy, and the absence of
runtime verifier scripts. State that generation protocols are withheld in the
initial release without inventing provenance.

- [ ] **Step 2: Run raw-response and JSONL CLI checks**

Create temporary submissions in tests and manually verify both forms:

```bash
uv run vgb-score --track property_calculation \
  --answers tasks/property_calculation/sample_answers.jsonl \
  --require-complete
```

Assert score `1.0`, then perturb Task 8 numeric only and assert score `0.5`.
Test malformed JSON, wrong unit, missing Task 8 phase fields, duplicate ids,
unknown ids, and incomplete coverage.

- [ ] **Step 3: Verify all suites**

```bash
uv run pytest tests/test_evaluate_routing.py tests/test_public_api.py \
  tests/test_installed_wheel.py -q
uv run pytest
uv build
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add docs/tracks/PropertyCalculation.md \
  src/verifier_grounded_benchmark/README.md tests/test_evaluate_routing.py
git commit -m "docs: document property calculation track"
```

## Task 8: Final End-to-End Audit

- [ ] Confirm `vgb.list_tracks()` returns all three formal tracks in stable
  order.
- [ ] Confirm `vgb.load_suite()` includes both property tasks without verifier
  spec conflicts.
- [ ] Confirm `Track.prompts()` exposes only English self-contained text, not
  `input_objects` or gold metadata.
- [ ] Confirm all four structured CIF values occur verbatim in their prompts
  and no prompt contains an authoring path.
- [ ] Confirm Task 7 tolerance edges and all Task 8 scores `0`, `0.5`, `1`.
- [ ] Confirm open-generation results and sample-answer scores are unchanged.
- [ ] Confirm wheels/sdists contain the three property task files and no source
  attachment dependency.
- [ ] Run `uv run pytest`, `uv build`, and the installed-wheel smoke test.
- [ ] Confirm `git status --short` is clean after the final commit.

## Completion Criteria

- `property_calculation` is a formal built-in track using the current task,
  registry, Suite, result, coverage, and CLI schemas.
- Missing `task_type` remains fully backward compatible with open generation.
- Task 7 accepts only `0.258031679 +/- 0.001 kJ/mol` under the canonical unit
  contract.
- Task 8 scores the `0.079 +/- 0.001 eV` dimension and the complete
  `alpha`/`beta` phase mapping equally within one task.
- Both prompts are English, tool-neutral, and contain complete structure-bearing
  inline CIF text; evaluation requires no uploads, paths, or attachment lookup.
- Gold values are public while initial generation protocols remain withheld.
- Incorrect but well-formed answers receive normal score rows; evaluator/task
  failures remain distinguishable through the standard failure taxonomy.
