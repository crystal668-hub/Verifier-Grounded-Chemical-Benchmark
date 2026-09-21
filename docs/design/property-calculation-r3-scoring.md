# Property Calculation R3 Scoring

Date: 2026-09-21. Release: v0.9.4.

R3 makes `src/verifier_grounded_benchmark/task/packs/family-policy.yaml` the
machine-readable family scoring policy for the two Property Calculation packs.
The loader validates every numeric gold profile against its family selector,
unit, transform, and expanded tolerance before exposing the pack to the public
scorer.

The `noncovalent_energy` family covers Basic B010-B015 and the interaction,
binding, and halogen-bond energy fields in Advanced A008/A013. Its symmetric
absolute zero-score width is `2 kcal/mol`.

Advanced A008 and A013 explicitly require preserving the energy sign. Their
profiles use the identity transform, so an opposite-sign result is scored by its
direct signed error and does not receive magnitude-equivalent credit. Advanced
A010 distances also use identity scoring; their existing `minimum_value: 0.0`
domain rejects negative distances before linear scoring.

The family policy is a public package resource, referenced by both scoring
configs. Per-profile tolerance fields remain expanded for compatibility with the
existing evaluator and custom scoring API; the loader verifies that they agree
with the family policy. Gold values, task weights, task aggregation, and
categorical rules are otherwise unchanged.
