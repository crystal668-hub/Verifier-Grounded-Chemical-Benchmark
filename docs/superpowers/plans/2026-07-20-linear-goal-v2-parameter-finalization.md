# Linear Goal v2 Parameter Finalization and Implementation Plan

**Date:** 2026-07-20

**Status:** Partially decided. The parameters in "Approved Decisions" are frozen inputs for the next implementation. Parameters in "Pending Decisions" must be resolved before formal task packs move to `linear_goal_v2`.

**Goal:** Replace provisional legacy-derived scoring parameters with reviewed, auditable `linear_goal_v2` profiles while preserving the canonical linear scoring formula and the immutable `linear_goal_v1` release.

**Architecture:** Keep `linear_goal_distance` as the only continuous scoring kernel. Treat the full-score target or region and the zero-score anchor as task policy. Derive each decay width from those endpoints. Store approved parameters in versioned scoring profiles, validate their provenance at task-pack load time, and expose the active scoring version through evaluation results and release metadata.

**Primary specification:** `docs/design/unified-linear-goal-scoring.md`

---

## 1. Decision Rules

The following rules are fixed for all remaining parameter decisions:

1. Determine the full-score target or region first.
2. Determine a zero-score anchor on each active failure side.
3. Derive the decay width as the distance between the full-score boundary and the zero-score anchor. Do not select a width only to reshape score distributions.
4. Property distributions may validate feasibility, saturation, source shift, and ordering, but may not directly define parameters unless a particular frozen distribution is explicitly declared to be the benchmark baseline.
5. A natural endpoint may be used only when it lies on the failure side and has a direct property interpretation.
6. A verifier-derived target and its anchors must use the same verifier version, method, protocol, units, hard domain, charge, and electronic-state policy.
7. Formal `linear_goal_v2` profiles must have approved provenance. A `provisional` profile may be evaluated only as shadow scoring and may not enter a formal v2 release.
8. `linear_goal_v1` profiles and release artifacts remain immutable. Approved values are introduced through new v2 profile ids and a new scoring version.
9. For unresolved xTB objectives, chemical literature must support both endpoints. The full-score target `T` represents a literature-supported excellent level in the requested optimization direction. The zero-score anchor `B` represents a literature-supported baseline, weak level, or failure-side reference; `B` is not another excellent target.
10. Literature values from experiments, DFT, or a different semiempirical method may identify the scientific level and reference compounds, but they may not be copied directly into a GFN2-xTB profile. The cited reference compounds must be recomputed with the frozen benchmark verifier protocol, and those recomputed values become the numeric `T/B` anchors.

## 2. Approved Decisions

### 2.1 Intrinsically bounded objectives

These profiles intentionally map the published metric range onto `[0, 1]`. Their targets are metric endpoints, not empirical quantiles.

| Planned v2 profile | Type | Full-score target | Zero-score anchor | Derived width | Decision basis |
| --- | --- | ---: | ---: | ---: | --- |
| `rdkit_qed_maximize_0p0_1p0_v2` | maximize | `1.0` | `0.0` | `1.0` | QED defined range |
| `rdkit_sa_score_minimize_1p0_10p0_v2` | minimize | `1.0` | `10.0` | `9.0` | SA score defined range |
| `rdkit_fraction_csp3_maximize_0p0_1p0_v2` | maximize | `1.0` | `0.0` | `1.0` | Fraction defined range |
| `rdkit_forcefield_optimization_converged_fraction_maximize_0p0_1p0_v2` | maximize | `1.0` | `0.0` | `1.0` | Fraction defined range |

The RDKit force-field profile remains experimental until that task pack is separately promoted. Its parameter decision is nevertheless final and must not diverge if the task becomes formal.

### 2.2 xTB relaxation quality gate

The shared xTB relaxation profile for tasks 001-013 is fixed as:

```yaml
type: minimize
unit: eV
full_score_target: 0.05
zero_score_anchor: 0.35
```

The derived right decay width is `0.30 eV`. Therefore:

| Relaxation energy | Quality score |
| ---: | ---: |
| `<= 0.05 eV` | `1.0` |
| `0.20 eV` | `0.5` |
| `>= 0.35 eV` | `0.0` |

Decision basis:

