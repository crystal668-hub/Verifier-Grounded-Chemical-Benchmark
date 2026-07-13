# Project-Level Limitations Document Design

**Date:** 2026-07-10

## Purpose

Create a durable project-level limitations document for claims made by the
verifier-grounded benchmark about research-task proximity. The document is
intended to support future paper writing and ongoing benchmark maintenance. It
records which parts of chemical research a benchmark score does and does not
represent, without changing task definitions or scoring.

## Location

The document will be stored at `docs/design/Limits.md`.

`docs/design/` is the appropriate category because these limitations are
cross-cutting design and measurement-boundary decisions. Track-specific
limitations remain in the corresponding file under `docs/tracks/`.

## Document Structure

`Limits.md` will contain these sections:

1. **Scope and interpretation**: define the document as a record of known
   research-task limits, rather than a claim that the benchmark is invalid.
2. **Research-task proximity**: state the first project-level limitation.
3. **Maintenance rules**: require future additions to distinguish documented
   facts from proposed work and to keep this document at project scope.

## First Limitation Entry

The first entry will state all of the following:

- The benchmark represents bounded candidate-design and computational
  screening work under stated objectives and answer formats.
- A high score does not establish competence in problem formulation, literature
  assessment, synthesis planning, experimental work, uncertainty assessment,
  interpretation, or wider scientific decision-making.
- The task structure is more constrained than open research settings, so a
  score supports only a task-specific capability claim.
- The document will not compare this benchmark with external benchmarks or
  make claims about their relative maturity.

## Non-goals

- Do not change scores, verifier choices, task prompts, or track membership.
- Do not duplicate all track-specific implementation limitations.
- Do not present unimplemented mitigation work as completed.
- Do not discuss fixed-verifier surrogate validity or compare this benchmark
  with external benchmarks in this initial document.

## Verification

The documentation change will be checked for valid Markdown structure and
internal link targets. The repository test suite will be run before each
commit, following the repository instructions.
