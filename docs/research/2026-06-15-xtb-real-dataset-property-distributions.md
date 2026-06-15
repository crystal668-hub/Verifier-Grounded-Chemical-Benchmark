# xTB Real-Dataset Property Distributions

## Environment

- Date: 2026-06-15
- Repository branch: `codex/xtb-next-property-tasks`
- Python: project `uv` environment, Python 3.12
- xTB executable: `/opt/homebrew/bin/xtb`
- xTB version: 6.7.1 (`edcfbbe`, compiled 2025-09-04)
- Environment smoke test: `uv run python scripts/check_xtb_env.py` returned `status: ok`; water smoke parsed gap, dipole, LUMO, polarizability, and total energy.

## Dataset Availability

This run completed a runtime-bounded QM9 pilot and did not complete the full planned multi-dataset quotas. Raw downloaded data and derived artifacts remain under ignored paths (`.cache/` and `artifacts/`) and are not committed.

| Dataset | Status | Records available | Eligible after domain filter | Notes |
| --- | --- | ---: | ---: | --- |
| QM9 | available | 20 normalized records used from a local `gdb9.sdf` conversion | 20 | Downloaded `gdb9.tar.gz` from DeepChem S3 into `.cache/xtb_real_datasets/qm9/`; converted first 20 SDF records to normalized JSONL for smoke pilot. |
| QMugs | unavailable | 0 | 0 | ETH Research Collection endpoint did not return a usable small programmatic subset within the runtime window; full dataset scale is not appropriate for automatic download in this task. |
| GEOM-Drugs | unavailable | 0 | 0 | Harvard Dataverse metadata resolved, but available files are 132 MB to 50 GB; no small drug subset was downloaded in this run. |
| Tartarus/OPV | unavailable | 0 | 0 | No reproducible small OPV subset was fetched during this run; coverage is `not_available`. |

## Sampling Method

The normalized QM9 records used fields required by `scripts/prepare_xtb_real_dataset_sample.py`: `dataset_name`, `record_id`, `xyz`, `charge`, `multiplicity`, and `geometry_source`. Sampling used seed `20260615`.

Preparation command:

```bash
uv run python scripts/prepare_xtb_real_dataset_sample.py \
  --source-manifest data/xtb_real_dataset_sources.yaml \
  --input-jsonl .cache/xtb_real_datasets/qm9/qm9_first20.jsonl \
  --output-dir artifacts/xtb_real_distribution/2026-06-15 \
  --seed 20260615 \
  --pilot
```

The pilot quota was underfilled by design: 20 QM9 records were available in this smoke run versus the 500-record QM9 light pilot target.

## Domain Filter Results

General xTB direct-XYZ domain filtering accepted all 20 normalized QM9 records:

| Dataset | Raw records | Filtered records | Sampled records | Rejected records |
| --- | ---: | ---: | ---: | ---: |
| QM9 | 20 | 20 | 20 | 0 |

For the hessian tier, only 3 of 20 records satisfied the stricter hessian domain; 17 records failed `atom_count` or `heavy_atom_count` domain checks.

## Property Distribution Summary

Pilot tier results:

| Tier | Rows | OK | Errors | Runtime sum |
| --- | ---: | ---: | ---: | ---: |
| light | 20 | 20 | 0 | 18.8 s |
| medium | 20 | 17 | 3 | 16.9 s |
| expensive | 20 | 3 | 17 | 6.5 s |

Key QM9 pilot quantiles:

| Property | N | P5 | P50 | P95 | Mean | Error rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `homo_lumo_gap` | 20 | 3.925 | 8.203 | 15.594 | 9.286 | 0.00 |
| `dipole_moment` | 20 | 0.000 | 2.024 | 4.392 | 2.036 | 0.00 |
| `lumo_energy` | 20 | -7.237 | -3.091 | 3.704 | -2.088 | 0.00 |
| `polarizability_per_heavy_atom` | 20 | 9.121 | 10.572 | 14.376 | 11.086 | 0.00 |
| `relaxation_energy` | 20 | 0.005 | 0.009 | 0.027 | 0.013 | 0.00 |
| `alpb_water_hexane_selectivity` | 20 | -0.066 | 0.045 | 0.413 | 0.109 | 0.15 |
| `global_electrophilicity` | 19 | 0.299 | 0.524 | 0.976 | 0.562 | 0.15 |
| `max_f_plus_on_carbon` | 18 | -0.056 | 0.216 | 0.377 | 0.142 | 0.15 |
| `f_plus_contrast` | 18 | -0.313 | -0.093 | 0.167 | -0.103 | 0.15 |
| `imaginary_frequency_count` | 3 | 0.000 | 0.000 | 0.900 | 0.333 | 0.85 |
| `entropy_298_per_heavy_atom` | 3 | 69.131 | 70.134 | 73.342 | 70.951 | 0.85 |