- `0.05 eV` is approximately `1.15 kcal/mol` and is the engineering threshold for a submitted geometry already close to a local minimum.
- `0.35 eV` is the task-declared rough-geometry boundary at which little or no credit is intended.
- The frozen expanded-run data validates feasibility: its relaxation-energy median is approximately `0.023 eV` and P95 is approximately `0.087 eV`. These quantiles validate the decision but do not define it.

The planned profile id is `xtb_relaxation_energy_minimize_0p05_0p35_v2`.

### 2.3 xTB imaginary-frequency stability gate

The stability gate is fixed as a nonnegative integer window:

```yaml
type: window
unit: count
full_score:
  min: 0
  max: 0
decay:
  lower_width: null
  upper_width: 2.0
```

This gives the discrete policy:

| Imaginary-frequency count | Stability score |
| ---: | ---: |
| `0` | `1.0` |
| `1` | `0.5` |
| `>= 2` | `0.0` |

The lower side is inactive because the property domain is nonnegative. The planned profile id is `xtb_imaginary_frequency_count_window_0_0_2p0_v2`.

### 2.4 RDKit window decay policy

For every RDKit descriptor window `[L, U]`, let `W = U - L`. Both decay widths are fixed to one complete target-window width:

```text
rL = W
rU = W
B_L = L - W
B_U = U + W
```

Values at or beyond `B_L/B_U` score zero. This gives the following approved parameters:

| Planned v2 profile | Full-score window | `rL` | `rU` | Zero-score anchors |
| --- | --- | ---: | ---: | --- |
| `rdkit_logp_window_1p0_3p0_2p0_v2` | `[1.0, 3.0]` | `2.0` | `2.0` | `-1.0`, `5.0` |
| `rdkit_tpsa_window_35p0_75p0_40p0_v2` | `[35.0, 75.0] angstrom^2` | `40.0` | `40.0` | `-5.0`, `115.0 angstrom^2` |
| `rdkit_hba_window_2_4_2p0_v2` | integer `[2, 4]` | `2.0` | `2.0` | `0`, `6` |
| `rdkit_hbd_window_1_2_1p0_v2` | integer `[1, 2]` | `1.0` | `1.0` | `0`, `3` |

Property-domain validation takes precedence over scoring. For example, a negative TPSA verifier result is an invalid measurement even though the mathematical lower zero-score anchor is `-5.0 angstrom^2`.

The experimental RDKit force-field window uses the same one-window rule on its physically active upper side. For `[0.0, 20.0] kcal/mol`, the lower side remains inactive by the nonnegative property domain, `rU = 20.0 kcal/mol`, and the upper zero-score anchor is `40.0 kcal/mol`. The planned profile id is `rdkit_forcefield_energy_range_kcal_mol_window_0p0_20p0_20p0_v2`.

Repeated uses of the same property, verifier protocol, and task semantics must reference the same approved profile. In particular, RDKit tasks 003/009, 004/009, 005/010, and 006/010 must not duplicate parameter definitions.

The RDKit logP target task is not a window task. Its target is `3.0`, and the requested `3-0` rule is interpreted symmetrically for the target primitive: both sides use `r=3.0-0=3.0`. The resulting zero-score anchors are `0.0` and `6.0`.

The planned profile id is `rdkit_logp_target_3p0_3p0_v2`:

```yaml
type: target
unit: dimensionless
full_score_target: 3.0
decay:
  lower_width: 3.0
  upper_width: 3.0
```

### 2.5 xTB full-score windows fixed by task statements

The following xTB full-score windows remain unchanged. Their decay widths are now fixed to one complete target-window width on each active side:

```text
W = U - L
rL = W
rU = W
B_L = L - W
B_U = U + W
```

| Planned v2 profile | Fixed full-score window | `rL=rU` | Zero-score anchors |
| --- | --- | ---: | --- |
| `xtb_homo_lumo_gap_window_3p5_5p5_2p0_v2` | `[3.5, 5.5] eV` | `2.0 eV` | `1.5`, `7.5 eV` |
| `xtb_dipole_moment_window_3p0_5p5_2p5_v2` | `[3.0, 5.5] D` | `2.5 D` | `0.5`, `8.0 D` |
| `xtb_homo_lumo_gap_window_2p5_4p2_1p7_v2` | `[2.5, 4.2] eV` | `1.7 eV` | `0.8`, `5.9 eV` |
| `xtb_dipole_moment_window_3p5_6p0_2p5_v2` | `[3.5, 6.0] D` | `2.5 D` | `1.0`, `8.5 D` |
| `xtb_dipole_moment_window_3p0_8p0_5p0_v2` | `[3.0, 8.0] D` | `5.0 D` | `-2.0`, `13.0 D` |

