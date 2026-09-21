# Property Calculation Numeric Domains

Date: 2026-09-21 (v0.10.0)

Numeric domains describe the requested quantity independently of the scoring
tolerance. An optional `minimum_value` in a `numeric_gold` profile is an inclusive
bound in the original answer units, checked before any value transform. Values
below it receive zero for that field, even if a wider tolerance would otherwise
give partial credit. The loader rejects nonfinite bounds and gold values outside
the domain. Missing bounds preserve the existing signed-number behavior.

Advanced 001 and 002 request absolute energy differences; Advanced 011 requests a
volume ratio. These quantities have `minimum_value: 0.0`. The same bound applies
to the distance field in Advanced 012, which uses the identity transform.
Advanced 010 instead compares absolute values in v0.10.0 and has no original-value
minimum bound, as required by the expert-reviewed task scoring rule.
Zero is in the domain; its score still depends on its error from the gold value.
For multi-field tasks such as Advanced 002, other fields retain their own scores.

Advanced 008 and 013 instead accept both signs for interaction/binding energies,
following the task owner's convention: stabilization energies and positive energy
magnitudes are both accepted. Their existing `absolute` transform compares
`abs(answer)` with `abs(gold)`. The sign-preservation wording is removed from both
prompts. This does not extend sign equivalence to other energy tasks or to signed
charges, spin densities, and electrochemical potentials.

See [v0.10.0 scoring](property-calculation-v0.10.0-scoring.md) for the current
task-specific widths. Gold values, field weights, and categorical matching rules
are unchanged.
