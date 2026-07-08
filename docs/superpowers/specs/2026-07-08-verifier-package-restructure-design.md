# Verifier Package Restructure Design

Date: 2026-07-08

## Background

The current `src/verifiers` layout mixes two different classification schemes.
Some property-level verification scripts are grouped by domain, such as
`descriptors`, `forcefield`, `materials`, `physchem`, and `quantum_ml`, while
other scripts are grouped by tool or model family, such as `xtb` and `opera`.
The implementation layer is also centralized under `src/verifiers/backends`,
which makes it unclear whether a module is a runnable verifier entrypoint, a
tool implementation, or shared framework code.

This design changes the verifier codebase to a tool/model-family package layout.
The change is intentionally a hard cut: old import paths and old verification
script paths will not be kept as compatibility shims.

## Goals

- Make each verifier package name identify the tool or model family directly.
- Remove the centralized `src/verifiers/backends` implementation directory.
- Keep shared framework utilities in a narrow `src/verifiers/common` package.
- Keep OpenMM runtime code inside an OpenMM family package, not in global
  shared code.
- Keep the user-facing verifier contract unchanged: each property still maps to
  one concrete property-level `verification_script`.
- Remove the experimental OPERA implementation during the restructure because it
  is not usable on the local architecture and remains only a trial backend.
- Update task specs, tests, scripts, and current documentation to the new paths.

## Non-Goals

- Do not change verifier result JSON semantics.
- Do not change task constraint semantics, scoring behavior, domain gates, or
  candidate payload shape.
- Do not collapse multiple properties into a single public script entrypoint.
- Do not preserve legacy imports such as `verifiers.backends.*`.
- Do not preserve legacy script paths such as `verifiers/descriptors/*.py`.
- Do not broadly rewrite historical Superpowers plans that describe how older
  code was originally created.

## User-Facing Contract

The external evaluation path remains:

```text
task constraint -> verifier_id -> verifier_specs.yaml -> property-level verification_script -> backend implementation
```

Each scored property continues to have its own runnable script path. For example,
after the restructure, RDKit QED remains a distinct verifier script, but its path
changes from:

```text
verifiers/descriptors/rdkit_qed.py
```

to:

```text
verifiers/rdkit_descriptors/rdkit_qed.py
```

The CLI payload contract stays the same: the runner sends JSON on stdin and the
script writes one verifier result JSON object on stdout. The script may delegate
to shared CLI helpers and backend modules internally, but users and task specs
still see one property-level script per property.

## Package Layout

The target package layout is:

```text
src/verifiers/
  __init__.py

  common/
    __init__.py
    property_cli.py
    result_schema.py
    scoring.py
    docker_model_runtime.py

  rdkit_descriptors/
    __init__.py
    backend.py
    cli.py
    rdkit_qed.py
    rdkit_logp.py
    rdkit_tpsa.py
    rdkit_mw.py
    rdkit_hba.py
    rdkit_hbd.py
    rdkit_sa_score.py
    rdkit_fraction_csp3.py

  rdkit_forcefield/
    __init__.py
    backend.py
    cli.py
    rdkit_energy_range.py
    rdkit_convergence.py

  xtb/
    __init__.py
    backend.py
    cli.py
    xtb_gap.py
    xtb_dipole.py
    xtb_relaxation_energy.py
    xtb_lumo.py
    xtb_polarizability.py
    xtb_solvation_selectivity.py
    xtb_electrophilicity.py
    xtb_fukui.py
    xtb_hessian_thermo.py

  admet_ai/
    __init__.py
    backend.py
    cli.py
    admet_ai_ames.py
    admet_ai_bbb.py
    admet_ai_caco2.py
    admet_ai_herg.py
    admet_ai_solubility_aqsoldb.py

  matgl/
    __init__.py
    backend.py
    cli.py
    matgl_bandgap.py
    matgl_formation_energy.py

  mace_mp/
    __init__.py
    backend.py
    cli.py
    mace_mp_energy.py
    mace_mp_energy_per_atom.py
    mace_mp_max_force.py
    mace_mp_stress_norm.py

  torchani/
    __init__.py
    backend.py
    cli.py
    torchani_total_energy.py
    torchani_energy_per_atom.py
    torchani_max_force.py

  soltrannet/
    __init__.py
    backend.py
    cli.py
    soltrannet_log_s.py

  molgpka/
    __init__.py
    backend.py
    cli.py
    molgpka_min_pka.py
    molgpka_max_pka.py
    molgpka_pka_count.py

  openmm/
    __init__.py
    runtime.py
    core_backend.py
    openff_backend.py
```

