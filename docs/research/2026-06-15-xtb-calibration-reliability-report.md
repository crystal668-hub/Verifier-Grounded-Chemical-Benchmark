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

## 2026-06-19 Advanced Iteration Update

The 2026-06-15 findings for `xtb_lumo_min_008` through `xtb_hessian_thermo_stability_013` were followed up with a control-curation-first pass. Thresholds were changed only where the real xTB calibration values showed that the previous bound was on the wrong scale or did not separate the curated controls.

Commands:

- `uv run python scripts/run_xtb_calibration.py --answers tasks/xtb_xyz/calibration_answers.jsonl --output artifacts/xtb_calibration/2026-06-19-advanced-iteration/final-results.json`
- `uv run python scripts/analyze_xtb_calibration.py --input artifacts/xtb_calibration/2026-06-19-advanced-iteration/final-results.json --output-dir artifacts/xtb_calibration/2026-06-19-advanced-iteration/final-analysis`

Artifacts:

- `artifacts/xtb_calibration/2026-06-19-advanced-iteration/final-results.json`
- `artifacts/xtb_calibration/2026-06-19-advanced-iteration/final-analysis/summary.json`
- `artifacts/xtb_calibration/2026-06-19-advanced-iteration/final-analysis/summary.md`

Final run summary: status `ok`; 35 calibration answers; 22 `ok` rows; 13 error rows; min score 0.000; mean score 0.366; max score 1.000. The error rows are still expected negative-baseline `domain_error` rows. No nonnegative advanced control produced a parser, xTB tool, convergence, or timeout failure.

### Task 8-13 Before/After Summary

| Task | 2026-06-15 issue | 2026-06-19 calibrated controls and properties | Final result |
| --- | --- | --- | --- |
| `xtb_lumo_min_008` | Positive and near-miss both saturated at 1.000 under the original LUMO bound. | Positive changed to `xtb_lumo_min_008_positive_push_pull_cinnamonitrile`, LUMO -8.566 eV. Near-miss changed to `xtb_lumo_min_008_near_miss_dimethylamino_nitrobenzene`, LUMO -8.029 eV. | LUMO bound tightened to `[-9.0, -6.0]`. Positive scored 0.855; near-miss scored 0.676. The near-miss remains intentionally challenging because both molecules are strong acceptor systems, but the score gap is no longer saturated. |
| `xtb_polarizability_dipole_opt_009` | The nominal positive had high polarizability but failed the 3-8 D dipole window; the previous near-miss was the better positive. | Positive changed to `xtb_polarizability_dipole_opt_009_positive_dicyanobenzene`, polarizability/heavy atom 9.343 and dipole 3.969 D. Near-miss changed to high-dipole dimethylamino nitrobenzene, polarizability/heavy atom 9.524 but dipole 10.034 D. | Thresholds retained. Positive scored 0.817; near-miss scored 0.301 because the dipole window correctly penalized an otherwise polarizable molecule. |
| `xtb_solvation_selectivity_alpb_010` | All nonnegative controls were far below the old 1.5 eV saturation point. | Positive changed to dimethylamino nitrobenzene, ALPB water-hexane selectivity 0.238 eV. Near-miss retained as trifluoroethyl nitroethane, 0.055 eV. Large push-pull stress case scored 0.014 eV. | ALPB upper bound changed from 1.5 to 0.35 eV. Positive scored 0.679; near-miss scored 0.158; stress scored 0.041. |
| `xtb_electrophilicity_max_011` | The old positive scored below the 0.6 promotion bar. | Positive changed to push-pull cinnamonitrile, global electrophilicity 2.494 eV. Near-miss changed to dicyanobenzene, 1.854 eV. | Electrophilicity upper bound changed from 4.0 to 3.8 eV. Positive scored 0.604; near-miss scored 0.410. |
| `xtb_fukui_carbon_site_012` | The old positive had negative carbon-site contrast, so the strongest f+ site was not carbon-selective. | Positive changed to QM9 `gdb9_000059`, max carbon f+ 0.276 and contrast 0.094. Near-miss changed to QM9 `gdb9_000071`, max carbon f+ 0.266 and contrast 0.032. Dimethylamino nitrobenzene retained as a stress case, max carbon f+ 0.075 and contrast -0.051. | Fukui thresholds retained. Structural domain changed to the validated local-reactivity domain: heavy atoms `[4, 32]`, at least 3 carbons, at least 1 hetero atom. Positive scored 0.668; near-miss scored 0.371; stress scored 0.000. |
| `xtb_hessian_thermo_stability_013` | Entropy thresholds were tightened in the previous pass, but the old positive became a zero-scoring low-entropy control. | Positive changed to QM9 `gdb9_000041`, entropy/heavy atom 76.095 J mol-1 K-1, zero imaginary frequencies, relaxation 0.0078 eV. Near-miss is hexafluoroisopropanol, entropy/heavy atom 40.598 and zero imaginary frequencies. Flexible dimethoxyethane remains a stress case with entropy/heavy atom 55.084 but 3 imaginary frequencies and relaxation 4.436 eV. | Entropy thresholds `[50.0, 80.0]` retained after positive-control replacement. Positive scored 0.851; near-miss scored 0.000; stress scored 0.000 through stability and geometry gates. |

