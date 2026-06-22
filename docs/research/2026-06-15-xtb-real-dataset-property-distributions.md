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
| QMugs | structure_archive_incomplete | 0 | 0 | The official Nextcloud structures endpoint is reachable enough to advertise a `7,180,016,346` byte `structures.tar.gz` and start a bounded download, but the local archive is still partial. Ancillary metadata access is mixed or stale in the latest probe: `download_links.txt` and `tarball_assignment.csv` returned HTTP 401, so normalization remains blocked until the structure archive is complete and usable. |
| GEOM-Drugs | validation_archive_no_sdf_members | 0 | 0 | Harvard Dataverse metadata resolved and lists downloadable files. The later bounded retry completed `censo.tar.gz`, but the archive contains `censo/rd_mols/*.pickle` members and no `.sdf` members for the current SDF converter; drug subset files remain too large for automatic download. |
| Tartarus/OPV | manual_or_generated_geometry_required | 0 | 0 | No license-compatible 3D OPV subset was fetched. OPV coverage needs an explicit source plus generated-geometry labeling before xTB calibration. |

## Dataset Access Repair Notes

The initial "unavailable" diagnosis conflated three different problems:

| Source | What failed before | Repair attempted | Current status |
| --- | --- | --- | --- |
| QMugs | ETH landing/API access timed out and full dataset scale looked prohibitive | Retried the official Nextcloud public structures endpoint with share token `X5vOBNSITAG5vzM`; the endpoint reported the full archive size and accepted a bounded resumable download | Structure access is partially validated, but the archive download is incomplete and ancillary metadata access is mixed or stale after HTTP 401 responses for `download_links.txt` and `tarball_assignment.csv`. |
| GEOM-Drugs | Only large Dataverse files were considered | Queried Dataverse API and identified small `censo.tar.gz` validation file plus large drug files; later retried the small validation archive with resume | Transfer for the small archive completed, but it is not an SDF-bearing archive, so GEOM still provides zero normalized records for this report. |
| Tartarus/OPV | No direct 3D molecule source was identified | Marked source as requiring manual or generated geometry with explicit provenance | Still not ready for automatic calibration. |

New repair tooling:

```bash
uv run python scripts/convert_xtb_real_dataset_sdf.py \
  --input <local.sdf-or-tar.gz> \
  --dataset-name qmugs \
  --output-jsonl .cache/xtb_real_datasets/qmugs/qmugs_sample.jsonl \
  --limit 1000
```

The converter accepts local SDF files and tar/tar.gz archives containing SDF files, emits the normalized JSONL schema consumed by `scripts/prepare_xtb_real_dataset_sample.py`, and allows bounded conversion with `--limit`.

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

1. Complete a bounded QMugs structure-cache download or streaming conversion, then rerun with at least one drug-like source before revisiting thresholds.
2. Keep property-level status accounting in all distribution runs; row-level status is too coarse for multi-property tiers.
3. Use tier-aware sampling: hessian-domain records for expensive tier, carbon-containing records for Fukui statistics, and broad samples for light tier.
4. Once source coverage is available, run the planned expanded counts: 10,000-30,000 light, 2,000-5,000 medium, and 500-1,000 expensive records.

## Expanded Run

Expanded execution was not run in this pass. The selected expanded sizes are deferred until at least one additional source family is available:

| Tier | Planned expanded range | Selected count for next run | Decision |
| --- | ---: | ---: | --- |
| light | 10,000-30,000 | 10,000 | Use the low end after QM9 plus a bounded QMugs or GEOM normalized JSONL sample are available. |
| medium | 2,000-5,000 | 2,000 | Use the low end with carbon-aware Fukui sampling and a bounded drug-like source. |
| expensive | 500-1,000 | 500 | Use the low end with hessian-domain-aware sampling only. |

Rationale: the rerun fixed smoke workflow issues and removed runtime failures, but it still covers only 60 QM9 records. Running expanded commands against only this source would scale a biased sample rather than improve threshold evidence.

