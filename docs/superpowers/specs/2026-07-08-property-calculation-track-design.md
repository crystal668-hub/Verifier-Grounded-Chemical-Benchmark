# Property Calculation Track Design

## Background

The benchmark currently focuses on verifier-grounded open-generation tasks: a model
proposes a chemical object, and the benchmark independently recomputes properties
with a verifier. The new task family adds a separate mode: the benchmark gives a
chemical object and asks the model or agent to report a computed property value.

This design records the agreed boundary for that task family. It does not select
specific properties yet, and it does not implement a new track.

## Goals

- Add a benchmark task family for property calculation questions.
- Keep this task family as an independent track parallel to open-generation tracks.
- Evaluate only the final reported value, not the model's intermediate tool use or
  reasoning process.
- Keep prompts tool-neutral: task wording should not instruct the model to use a
  specific backend, verifier, package, or script.
- Use directly computable structure inputs, such as SMILES, XYZ, and CIF.
- Publish gold answers with the task data.
- Support single-property tasks first while leaving the schema compatible with
  future multi-property tasks.

## Non-Goals

- Do not replace verifier-grounded open-generation tasks.
- Do not require or inspect agent traces, tool calls, scripts, or intermediate
  calculations.
- Do not use chemical names as the core first-version input representation.
- Do not decide numeric tolerance, relative error policy, continuous scoring, or
  leaderboard aggregation in this design.
- Do not research or choose concrete properties before expert sample tasks are
  available.

## Track Positioning

The property calculation task family should be exposed as a distinct track, conceptually
named `property_calculation`. It should sit beside existing open-generation tracks
instead of being nested inside RDKit, xTB, or future backend-specific tracks.

This keeps the evaluation contract clear:

- Open-generation tracks evaluate generated candidates with verifier scripts.
- Property calculation tracks evaluate submitted numeric answers against published
  gold answers.

The track may still record how each gold answer was generated, but gold-generation
provenance is maintenance metadata, not part of the model-facing task instruction.

## Model-Facing Task Shape

Each first-version task should present:

- A directly computable chemical or materials object.
- One requested property.
- The expected unit.
- A concise final-answer format.

Examples of acceptable input representations:

- Small-molecule SMILES.
- Molecular XYZ coordinates.
- Materials CIF content or a path-like packaged CIF reference.

Examples of excluded first-version representations:

- Common chemical names.
- Trade names.
- Database identifiers that require lookup before calculation.

Task prompts should follow the existing wording guideline: they may name the scientific
property and unit, but they should not name the evaluator implementation or tell the
model which tool to call.

## Data Model

A property calculation task record should contain the following conceptual fields:

```yaml
task_id: property_calc_example_001
track: property_calculation
task_type: property_calculation
prompt: "Given the following SMILES, report the molecular weight in daltons. ..."
input_object:
  type: smiles
  value: "CCO"
requested_properties:
  - name: molecular_weight
    unit: Da
    display_precision: 3
gold_answers:
  - property: molecular_weight
    value: 46.069
    unit: Da
gold_provenance:
  protocol_id: rdkit_descriptor_mw_v1
  generated_at: "2026-07-08"
  code_version: "recorded when generated"
  dependency_versions:
    rdkit: "recorded when generated"
```

The first version should create one requested property per task. The list-shaped
`requested_properties` and `gold_answers` fields reserve a clean path for future
multi-property tasks without changing the task type.

## Answer Contract

The preferred structured answer shape is:

```json
{"task_id": "property_calc_example_001", "answer": 46.069, "unit": "Da"}
```

The evaluator may also support raw model responses through an answer extractor, but
the canonical normalized answer should contain:

- `task_id`
- numeric `answer`
- optional `unit`

If multi-property tasks are added later, the normalized answer can extend to a mapping
or list of property-value records.

## Evaluation Flow

The evaluator should:

1. Load the task and public gold answer.
2. Normalize the submitted answer into a numeric value and unit.
3. Check whether the submitted unit is compatible with the requested property.
4. Compare the submitted value with the gold value.
5. Emit a result row containing the submitted value, gold value, unit, parse status,
   comparison status, and score fields defined by the concrete track policy.

This flow intentionally does not invoke verifier scripts during model evaluation.
The benchmark may provide separate maintainer tooling to regenerate or audit gold
answers, but that tooling is outside the model-scoring path.

## Gold Answer Policy

Gold answers are public. This makes the track transparent and easy to reproduce, but
it also means the same published split should not be treated as a blind leaderboard
alone.

The track is still useful for:

- Local sanity checks.
- Agent tool-use and calculation capability analysis.
- Regression testing across model versions.
- Comparing whether systems can recover correct values under tool-neutral prompts.

Gold provenance should be recorded so maintainers can audit or regenerate answers
when dependencies change. Provenance belongs in task metadata or a companion manifest,
not in the prompt.

## Deferred Decisions

The following decisions are intentionally postponed until a concrete track is ready
to implement:

- Absolute versus relative tolerance.
- Binary correctness versus continuous error-based scoring.
- Unit conversion policy beyond simple unit compatibility.
- Leaderboard aggregation and reporting metrics.
- Exact task pack filenames and registry integration.
- Concrete property selection.

Property selection is deferred until expert-authored sample tasks are available.
Those examples should drive the next design pass and any research into currently
implemented calculation backends.

## Implementation Notes for a Future Plan

A future implementation plan should likely include:

- A task-pack schema extension for `task_type: property_calculation`.
- A gold-answer loader and normalized-answer parser.
- A property-calculation evaluator separate from verifier-script dispatch.
- Tests for structured answers, raw answer extraction, unit handling, and missing
  or malformed numeric outputs.
- A small public sample task pack once expert examples are available.

The future implementation should not route these tasks through the existing
property-level verifier-script execution path unless the operation is explicitly
gold regeneration or maintainer audit.
