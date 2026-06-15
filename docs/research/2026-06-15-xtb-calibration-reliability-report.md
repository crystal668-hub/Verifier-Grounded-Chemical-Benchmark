# xTB Calibration Reliability Report

## Environment

- Date: 2026-06-15
- xTB executable: `/opt/homebrew/bin/xtb`
- xTB version: 6.7.1 (edcfbbe), compiled 2025-09-04
- Python: 3.12.13
- Command: `uv run python scripts/run_xtb_calibration.py --answers tasks/xtb_xyz/calibration_answers.jsonl --output artifacts/xtb_calibration/2026-06-15/results.json`
- Analysis command: `uv run python scripts/analyze_xtb_calibration.py --input artifacts/xtb_calibration/2026-06-15/results.json --output-dir artifacts/xtb_calibration/2026-06-15/analysis`
- Raw local artifacts: `artifacts/xtb_calibration/2026-06-15/results.json`, `artifacts/xtb_calibration/2026-06-15/analysis/summary.json`

## Summary

| Task | Positive max | Negative max | Error rate | Recommendation |
| --- | ---: | ---: | ---: | --- |
| xtb_gap_window_001 | 1.000 | 0.000 | 50% | keep_thresholds |
| xtb_dipole_window_002 | 1.000 | 0.000 | 50% | keep_thresholds |
| xtb_gap_max_003 | 0.808 | 0.000 | 50% | keep_thresholds |
| xtb_gap_min_004 | 0.740 | 0.000 | 50% | keep_thresholds |
| xtb_dipole_max_005 | 1.000 | 0.000 | 50% | keep_thresholds |
| xtb_low_gap_high_dipole_opt_006 | 0.845 | 0.000 | 50% | keep_thresholds |
| xtb_gap_dipole_window_007 | 1.000 | 0.000 | 50% | keep_thresholds |
| xtb_lumo_min_008 | 1.000 | 0.000 | 33% | tighten_thresholds |
| xtb_polarizability_dipole_opt_009 | 0.055 | 0.000 | 33% | needs_more_positive_controls |
| xtb_solvation_selectivity_alpb_010 | 0.037 | 0.000 | 25% | needs_more_positive_controls |
| xtb_electrophilicity_max_011 | 0.498 | 0.000 | 33% | needs_more_positive_controls |
| xtb_fukui_carbon_site_012 | 0.000 | 0.000 | 33% | needs_more_positive_controls |
| xtb_hessian_thermo_stability_013 | 1.000 | 0.000 | 25% | tighten_thresholds |

The calibration run scored 34 candidates: 21 `ok` rows and 13 error rows. All errors were expected `domain_error` outcomes for simple negative baselines. No parser, xTB tool, optimization convergence, or timeout failures appeared in this run.

## Per-Task Findings

### xtb_gap_window_001

- Positive controls: `xtb_gap_window_001_positive_perfluoropropyl_nitrile` scored 1.000 with HOMO-LUMO gap 5.394 eV and near-zero relaxation energy.
- Negative baselines: `xtb_gap_window_001_negative_water` failed with `domain_error` because heavy atom count is below [6, 40].
- Failure modes: expected structural-domain rejection only.
- Threshold recommendation: keep_thresholds.

### xtb_dipole_window_002

- Positive controls: `xtb_dipole_window_002_positive_trifluoroethyl_nitroethane` scored 1.000 with dipole 3.967 Debye and near-zero relaxation energy.
- Negative baselines: `xtb_dipole_window_002_negative_methane` failed with `domain_error` because heavy atom count is below [5, 40].
- Failure modes: expected structural-domain rejection only.
- Threshold recommendation: keep_thresholds.

### xtb_gap_max_003

- Positive controls: `xtb_gap_max_003_positive_hexafluoroisopropanol` scored 0.808 with gap 11.616 eV.
- Negative baselines: `xtb_gap_max_003_negative_benzene` failed with `domain_error` because heavy atom count is below [8, 40].
- Failure modes: expected structural-domain rejection only.
- Threshold recommendation: keep_thresholds.

### xtb_gap_min_004

- Positive controls: `xtb_gap_min_004_positive_push_pull_azo_nitroarene` scored 0.740 with gap 1.299 eV.
- Negative baselines: `xtb_gap_min_004_negative_ethene` failed with `domain_error` because heavy atom count is below [8, 40].
- Failure modes: expected structural-domain rejection only.
- Threshold recommendation: keep_thresholds.

### xtb_dipole_max_005

- Positive controls: `xtb_dipole_max_005_positive_dimethylamino_nitrobenzene` scored 1.000 with dipole 10.034 Debye.
- Negative baselines: `xtb_dipole_max_005_negative_carbon_dioxide` failed with `domain_error` because heavy atom count is below [6, 40].
- Failure modes: expected structural-domain rejection only.
- Threshold recommendation: keep_thresholds.

### xtb_low_gap_high_dipole_opt_006

- Positive controls: `xtb_low_gap_high_dipole_opt_006_positive_push_pull_cinnamonitrile` scored 0.845 with gap 1.432 eV and dipole 13.471 Debye.
- Negative baselines: `xtb_low_gap_high_dipole_opt_006_negative_acetonitrile` failed with `domain_error` because heavy atom count is below [8, 40].
- Failure modes: expected structural-domain rejection only.
- Threshold recommendation: keep_thresholds.

### xtb_gap_dipole_window_007

- Positive controls: `xtb_gap_dipole_window_007_positive_dicyanobenzene` scored 1.000 with gap 3.634 eV and dipole 3.969 Debye.
- Negative baselines: `xtb_gap_dipole_window_007_negative_formaldehyde` failed with `domain_error` because heavy atom count is below [8, 40].
- Failure modes: expected structural-domain rejection only.
- Threshold recommendation: keep_thresholds.

