# Property Calculation v0.10.0 scoring

Date: 2026-09-21. Status: approved by the benchmark owner after expert review.

Each numeric scoring profile defines its own lower and upper tolerances.
The public `family-policy.yaml`, loader dependency, and cross-profile family
validation are removed. Existing family labels and unchanged profiles' R3
provenance remain historical attribution, not enforceable constraints.

| Task | Fields | Symmetric zero-score width | Transform |
| --- | --- | --- | --- |
| Basic 013 | binding_energy | 3 kcal/mol | identity (unchanged) |
| Advanced 008 | interaction_energy, binding_energy | 10 kcal/mol | absolute |
| Advanced 010 | oh_bond_distance, h_o_contact_distance | 0.1 angstrom | absolute |
| Advanced 013 | halogen_bond_interaction_energy | 5 kcal/mol | absolute |

For these three Advanced tasks, score is
`max(0, 1 - abs(abs(answer) - abs(gold)) / width)`.
Both signs receive the same score. Advanced 010's original-value minimum bound
is removed so negative values can reach the absolute transform. Advanced 008
and 013 no longer require sign preservation in their prompts. Basic 013 retains
signed scoring and its sign-preservation prompt.

All other tolerances, transforms, numeric domains, gold values, field weights,
aggregation, and categorical matching rules remain unchanged. In particular,
Advanced 012 retains its nonnegative distance domain and 0.2 angstrom width.
Tolerances remain linear zero-score widths, not full-credit acceptance bands.

Advanced 011 already explicitly requires a spherical probe radius of
1.2 angstrom in the current source prompt; v0.10.0 preserves and tests that
condition. Its gold and scoring profile remain unchanged.

The package and all four formal task packs use version 0.10.0. Scoring algorithm
version `linear_goal_v2` and result schema version `3` remain unchanged because
this release updates task configuration, not either interface.