These window values do not require literature-derived `T/B` research. Property-domain validation still takes precedence if an anchor lies outside the physically realizable domain.

### 2.6 Property Calculation numeric-gold policy

For each of the two current positive numeric gold answers `g`, the full-score target is `g` and both decay widths are the distance from the gold answer to zero, expressed in the gold-answer unit:

```text
L = U = g
tauL = tauU = g - 0 = g
B_L = 0
B_U = 2g
```

This policy is approved for the two current tasks:

| Planned v2 profile | Gold target | `tauL` | `tauU` | Zero-score anchors |
| --- | ---: | ---: | ---: | ---: |
| `property_calculation_free_energy_difference_numeric_gold_v2` | `0.258031679 kJ/mol` | `0.258031679 kJ/mol` | `0.258031679 kJ/mol` | `0`, `0.516063358 kJ/mol` |
| `property_calculation_potential_energy_difference_numeric_gold_v2` | `0.079 eV` | `0.079 eV` | `0.079 eV` | `0`, `0.158 eV` |

The score is one only at the gold answer, decays linearly to zero at zero and twice the gold answer, and is zero outside that support. This rule does not automatically extend to a future zero or negative gold answer because a decay width must remain positive.

### 2.7 Property Calculation exact-string answers

The `ambient_pressure_phase` gold remains exact string `alpha`, and the `high_pressure_phase` gold remains exact string `beta`.

### 2.8 xTB gap and dipole literature profiles

The first literature-reviewed xTB batch is frozen in
`docs/research/2026-07-21-xtb-gap-dipole-linear-goal-dossier.md`. Values are
recomputed with the formal GFN2-xTB verifier protocol; literature values are
used only to establish the scientific ordering and reference level.

| Profile | Direction | `T` | `B` | Unit |
| --- | --- | ---: | ---: | --- |
| `xtb_homo_lumo_gap_maximize_10p0_12p0_v2` | maximize | `9.749630028571` | `1.389963462368` | eV |
| `xtb_homo_lumo_gap_minimize_0p0_5p0_v2` | minimize | `1.389963462368` | `9.749630028571` | eV |
| `xtb_dipole_moment_maximize_3p0_10p0_v2` | maximize | `13.374` | `3.320` | D |

The dipole-max profile is shared by tasks 005 and 006 because they use the same
verifier, property, direction, unit, and hard electronic-state policy. The
ordered controls and literature citations are part of the dossier; no legacy
bound remains in the approved provenance.

## 3. Pending Decisions

No value in this section may be copied from its v1 profile without independent approval.

### 3.1 xTB unresolved profile inventory

The current xTB pack contains 21 scoring profiles after the dipole-max profile
reuse above. The relaxation-quality, imaginary-frequency, five window profiles,
and the three profiles in section 2.8 are approved, leaving these 11 profiles
unresolved. All 11 require literature-supported `T/B` research.

#### T/B anchors: 11 profiles

- `xtb_lumo_energy_minimize_neg_9p0_neg_6p0_v1` (task 008): LUMO-energy minimize.
- `xtb_polarizability_per_heavy_atom_maximize_4p0_12p0_v1` (task 009): polarizability per heavy atom maximize.
- `xtb_alpb_water_hexane_selectivity_maximize_0p0_0p35_v1` (task 010): ALPB selectivity maximize.
- `xtb_global_electrophilicity_maximize_0p5_3p8_v1` (task 011): global electrophilicity maximize.
- `xtb_max_f_plus_on_carbon_maximize_0p05_0p35_v1` (task 012): maximum carbon-site `f+` maximize.
- `xtb_f_plus_contrast_maximize_0p0_0p15_v1` (task 012): carbon-site `f+` contrast maximize.
- `xtb_entropy_298_per_heavy_atom_maximize_50p0_80p0_v1` (task 013): entropy per heavy atom maximize.
- `xtb_dipole_moment_minimize_0p0_20p0_v1` (task 014): fixed-formula dipole minimize.
- `xtb_homo_lumo_gap_minimize_0p0_10p0_v1` (tasks 015 and 016): exact-composition gap minimize.
- `xtb_total_energy_minimize_neg_50p3_neg_50p25_v1` (task 017): ROY same-molecule single-point energy.
- `xtb_total_energy_minimize_neg_148p2_neg_148p15_v1` (task 018): Ritonavir same-molecule optimized energy.

