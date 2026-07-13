# Expert Sample Task Integration Design

**Date:** 2026-07-13

## Purpose

Integrate eight expert-authored chemistry and materials sample questions into
the benchmark plan without mixing open-generation scoring with fixed-answer
property calculation scoring. The design preserves the existing RDKit and xTB
track boundaries and completes the concrete property-calculation decisions
deferred by `2026-07-08-property-calculation-track-design.md`.

This document defines task placement, model-facing inputs, answer contracts,
scoring, evaluator routing, error behavior, calibration, and release gates. It
does not implement the tasks.

## Confirmed Global Decisions

- All model-facing tasks consist of one self-contained English text prompt.
- The benchmark does not require file uploads or attachment resolution.
- Any CIF input is copied in full into the prompt as standard CIF text.
- Model-facing prompts remain tool-neutral and do not name RDKit, xTB,
  verifier scripts, or gold-generation protocols.
- Expert restrictions are enforced as written. Additional chemical-domain
  restrictions are not imported from neighboring benchmark tasks.
- Where the expert prompt names a molecule or conformer, requiring one
  connected molecular graph and preserving the named structure is an object
  validity requirement, not an additional optimization constraint.
- Tasks are assigned by evaluation contract, not grouped into a mixed
  expert-sample track.
- Gold answers for property-calculation tasks are public. Their generation
  protocols are not disclosed in the initial release.
- Task 8 remains one task with a compound, machine-scored answer.

## Track Placement

| Expert task | Track | Submitted object | Evaluation contract |
|---|---|---|---|
| 1 | `rdkit` | SMILES | Recompute structural constraints and logP |
| 2 | `xtb` | Explicit-H XYZ | Recompute optimized-geometry dipole |
| 3 | `xtb` | Charged explicit-H XYZ | Recompute optimized-geometry HOMO-LUMO gap |
| 4 | `xtb` | Charged explicit-H XYZ | Recompute optimized-geometry HOMO-LUMO gap |
| 5 | `xtb` | ROY explicit-H XYZ | Recompute submitted-geometry single-point energy |
| 6 | `xtb` | Ritonavir explicit-H XYZ | Recompute optimized-geometry energy |
| 7 | `property_calculation` | Numeric JSON answer | Compare with public gold answer |
| 8 | `property_calculation` | Multi-property JSON answer | Compare numeric and categorical fields with public gold answers |

No new mixed track is introduced. Tasks 1-6 extend the existing task packs
only after their formalization gates pass. Tasks 7-8 establish the independent
`property_calculation` track described by the earlier design.

## Model Input Policy

The `prompt` field is the only model input. For tasks 7 and 8, each crystal is
introduced by a stable label followed by a fenced `cif` block containing the
complete source CIF. The runner does not read an external CIF path when
constructing prompts.

The task record also stores the same CIF values under `input_objects` for
machine inspection. Tests must assert that each structured `input_objects`
value occurs verbatim in the prompt. This deliberate duplication preserves the
existing `Track.prompts()` contract while retaining the structured input model
from the property-calculation design.

The expert reference image and answer notes are authoring evidence only. They
are not model inputs and are not packaged as runtime task assets.

## Task Designs

### Task 1: Target logP Molecule

The prompt asks for one molecule as a SMILES string.

Hard requirements:

- Allowed elements are exactly H, C, O, N, S, F, and Cl.
- Add implicit hydrogens before counting atoms.
- Total atom count, including hydrogen, is at most 40.
- Oxygen fraction is `oxygen_atom_count / total_atom_count` and is at least
  0.10.
- No neutral-charge or closed-shell restriction is added.

The answer uses the existing `final_answer_line` and `value_type: smiles`
schema. Invalid SMILES, multiple components, invalid valence, disallowed
elements, excess atom count, or insufficient oxygen fraction receive zero.

The property score is a target-distance score:

```text
score = exp(-abs(logp - 3.0) / 0.5)
```

### Task 2: Minimum-Dipole C12H16N3O8 Molecule

The model submits one connected molecule as an explicit-H XYZ block. The
formula must be exactly `C12H16N3O8`. The calculation is fixed to a neutral
doublet with charge 0 and one unpaired electron.

The verifier optimizes the submitted geometry with the frozen xTB protocol and
then evaluates the dipole magnitude. The dipole receives a continuous
minimization score. Its frozen scoring range is produced by the calibration
stage; the task cannot become formal before that range is recorded.

A local xTB 6.7.1 smoke test confirmed that the formula is computationally
admissible as `charge=0`, `UHF=1`. This establishes backend feasibility only;
it does not establish a scoring range, runtime budget, or formal-task status.

