# AtomisticSkills MCP Removal Design

Date: 2026-07-02

## Goal

Remove the executable AtomisticSkills MCP integration path from the repository.
After this cleanup, current benchmark code should not depend on an external
AtomisticSkills checkout, AtomisticSkills MCP servers, AtomisticSkills conda
environments, or the Python `mcp` package.

This is a cleanup of the experimental MCP prototype path only. Historical
research notes remain as records of prior investigation.

## Decisions

- Remove the `atomisticskills_smoke` task pack.
- Remove the `mace_materials` task pack. MACE will return later through a
  native Python backend and a new task design.
- Remove the current `matgl_materials` task pack. MatGL will return later
  through formal native Python task specs rather than the AtomisticSkills MCP
  prototype specs.
- Keep the native MatGL Python backend, scripts, environment check, and tests.
- Keep `docs/research/` AtomisticSkills analysis documents unchanged.
- Update current design and package-facing documentation that describes active
  task packs or current backend status.

## Remove

Delete these task packs:

- `tasks/atomisticskills_smoke/`
- `tasks/mace_materials/`
- `tasks/matgl_materials/`

Delete AtomisticSkills and MCP verifier implementation files:

- `verifiers/atomisticskills_backend.py`
- `verifiers/atomisticskills_mcp_shims/`
- `verifiers/backends/atomisticskills_matgl_properties.py`
- `verifiers/backends/mace_properties.py`
- `verifiers/materials/atomisticskills_matgl_bandgap.py`
- `verifiers/materials/atomisticskills_matgl_formation_energy.py`
- `verifiers/materials/atomisticskills_matgl_property_script.py`
- `verifiers/materials/mace_energy.py`
- `verifiers/materials/mace_property_script.py`

Delete AtomisticSkills setup and smoke-check scripts:

- `scripts/check_atomisticskills_env.py`
- `scripts/check_atomisticskills_matgl_env.py`
- `scripts/check_atomisticskills_mace_env.py`
- `scripts/setup_atomisticskills_first_batch.sh`
- `scripts/setup_atomisticskills_matgl.sh`
- `scripts/setup_atomisticskills_mace.sh`

Delete tests that exclusively cover the removed path:

- AtomisticSkills adapter tests.
- AtomisticSkills first-batch setup/check tests.
- AtomisticSkills MatGL MCP backend/script/task tests.
- MACE MCP backend/script/task tests.

Tests that only use AtomisticSkills task ids as answer-extraction examples
should be rewritten to neutral test ids instead of removed.

## Keep

Keep the native MatGL Python implementation:

- `verifiers/backends/matgl_properties.py`
- `verifiers/materials/matgl_bandgap.py`
- `verifiers/materials/matgl_formation_energy.py`
- `verifiers/materials/matgl_property_script.py`
- `scripts/check_matgl_env.py`
- Native MatGL tests.

Because `tasks/matgl_materials/fixtures/Si.cif` will be removed, native MatGL
tests and `scripts/check_matgl_env.py` must stop depending on that task-pack
fixture. Move the Si CIF fixture to a non-prototype location such as
`tests/fixtures/Si.cif`, and make `check_matgl_env.py` use an internal or
non-task-pack fixture path so it remains runnable after prototype task-pack
removal.

Keep the `materials` optional dependency group containing `matgl==4.0.2`.

## Package And Dependency Updates

Update `pyproject.toml`:

- Remove `mcp>=1.27.2` from project dependencies.
- Remove wheel `force-include` entries for:
  - `tasks/atomisticskills_smoke`
  - `tasks/mace_materials`
  - `tasks/matgl_materials`
- Keep packaged formal task packs such as RDKit and xTB.

Update `uv.lock` after changing dependencies.

Packaging tests should confirm that removed prototype task packs are no longer
published and that the `materials` extra still exposes MatGL only.

## Documentation Updates

Update current-state documentation, including:

- `docs/design/INITIAL-DESIGN.md`
- `docs/superpowers/specs/2026-06-29-pipeline-package-framework-design.md`

The new current state should say:

- AtomisticSkills MCP prototypes were removed from the active codebase.
- MatGL will use native Python dependencies for future formal task specs.
- MACE will be reintroduced only after a native Python backend and task design
  are available.
- The public suite remains limited to formal tracks such as RDKit and xTB.

Do not rewrite historical research reports under `docs/research/`.

## Acceptance Criteria

- `rg -n "AtomisticSkills|atomisticskills|atomisticskills_mcp|mace-agent|matgl-agent|base-agent|drugdisc-agent|xrd-agent" verifiers scripts tests tasks pyproject.toml`
  returns no active code, task, script, or test references.
- `rg -n "\bmcp\b" pyproject.toml verifiers scripts tests tasks` returns no
  active dependency or implementation references.
- Native MatGL tests still pass without `tasks/matgl_materials/`.
- Full test suite passes with `uv run pytest`.
- Lockfile is consistent after dependency removal.
- A git commit records the cleanup after tests pass.