The old directories below are removed:

- `src/verifiers/backends`
- `src/verifiers/descriptors`
- `src/verifiers/forcefield`
- `src/verifiers/materials`
- `src/verifiers/physchem`
- `src/verifiers/quantum_ml`
- `src/verifiers/opera`

## Common Package Boundary

`src/verifiers/common` contains only framework utilities shared across verifier
families:

- `property_cli.py`: shared stdin/stdout property verifier script contract.
- `result_schema.py`: common result and error result constructors.
- `scoring.py`: generic scoring helpers.
- `docker_model_runtime.py`: Docker/HTTP runtime helpers reused by containerized
  model backends such as SolTranNet and MolGpKa.

OpenMM runtime code is not global common code. It moves to
`src/verifiers/openmm/runtime.py` because it is shared only inside the OpenMM
family.

## Backend Module Boundary

Each tool/model package owns its implementation module:

| Current module | Target module |
|---|---|
| `verifiers.backends.rdkit_descriptors` | `verifiers.rdkit_descriptors.backend` |
| `verifiers.backends.rdkit_forcefield` | `verifiers.rdkit_forcefield.backend` |
| `verifiers.backends.xtb_properties` | `verifiers.xtb.backend` |
| `verifiers.backends.admet_ai_properties` | `verifiers.admet_ai.backend` |
| `verifiers.backends.matgl_properties` | `verifiers.matgl.backend` |
| `verifiers.backends.mace_mp_properties` | `verifiers.mace_mp.backend` |
| `verifiers.backends.torchani_properties` | `verifiers.torchani.backend` |
| `verifiers.backends.soltrannet_properties` | `verifiers.soltrannet.backend` |
| `verifiers.backends.molgpka_properties` | `verifiers.molgpka.backend` |
| `verifiers.backends.openmm_runtime` | `verifiers.openmm.runtime` |
| `verifiers.backends.openmm_core_properties` | `verifiers.openmm.core_backend` |
| `verifiers.backends.openmm_openff_properties` | `verifiers.openmm.openff_backend` |

No `verifiers.backends` package remains after migration.

## OPERA Removal

The OPERA implementation is removed as part of this restructure:

- Delete `src/verifiers/opera`.
- Delete `src/verifiers/backends/opera_properties.py`.
- Delete OPERA-specific tests.
- Delete `scripts/check_opera_env.py`.
- Remove OPERA from current capability inventories and track-facing docs.

Historical research notes may continue to mention OPERA as a past investigation,
but current implementation and capability documents should no longer present it
as an available backend.

## Property CLI Helper

The existing repeated `*_property_script.py` helpers are replaced by one common
helper in `verifiers.common.property_cli`. Each family package exposes a small
`cli.py` that binds the family evaluator and any family-specific JSON formatting
settings.

For example, a package CLI module should look conceptually like:

```python
from verifiers.common.property_cli import run_property_script
from verifiers.xtb.backend import evaluate_xtb_property_constraint


def main(property_name: str) -> None:
    run_property_script(
        expected_name=property_name,
        spec_field="property_name",
        mismatch_label="property",
        evaluator=evaluate_xtb_property_constraint,
        sort_keys=False,
    )
```

Each property script remains a thin executable entrypoint:

```python
from verifiers.xtb.cli import main


if __name__ == "__main__":
    main("homo_lumo_gap")
```