No unrelated atom-count, element, formula-denylist, or relaxation-energy
constraint is added.

### Task 3: Low-Gap Molecule with Two Fluorines

Hard requirements:

- Allowed elements are exactly H, C, O, N, S, F, and Cl.
- Total atom count, including explicit hydrogen, is at most 40.
- Fluorine count is exactly 2.
- Carbon count is at most 10.
- The molecule is closed-shell.

The answer remains the existing fenced XYZ answer format. The XYZ comment line
must have the exact shape `charge=<integer>`. The extractor still returns a
standard `{"xyz": ...}` candidate; the xTB parser reads the charge from the
comment. The verifier fixes the number of unpaired electrons to zero and
checks that the declared charge and electron count are compatible with a
closed-shell state.

The verifier optimizes the geometry and continuously minimizes the resulting
HOMO-LUMO gap. The frozen scoring range comes from calibration.

### Task 4: Low-Gap Molecule with Ten Carbons

Task 4 uses the same answer, charge, electron-state, optimization, and scoring
contracts as task 3. Its structural requirements are:

- Allowed elements are exactly H, C, O, N, S, F, and Cl.
- Total atom count, including explicit hydrogen, is at most 40.
- Carbon count is exactly 10.
- Fluorine count is exactly 2.
- The molecule is closed-shell.

### Task 5: ROY Submitted-Conformer Energy

The prompt includes this reference SMILES:

```text
Cc1cc(c(s1)Nc2ccccc2[N+](=O)[O-])C#N
```

The model submits one explicit-H XYZ conformer. The verifier requires formula
`C12H9N3O2S`, one connected component, charge 0, zero unpaired electrons, and
a molecular graph isomorphic to the reference structure.

The verifier performs a single-point calculation on the submitted coordinates
without geometry optimization. The total energy receives a continuous
minimization score over a frozen same-molecule calibration range. Absolute
energies are not compared across different molecules or tasks.

### Task 6: Ritonavir Optimized Energy

The prompt includes the name Ritonavir and this exact isomeric SMILES:

```text
CC(C)C1=NC(=CS1)CN(C)C(=O)N[C@@H](C(C)C)C(=O)N[C@@H](CC2=CC=CC=C2)C[C@@H]([C@H](CC3=CC=CC=C3)NC(=O)OCC4=CN=CS4)O
```

The reference structure has formula `C37H48N6O5S2`, 50 heavy atoms, 98 total
atoms after adding hydrogen, formal charge 0, and four specified
stereocenters.

The model submits an explicit-H XYZ conformer. Before calculation, the
verifier checks formula, atom count, connectedness, molecular-graph identity,
and stereochemistry. It optimizes the candidate with charge 0 and zero
unpaired electrons, evaluates the optimized energy, and rechecks graph identity
and stereochemistry after optimization. Fragmentation, rearrangement, or
stereochemical loss fails the identity gate.

The task remains non-formal until a multi-conformer live calibration establishes
acceptable convergence, runtime, memory, timeout, and energy-score bounds for
the 98-atom system.

### Task 7: 300 K Crystal Free-Energy Difference

The English prompt contains the complete `ETDIAM01` and `ETDIAM18` CIF values.
It asks for the absolute 300 K free-energy difference in `kJ/mol`.

The gold answer is `0.258031679 kJ/mol`. The source intermediate difference is
`2.6743099 meV`; meV is not an accepted final-answer unit. The numeric answer
is correct when:

```text
abs(submitted_value - 0.258031679) <= 0.001 kJ/mol
```

The task score is 1 for a correct value and unit and 0 otherwise.

### Task 8: Crystal Potential-Energy Difference and Phase Assignment

The English prompt contains the complete `alpha_CONTCAR` and `beta_CONTCAR`
CIF values. It asks for the absolute potential-energy difference in eV and the
ambient-pressure and high-pressure phase labels.

The public gold values are:

- Potential-energy difference: `0.079 eV`.
- Ambient-pressure phase: `alpha`.
- High-pressure phase: `beta`.

The numeric component is correct when:

```text
abs(submitted_value - 0.079) <= 0.001 eV
```

The phase component is correct only when both phase labels match. The final
score is:

```text
score = (numeric_score + phase_score) / 2
```

The possible task scores are 0, 0.5, and 1.

## Schema Compatibility

### Common Task Envelope

All tracks retain the existing common task fields:

```yaml
task_id: string
version: integer
object_type: string
difficulty: string
formal_track: boolean
capability_tags: [string]
prompt: string
answer_schema: mapping
scoring: mapping
failure_policy: mapping
```

