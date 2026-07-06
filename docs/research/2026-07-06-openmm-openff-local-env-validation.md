# OpenMM + OpenFF Local Environment Validation

Date: 2026-07-06

## Summary

The optional `vgb-openmm-openff` conda environment should use Python 3.11.
Python 3.12 can run the OpenMM core smoke test, but the OpenFF path fails while
importing OpenFF Interchange before molecule parameterization starts.

## Observations

- `python=3.12` solved to OpenMM 8.5.2, OpenFF Toolkit 0.18.1, OpenFF
  Interchange 0.4.10, OpenMMForceFields 0.16.0, and RDKit 2025.9.5.
- Core OpenMM smoke passed on the `Reference` platform.
- OpenFF smoke failed with `unsupported operand type(s) for |:
  'typing.TypeAliasType' and 'str'` in OpenFF Interchange import code.
- A Python 3.11 dry-run resolved to OpenMM 8.5.2, OpenFF Toolkit 0.18.0,
  OpenFF Interchange 0.5.2, OpenMMForceFields 0.16.0, and RDKit 2025.09.5.

## Decision

Use Python 3.11 for `envs/openmm-openff.yml`. This keeps OpenMM/OpenFF/GAFF
inside a local optional runtime and avoids changing the project default Python
or dependency set.