### Threshold and Control Rationale

- `xtb_lumo_min_008`: The tighter upper bound at -6.0 eV makes the task distinguish very strong acceptors from merely low-LUMO candidates while keeping the positive comfortably above 0.75. The near-miss score of 0.676 is acceptable as a hard near-miss rather than a failed separation because dimethylamino nitrobenzene is also a strong push-pull acceptor.
- `xtb_polarizability_dipole_opt_009`: No numeric threshold change was needed. Dicyanobenzene validates the intended intersection of high per-heavy-atom polarizability and moderate dipole, while dimethylamino nitrobenzene demonstrates that high polarizability alone is not enough when the dipole exceeds the window.
- `xtb_solvation_selectivity_alpb_010`: The old 1.5 eV upper bound was not supported by the real distribution. In the 60-row medium distribution artifact, ALPB water-over-hexane selectivity had median 0.075 eV, 90th percentile 0.279 eV, 95th percentile 0.373 eV, and maximum 0.504 eV. Setting the upper bound to 0.35 eV places saturation near the high end of observed realistic values without requiring an out-of-distribution control.
- `xtb_electrophilicity_max_011`: Push-pull cinnamonitrile is chemically appropriate because conjugated donor-acceptor substitution lowers the LUMO and raises global electrophilicity. The 3.8 eV upper bound keeps the positive just above the 0.6 promotion bar while preserving separation from dicyanobenzene.
- `xtb_fukui_carbon_site_012`: The task is a local carbon-site reactivity task, not a large-molecule generation task. The QM9 controls establish that the scoring function works when a carbon atom has both high f+ and positive contrast over competing atoms. The smaller structural domain is therefore better aligned with the measured objective and avoids rejecting the only validated positive controls.
- `xtb_hessian_thermo_stability_013`: The retained `[50.0, 80.0]` entropy bound is supported by the new QM9 positive at 76.095 J mol-1 K-1 per heavy atom. The hessian stress case confirms that entropy alone cannot overcome imaginary frequencies or rough submitted geometry.

After this iteration, the original task8-13 recommendations of `tighten_thresholds` and `needs_more_positive_controls` are resolved for the current calibration pack. The main retained caveat is task8: its near-miss remains moderately high because both controls are chemically strong acceptors. That is acceptable for a discriminative advanced task, but future larger calibration sets should include additional mid-strength acceptors to measure the slope around the promotion threshold.

## Per-Task Findings

The following per-task findings describe the original 2026-06-15 baseline run. For tasks 8-13, use the 2026-06-19 advanced iteration section above as the current recommendation.

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

## Recommended Follow-Ups After 2026-06-19

- Task8-13 calibration: the immediate control-curation and threshold follow-up items from the 2026-06-15 report are resolved by the 2026-06-19 advanced iteration.
- Sample-answer updates: `tasks/xtb_xyz/sample_answers.jsonl` still has not been expanded as part of this calibration report. Add advanced sample answers only after deciding which curated controls should also serve as public examples.
- Broader calibration: run a larger, more chemically diverse real-distribution sample before making another global threshold pass. Task8 would benefit most from additional mid-strength acceptor controls between the current positive and near-miss.
- Parser hardening: no parser fixes are indicated by this run.
- Runtime changes: no timeout or xTB runtime fixes are indicated by this run.