The v1 suffixes above identify current profiles only; none of their legacy numbers are approved for v2.

### 3.2 xTB literature and protocol requirements

For each unresolved xTB profile requiring `T/B`, the literature investigation must produce two distinct anchors:

- `T`: an excellent literature-supported level in the task's optimization direction;
- `B`: a literature-supported baseline, weak level, or failure-side reference.

The research record must cite the literature source, identify the reference compounds or structures, explain why they represent excellent and baseline levels, and record their recomputed values under the frozen GFN2-xTB benchmark protocol. Window profiles are excluded from this T/B research requirement because their widths are fixed by the target-window rule above.

For ROY and Ritonavir, literature may identify relevant conformers or structures, but only same-molecule GFN2-xTB energies from the frozen single-point or optimization protocol may become numeric anchors.

## 4. Approval Gate for Remaining Profiles

Each pending profile must have a parameter dossier containing:

- property, units, verifier id and protocol hash;
- hard-domain and electronic-state assumptions;
- proposed full-score target or region;
- proposed zero-score anchor on every active side;
- named target/reference and zero/reference artifacts, or a cited scientific/engineering boundary;
- scores for the target reference, zero reference, and at least one ordered intermediate control;
- expanded-distribution diagnostics used only as validation;
- reviewer, review date, decision, and provenance hash.

A profile is approved only when the dossier demonstrates:

1. correct units and monotonic direction;
2. full score for the declared success reference where such a reference is required;
3. zero score for the declared failure reference or boundary;
4. expected ordering for intermediate controls;
5. no dependence on participant submissions or leaderboard outcomes;
6. no accidental reuse across different verifier protocols.

## 5. Planned Implementation Changes

Implementation must not begin by editing v1 profile values. Once all formal-pack parameters are approved:

- [ ] Add explicit support for `linear_goal_v2` while preserving the ability to identify historical v1 results.
- [ ] Remove hard-coded `linear_goal_v1` result metadata and propagate the loaded pack scoring version.
- [ ] Add v2 profile ids and approved provenance; do not overwrite v1 release artifacts.
- [ ] Strengthen profile validation so formal v2 profiles require approved review metadata and evidence identifiers.
- [ ] Prevent legacy constraint migration from being treated as v2 parameter approval.
- [ ] Update task prompts and public scoring documentation wherever a newly approved full-score or zero-score boundary is user-visible.
- [ ] Update the xTB calibration duplicate pack to reference the same v2 profiles as matching formal tasks.
- [ ] Add boundary, midpoint, profile-reuse, provenance, release, and regression tests.
- [ ] Build a new release with v2 scoring-profile hashes and verify that v0.2.0 remains unchanged.

Likely implementation files include:

- `src/verifier_grounded_benchmark/task/schema/common.py`
- `src/verifier_grounded_benchmark/task/loader.py`
- `src/verifier_grounded_benchmark/evaluation/property_calculation/evaluator.py`
- task-pack `tasks.yaml` files under `src/verifier_grounded_benchmark/task/packs/`
- `src/verifier_grounded_benchmark/task/calibration/xtb/tasks.yaml`
- scoring, loader, evaluation, release, and task-pack tests under `tests/`
- track documentation under `docs/tracks/`

## 6. Verification and Commit Discipline

For every implementation change:

1. Run focused tests for the changed scorer, schema, evaluator, or task pack.
2. Run the full test suite with `uv run pytest`.
3. Confirm formal v2 packs contain no provisional profile and no legacy-derived provenance.
4. Confirm historical v1 release checksums and artifacts are unchanged.
5. Create a focused git commit only after the tests pass.

## 7. Discussion Order

Resolve the pending values in this order so later choices can reuse earlier anchors consistently:

1. xTB gap and dipole literature references, targets, and anchors.
2. Remaining xTB advanced-property literature references, targets, and anchors.
3. ROY and Ritonavir literature conformers, protocol-specific energy targets and anchors, and energy scales.
