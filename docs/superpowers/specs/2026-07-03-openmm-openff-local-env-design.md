# OpenMM + OpenFF/GAFF Local Optional Environment Design

Date: 2026-07-03

## Goal

Design a local optional conda-managed environment for OpenMM + OpenFF/GAFF
verifier development. The environment should let developers run OpenMM core,
OpenFF/SMIRNOFF, and GAFF smoke checks locally without adding those heavy
dependencies to the default `uv` environment.

The first deployable target is an environment and verification harness, not a
formal public task track. Formal OpenMM tasks should only follow after the local
runtime can be installed, checked, and diagnosed consistently.

This round is limited to a usable backend/runtime path. It should not design,
add, register, or tune benchmark tasks.

## Scope

This design covers:

- A conda/mamba environment for OpenMM + OpenFF ecosystem dependencies.
- A local environment check script that reports structured JSON.
- A narrow OpenMM core smoke calculation.
- An OpenFF/SMIRNOFF small-molecule system creation and minimization smoke.
- A GAFF availability/system-creation smoke as an optional second path.
- Failure taxonomy for missing environment versus calculation failure.
- Tests that do not require OpenMM/OpenFF to be installed in the default
  environment.

This design does not cover:

- Docker or a production verifier image.
- Long molecular dynamics, free energy, FEP, MM/PBSA, MM/GBSA, docking, or
  binding affinity tasks.
- Adding OpenMM/OpenFF/GAFF dependencies to default `pyproject.toml`
  dependencies.
- Making OpenMM tasks formal or registering them as builtin public tracks.
- Adding or modifying `tasks/` task packs, `sample_answers.jsonl`, or
  `verifier_specs.yaml` files for OpenMM.
- Designing task prompts, task thresholds, calibration sets, or benchmark
  scoring distributions.
- Supporting arbitrary protein-ligand preparation, protonation, tautomer
  enumeration, or receptor preparation.

## Current Repository Context

The active package now uses a `src/` layout. Core verifier implementations live
under `src/verifiers/`, and current formal task packs are RDKit and xTB. The
RDKit force-field prototype already exists under `tasks/rdkit_forcefield/` and
`src/verifiers/backends/rdkit_forcefield.py`.

Default project dependencies are intentionally lightweight. `pyproject.toml`
currently keeps RDKit in the main environment and places heavier future
backends in optional groups. This is consistent with treating OpenMM/OpenFF as
a local optional runtime rather than a default dependency.

Existing research notes already concluded:

- OpenMM core is relatively easy to install and can run fixed fixture systems.
- Arbitrary small-molecule OpenMM parameterization is the heavier part because
  it depends on OpenFF Toolkit, AmberTools/GAFF, template generators, and
  version-compatible chemistry toolkits.
- RDKit ETKDG + MMFF/UFF remains the P0 force-field baseline. OpenMM/OpenFF is
  a P1/P2 extension once the optional runtime is stable.

## Recommended Environment Strategy

Use a conda-forge environment as the canonical local optional runtime.

Recommended environment file:

- `envs/openmm-openff.yml`

Recommended environment name:

- `vgb-openmm-openff`

Recommended package set:

```yaml
name: vgb-openmm-openff
channels:
  - conda-forge
dependencies:
  - python=3.12
  - openmm
  - openff-toolkit
  - openff-interchange
  - openmmforcefields
  - ambertools
  - rdkit
  - numpy
  - pyyaml
  - pytest
```

Python `3.12` should be the first target because the project requires
`>=3.12,<3.13`. If the OpenFF/AmberTools solver fails on supported developer
platforms, the implementation plan may introduce a separate clearly named
fallback environment file with Python `3.11`, but that fallback must not become
the default without recording the reason.

Installation command:

```bash
mamba env create -f envs/openmm-openff.yml
conda activate vgb-openmm-openff
python scripts/check_openmm_openff_env.py
```

`conda` may be used when `mamba` is unavailable, but docs should recommend
`mamba` because OpenFF and AmberTools dependency solving is heavier than the
base project environment.

## Why Not A `uv` Dependency Group

The OpenMM core package can often be installed through Python packaging, but
the full OpenFF/GAFF path is not just OpenMM. It needs a compatible mix of
OpenFF Toolkit, OpenFF Interchange, AmberTools, RDKit, and OpenMMForceFields.
OpenFF documentation recommends conda-forge/mamba for this ecosystem, and prior
local probing found direct `uv` installation unsuitable for the full
OpenFF/GAFF target.

Therefore:

- Do not add OpenMM/OpenFF/GAFF packages to default dependencies.
- Do not rely on a normal `uv sync` to provide OpenMM/OpenFF runtime support.
- Do not make default `uv run pytest` depend on the conda environment.
- Do allow tests to validate the environment file contents and missing-env
  behavior.

## Capability Layers

### Layer 1: OpenMM Core

Purpose: prove the OpenMM engine is importable and can execute a deterministic
small calculation.

Inputs:

- No arbitrary user molecule.
- Built-in or scripted toy system, such as a two-particle system, a tiny water
  box fixture, or a fixed peptide fixture.

Outputs:

- `openmm_version`
- `openmm_platforms`
- `selected_platform`
- `initial_energy_kj_mol`
- `minimized_energy_kj_mol`
- `energy_drop_kj_mol`
- `final_max_force_kj_mol_nm`

This layer validates OpenMM runtime health. It does not validate arbitrary
small-molecule parameterization.

### Layer 2: OpenFF/SMIRNOFF Ligand System Creation

Purpose: prove a small molecule can be converted into an OpenMM `System` using
OpenFF force fields.

Inputs:

- A single-component SMILES fixture, such as ethanol or aspirin.
- Explicitly fixed protonation, formal charge, and stereochemistry expectations.

Workflow:

1. Create an OpenFF `Molecule` from SMILES.
2. Generate or import a conformer.
3. Assign charges through the configured toolkit path.
4. Load a fixed SMIRNOFF force field, such as a pinned OpenFF Sage release.
5. Build an OpenMM `System`.
6. Run a short minimization smoke.

Outputs:

- `openff_toolkit_version`
- `openff_interchange_version`
- `forcefield_name`
- `charge_method`
- `parameterization_success`
- `system_particle_count`
- `initial_energy_kj_mol`
- `minimized_energy_kj_mol`
- `energy_drop_kj_mol`
- `final_max_force_kj_mol_nm`
- `rmsd_to_minimized_angstrom`

This should be the primary local optional backend path. It is more scientifically
useful than RDKit MMFF/UFF while still bounded enough for verifier smoke tests.

### Layer 3: GAFF Via OpenMMForceFields

Purpose: prove that the GAFF path is available and diagnosable in the same local
environment.

Inputs:

- The same small SMILES fixture used by the OpenFF smoke when possible.

Workflow:

1. Build an OpenMM topology for the ligand.
2. Use `openmmforcefields` GAFF template generator with AmberTools-backed
   parameterization.
3. Create an OpenMM `System`.
4. Optionally run the same minimization smoke.

Outputs:

- `openmmforcefields_version`
- `ambertools_available`
- `gaff_template_generator_available`
- `gaff_forcefield_name`
- `parameterization_success`
- `system_particle_count`
- Minimization metrics when system creation succeeds.

GAFF should be treated as a second-stage optional path inside the local
environment. The first OpenMM/OpenFF implementation should not make formal
task correctness depend on GAFF until GAFF smoke behavior is stable across
developer machines.

## Failure Taxonomy

Use `verifier_env_error` for local runtime availability and configuration
problems. This is distinct from `verifier_tool_error`.

Required classifications:

| Failure | failure_type | Example message |
|---|---|---|
| Conda environment missing or not activated | `verifier_env_error` | `OpenMM/OpenFF optional environment is not active; run conda activate vgb-openmm-openff` |
| Required package missing | `verifier_env_error` | `missing optional dependency: openff.toolkit` |
| Required package version outside supported range | `verifier_env_error` | `openmm version 8.x required, found ...` |
| No usable OpenMM platform | `verifier_env_error` | `no OpenMM Reference or CPU platform available` |
| AmberTools unavailable for GAFF path | `verifier_env_error` | `GAFF path requires AmberTools in the optional conda environment` |
| Candidate SMILES/SDF cannot be parsed | `parse_error` | `candidate must include a parseable single-component SMILES` |
| Candidate outside allowed elements, charge, atom count, or component domain | `domain_error` | `formal charge outside [-1, 1]` |
| OpenFF/GAFF parameterization fails for an in-domain molecule | `verifier_tool_error` | `OpenFF parameterization failed: ...` |
| OpenMM `System` creation fails after dependencies are present | `verifier_tool_error` | `OpenMM system creation failed: ...` |
| Minimization or energy evaluation returns non-finite values | `verifier_tool_error` | `OpenMM energy was not finite` |
| Calculation exceeds timeout | `verifier_timeout` | `OpenMM minimization exceeded timeout` |

The repository currently contains existing uses of `verifier_environment_error`.
OpenMM implementation should introduce and use `verifier_env_error` as the
canonical short name requested for this optional-runtime class. The
implementation plan must include tests and documentation updates so the new
OpenMM path does not silently mix the two names.

## Environment Check Script

Create:

- `scripts/check_openmm_openff_env.py`

Behavior:

- Always writes one JSON object to stdout.
- Exits `0` only when the required checks for the requested mode pass.
- Exits nonzero when the environment is missing or a smoke check fails.
- Does not require a task pack or answer file.

Suggested CLI:

```bash
python scripts/check_openmm_openff_env.py
python scripts/check_openmm_openff_env.py --mode core
python scripts/check_openmm_openff_env.py --mode openff
python scripts/check_openmm_openff_env.py --mode gaff
python scripts/check_openmm_openff_env.py --mode all
```

Default mode should be `all`, but `gaff` failure may be represented as
`gaff_status: "missing"` only if `openff` and `core` pass and the script's docs
explicitly say GAFF is optional. If `--mode gaff` is requested directly, missing
AmberTools or GAFF support is a `verifier_env_error` and a nonzero exit.

Suggested success payload:

```json
{
  "status": "ok",
  "failure_type": null,
  "message": null,
  "versions": {
    "openmm": "8.x",
    "openff_toolkit": "...",
    "openff_interchange": "...",
    "openmmforcefields": "...",
    "rdkit": "..."
  },
  "platforms": ["Reference", "CPU"],
  "checks": {
    "core": {"status": "ok"},
    "openff": {"status": "ok"},
    "gaff": {"status": "ok"}
  }
}
```

Suggested missing-env payload:

```json
{
  "status": "error",
  "failure_type": "verifier_env_error",
  "message": "missing optional dependency: openff.toolkit",
  "versions": {},
  "platforms": [],
  "checks": {
    "core": {"status": "skipped"},
    "openff": {"status": "error", "failure_type": "verifier_env_error"},
    "gaff": {"status": "skipped"}
  }
}
```

## Backend Design Boundary

The local environment check should come first. After it is stable, implement
the first backend under `src/verifiers/backends/`.

Backend implementation must stop at reusable verifier code and environment
diagnostics. It must not create OpenMM benchmark task packs in `tasks/`, add
OpenMM sample answers, or register OpenMM as a formal track in the public
registry during this round.

Recommended backend names:

- `openmm_core_properties.py`
- `openmm_openff_properties.py`

Initial OpenMM core backend:

- Accepts a fixed fixture id or a scripted built-in system.
- Does not accept arbitrary SMILES.
- Computes energy/minimization/max-force metrics only.

Initial OpenFF ligand backend:

- Accepts single-component SMILES.
- Uses OpenFF/SMIRNOFF as the primary force field.
- Allows GAFF only behind an explicit `forcefield_family: gaff` backend config.
- Uses strict domain gates before parameterization.

Suggested backend config:

```yaml
backend:
  type: openmm_openff_ligand
  forcefield_family: openff
  forcefield_name: openff-2.2.1
  charge_method: am1bcc
  platform: Reference
  max_minimization_iterations: 200
  energy_tolerance_kj_mol: 10.0
domain:
  allowed_elements: [H, C, N, O, F, P, S, Cl, Br, I]
  heavy_atom_count: [2, 60]
  formal_charge: [-1, 1]
  require_single_component: true
```

The exact pinned OpenFF force field should be selected during implementation
based on the conda environment's installed force-field files and documented in
the backend `versions` payload.

## Test Strategy

Default tests must pass without the optional conda environment.

Required tests:

- `envs/openmm-openff.yml` exists and contains expected conda-forge packages.
- `scripts/check_openmm_openff_env.py` returns structured JSON with
  `failure_type: verifier_env_error` when imports are mocked as missing.
- The check script validates requested modes and rejects invalid modes with a
  structured error.
- Future backend tests mock missing OpenMM/OpenFF imports and assert
  `verifier_env_error`, not `verifier_tool_error`.
- Live OpenMM/OpenFF smoke tests are skipped unless explicitly enabled by an
  environment variable such as `VGB_RUN_OPENMM_OPENFF_LIVE=1`.

Suggested live test gate:

```bash
VGB_RUN_OPENMM_OPENFF_LIVE=1 pytest tests/test_openmm_openff_env_live.py -v
```

Full repository verification remains:

```bash
uv run pytest
```

## Documentation Updates

Update or create:

- `docs/tracks/OpenMM-OpenFF.md` for backend-specific status once implementation
  begins.
- `docs/research/` only for new exploratory findings, not for the implementation
  spec itself.
- `docs/design/INITIAL-DESIGN.md` only if public failure taxonomy or active
  backend status changes materially.

The local setup docs should state that OpenMM/OpenFF is optional and not part of
the default benchmark install.

## Acceptance Criteria

The first implementation that follows this design is acceptable when:

- `envs/openmm-openff.yml` defines a conda-forge local optional environment.
- `scripts/check_openmm_openff_env.py` provides structured JSON diagnostics.
- Missing optional runtime produces `failure_type: verifier_env_error`.
- Default `uv run pytest` passes without OpenMM/OpenFF installed.
- In the activated conda environment, `python scripts/check_openmm_openff_env.py
  --mode core` succeeds.
- In the activated conda environment, `python scripts/check_openmm_openff_env.py
  --mode openff` succeeds for a small molecule fixture.
- GAFF mode either succeeds or fails with a clear `verifier_env_error` that
  names the missing dependency or toolkit path.
- No OpenMM/OpenFF packages are added to default project dependencies.
- A git commit records the environment design and subsequent implementation
  after tests pass.

## References

- OpenMM User Guide, running simulations: https://docs.openmm.org/latest/userguide/application/02_running_sims.html
- OpenMM installation documentation: https://docs.openmm.org/latest/userguide/application/01_getting_started.html
- OpenFF Toolkit installation documentation: https://docs.openforcefield.org/projects/toolkit/en/stable/installation.html
- OpenFF Toolkit API documentation: https://docs.openforcefield.org/projects/toolkit/en/stable/api/generated/openff.toolkit.typing.engines.smirnoff.ForceField.html
- OpenFF Interchange documentation: https://docs.openforcefield.org/projects/interchange/en/stable/
- OpenMMForceFields project: https://github.com/openmm/openmmforcefields
