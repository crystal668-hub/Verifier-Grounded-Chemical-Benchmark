# Property Calculation Easy Track

Updated: 2026-08-25

## Positioning

`property_calculation_easy` is a formal track for 51 fixed-input, basic molecular property
questions. It is separate from `property_calculation`; adding or revising easy-track tasks does not
change the original track's 20 task definitions, scoring profiles, or sample answers.

The track covers aqueous solvation free energies, redox potentials, noncovalent binding energies,
polarizabilities, dipole moments, bond orders, molecular-surface properties, crystal densities,
atomic spin densities, Fukui functions, standard entropies, a dimerization enthalpy, Mulliken
charges, and vertical excitation energies.

## Runtime Contract

The track reuses `task_type: property_calculation`. Its evaluator parses a single JSON answer from
the `FINAL ANSWER:` line and compares it with the task's numeric or exact-string gold. It does not
run a property verifier, reproduce the source calculation, or require an external quantum
chemistry executable.

```yaml
task_pack:
  id: property_calculation_easy
  scoring_version: linear_goal_v2
task_type: property_calculation
```

`verifier_specs.yaml` therefore contains an empty `verifiers` list. Numeric scores use the same
`linear_goal_v2` implementation as the original property-calculation track. When provided, source
reference values widen the scoreable interval between the reference and expert gold; otherwise,
track-local profile widths follow the expert answer's reported precision.

## Input And Gold Policy

Every task embeds its molecule, molecular pair, condition, target property, and unit directly in an
English prompt. Atom-specific tasks explicitly state zero-based indices where needed. Source CSV
commands and local environment paths are maintenance evidence only and are never executed by the
benchmark or shown to the model.

The expert `answer` value is the frozen gold. Experimental or higher-level reference values define
scoreable tolerance ranges but are not substituted for the expert result. Canonical sample answers
are included for local scoring sanity checks, following the same public-gold policy as
`property_calculation`.
