# Expert Open-Generation xTB Calibration

## Decision

Expert Tasks 2-6 pass their live-calibration gates and may be promoted to the
formal `xtb` task pack. The calibration established fixed scoring ranges,
timeouts, resource envelopes, electronic states, and molecular-identity
behavior. No task was admitted by weakening an expert constraint.

The calibration candidates and their geometries remain distribution-excluded.
This report contains aggregated evidence only and does not disclose a candidate
generation protocol.

## Environment

- Date: 2026-07-13
- xTB executable: `/opt/homebrew/bin/xtb`
- xTB version: 6.7.1 (`edcfbbe`)
- Method: GFN2-xTB
- Host: Apple M4, 10 logical CPUs, 16 GiB RAM
- Operating system: macOS 26.5.1
- Final result artifact: `build/expert-xtb-calibration/final-results.json`
- Final analysis artifact: `build/expert-xtb-calibration/final-analysis/summary.json`

The build artifacts are local evidence and are not included in release
packages.

## Live Results

The final run evaluated 17 records: 12 positive conformers and 5 negative
controls. All 12 positive conformers completed with status `ok`. Every negative
control failed at the intended structural domain gate with `domain_error`.
There were no xTB environment errors, tool errors, non-convergence results, or
timeouts.

| Task | Positive runs | Observed property range | Positive wall time | Convergence / identity evidence |
| --- | ---: | --- | --- | --- |
| Task 2, dipole | 2/2 | 3.437-5.367 D | 2.16-5.40 s | 2/2 optimizations converged; charge 0, UHF 1 |
| Task 3, gap | 2/2 | 1.7081475-1.7081485 eV | 0.19-0.20 s | 2/2 optimizations converged; charge 0, UHF 0 |
| Task 4, gap | 2/2 | 1.2426672-1.2426685 eV | 0.24-0.25 s | 2/2 optimizations converged; charge 0, UHF 0 |
| Task 5, ROY energy | 3/3 | -50.2891077 to -50.2891071 Eh | 0.17-0.18 s | 3/3 submitted structures matched the ROY graph; single-point mode does not optimize |
| Task 6, Ritonavir energy | 3/3 | -148.1927186 to -148.1834769 Eh | 6.82-19.85 s | 3/3 converged; graph and all four stereocenters matched before and after optimization |

An additional complete pass reached -148.1979625 Eh and 27.54 s for one
Ritonavir conformer. It still converged and retained graph and stereochemistry,
so the repeated-run envelope remains inside the frozen scoring and timeout
ranges.

Task 6 was also run as three isolated one-candidate processes under macOS
`/usr/bin/time -l`. The measured maximum resident set sizes were 90.625,
96.297, and 97.453 MiB, with isolated wall times of 6.83, 12.13, and 19.89 s.
These measurements include the evaluator invocation and therefore provide a
conservative process-level observation for the xTB calculation. The formal
8192 MiB resource envelope leaves substantial headroom.

## Frozen Gates

All scoring uses the existing linear `minimize_bounded` definition. Values at
or below `lower` score 1, and values at or above `upper` score 0.

| Task | Property | Lower | Upper | Timeout | Resource envelope | Gate |
| --- | --- | ---: | ---: | ---: | --- | --- |
| Task 2 | dipole moment (D) | 0.0 | 20.0 | 240 s | 2 CPU, 4096 MiB | pass |
| Task 3 | HOMO-LUMO gap (eV) | 0.0 | 10.0 | 240 s | 2 CPU, 4096 MiB | pass |
| Task 4 | HOMO-LUMO gap (eV) | 0.0 | 10.0 | 240 s | 2 CPU, 4096 MiB | pass |
| Task 5 | submitted ROY energy (Eh) | -50.30 | -50.25 | 300 s | 2 CPU, 4096 MiB | pass |
| Task 6 | optimized Ritonavir energy (Eh) | -148.20 | -148.15 | 600 s | 2 CPU, 8192 MiB | pass |

The energy ranges are molecule-specific. Task 5 compares ROY conformers only,
and Task 6 compares Ritonavir conformers only; their absolute energies are not
comparable to one another or to any other benchmark task. With the frozen
ranges, the observed ROY controls score approximately 0.782, and the observed
Ritonavir controls score 0.670-0.959.

## Limitations

- The calibration is a small verifier-operability study, not an estimate of
  the participant answer distribution.
- Runtime and memory were measured on one Apple M4 host. The timeouts include
  large margins for slower runners, but deployment environments should still
  retain timeout and memory monitoring.
- Task 5's sampled conformers occupy a very narrow energy range. The frozen
  range intentionally adds headroom for less favorable but graph-valid
  submitted geometries.
- xTB values are fixed-method surrogate properties, not experimental or
  high-level ab initio reference values.