The registry remains the source of the track name, so tasks do not duplicate a
`track` field. Property-calculation tasks add
`task_type: property_calculation`. A missing `task_type` continues to mean
`open_generation`, preserving all existing task packs.

Open-generation tasks retain `constraints` and optional `structural_domain`.
Property-calculation tasks instead use `input_objects`,
`requested_properties`, `gold_answers`, and `gold_provenance`; they do not
create fake verifier constraints.

### Property-Calculation Task Fields

Task 7 uses the following field contract. This is a schema illustration, not a
task record: each `value` field in the implemented YAML contains the complete
43-line CIF text rather than a path, placeholder, or attachment reference.

```yaml
task_type: property_calculation
object_type: crystal_pair
input_objects:
  - object_id: ETDIAM01
    type: cif
    value: string
    presentation: prompt_inline
  - object_id: ETDIAM18
    type: cif
    value: string
    presentation: prompt_inline
requested_properties:
  - name: free_energy_difference
    value_type: number
    unit: kJ/mol
    display_precision: 9
gold_answers:
  - property: free_energy_difference
    value: 0.258031679
    unit: kJ/mol
    absolute_tolerance: 0.001
gold_provenance:
  disclosure: withheld_initial_release
```

Task 8 uses the same list-shaped fields with three requested properties and
three gold-answer entries:

| Property | Value type | Unit | Gold value | Comparison group |
|---|---|---|---|---|
| `potential_energy_difference` | number | `eV` | `0.079` with `0.001` absolute tolerance | numeric |
| `ambient_pressure_phase` | string | none | `alpha` | phase mapping |
| `high_pressure_phase` | string | none | `beta` | phase mapping |

The two phase fields form one all-or-nothing comparison group. The numeric
group and phase-mapping group each carry weight 0.5. This is the
multi-property extension reserved by the earlier property-calculation design.

### Answer Schema and Normalization

Both property-calculation tasks reuse the implemented answer-schema vocabulary:

```yaml
answer_schema:
  format: final_answer_line
  final_answer_prefix: "FINAL ANSWER:"
  value_type: json
  cardinality: one
```

Task 7 model output:

```text
FINAL ANSWER: {"answer":0.258031679,"unit":"kJ/mol"}
```

Its canonical normalized structured answer is:

```json
{"task_id":"property_calc_free_energy_001","answer":0.258031679,"unit":"kJ/mol"}
```

Task 8 model output uses the reserved multi-property list:

```text
FINAL ANSWER: {"answers":[{"property":"potential_energy_difference","value":0.079,"unit":"eV"},{"property":"ambient_pressure_phase","value":"alpha"},{"property":"high_pressure_phase","value":"beta"}]}
```

The current extractor already parses raw `value_type: json` final-answer lines
into a JSON candidate. The property-calculation implementation extends
normalization to unwrap that candidate into the canonical `answer` or `answers`
record and to accept the equivalent already-structured answer JSONL.
Open-generation normalization remains unchanged.

### Evaluator Routing

The evaluator resolves `task_id`, normalizes the answer, and then dispatches on
`task_type` before requiring open-generation constraints:

```text
task_type missing or open_generation -> existing constraint/verifier-script path
task_type property_calculation       -> gold-answer comparison path
```

The property-calculation path never executes a verifier script during model
evaluation. The current `TrackDefinition` requires a verifier-spec path, so the
new track supplies a compatibility file containing `verifiers: []`. This avoids
changing the registry, Track, Suite, CLI, and package APIs merely to represent
the absence of runtime verifiers.

### Result Schema

Property-calculation results use the same outer result contract as existing
open-generation results:

```yaml
task_id: string
status: ok | error
canonical_smiles: null
properties: mapping
scores:
  validity_gate: number
  domain_gate: number
  constraint_scores: [mapping]
  property_score: number
  score: number
failure_type: string | null
message: string | null
versions: mapping
```

The `properties` mapping records submitted and gold values. Task 7 emits one
absolute-tolerance item in `constraint_scores`. Task 8 emits two logical items:
`potential_energy_difference` and `pressure_phase_assignment`. Its scoring
aggregation is `arithmetic_mean`.

## Required Capability Changes

### Shared Scoring

- Add target-distance scoring for task 1.
- Add binary absolute-tolerance scoring for numeric property calculations.
- Add exact categorical mapping scoring.
- Add arithmetic-mean aggregation without changing the existing default
  geometric mean.

### RDKit Domain Inspection

- Compute total atom count after adding implicit hydrogen.
- Compute element counts and atom fractions.
- Enforce task-specific allowed elements without importing the current baseline
  charge, molecular-weight, or heavy-atom gates.