## Limitations

- This is a smoke pilot, not the full real-dataset distribution study.
- Only 60 normalized QM9 SDF records were used in the rerun.
- The QMugs structure endpoint and GEOM Dataverse metadata are partially reachable, but QMugs ancillary metadata access is mixed or stale and no non-QM9 3D records were normalized or run through xTB in this report.
- Score-threshold fractions were not computed against official task constraints in this run; the analyzer currently reports property quantiles and failure diagnostics.
- Generated artifacts are intentionally uncommitted; the committed deliverable is this report plus reproducible scripts and tests.

## Dataset Expansion Prep Input Status

The 2026-06-16 bounded acquisition pass produced `artifacts/xtb_real_distribution/2026-06-15-expansion-prep/source_availability.local.json` and `artifacts/xtb_real_distribution/2026-06-15-expansion-prep/source_availability.remote.json`. The availability inspector completed with `remote_checked: true` and recorded per-file access results and failures: the QMugs structures endpoint advertised `7,180,016,346` bytes, while `qmugs/download_links.txt` and `qmugs/tarball_assignment.csv` returned HTTP 401 and GEOM `censo.tar.gz` returned HTTP 403 in that metadata probe.

| Source | Prep status | Normalized records | Decision |
| --- | --- | ---: | --- |
| QM9 | available | 60 | Keep as baseline source. |
| QMugs | blocked_or_underfilled | 0 | Do not run Expanded Run; complete QMugs archive conversion first. |
| GEOM-Drugs | validation_unavailable_or_no_sdf | 0 | Do not count GEOM toward coverage until a usable 3D archive is normalized. |
| Tartarus/OPV | manual_or_generated_geometry_required | 0 | Keep out of automatic calibration until provenance is explicit. |

Observed blockers: the bounded QMugs `structures.tar.gz` attempt timed out after 120 seconds with a partial `25,788,416` byte file, far below the advertised archive size, so `qmugs_structure_archive_incomplete` blocks normalization. The GEOM `censo.tar.gz` retry completed to `25,375,585` bytes and opens as a tar archive, but it contains `censo/rd_mols/*.pickle` members and zero `.sdf` members; the SDF converter returned `status: ok` with `written: 0`, so the current validation blocker is `geom_validation_no_sdf_members`.

## Dataset Expansion Prep Sample Build Decision

Intermediate mixed sample build status: `not_ready_for_intermediate_calibration`.

Reason: no non-QM9 normalized JSONL with records is available. The local `.cache/xtb_real_datasets/qmugs/qmugs_bounded.jsonl` file is missing (`0` records), and `.cache/xtb_real_datasets/geom_drugs/geom_validation.jsonl` exists but is `0` bytes with `0` records. QMugs remains blocked by `qmugs_structure_archive_incomplete`; GEOM validation conversion produced `0` SDF-normalized records because `censo.tar.gz` contains pickle members and no `.sdf` members.

Next action: complete a usable QMugs structure archive conversion or add a GEOM pickle/conformer converter before building mixed intermediate samples. Keep Expanded Run blocked until at least one non-QM9 normalized JSONL has records.

## 2026-06-21 Blocking Repair and Intermediate Calibration

This section supersedes the previous `not_ready_for_intermediate_calibration` sample-build decision. The two blocking non-QM9 inputs are now accessible for bounded calibration without full dataset downloads:

| Source | Repair result | Normalized candidate records | Provenance |
| --- | --- | ---: | --- |
| QMugs | The partial local `structures.tar.gz` is stream-readable and contains usable SDF members even though the full 7.18 GB archive is not cached. | 600 | `.cache/xtb_real_datasets/qmugs/qmugs_partial_bounded600.jsonl`, `geometry_source=dataset_sdf_3d_partial_archive` |
| GEOM-Drugs | Added a GEOM censo pickle converter for `censo/rd_mols/*.pickle` members containing RDKit conformers. | 500 | `.cache/xtb_real_datasets/geom_drugs/geom_censo_bounded500.jsonl`, `geometry_source=geom_pickle_rdkit_conformer` |

