# Task Prompt Wording Guidelines

Date: 2026-06-29

## Purpose

Task prompts should read like natural chemistry or materials-design requests. They should tell a model what candidate object to produce, what scientific properties matter, and what answer format is required. They should not tell the model which verifier, backend, script, or benchmark mechanism will evaluate the answer.

This keeps the task focused on first-principles problem solving: a model may use chemical intuition, literature, search, scripts, external tools, or no tools at all. The benchmark only judges the final candidate under the fixed public evaluation protocol.

## Three-Layer Boundary

Use three separate layers for task meaning, evaluation transparency, and machine execution.

1. Prompt requirements
   - Audience: the model being evaluated.
   - Content: candidate representation, chemical or materials constraints, target property ranges, geometry quality expectations, and final-answer format.
   - Style: tool-neutral natural language.
   - Avoid: backend names, verifier ids, script paths, scoring internals, and benchmark meta-language.

2. Documentation and track cards
   - Audience: benchmark users and maintainers.
   - Content: evaluation protocol, scientific interpretation, surrogate method limitations, tool versions, calibration evidence, and known failure modes.
   - Tool names are appropriate here because transparency and reproducibility require method disclosure.

3. Machine-readable specs
   - Audience: runner and verifier implementation.
   - Content: `verifier_id`, `verification_script`, backend type, method, version, domain gates, thresholds, scoring parameters, resource limits, and failure policy.
   - This layer remains exact and implementation-specific.

## Prompt Wording Rules

Do not use these kinds of phrases in a task `prompt`:

- Tool or backend names as requirements, such as "RDKit-calculated", "local xTB", "GFN2-xTB", "MatGL", or "MACE-MP-small".
- Verifier implementation details, such as "verifier_id", script paths, "sigma", or "geometric_mean".
- Benchmark meta-language, such as "benchmark-evaluated", "benchmark optimization", or "benchmark protocol".

Prefer direct property and object language:

- "Molecular weight must be at most 600.0 daltons."
- "Coordinates must be in Angstrom and chemically plausible for a neutral closed-shell small molecule."
- "The submitted XYZ should already be close to a physically reasonable local minimum."
- "After geometry optimization, have a HOMO-LUMO gap between 3.5 and 5.5 eV."

## Examples

RDKit molecular weight gate:

```text
Avoid: RDKit-calculated molecular weight must be at most 600.0 daltons.
Use:   Molecular weight must be at most 600.0 daltons.
```

xTB geometry quality:

```text
Avoid: Coordinates must be in Angstrom and suitable for local xTB optimization.
Use:   Coordinates must be in Angstrom and chemically plausible for a neutral closed-shell small molecule.

Avoid: The submitted XYZ should already be close to a low-energy xTB geometry.
Use:   The submitted XYZ should already be close to a physically reasonable local minimum.
```

Evaluation protocol disclosure belongs outside the prompt:

```text
Prompt: After geometry optimization, have a HOMO-LUMO gap between 3.5 and 5.5 eV.
Docs/spec: The fixed evaluator optimizes submitted XYZ geometries with GFN2-xTB before parsing the HOMO-LUMO gap.
```

Materials prototype properties:

```text
Avoid: MatGL formation energy between -0.05 and 0.05 eV in the fixed MEGNet formation-energy model output convention.
Use:   Formation energy between -0.05 and 0.05 eV.
```

## Regression Expectation

Prompt wording tests should inspect only the `prompt` field in task YAML files. It is valid and expected for task ids, capability tags, notes, verifier specs, track docs, and design docs to contain tool names and benchmark terminology.
