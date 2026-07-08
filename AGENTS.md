# Agent Guidelines

- After every change, run the tests first, then create a git commit.

## Branch Development Discipline

- **Keep `main` stable**
  - Agents must keep `main` in a runnable and releasable state by default.
  - Do not develop directly on `main` unless explicitly instructed by the user.

- **Inspect state before starting**
  - Check the current Git state before making changes.
  - Identify and preserve user changes that are unrelated to the current task.
  - Do not overwrite, revert, or discard existing user changes.

- **Use short-lived branches**
  - Each task should be completed on its own dedicated branch.
  - A branch should serve one clear purpose only.
  - Delete the branch after the task is completed and merged.

- **Use clear branch names**
  - Use `feat/xxx` for new features.
  - Use `fix/xxx` for bug fixes.
  - Use `refactor/xxx` for refactoring.
  - Use `chore/xxx` for maintenance work.
  - Use `docs/xxx` for documentation changes.
  - Use `exp/xxx` for experimental work.
  - Use `hotfix/xxx` for urgent fixes.

- **Keep commits clear**
  - Keep the scope of changes focused.
  - Make small, coherent commits.
  - Avoid mixing unrelated changes in the same commit.
  - Commit messages should clearly describe the purpose of the change.

- **Verify before merging**
  - Sync with the latest `main` according to the project's existing workflow before merging.
  - Run the relevant tests, lint checks, and build checks before merging.
  - If verification fails, fix the issue or clearly explain the failure.

- **Use `git worktree` when needed**
  - Use an isolated `git worktree` when working on multiple tasks in parallel.
  - Use `git worktree` when switching branches would interfere with unfinished work.
  - Before using a project-local worktree directory, confirm it is ignored by `.gitignore`.

- **Use tags for releases**
  - Mark important release points with Git tags.
  - Prefer semantic version tags such as `v1.2.0`.

- **Avoid destructive operations**
  - Do not perform operations that may lose changes without explicit user permission.
  - Do not reset, overwrite, discard, or revert existing user changes without explicit permission.

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