QMugs conversion emitted RDKit warnings that some molecules were tagged as 2D despite nonzero Z coordinates. The normalized XYZ rows preserve the provided 3D coordinates, so the warning is recorded as source metadata inconsistency rather than a conversion failure.

Commands used for the bounded non-QM9 repair:

```bash
uv run python scripts/convert_xtb_real_dataset_sdf.py \
  --input .cache/xtb_real_datasets/qmugs/structures.tar.gz \
  --dataset-name qmugs \
  --output-jsonl .cache/xtb_real_datasets/qmugs/qmugs_partial_bounded600.jsonl \
  --record-id-property CHEMBL_ID \
  --geometry-source dataset_sdf_3d_partial_archive \
  --limit 600

uv run python scripts/convert_xtb_real_dataset_geom_pickle.py \
  --input .cache/xtb_real_datasets/geom_drugs/censo.tar.gz \
  --output-jsonl .cache/xtb_real_datasets/geom_drugs/geom_censo_bounded500.jsonl \
  --limit 500 \
  --max-conformers-per-molecule 1
```

The mixed intermediate sample preparation used QM9 plus both non-QM9 sources:

```bash
uv run python scripts/prepare_xtb_real_dataset_sample.py \
  --source-manifest data/xtb_real_dataset_sources.yaml \
  --input-jsonl .cache/xtb_real_datasets/qm9/qm9_smoke60.jsonl \
  --input-jsonl .cache/xtb_real_datasets/qmugs/qmugs_partial_bounded600.jsonl \
  --input-jsonl .cache/xtb_real_datasets/geom_drugs/geom_censo_bounded500.jsonl \
  --output-dir artifacts/xtb_real_distribution/2026-06-21-expansion-prep \
  --seed 20260615 \
  --intermediate
```

Sample preparation results:

| Metric | Count |
| --- | ---: |
| Raw normalized input records | 1,160 |
| Domain-filtered records | 817 |
| Unique mixed sampled records | 478 |
| Rejected records | 343 |

Filtered source coverage:

| Source | Filtered records |
| --- | ---: |
| QM9 | 60 |
| QMugs | 507 |
| GEOM-Drugs | 250 |

Tier-aware prepared files:

| Tier file | Rows | Dataset mix |
| --- | ---: | --- |
| `sampled_records.light.jsonl` | 810 | GEOM 250, QM9 60, QMugs 500 |
| `sampled_records.medium.jsonl` | 460 | GEOM 150, QM9 60, QMugs 250 |
| `sampled_records.expensive.jsonl` | 114 | GEOM 17, QM9 60, QMugs 37 |

The full 478-record light run was interrupted after about 10 minutes because the current runner executes each record/property verifier sequentially and was still in early light-tier verifier calls. For this staged delivery, balanced intermediate slices were generated while preserving all three sources:

| Slice | Rows | Dataset mix |
| --- | ---: | --- |
| Light | 60 | GEOM 20, QM9 20, QMugs 20 |
| Medium | 24 | GEOM 8, QM9 8, QMugs 8 |
| Expensive | 12 | GEOM 4, QM9 4, QMugs 4 |

Slice result files:

- `artifacts/xtb_real_distribution/2026-06-21-expansion-prep/light_slice_results.json`
- `artifacts/xtb_real_distribution/2026-06-21-expansion-prep/medium_slice_results.json`
- `artifacts/xtb_real_distribution/2026-06-21-expansion-prep/expensive_slice_results.json`
- `artifacts/xtb_real_distribution/2026-06-21-expansion-prep/analysis/expanded_run_readiness.json`
- `artifacts/xtb_real_distribution/2026-06-21-expansion-prep/intermediate_calibration_summary.json`

Intermediate xTB calibration result:

