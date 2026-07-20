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

### 2.4 Full-score regions fixed by task statements

The following full-score regions are already part of the task definition and remain unchanged in v2. This decision does not approve their pending decay widths.

| Property/task usage | Type | Fixed full-score region or target | Decay status |
| --- | --- | --- | --- |
| RDKit logP window, tasks 003 and 009 | window | `[1.0, 3.0]` | pending |
| RDKit TPSA window, tasks 004 and 009 | window | `[35.0, 75.0] angstrom^2` | pending |
| RDKit HBA window, tasks 005 and 010 | window | integer `[2, 4]` | pending |
| RDKit HBD window, tasks 006 and 010 | window | integer `[1, 2]` | pending |
| RDKit logP target, task 011 | target | `3.0` | pending |
| RDKit force-field energy range | window | `[0.0, 20.0] kcal/mol`; lower side inactive | upper width pending |
| xTB gap window, task 001 | window | `[3.5, 5.5] eV` | pending |
| xTB dipole window, task 002 | window | `[3.0, 5.5] D` | pending |
| xTB gap window, task 007 | window | `[2.5, 4.2] eV` | pending |
| xTB dipole window, task 007 | window | `[3.5, 6.0] D` | pending |
| xTB dipole window, task 009 | window | `[3.0, 8.0] D` | pending |

Repeated uses of the same property, verifier protocol, and task semantics must reference the same approved profile. In particular, RDKit tasks 003/009, 004/009, 005/010, and 006/010 must not duplicate parameter definitions.

### 2.5 Property Calculation fixed answers

The following task answers remain fixed, but their numeric decay tolerances are not approved:

| Property | Fixed gold | Scoring primitive | Tolerance status |
| --- | --- | --- | --- |
| `free_energy_difference` | `0.258031679 kJ/mol` | numeric gold | pending protocol and error budget |
| `potential_energy_difference` | `0.079 eV` | numeric gold | pending protocol and error budget |
| `ambient_pressure_phase` | exact string `alpha` | exact string | fully determined |
| `high_pressure_phase` | exact string `beta` | exact string | fully determined |

The numeric values are frozen task data, not evidence that the existing `0.001` tolerances are valid.

## 3. Pending Decisions

No value in this section may be copied from its v1 profile without independent approval.

### 3.1 RDKit decay anchors

- logP window `[1.0, 3.0]`: lower and upper zero-score anchors.
- TPSA window `[35.0, 75.0]`: lower and upper zero-score anchors.
- HBA window `[2, 4]`: lower and upper integer zero-score anchors.
- HBD window `[1, 2]`: lower and upper integer zero-score anchors.
- logP target `3.0`: lower and upper zero-score anchors.
- Experimental force-field energy range `[0.0, 20.0] kcal/mol`: upper zero-score anchor.

### 3.2 xTB main-property profiles

- Window decay anchors for gap and dipole tasks 001, 002, 007, and 009.
- Targets and anchors for gap maximize/minimize tasks 003, 004, 006, 015, and 016.
- Targets and anchors for dipole maximize/minimize tasks 005, 006, and 014.
- Targets and anchors for LUMO, polarizability per heavy atom, ALPB selectivity, global electrophilicity, carbon `f+`, `f+` contrast, and entropy per heavy atom.
- Molecule- and protocol-specific targets and anchors for ROY and Ritonavir total energies.

The current v1 values remain calibration evidence only. They are not approved defaults.

### 3.3 Property Calculation tolerances

The existing symmetric `0.001 kJ/mol` and `0.001 eV` values are not approved. Before selecting `tauL/tauU`, record:

- the gold-generation method and software versions;
- convergence parameters and numerical repeatability;
- whether the expected answer is a protocol reproduction or a scientific estimate;
- the reporting precision required by the prompt;
- an error budget that distinguishes numerical precision from method discrepancy.

If the calculation is directionally asymmetric, `tauL` and `tauU` may differ, but the asymmetry must be justified by that error budget.

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

1. RDKit window and target decay anchors.
2. xTB gap and dipole targets, anchors, and window decay relationships.
3. Remaining xTB advanced-property targets and anchors.
4. ROY and Ritonavir conformer-energy references and energy scales.
5. Property Calculation gold protocols and numeric tolerances.
6. Experimental RDKit force-field upper decay anchor.
