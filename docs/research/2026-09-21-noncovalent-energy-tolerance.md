# Noncovalent Energy Tolerance Projection

Date: 2026-09-21. Status: v0.9.4 formal scoring projection.

The zero-score width for the `noncovalent_energy` family was changed from
`1` to `2 kcal/mol` for the six Basic binding-energy fields B010-B015 and the
three Advanced fields A008 interaction energy, A008 binding energy, and A013
halogen-bond energy. A008/A013 now use signed identity scoring, while A010
distances use signed identity scoring with their existing nonnegative domain.
Gold values, field weights, and task aggregation were unchanged.

The calculation used the current answer workbooks `516177f8058f43d3a65127b6ba0a147a.xlsx`
(Basic, 51 tasks) and `71ba494357c643f69dcb8e6ae28ab299.xlsx` (Advanced, 20 tasks).
Scores were recomputed through the current property evaluator, including the
current joint phase aggregation for Advanced 002. Each workbook contributes the
same four groups: GPT skill-on, GPT skill-off, Qwen skill-on, and Qwen skill-off.

## Group Means

| Track / rule | GPT skill-on | GPT skill-off | Qwen skill-on | Qwen skill-off |
| --- | ---: | ---: | ---: | ---: |
| Basic current formal rule, 1 kcal/mol | 86.07 | 88.25 | 86.48 | 86.20 |
| Basic candidate, 2 kcal/mol | 87.72 | 89.52 | 87.28 | 86.71 |
| Basic change | +1.65 | +1.26 | +0.80 | +0.51 |
| Advanced current formal rule, 1 kcal/mol | 59.23 | 40.89 | 53.07 | 36.57 |
| Advanced candidate, 2 kcal/mol | 60.91 | 42.56 | 56.00 | 39.75 |
| Advanced change | +1.69 | +1.68 | +2.93 | +3.18 |

The candidate raises the overall mean by 1.06 points for Basic and 2.37 points
for Advanced. The average within-task four-group standard deviation changes from
10.91 to 10.06 for Basic and from 24.59 to 24.51 for Advanced. The mean pairwise
absolute group gap changes from 14.04 to 12.86 for Basic and from 31.23 to 31.32
for Advanced.

Basic has 6 affected tasks, all B010-B015. Advanced has 2 affected tasks, A008
and A013. The other 63 tasks and all categorical fields retain their scores.
The affected task-level scores are recorded in
[task_scores.csv](2026-09-21-noncovalent-energy-tolerance/task_scores.csv).

The number of all-group-zero tasks changes from 3 to 2 in Advanced and remains
zero in Basic. The individual zero rate changes from 3.43% to 2.94% in Basic and
from 33.75% to 27.50% in Advanced. No task reaches at least 90 in all four groups
under either rule in Advanced; Basic remains at 19 such tasks.

This report records the v0.9.4 formal scoring projection. It does not claim that
2 kcal/mol is an independently calibrated chemical uncertainty; the family
policy records that calibration status separately.