| Tier | Rows | OK | Partial | Errors | Skipped | Property-level error rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| light | 60 | 60 | 0 | 0 | 0 | 0.00 |
| medium | 24 | 24 | 0 | 0 | 0 | 0.00 |
| expensive | 12 | 12 | 0 | 0 | 0 | 0.00 |

Key intermediate quantiles across all slice sources:

| Property | N | P5 | P50 | P95 | Mean | Error rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `homo_lumo_gap` | 60 | 1.495 | 3.113 | 12.241 | 3.919 | 0.00 |
| `dipole_moment` | 60 | 0.001 | 4.214 | 8.142 | 4.108 | 0.00 |
| `lumo_energy` | 60 | -8.852 | -7.011 | 1.167 | -6.402 | 0.00 |
| `polarizability_per_heavy_atom` | 60 | 8.718 | 9.863 | 11.568 | 9.932 | 0.00 |
| `relaxation_energy` | 60 | 0.000 | 0.017 | 0.159 | 0.050 | 0.00 |
| `alpb_water_hexane_selectivity` | 24 | -0.319 | -0.119 | 0.218 | -0.096 | 0.00 |
| `global_electrophilicity` | 24 | 0.392 | 1.439 | 2.053 | 1.300 | 0.00 |
| `max_f_plus_on_carbon` | 24 | -0.000 | 0.079 | 0.286 | 0.107 | 0.00 |
| `f_plus_contrast` | 24 | -0.133 | 0.009 | 0.055 | -0.003 | 0.00 |
| `imaginary_frequency_count` | 12 | 0.000 | 0.000 | 0.450 | 0.083 | 0.00 |
| `entropy_298_per_heavy_atom` | 12 | 29.725 | 36.711 | 73.639 | 46.317 | 0.00 |

Expanded Run readiness artifact:

| Metric | Value |
| --- | ---: |
| Non-QM9 unique records with at least one OK property | 32 |
| Attempted properties | 420 |
| Error properties | 0 |
| Property error rate | 0.00 |
| Hessian runtime/parser failures | 0 |
| Blockers | `non_qm9_ok_records_below_100` |

Decision: `Dataset Expansion Prep / intermediate calibration` is now complete for a staged slice, and the previous data-access blocker is repaired enough to support larger bounded calibration. The project is still `not_ready` for the formal Expanded Run because the xTB-executed non-QM9 unique record count is below the 100-record readiness floor. The next step should be a larger bounded calibration run that targets at least 100 unique non-QM9 OK records, ideally after adding progress/checkpointing or batching support to the runner so the prepared 478-record mixed sample can complete without losing partial progress.

## 2026-06-22 Expanded Run Preparation

The next calibration pass added checkpoint/resume support to `scripts/run_xtb_real_dataset_distribution.py` and reran a larger non-QM9 light-tier slice. This directly addressed the previous readiness blocker, `non_qm9_ok_records_below_100`.

Runner preparation:

- Added `--resume`, `--checkpoint-every`, and `--progress-every`.
- Resume keys use `(tier, dataset_name, record_id)` and keep dataset names and tiers distinct.
- Checkpoints write analyzer-compatible JSON with `status: running`; normal completion rewrites the same output with `status: ok`.

Expanded non-QM9 calibration input:

| Slice | Rows | Unique records | Dataset mix | Atom count range |
| --- | ---: | ---: | --- | --- |
| `sampled_records.light.non_qm9_unique140.jsonl` with `--max-records 120` | 120 | 120 | GEOM 70, QMugs 50 | 17-44 |

Command:

```bash
.venv/bin/python scripts/run_xtb_real_dataset_distribution.py \
  --sampled-records artifacts/xtb_real_distribution/2026-06-21-expansion-prep/sampled_records.light.non_qm9_unique140.jsonl \
  --tier light \
  --max-records 120 \
  --output artifacts/xtb_real_distribution/2026-06-21-expansion-prep/light_non_qm9_unique120_results.json \
  --checkpoint-every 10 \
  --progress-every 10 \
  --resume
```