### xtb_lumo_min_008

- Positive controls: `xtb_lumo_min_008_positive_push_pull_azo_nitroarene` scored 1.000 with LUMO -8.442 eV.
- Negative baselines: `xtb_lumo_min_008_negative_benzene` failed with `domain_error` because heavy atom count is below [8, 40].
- Failure modes: expected structural-domain rejection only.
- Threshold recommendation: tighten_thresholds. The intended near miss `xtb_lumo_min_008_near_miss_dicyanobenzene` also scored 1.000 with LUMO -8.217 eV, so the current bounded scoring does not separate strong and moderate acceptor controls.

### xtb_polarizability_dipole_opt_009

- Positive controls: `xtb_polarizability_dipole_opt_009_positive_push_pull_cinnamonitrile` scored 0.055. It had high polarizability per heavy atom, 9.649 au/heavy atom, but dipole 13.471 Debye outside the 3.0 to 8.0 Debye window.
- Negative baselines: `xtb_polarizability_dipole_opt_009_negative_methanol` failed with `domain_error` because heavy atom count is below [8, 40].
- Failure modes: expected structural-domain rejection only.
- Threshold recommendation: needs_more_positive_controls. The near miss `xtb_polarizability_dipole_opt_009_near_miss_dicyanobenzene` scored 0.817 and is better than the nominal positive candidate; the labels need follow-up curation before threshold changes.

### xtb_solvation_selectivity_alpb_010

- Positive controls: `xtb_solvation_selectivity_alpb_010_positive_trifluoroethyl_nitroethane` scored 0.037 with water/hexane selectivity 0.055 eV.
- Negative baselines: `xtb_solvation_selectivity_alpb_010_negative_acetonitrile` failed with `domain_error` because heavy atom count is below [8, 36].
- Failure modes: expected structural-domain rejection only.
- Threshold recommendation: needs_more_positive_controls. The highest nonnegative selectivity in this pack was the near miss at 0.238 eV, still far below the current 1.5 eV saturation point.

### xtb_electrophilicity_max_011

- Positive controls: `xtb_electrophilicity_max_011_positive_push_pull_azo_nitroarene` scored 0.498 with global electrophilicity 2.244 eV.
- Negative baselines: `xtb_electrophilicity_max_011_negative_formaldehyde` failed with `domain_error` because heavy atom count is below [8, 40].
- Failure modes: expected structural-domain rejection only.
- Threshold recommendation: needs_more_positive_controls. The current positive is plausible but below the 0.6 sample-promotion bar.

### xtb_fukui_carbon_site_012

- Positive controls: `xtb_fukui_carbon_site_012_positive_dimethylamino_nitrobenzene` scored 0.000. It had max carbon f+ 0.075 but negative contrast, -0.051, so the strongest f+ site is not carbon-selective.
- Negative baselines: `xtb_fukui_carbon_site_012_negative_nitromethane` failed with `domain_error` because heavy atom count is below [8, 32].
- Failure modes: expected structural-domain rejection only.
- Threshold recommendation: needs_more_positive_controls. Both current nonbaseline candidates had negative f+ contrast.

### xtb_hessian_thermo_stability_013

- Positive controls: `xtb_hessian_thermo_stability_013_positive_trifluoroethyl_nitroethane` scored 1.000 with zero imaginary frequencies and entropy per heavy atom 43.397 J mol-1 K-1.
- Negative baselines: `xtb_hessian_thermo_stability_013_negative_methane` failed with `domain_error` because atom count is below [6, 48].
- Failure modes: expected structural-domain rejection only. The stress case `xtb_hessian_thermo_stability_013_stress_flexible_dimethoxyethane` ran successfully and scored 0.000 because relaxation energy was 4.436 eV and imaginary frequency count was 3.
- Threshold recommendation: tighten_thresholds. Current entropy scoring saturates for stable compact molecules because observed entropy per heavy atom values are far above the current upper bound of 18.0.

## Cross-Task Reliability

- Parser failures: none observed.
- Optimization failures: none observed.
- Timeout failures: none observed.
- xTB tool failures: none observed.
- Domain failures: 13 expected negative baselines failed with `domain_error`.
- Relaxation-energy gate behavior: all optimized seed positives had near-zero relaxation energy. The rough flexible hessian stress case produced relaxation energy 4.436 eV and final score 0.000, confirming the quality gate catches rough submitted XYZ geometries.
- Stability-gate behavior: the hessian stress case produced 3 imaginary frequencies and was gated to score 0.000; stable hessian controls had zero imaginary frequencies.
- Runtime behavior: the large solvation stress case completed without timeout or parser failure.

## Recommended Follow-Ups

- Threshold changes: prepare a follow-up threshold plan for `xtb_lumo_min_008` and `xtb_hessian_thermo_stability_013`; both currently saturate too easily on the tested controls.
- Sample-answer updates: do not update `tasks/xtb_xyz/sample_answers.jsonl` in this commit. Task 8 and task 13 have high-confidence candidates, but tasks 9 through 12 do not yet have `positive_candidate` rows scoring at least 0.6, so the advanced sample pack is not ready to expand to 13 tasks.
- Positive-control curation: find stronger positives for `xtb_polarizability_dipole_opt_009`, `xtb_solvation_selectivity_alpb_010`, `xtb_electrophilicity_max_011`, and `xtb_fukui_carbon_site_012`.
- Parser hardening: no parser fixes are indicated by this run.
- Runtime changes: no timeout or xTB runtime fixes are indicated by this run.
