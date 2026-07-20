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

The RDKit logP target task is not a window task. Its target remains `3.0`, but its left and right decay widths remain pending.

### 2.5 xTB full-score windows fixed by task statements

The following xTB full-score windows remain unchanged. Their decay anchors are pending literature review together with the other xTB profiles.

| Property/task usage | Fixed full-score window |
| --- | --- |
| xTB gap, task 001 | `[3.5, 5.5] eV` |
| xTB dipole, task 002 | `[3.0, 5.5] D` |
| xTB gap, task 007 | `[2.5, 4.2] eV` |
| xTB dipole, task 007 | `[3.5, 6.0] D` |
| xTB dipole, task 009 | `[3.0, 8.0] D` |

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

## 3. Pending Decisions

No value in this section may be copied from its v1 profile without independent approval.

### 3.1 RDKit target decay anchors

- logP target `3.0`: lower and upper zero-score anchors.

### 3.2 xTB main-property profiles

- Window decay anchors for gap and dipole tasks 001, 002, 007, and 009.
- Targets and anchors for gap maximize/minimize tasks 003, 004, 006, 015, and 016.
- Targets and anchors for dipole maximize/minimize tasks 005, 006, and 014.
- Targets and anchors for LUMO, polarizability per heavy atom, ALPB selectivity, global electrophilicity, carbon `f+`, `f+` contrast, and entropy per heavy atom.
- Molecule- and protocol-specific targets and anchors for ROY and Ritonavir total energies.

The current v1 values remain calibration evidence only. They are not approved defaults.

For each xTB profile, the literature investigation must produce two distinct anchors:

- `T`: an excellent literature-supported level in the task's optimization direction;
- `B`: a literature-supported baseline, weak level, or failure-side reference.

The research record must cite the literature source, identify the reference compounds or structures, explain why they represent excellent and baseline levels, and record their recomputed values under the frozen GFN2-xTB benchmark protocol. For window tasks, literature must likewise support a failure-side reference on each active side; the prompt-defined full-score window itself remains unchanged.

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

1. xTB gap and dipole literature references, targets, anchors, and window decay relationships.
2. Remaining xTB advanced-property literature references, targets, and anchors.
3. ROY and Ritonavir literature conformers, protocol-specific energy references, and energy scales.
4. RDKit logP target decay anchors.