### xTB Input and Domain Inspection

- Parse `charge=<integer>` from the XYZ comment for tasks 3 and 4.
- Support fixed task charge/spin and candidate-declared charge with fixed spin.
- Check exact and maximum element counts, exact formula, and electron parity.
- Add submitted-geometry single-point total energy.
- Add reference-graph and stereochemistry identity checks before calculation.
- Recheck identity after optimization for task 6.
- Preserve existing xTB task behavior for every current task.

### Property-Calculation Evaluation

- Load list-shaped requested properties and gold answers from the task record.
- Normalize single-property and multi-property JSON answers.
- Enforce the prompt-specified canonical unit; no implicit unit conversion is
  required in the initial release.
- Return per-component comparison details inside the common result schema.
- Register and package the new track with an empty verifier-spec list and public
  sample answers.

## Error and Partial-Credit Policy

- Missing final-answer marker, malformed JSON, malformed SMILES, or malformed
  XYZ is a `parse_error`.
- Invalid coordinates or multiple inferred molecular components are validity
  failures under the existing failure taxonomy.
- Element, count, formula, charge/spin, molecular identity, or stereochemistry
  mismatches are `domain_error` results.
- Missing xTB, backend failure, non-convergence, and timeout retain the existing
  verifier environment/tool/timeout taxonomy.
- A valid task 7 JSON answer with a wrong value or unit has status `ok` and
  score 0; it is an incorrect answer, not an evaluator error.
- For task 8, a missing or incorrect numeric field gives `numeric_score=0`
  while a complete correct phase mapping can still earn 0.5. A missing or
  incorrect phase field gives `phase_score=0` while a correct numeric answer
  can still earn 0.5.
- Completely malformed task 8 JSON is a parse error and receives zero.

## Gold Answer Disclosure

The public task data includes gold values, consistent with the existing
property-calculation design. For the initial release, public metadata records:

```yaml
gold_provenance:
  disclosure: withheld_initial_release
```

The prompt must not expose gold values or generation details. Withholding the
protocol reduces independent external regeneration and is recorded as an
initial-release limitation rather than represented as complete provenance.

## Verification and Formalization Gates

### Prompt and Schema Tests

- Verify every prompt is English and tool-neutral.
- Verify tasks 7 and 8 contain no file paths or attachment instructions.
- Verify each `input_objects` CIF occurs verbatim in its prompt.
- Parse all four inline CIF values and check labels, formulas, atom counts, and
  cell volumes.
- Verify task records load through the existing task loader and registry shell.
- Verify current task packs still default to `open_generation`.

### Constraint and Identity Tests

- Test every lower, upper, exact-count, and ratio boundary for tasks 1-4.
- Test charge parsing and closed-shell electron compatibility for tasks 3-4.
- Test ROY formula and graph identity acceptance and rejection.
- Test Ritonavir formula, graph, stereochemistry, and post-optimization identity
  checks.

### Evaluation Tests

- Use fake xTB runners for single-point, optimization, doublet, dynamic charge,
  non-convergence, and timeout paths.
- Test task 7 values immediately inside and outside the absolute tolerance and
  test unit mismatch.
- Test task 8 malformed JSON, missing fields, incorrect phase mappings, and all
  final scores 0, 0.5, and 1.
- Verify coverage, summaries, result serialization, Suite routing, and CLI
  behavior remain consistent across all three tracks.
- Run the full repository test suite before every commit.

### Live Calibration

Tasks 2-6 require live xTB calibration before task cards are added to a formal
pack. Calibration freezes scoring bounds and records convergence and resource
evidence. Task 6 additionally requires a multi-conformer 98-atom study showing
that runtime, memory, timeout, structure retention, and optimization convergence
are acceptable for benchmark evaluation.

No candidate task is placed in a formal pack merely by setting
`formal_track: false`, because current track coverage does not filter task rows
by that field. A task enters the built-in formal pack only after its gates pass.

## Implementation Decomposition

This design produces two independent implementation plans:

1. RDKit and xTB open-generation extensions for tasks 1-6, including live
   calibration before formal task-pack changes.
2. The `property_calculation` track for tasks 7-8, including inline CIF prompts,
   gold comparison, registry integration, and packaging.

Each plan must produce independently testable software and focused commits.

## Non-Goals

- Do not create a mixed expert-sample track.
- Do not require or inspect model traces, tool calls, or intermediate files.
- Do not expose task 7 or task 8 gold-generation protocols in the initial
  release.
- Do not add chemical restrictions absent from the expert-authored questions.
- Do not claim a globally optimal conformer or experimental property from a
  high score under the fixed verifier.
