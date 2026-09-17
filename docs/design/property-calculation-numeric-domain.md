# Property Calculation Numeric Domains

Date: 2026-09-17

Numeric domains describe the requested quantity independently of the scoring
tolerance. An optional `minimum_value` in a `numeric_gold` profile is an inclusive
bound in the original answer units, checked before any value transform. Values
below it receive zero for that field, even if a wider tolerance would otherwise
give partial credit. The loader rejects nonfinite bounds and gold values outside
the domain. Missing bounds preserve the existing signed-number behavior.

Advanced 001 and 002 request absolute energy differences; Advanced 011 requests a
volume ratio. These quantities have `minimum_value: 0.0`. The same bound applies
to the three distance fields in Advanced 010 and 012. Distances use the identity
transform: a negative distance is not another convention for a positive length.
Zero is in the domain; its score still depends on its error from the gold value.
For multi-field tasks such as Advanced 002, other fields retain their own scores.

Advanced 008 and 013 instead accept both signs for interaction/binding energies,
following the task owner's convention: stabilization energies and positive energy
magnitudes are both accepted. Their existing `absolute` transform compares
`abs(answer)` with `abs(gold)`. The sign-preservation wording is removed from both
prompts. This does not extend sign equivalence to other energy tasks or to signed
charges, spin densities, and electrochemical potentials.

The domain and prompt corrections apply to the source task pack. Tolerance
calibration is a separate decision; this correction does not change any widths,
gold values, field weights, or categorical matching rules.
