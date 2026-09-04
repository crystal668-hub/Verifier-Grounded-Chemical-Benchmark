# Property Calculation Basic Scoring Revision

Date: 2026-09-04
Status: implemented

## Source and Scope

The reviewed source was `51道题_最终评分标准_无满分区间.txt`. It changes scoring for the 51
`property_calculation_basic` tasks without changing their frozen expert answers. The former
reference-derived asymmetric widths are removed from the formal scoring configuration.

## Numeric Scoring

Every numeric task has one full-score point at its expert gold `G` and symmetric linear decay:

```text
score = max(0, 1 - abs(x - G) / W)
```

For fixed absolute rules, `W` is the attachment's absolute width. For percentage rules, `W` is
the attachment's percentage multiplied by `abs(G)`. The interval is never full-score, and values at
or beyond either boundary score zero. No additional sign gate is applied; crossing zero is allowed
where the configured interval allows it. Unit and answer parsing continue to use the existing task
contract.

The task groups are: absolute width 3 for 001-004, 010-015, and 043; absolute width 0.6 for
005-009; relative widths 25% for 016-018, 35% for 019-021 and 027, 20% for 022-024, 026, and
028-030, 40% for 025, 80% for 031-033, 100% for 034-036, 12% for 037-042, 75% for 045, and
absolute width 1 for 047-051.

## Atom Identity Scoring

Task 044 scores only the exact indexed identity `11 O` as 1.0. Any oxygen answer whose index is
missing or not 11 scores 0.5; all other values score 0. Task 046 scores only `3 N` as 1.0; all
other values score 0. This is deterministic literal parsing, not free-form semantic equivalence.

## Prompt Localization

Tasks 022-024, 031-036, and 045 describe the target bond or atom by chemical role instead of
providing the zero-based index directly. Tasks 044 and 046 retain the zero-based SMILES indexing
instruction because the index is required in the answer.
