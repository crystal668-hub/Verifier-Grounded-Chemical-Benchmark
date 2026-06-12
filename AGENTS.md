# Agent Guidelines

- After every change, run the tests first, then create a git commit.

## Documentation Layout

- Use `docs/` as the only top-level documentation directory. Do not create or
  resurrect a separate `doc/` directory.
- Store benchmark architecture, system design, schema/interface design, and
  cross-cutting design decisions in `docs/design/`.
- Store exploratory analyses, dated research notes, tool investigations,
  feasibility reviews, and validation reports in `docs/research/`. Prefer a
  `YYYY-MM-DD-...` filename prefix for time-bound research documents.
- Store benchmark track or backend-specific documentation in `docs/tracks/`,
  such as RDKit, xTB, MatGL, MACE, or future track capability summaries.
- Store Superpowers-generated implementation plans in
  `docs/superpowers/plans/`.
- Store Superpowers-generated specifications and design specs in
  `docs/superpowers/specs/`.
- When adding documentation, choose the narrowest existing category that fits.
  Add a new `docs/` subdirectory only when the document clearly does not belong
  to any existing category, and update this section with the new rule.
