# TorchANI ANI-2x Backend

Status: backend capability document, not a registered formal benchmark track.

## Purpose

This backend wraps TorchANI ANI-2x as a native optional runtime for direct-XYZ
small-molecule quantum-ML energy and force properties.

## Input

The candidate must provide an `xyz` string. The backend does not generate
conformers from SMILES.

## Properties

| Verifier property | Unit | Meaning |
|---|---:|---|
| `torchani_total_energy_hartree` | Hartree | ANI-2x total molecular energy. |
| `torchani_energy_per_atom_hartree` | Hartree/atom | Total energy divided by atom count. |
| `torchani_max_force_hartree_per_angstrom` | Hartree/Angstrom | Maximum atomic force norm. |

## Runtime

Install the optional runtime with:

```bash
uv sync --group torchani
```

Run the local diagnostic:

```bash
uv run --group torchani python scripts/check_torchani_env.py
```

## Limitations

- ANI-2x supports a limited organic element domain: H, C, N, O, F, S, and Cl.
- Absolute total energy should be used only with carefully constrained formula
  or composition domains.
- This backend is CPU-usable but still loads PyTorch and TorchANI model weights.
