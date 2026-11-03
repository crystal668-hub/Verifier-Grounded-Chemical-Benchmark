# Project-Level Limitations

Updated: 2026-11-03. Research positioning: [design and narrative](INITIAL-DESIGN.md).

## Scope and interpretation

This document records limits on how the verifier-grounded benchmark should be
interpreted. These limits do not make the benchmark invalid. They define the
research task that a score represents and the conclusions a score cannot
support.

## Research-task proximity

The benchmark represents two bounded tasks within chemical research.
Open generation asks a system to construct a candidate under stated property
objectives and structural constraints, then recomputes its properties using a
fixed verification workflow. Property calculation asks for properties of a
given object under the stated conditions, then compares the submitted answer
with a frozen reference. These tasks cover candidate construction and property
solving; they do not represent the complete research process.

A benchmark score does not establish that a system can independently:

- formulate a scientifically important research problem or hypothesis;
- judge literature quality, reconcile conflicting evidence, or select an
  appropriate research direction;
- devise a synthetic route, plan experiments, or execute laboratory work;
- assess measurement uncertainty, interpret unexpected results, or revise a
  research plan using new evidence; or
- make the broader practical, safety, or scientific-value decisions required
  to advance a chemical project.

The stated objectives, object representations, and final-answer formats also
make the task more structured than an open research setting. A high score
supports a claim about final outcomes under the specified task, reference
protocol, and scoring rules. The evaluator does not inspect tool calls or
intermediate reasoning. A score alone cannot distinguish tool use from recalled
knowledge or identify the contribution of a particular harness component.

## Reference and scoring interpretation

Open-generation evidence is computed at evaluation time; property-calculation
gold is frozen before evaluation. Repeating a gold-comparison score or testing
gold round trips does not independently reproduce the source science. Known
input and protocol limits remain relevant even when the reference value is
frozen; see the [expert-task conversion record](../research/2026-08-20-task14-25-property-calculation-conversion-plan.md).

Continuous scores express proximity to a task goal or reference value. Decay
widths are scoring parameters, not automatically uncertainty estimates or
validated corrections for differences between scientific methods. Hard gates
and discrete-answer rules remain part of the evaluation. Results should report
the two task families separately; the current full-suite mean weights 30
open-generation and 70 property-calculation tasks equally per task.

## Computational and data boundaries

The local evaluation design uses RDKit and xTB/CREST for open generation and
avoids rerunning reference calculations for property tasks. This separates
scoring costs from reference-generation costs and the respondent's solving
costs. It does not establish that every task can be solved from scratch on
every personal computer. Executed validation and its limits are recorded in the
[RC acceptance report](../../releases/v1.0.0-rc/VALIDATION.md).

Property gold and scoring data remain in the distribution for offline scoring,
although ordinary prompt views omit them. Removing public sample answers does
not create a hidden test set or establish resistance to contamination.

## Maintenance rules

- Add a limitation only when it describes an implemented task, an observed
  measurement boundary, or a documented evaluation result.
- Distinguish established facts from proposed future work.
- Keep this document focused on shared interpretation boundaries. Track-specific
  method limitations belong in the corresponding document under `docs/tracks/`.
