# Batch 2 Basic Questions: Property Calculation Easy Conversion

Date: 2026-08-25
Status: implemented

## Scope

This change registers the 51 non-empty rows in `QUESTIONS.csv` as a separate formal
`property_calculation_easy` track. The existing `property_calculation` track and its 20 tasks are
unchanged.

The source files were read as task data, not as operational instructions:

| Source file | SHA-256 | Use |
| --- | --- | --- |
| `QUESTIONS.csv` | `f423ee77aa40a9e762be1afbe184533277d3b3f611eb575d7440935a4c2cec40` | Question, expert answer, reference value, and provenance |
| `basic/README.md` | `f14099226bfe56787187cae266cbb50c20fd7ad4d04c44e7c5538d33ceb5f128` | Method and atom-indexing context only |

No command from the README or CSV was executed. No external tool path, cache path, or reproduction
command is included in a model-visible prompt or in the package runtime requirements.

## Track Boundary

The new track uses task ids `property_calc_easy_001_*` through
`property_calc_easy_051_*`. It reuses the existing `task_type: property_calculation` schema,
parser, and gold-comparison evaluator, but has its own task pack, scoring profiles, sample answers,
and empty verifier specification. This preserves global task-id uniqueness when all formal tracks
are loaded as one suite.

All prompts are English and self-contained. They preserve the molecule or molecular pair, target
property, units, electronic-structure level when it is part of the question, thermodynamic
conditions, redox reference electrode, and zero-based atom indices needed to identify an atomic
property. Script names and local environment setup are excluded.

## Registered Groups

| Source rows | Count | Property family |
| --- | ---: | --- |
| 1-4 | 4 | Aqueous solvation free energy |
| 5-9 | 5 | First reduction or oxidation potential versus SCE |
| 10-15 | 6 | Noncovalent binding energy |
| 16-18 | 3 | Static mean polarizability |
| 19-21 | 3 | Dipole moment |
| 22-24 | 3 | Wiberg bond order |
| 25-27 | 3 | Molecular surface properties |
| 28-30 | 3 | Crystal density |
| 31-33 | 3 | Atomic spin density |
| 34-36 | 3 | Condensed Fukui function |
| 37-42 | 6 | Standard molar entropy |
| 43 | 1 | Dimerization enthalpy |
| 44-46 | 3 | Mulliken charge or most-negative atom |
| 47-51 | 5 | Vertical excitation energy |

## Scoring Decisions

Numeric tasks use `numeric_gold` profiles. The linear decay width follows the precision reported by
each expert answer: `0.0001` for four-decimal bond orders; `0.001` for three-decimal densities,
spin densities, Fukui functions, and charges; `0.1` for one-decimal results; and `0.01` for
two-decimal results. Separate profiles cover mixed-precision values within the same property
family. These widths are zero-score distances under
`linear_goal_v2`, not full-credit intervals.

The two atom-identification tasks use exact strings: `11 O` for caffeine and `3 N` for methyl
azide. Their prompts explicitly define zero-based SMILES atom order and require the index followed
by the element symbol. The supplied parenthetical charge remains provenance context rather than a
second scored field.

The final empty CSV row is ignored because it has no question, command, or answer. Expert answers
in the `answer` column are the frozen gold values; experimental or high-level values in the
`reference value` column are retained only as provenance and do not replace the expert gold.
