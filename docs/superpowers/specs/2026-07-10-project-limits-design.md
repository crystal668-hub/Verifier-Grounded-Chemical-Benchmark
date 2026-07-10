# Project-Level Limitations Document Design

**Date:** 2026-07-10

## Purpose

Create a durable project-level limitations document for claims made by the
verifier-grounded benchmark. The document is intended to support future paper
writing and ongoing benchmark maintenance. It records what a benchmark score
does and does not establish, without changing task definitions or scoring.

## Location

The document will be stored at `docs/design/Limits.md`.

`docs/design/` is the appropriate category because these limitations are
cross-cutting design and measurement-boundary decisions. Track-specific
limitations remain in the corresponding file under `docs/tracks/`.

## Document Structure

`Limits.md` will contain these sections:

1. **Scope and interpretation**: define the document as a record of known
   measurement limits, rather than a claim that the benchmark is invalid.
2. **Fixed-verifier surrogate validity and optimization risk**: the first
   project-level limitation.
3. **Maintenance rules**: require future additions to distinguish verified
   facts, current mitigations, and unresolved work.

## First Limitation Entry

The first entry will state all of the following:

- A high score means that a submitted candidate satisfies the specified,
  versioned verifier under its declared conditions.
- A high score does not establish experimental success, agreement with a
  higher-fidelity method, or broad chemical usefulness.
- A model or agent can optimize the public scoring oracle directly, including
  through repeated evaluation, threshold-specific search, or exploiting a
  surrogate's applicability-domain weaknesses.
- Existing controls, such as input validity checks, domain gates, fixed
  versions, geometry-quality gates, and calibration, reduce some failure modes
  but do not eliminate surrogate-to-experiment mismatch.
- Future validation should include independent or higher-fidelity checks,
  cross-verifier agreement, and, where appropriate, experimental or curated
  external evidence.

## Non-goals

- Do not change scores, verifier choices, task prompts, or track membership.
- Do not duplicate all track-specific implementation limitations.
- Do not present unimplemented mitigation work as completed.

## Verification

The documentation change will be checked for valid Markdown structure and
internal link targets. The repository test suite will be run before each
commit, following the repository instructions.
