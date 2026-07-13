# Project-Level Limitations

## Scope and interpretation

This document records limits on how the verifier-grounded benchmark should be
interpreted. These limits do not make the benchmark invalid. They define the
research task that a score represents and the conclusions a score cannot
support.

## Research-task proximity

The benchmark represents a bounded form of chemical research: given stated
property objectives and an answer schema, a system proposes a chemical
candidate that is assessed by the benchmark's verification workflow. This is
closer to candidate-design and computational screening work than to a
fixed-answer question, but it is not a complete representation of chemical
research.

A benchmark score does not establish that a system can independently:

- formulate a scientifically important research problem or hypothesis;
- judge literature quality, reconcile conflicting evidence, or select an
  appropriate research direction;
- devise a synthetic route, plan experiments, or execute laboratory work;
- assess measurement uncertainty, interpret unexpected results, or revise a
  research plan using new evidence; or
- make the broader practical, safety, or scientific-value decisions required
  to advance a chemical project.

The stated objectives, candidate representation, and final-answer format also
make the task more structured than an open research setting. A high score
therefore supports a claim about performance on this specified
candidate-design-and-verification task, not a general claim of chemical
research capability.

## Maintenance rules

- Add a limitation only when it describes an implemented task, an observed
  measurement boundary, or a documented evaluation result.
- Distinguish established facts from proposed future work.
- Keep this document focused on research-task proximity. Track-specific
  method limitations belong in the corresponding document under `docs/tracks/`.
