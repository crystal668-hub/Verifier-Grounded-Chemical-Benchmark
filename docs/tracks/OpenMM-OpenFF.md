# OpenMM + OpenFF/GAFF Backend Status

Updated: 2026-07-03

## Status

This is a local optional backend/runtime path. It is not a formal benchmark
track and is not registered in the public suite.

This round intentionally does not add OpenMM task packs, sample answers,
verifier specs, task prompts, thresholds, or calibration data.

## Local Environment

Create the optional conda environment:

```bash
mamba env create -f envs/openmm-openff.yml
conda activate vgb-openmm-openff
python scripts/check_openmm_openff_env.py --mode all
```

Use `conda env create -f envs/openmm-openff.yml` only when `mamba` is
unavailable.

## Failure Types

- `verifier_env_error`: optional conda environment is missing, inactive, missing
  required packages, missing usable OpenMM platform, or missing GAFF/AmberTools
  support for GAFF mode.
- `verifier_tool_error`: OpenMM/OpenFF/GAFF is installed, but parameterization,
  system creation, minimization, or energy/force evaluation fails.
- `parse_error`: candidate molecular input cannot be parsed.
- `domain_error`: candidate is outside allowed element, charge, atom-count, or
  component-count domain.

## Implemented Backend Surfaces

- `src/verifiers/backends/openmm_core_properties.py`
  - fixed fixture OpenMM energy/minimization smoke
  - no arbitrary SMILES

- `src/verifiers/backends/openmm_openff_properties.py`
  - single-component SMILES ligand path
  - OpenFF/SMIRNOFF primary mode
  - GAFF mode kept behind explicit backend config

## Non-Goals

- No formal OpenMM task pack.
- No benchmark thresholds or task prompts.
- No binding affinity, FEP, docking, long MD, or free-energy scoring.
- No default dependency changes.