This keeps the public one-property-one-script model while removing duplicated
per-family helper implementations.

## Task Spec Migration

All active and prototype `verification_script` paths must be updated to the new
package paths. Examples:

| Current path | Target path |
|---|---|
| `verifiers/descriptors/rdkit_qed.py` | `verifiers/rdkit_descriptors/rdkit_qed.py` |
| `verifiers/forcefield/rdkit_energy_range.py` | `verifiers/rdkit_forcefield/rdkit_energy_range.py` |
| `verifiers/materials/matgl_bandgap.py` | `verifiers/matgl/matgl_bandgap.py` |
| `verifiers/materials/mace_mp_energy_per_atom.py` | `verifiers/mace_mp/mace_mp_energy_per_atom.py` |
| `verifiers/quantum_ml/torchani_total_energy.py` | `verifiers/torchani/torchani_total_energy.py` |
| `verifiers/physchem/soltrannet_log_s.py` | `verifiers/soltrannet/soltrannet_log_s.py` |
| `verifiers/physchem/molgpka_min_pka.py` | `verifiers/molgpka/molgpka_min_pka.py` |

The xTB package already uses a tool-family directory, but its backend and CLI
helper still change:

| Current module | Target module |
|---|---|
| `verifiers.xtb.xtb_property_script` | `verifiers.xtb.cli` |
| `verifiers.backends.xtb_properties` | `verifiers.xtb.backend` |

## Tests and Scripts

Tests must be updated to import only new package paths. Any test that still
imports `verifiers.backends.*` or one of the removed domain directories should
fail and be corrected.

Operational scripts must be updated similarly, including environment checks and
xTB real-dataset utilities:

- `scripts/check_admet_ai_env.py`
- `scripts/check_mace_mp_env.py`
- `scripts/check_matgl_env.py`
- `scripts/check_molgpka_env.py`
- `scripts/check_openmm_openff_env.py`
- `scripts/check_soltrannet_env.py`
- `scripts/check_torchani_env.py`
- `scripts/check_xtb_env.py`
- `scripts/prepare_xtb_real_dataset_sample.py`
- `scripts/run_xtb_real_dataset_distribution.py`

OPERA scripts and tests are removed instead of migrated.

## Documentation

Current docs should describe the new package layout:

- `docs/design/INITIAL-DESIGN.md`
- `docs/research/2026-07-06-verifier-backend-property-inventory.md`
- `docs/tracks/RDKit.md`
- `docs/tracks/RDKit-Forcefield.md`
- `docs/tracks/xTB.md`
- `docs/tracks/OpenMM-OpenFF.md`

Historical implementation plans and older research notes may remain unchanged
unless they are presented as current capability documentation.

## Migration Constraints

- Work happens on `refactor/verifier-package-restructure`, not on `main`.
- Do not add compatibility shim modules or packages.
- Delete old package directories after their contents have moved.
- Keep changes mechanical where possible: move files, update imports, update task
  paths, then verify behavior.
- Treat any remaining reference to removed current paths in source, tests, task
  specs, or current docs as a migration bug.

## Verification Plan

Before committing implementation changes, run:

```bash
uv run pytest
```

Also run a path-reference scan after migration:

```bash
rg "verifiers\\.backends|verifiers/(backends|descriptors|forcefield|materials|physchem|quantum_ml|opera)|verifiers\\.(descriptors|forcefield|materials|physchem|quantum_ml|opera)" src tests tasks scripts docs
```

Remaining hits are acceptable only in explicitly historical documentation. Source,
tests, task specs, scripts, and current track/design docs should not depend on
removed paths.

## Risks

- Hard-cut migration will break any untracked external consumer still importing
  `verifiers.backends.*`.
- Task specs with stale `verification_script` paths will fail at runtime.
- Optional backend tests may still require mocking optional dependencies so the
  default test suite remains lightweight.
- Documentation churn is unavoidable because path names are part of the benchmark
  contract.

These risks are accepted for this restructure because the goal is a clean package
architecture without legacy compatibility layers.
