# MACE-MP Backend

Status: backend capability document, not a registered formal benchmark track.

## Purpose

This backend wraps the MACE-MP foundation potential through the MACE ASE
calculator as a native optional runtime for periodic material energy, force,
and stress properties.

## Input

The candidate must provide a `cif` string. The backend parses the CIF with
pymatgen and converts the structure to ASE Atoms.

## Properties

| Verifier property | Unit | Meaning |
|---|---:|---|
| `mace_mp_energy_ev` | eV | MACE-MP total potential energy. |
| `mace_mp_energy_per_atom_ev` | eV/atom | Total potential energy divided by atom count. |
| `mace_mp_max_force_ev_per_angstrom` | eV/Angstrom | Maximum atomic force norm. |
| `mace_mp_stress_norm_ev_per_angstrom3` | eV/Angstrom^3 | Norm of ASE stress vector. |

## Runtime

Install the optional runtime with:

```bash
uv sync --group mace
```

Run the local diagnostic:

```bash
uv run --group mace python scripts/env/check_mace_mp_env.py
```

The first run may download the selected MACE-MP checkpoint into `~/.cache/mace`.

## Limitations

- Energy zero points and stress behavior are model-specific and must not be
  mixed with MatGL formation-energy labels.
- The first implementation uses the `small` MACE-MP model on CPU for verifier
  practicality.
- Formal benchmark tasks need calibration before this backend is exposed as a
  public track.
