# xTB Real-Dataset Property Distributions

## Environment

- Date: 2026-06-15
- Repository branch: `codex/xtb-next-property-tasks`
- Python: project `uv` environment, Python 3.12
- xTB executable: `/opt/homebrew/bin/xtb`
- xTB version: 6.7.1 (`edcfbbe`, compiled 2025-09-04)
- Environment smoke test: `uv run python scripts/check_xtb_env.py` returned `status: ok`; water smoke parsed gap, dipole, LUMO, polarizability, and total energy.

## Smoke Issue Review

The first smoke run exposed workflow issues rather than an xTB installation failure.

| Issue | Evidence | Root cause | Fix |
| --- | --- | --- | --- |
| Medium tier reported 3 verifier/tool errors | 2 Fukui failures and 1 GFN1/IPEA abnormal termination in the first 20 QM9 records | The first-20 sample included molecules outside the effective carbon-site/Fukui calibration slice and was too brittle for medium-tier smoke | Rerun used a deterministic 60-record QM9 subset with carbon-containing, hessian-domain-compatible molecules. Runner now records per-property status instead of only row-level status. |
| Expensive tier reported 17 domain errors | 17 of 20 records failed hessian `atom_count` or `heavy_atom_count` domain | The broad sample was not hessian-domain-aware | Runner now pre-skips hessian-domain-ineligible properties as `domain_skip`; rerun input was selected to satisfy hessian structural bounds. |
| Analyzer overstated property error rates | One tier row failure was counted against every property in that tier | Analyzer counted row status, not property status | Analyzer now uses `property_statuses` when available and reports property-level ok/error/skipped counts. |
| Report over-interpreted smoke failures | `needs_parser_or_runtime_fix` was assigned to several tasks from a 20-record brittle sample | Failure classification mixed sampling/domain issues with actual parser/tool failures | Updated recommendations distinguish smoke workflow fixes from threshold evidence needs. |

## Dataset Availability

This run completed a runtime-bounded QM9 smoke pilot and did not complete the full planned multi-dataset quotas. Raw downloaded data and derived artifacts remain under ignored paths (`.cache/` and `artifacts/`) and are not committed.

| Dataset | Status | Records available | Eligible after domain filter | Notes |
| --- | --- | ---: | ---: | --- |
| QM9 | available | 60 normalized records used from a local `gdb9.sdf` conversion | 60 | Downloaded `gdb9.tar.gz` from DeepChem S3 into `.cache/xtb_real_datasets/qm9/`; converted deterministic carbon-containing, hessian-domain-compatible records from `gdb9.sdf`. |
| QMugs | unavailable | 0 | 0 | ETH Research Collection endpoint did not return a usable small programmatic subset within the runtime window; full dataset scale is not appropriate for automatic download in this task. |
| GEOM-Drugs | unavailable | 0 | 0 | Harvard Dataverse metadata resolved, but available files are 132 MB to 50 GB; no small drug subset was downloaded in this run. |
| Tartarus/OPV | unavailable | 0 | 0 | No reproducible small OPV subset was fetched during this run; coverage is `not_available`. |

## Sampling Method

The rerun normalized 60 QM9 SDF records with fields required by `scripts/prepare_xtb_real_dataset_sample.py`: `dataset_name`, `record_id`, `xyz`, `charge`, `multiplicity`, and `geometry_source`. The deterministic smoke input selected records with at least one carbon atom, heavy atom count between 4 and 18, and atom count between 6 and 48 to exercise Fukui and hessian tiers without predictable domain failures. Sampling used seed `20260615`.

Preparation command:

```bash
uv run python scripts/prepare_xtb_real_dataset_sample.py \
  --source-manifest data/xtb_real_dataset_sources.yaml \
  --input-jsonl .cache/xtb_real_datasets/qm9/qm9_smoke60.jsonl \
  --output-dir artifacts/xtb_real_distribution/2026-06-15-rerun \
  --seed 20260615 \
  --pilot
```

The pilot quota remains underfilled: 60 QM9 records were available in this rerun versus the 500-record QM9 light pilot target.

## Domain Filter Results

General xTB direct-XYZ filtering accepted all 60 normalized QM9 records:

| Dataset | Raw records | Filtered records | Sampled records | Rejected records |
| --- | ---: | ---: | ---: | ---: |
| QM9 | 60 | 60 | 60 | 0 |

The rerun input was hessian-domain-aware, so the expensive tier had no domain skips.

## Property Distribution Summary

Rerun tier results:

| Tier | Rows | OK | Partial | Errors | Skipped |
| --- | ---: | ---: | ---: | ---: | ---: |
| light | 60 | 60 | 0 | 0 | 0 |
| medium | 60 | 60 | 0 | 0 | 0 |
| expensive | 60 | 60 | 0 | 0 | 0 |

Key QM9 rerun quantiles:

| Property | N | P5 | P50 | P95 | Mean | Error rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `homo_lumo_gap` | 60 | 2.357 | 5.158 | 12.610 | 6.302 | 0.00 |
| `dipole_moment` | 60 | 0.000 | 2.619 | 5.389 | 2.603 | 0.00 |
| `lumo_energy` | 60 | -8.698 | -5.607 | 1.428 | -4.687 | 0.00 |
| `polarizability_per_heavy_atom` | 60 | 8.602 | 9.952 | 11.694 | 10.053 | 0.00 |
| `relaxation_energy` | 60 | 0.009 | 0.019 | 0.037 | 0.021 | 0.00 |
| `alpb_water_hexane_selectivity` | 60 | -0.108 | 0.075 | 0.373 | 0.088 | 0.00 |
| `global_electrophilicity` | 60 | 0.313 | 0.642 | 1.641 | 0.749 | 0.00 |
| `max_f_plus_on_carbon` | 60 | -0.021 | 0.188 | 0.277 | 0.159 | 0.00 |
| `f_plus_contrast` | 60 | -0.207 | -0.014 | 0.137 | -0.045 | 0.00 |
| `imaginary_frequency_count` | 60 | 0.000 | 0.000 | 1.000 | 0.150 | 0.00 |
| `entropy_298_per_heavy_atom` | 60 | 54.515 | 65.298 | 75.229 | 66.301 | 0.00 |

No light-tier record failed the relaxation-energy gate; all 60 relaxation energies were below 0.35 eV. Nine of 60 hessian calculations had one imaginary frequency, so the hessian stability-gate failure fraction was 0.15 in this smoke subset.

## Per-Task Threshold Implications

The rerun is cleaner than the first smoke, but it is still too small and QM9-only to justify threshold changes.

| Task | Recommendation | Rationale |
| --- | --- | --- |
| `xtb_gap_window_001` | `needs_more_data` | QM9 gap distribution is broad, but drug-like and materials slices are missing. |
| `xtb_dipole_window_002` | `needs_more_data` | Dipole values are plausible with no run failures; more source coverage is needed. |
| `xtb_gap_max_003` | `needs_more_data` | High-gap tail exists in QM9, but saturation risk requires larger broad sampling. |
| `xtb_gap_min_004` | `needs_more_data` | Low-gap conclusions need OPV/materials-biased coverage. |
| `xtb_dipole_max_005` | `needs_more_data` | High-dipole drug-like structures are not represented by this QM9-only subset. |
| `xtb_low_gap_high_dipole_opt_006` | `needs_more_data` | Multi-objective tails require larger and more diverse samples. |
| `xtb_gap_dipole_window_007` | `needs_more_data` | Joint gap/dipole density cannot be inferred from 60 QM9 records. |
| `xtb_lumo_min_008` | `needs_more_data` | LUMO values span a wide range, but acceptor-biased drug/materials subsets are missing. |
| `xtb_polarizability_dipole_opt_009` | `needs_more_data` | Larger flexible molecules are missing. |
| `xtb_solvation_selectivity_alpb_010` | `needs_more_data` | Rerun had 60/60 successful ALPB selectivity values, but source coverage is still narrow. |
| `xtb_electrophilicity_max_011` | `needs_more_data` | Rerun had 60/60 successful electrophilicity values; broader chemistry is needed before threshold action. |
| `xtb_fukui_carbon_site_012` | `needs_more_data` | Rerun had 60/60 successful carbon Fukui values after carbon-aware sampling; task calibration still needs diverse carbon-rich molecules. |
| `xtb_hessian_thermo_stability_013` | `needs_more_data` | Hessian tier ran cleanly, but one-source smoke data is not enough for thermochemistry thresholds. |

## Failure and Runtime Analysis

The rerun failure summary is empty:

| Dataset | Failure type | Count | Notes |
| --- | --- | ---: | --- |
| QM9 | none | 0 | All light, medium, and expensive tier properties completed for all 60 records. |

The remaining chemistry signal to track is hessian stability: 15% of the hessian-domain smoke records had one imaginary frequency. That is not a parser/runtime failure; it should be handled as a property distribution and stability-gate statistic in larger runs.

## Recommended Threshold Follow-Ups

1. Add a dataset acquisition/conversion pass for at least one drug-like source before revisiting thresholds.
2. Keep property-level status accounting in all distribution runs; row-level status is too coarse for multi-property tiers.
3. Use tier-aware sampling: hessian-domain records for expensive tier, carbon-containing records for Fukui statistics, and broad samples for light tier.
4. Once source coverage is available, run the planned expanded counts: 10,000-30,000 light, 2,000-5,000 medium, and 500-1,000 expensive records.

## Expanded Run

Expanded execution was not run in this pass. The selected expanded sizes are deferred until at least one additional source family is available:

| Tier | Planned expanded range | Selected count for next run | Decision |
| --- | ---: | ---: | --- |
| light | 10,000-30,000 | 10,000 | Use the low end after QM9 plus at least one drug-like dataset are available. |
| medium | 2,000-5,000 | 2,000 | Use the low end with carbon-aware Fukui sampling and at least one drug-like dataset. |
| expensive | 500-1,000 | 500 | Use the low end with hessian-domain-aware sampling only. |

Rationale: the rerun fixed smoke workflow issues and removed runtime failures, but it still covers only 60 QM9 records. Running expanded commands against only this source would scale a biased sample rather than improve threshold evidence.

## Limitations

- This is a smoke pilot, not the full real-dataset distribution study.
- Only 60 normalized QM9 SDF records were used in the rerun.
- QMugs, GEOM-Drugs, and OPV coverage are unavailable in this report.
- Score-threshold fractions were not computed against official task constraints in this run; the analyzer currently reports property quantiles and failure diagnostics.
- Generated artifacts are intentionally uncommitted; the committed deliverable is this report plus reproducible scripts and tests.