Expanded-prep calibration result:

| Tier/source | Rows | OK | Partial | Errors | Skipped | Runtime total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| non-QM9 light | 120 | 120 | 0 | 0 | 0 | 606.72 s |
| medium slice | 24 | 24 | 0 | 0 | 0 | 116.46 s |
| expensive slice | 12 | 12 | 0 | 0 | 0 | 11.13 s |

Readiness was recomputed from:

- `artifacts/xtb_real_distribution/2026-06-21-expansion-prep/light_non_qm9_unique120_results.json`
- `artifacts/xtb_real_distribution/2026-06-21-expansion-prep/medium_slice_results.json`
- `artifacts/xtb_real_distribution/2026-06-21-expansion-prep/expensive_slice_results.json`

Expanded Run readiness:

| Metric | Value |
| --- | ---: |
| Non-QM9 unique records with at least one OK property | 127 |
| Attempted properties | 720 |
| Error properties | 0 |
| Property error rate | 0.00 |
| Hessian runtime/parser failures | 0 |
| Blockers | none |
| Ready for formal Expanded Run | `true` |

Formal Expanded Run preparation artifact:

- `artifacts/xtb_real_distribution/2026-06-21-expansion-prep/formal_expanded_run_prep_manifest.json`
- `artifacts/xtb_real_distribution/2026-06-21-expansion-prep/analysis-expanded-prep/expanded_run_readiness.json`

Recommended formal run target remains the low end of the planned expanded quotas:

| Tier | Formal target count | Input file |
| --- | ---: | --- |
| light | 10,000 | `sampled_records.light.jsonl` |
| medium | 2,000 | `sampled_records.medium.jsonl` |
| expensive | 500 | `sampled_records.expensive.jsonl` |

Command template:

```bash
RUN_ID=2026-06-22-expanded-run
mkdir -p artifacts/xtb_real_distribution/$RUN_ID

.venv/bin/python scripts/run_xtb_real_dataset_distribution.py \
  --sampled-records artifacts/xtb_real_distribution/2026-06-21-expansion-prep/sampled_records.light.jsonl \
  --tier light \
  --max-records 10000 \
  --output artifacts/xtb_real_distribution/$RUN_ID/light_results.json \
  --checkpoint-every 25 \
  --progress-every 25 \
  --resume

.venv/bin/python scripts/run_xtb_real_dataset_distribution.py \
  --sampled-records artifacts/xtb_real_distribution/2026-06-21-expansion-prep/sampled_records.medium.jsonl \
  --tier medium \
  --max-records 2000 \
  --output artifacts/xtb_real_distribution/$RUN_ID/medium_results.json \
  --checkpoint-every 10 \
  --progress-every 10 \
  --resume

.venv/bin/python scripts/run_xtb_real_dataset_distribution.py \
  --sampled-records artifacts/xtb_real_distribution/2026-06-21-expansion-prep/sampled_records.expensive.jsonl \
  --tier expensive \
  --max-records 500 \
  --output artifacts/xtb_real_distribution/$RUN_ID/expensive_results.json \
  --checkpoint-every 5 \
  --progress-every 5 \
  --resume

.venv/bin/python scripts/analyze_xtb_real_dataset_distribution.py \
  --inputs \
    artifacts/xtb_real_distribution/$RUN_ID/light_results.json \
    artifacts/xtb_real_distribution/$RUN_ID/medium_results.json \
    artifacts/xtb_real_distribution/$RUN_ID/expensive_results.json \
  --output-dir artifacts/xtb_real_distribution/$RUN_ID/analysis \
  --expanded-readiness
```

Decision: formal Expanded Run preparation is complete. The source-coverage, property-error-rate, and Hessian runtime/parser gates are satisfied. OPV remains outside automatic calibration until a provenance-explicit 3D geometry source is available, but it is no longer a blocker for launching the QM9 + QMugs + GEOM formal Expanded Run.
