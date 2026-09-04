# Property Calculation Basic Track

Updated: 2026-09-04

## Positioning

`property_calculation_basic` is a formal track for 51 fixed-input, basic molecular property
questions. It is separate from `property_calculation_advanced`; adding or revising basic-track tasks does not
change the advanced track's 20 task definitions or scoring profiles.

The track covers aqueous solvation free energies, redox potentials, noncovalent binding energies,
polarizabilities, dipole moments, bond orders, molecular-surface properties, crystal densities,
atomic spin densities, Fukui functions, standard entropies, a dimerization enthalpy, Mulliken
charges, and vertical excitation energies.

## Runtime Contract

The track reuses `task_type: property_calculation`. Its evaluator parses a single JSON answer from
the `FINAL ANSWER:` line and compares it with the task's numeric or atom-identity gold. It does not
run a property verifier, reproduce the source calculation, or require an external quantum
chemistry executable.

```yaml
task_pack:
  id: property_calculation_basic
  scoring_version: linear_goal_v2
task_type: property_calculation
```

`verifier_specs.yaml` therefore contains an empty `verifiers` list. Numeric scores use the same
`linear_goal_v2` implementation as the original property-calculation track. Each numeric task has a
single full-score gold and symmetric linear decay on both sides. The configured absolute width is
either the fixed absolute error from the reviewed standard or the reviewed percentage multiplied by
`abs(gold)`. There is no full-score interval and reference values do not widen the scoreable range.

Tasks 044 and 046 use deterministic atom-identity scoring. Task 044 gives 1.0 only to `11 O`, 0.5
to an oxygen symbol with a missing or incorrect index, and 0 otherwise. Task 046 gives 1.0 only to
`3 N` and 0 otherwise.

## Input And Gold Policy

Every task embeds its molecule, molecular pair, condition, target property, and unit directly in an
English prompt. Property tasks that require chemical localization describe the target atom or bond
by its chemical role, so the respondent must identify it before calculating the value. The two atom-
identity tasks explicitly define zero-based SMILES indexing because the index is part of the answer.
Source CSV
commands and local environment paths are maintenance evidence only and are never executed by the
benchmark or shown to the model.

The expert `answer` value is the frozen gold. Experimental or higher-level reference values are
provenance only and do not affect scoring. This track does not ship sample answers; use test fixtures
or model outputs for local scoring.
