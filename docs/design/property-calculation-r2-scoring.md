# Property Calculation R2 Scoring

Date: 2026-09-17. Release: v0.9.3.

The benchmark owner approved the complete
`property_family_anchors_2026_09_17_r2` policy and its rescoring results for formal
use. The Basic and Advanced `scoring.yaml` files now contain exactly the approved
R2 scoring fields, with formal release provenance. The archived candidate files
and results remain under
`docs/research/2026-09-17-property-tolerance-policy/`.

## Release Contract

- All 71 numeric fields use the approved property-family widths. Gold values,
  field weights, categorical scoring, and task IDs are unchanged.
- Advanced 001 and 002 use absolute zero-score widths of 8 kJ/mol and 0.8 eV.
  Negative values score zero before tolerance evaluation. Zero is a valid answer
  and receives the ordinary linear score based on its absolute error.
- Basic 037-042 all use a relative zero-score width of 10% of the gold magnitude.
  Relative errors of 1%, 5%, and 10% receive 90, 50, and 0 points respectively.
- Other parameters are the R2 family rules in the
  [full parameter table](../research/2026-09-17-property-tolerance-policy.md).
- Advanced 001/002/011 and the distance fields in 010/012 have independent
  nonnegative domains. Advanced 008/013 retain magnitude-based scoring, with
  sign-preservation wording removed from their prompts. See the
  [numeric domain contract](property-calculation-numeric-domain.md).
- Result schema 3, `linear_goal_v2`, the 105-task inventory, and RDKit/xTB scoring
  behavior are unchanged. The package and all four task packs are version 0.9.3.

## Approval And Evidence

`review_status: approved` records the owner's decision to adopt these scoring
standards, not independent validation of every chemical reference or uncertainty.
Numeric profile provenance retains `calibration_status` from the R2 candidate:
`pending_independent_calibration`, or `retained_pending_target_definition` for
Advanced 018. The latter's existing asymmetric 10/1 percentage-point widths remain
unchanged, as accepted in the complete R2 scheme.

The existing questions about source protocols and target definitions remain
documented in the research report. Approval does not assert new chemistry
calculations, new model answers, or independent statistical calibration.

## Verification And Artifacts

Regression tests compare every released scoring field against the frozen R2
candidate and, when the private workbooks are present, compare all 284 answer
scores against the accepted R2 table. Historical experiments load the published
v0.9.2 profile inventory for their baseline rather than whichever formal scoring
configuration is currently installed.

The release builder produces a wheel and sdist from a clean source commit,
verifies equal packaged payloads, and writes `manifest.json`, `task-inventory.json`,
and `SHA256SUMS` to `releases/v0.9.3/`. The manifest identifies the canonical source
commit separately from the later commit containing these release records.