## Per-Task Threshold Implications

The pilot is too small and too QM9-only to justify threshold changes. Every task recommendation is therefore conservative.

| Task | Recommendation | Rationale |
| --- | --- | --- |
| `xtb_gap_window_001` | `needs_more_data` | QM9 gap distribution was broad, but only 20 small-molecule records were sampled and no drug-like/materials slice was available. |
| `xtb_dipole_window_002` | `needs_more_data` | Dipole values look plausible, but sample size and source coverage are insufficient. |
| `xtb_gap_max_003` | `needs_more_data` | The high-gap tail exists in QM9, but this smoke pilot cannot estimate broad real-dataset saturation. |
| `xtb_gap_min_004` | `needs_more_data` | QM9 first records do not represent low-gap chemical space. OPV/materials coverage is missing. |
| `xtb_dipole_max_005` | `needs_more_data` | More QMugs/GEOM coverage is needed for high-dipole drug-like structures. |
| `xtb_low_gap_high_dipole_opt_006` | `needs_more_data` | Multi-objective tails require much larger and more diverse samples. |
| `xtb_gap_dipole_window_007` | `needs_more_data` | Joint gap/dipole density cannot be inferred from 20 QM9 records. |
| `xtb_lumo_min_008` | `needs_more_data` | LUMO spread is large in the smoke sample, but no drug-like acceptor-biased subset was available. |
| `xtb_polarizability_dipole_opt_009` | `needs_more_data` | Polarizability per heavy atom is stable in this small slice; larger flexible molecules are missing. |
| `xtb_solvation_selectivity_alpb_010` | `needs_parser_or_runtime_fix` | Medium tier had 15% verifier/tool failures, above the 5% rule-of-thumb threshold. |
| `xtb_electrophilicity_max_011` | `needs_parser_or_runtime_fix` | One GFN1/IPEA property run failed with xTB abnormal termination in the 20-record pilot. |
| `xtb_fukui_carbon_site_012` | `needs_parser_or_runtime_fix` | Two records did not produce parseable carbon Fukui properties; medium-tier failure rate exceeded 5%. |
| `xtb_hessian_thermo_stability_013` | `needs_more_data` | Only 3 records entered the hessian domain; hessian-domain sampling must be stratified before threshold conclusions. |

## Failure and Runtime Analysis

Failure summary:

| Dataset | Failure type | Count | Notes |
| --- | --- | ---: | --- |
| QM9 | `verifier_tool_error` | 3 | Two Fukui calculations did not expose required carbon-site properties; one electrophilicity property run ended with xTB abnormal termination. |
| QM9 | `domain_error` | 17 | Hessian-domain structural restriction rejected small records before hessian calculation. |

No light-tier record failed the relaxation-energy gate; all 20 relaxation energies were below 0.35 eV. Among the three hessian-domain records, one had one imaginary frequency.

## Recommended Threshold Follow-Ups

1. Add a dataset acquisition/conversion pass for at least one drug-like source before revisiting thresholds.
2. Improve medium-tier failure triage: distinguish expected no-carbon Fukui/domain cases from true parser/tool failures, and add a pre-check for Fukui carbon eligibility if the task requires carbon-site statistics.
3. Add hessian-domain-aware sampling so expensive tier quotas are selected from eligible molecules instead of relying on broad pilot records.
4. Once source coverage is available, run the planned expanded counts: 10,000-30,000 light, 2,000-5,000 medium, and 500-1,000 expensive records.

## Expanded Run

Expanded execution was not run in this pass. The selected expanded sizes are deferred until two prerequisites are met:

| Tier | Planned expanded range | Selected count for next run | Decision |
| --- | ---: | ---: | --- |
| light | 10,000-30,000 | 10,000 | Use the low end after QM9 plus at least one drug-like dataset are available. |
| medium | 2,000-5,000 | 2,000 | Use the low end after medium-tier parser/tool triage reduces failure rate below 5%. |
| expensive | 500-1,000 | 500 | Use the low end with hessian-domain-aware sampling only. |

Rationale: the pilot covered only 20 QM9 records, medium-tier failure rate was 15%, and hessian-domain eligibility was 3/20. Running the expanded commands against this source mix would scale a biased sample rather than improve threshold evidence. The next expanded run should first add a reproducible QMugs or GEOM-derived normalized JSONL input and select the hessian tier from records known to satisfy the stricter hessian domain.

## Limitations

- This is a smoke pilot, not the full real-dataset distribution study.
- Only the first 20 normalized QM9 SDF records were used.
- QMugs, GEOM-Drugs, and OPV coverage are unavailable in this report.
- Score-threshold fractions were not computed against official task constraints in this run; the analyzer currently reports property quantiles and failure diagnostics.
- Generated artifacts are intentionally uncommitted; the committed deliverable is this report plus reproducible scripts and tests.
