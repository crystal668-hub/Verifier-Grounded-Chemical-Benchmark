# MolGpKa Backend

Status: backend capability document, not a registered formal benchmark track.

## Purpose

This backend wraps MolGpKa through the `ghcr.io/quanted/cts-molgpka` Docker
image to predict ionizable-site pKa values from a single-component
small-molecule SMILES.

## Properties

| Verifier property | Meaning |
|---|---|
| `molgpka_min_pka` | Minimum predicted pKa in the MolGpKa pKa list. |
| `molgpka_max_pka` | Maximum predicted pKa in the MolGpKa pKa list. |
| `molgpka_pka_count` | Number of predicted ionizable pKa values. |

The raw list is retained as `molgpka_pka_values` in verifier result
properties.

## Runtime

Default development runtime:

```yaml
molgpka:
  runtime: external_docker
  image: ghcr.io/quanted/cts-molgpka:dev-acafcb3fb93dbf8dcf6c952cbf3b12161e7f468d
  platform: linux/amd64
  timeout_seconds: 120
```

The backend uses a one-shot container command that calls
`CTSMolgpka().main(smiles)` through `micromamba run -n MolGpka python`.

## Environment Check

```bash
uv run python scripts/check_molgpka_env.py --smiles 'CC(O)=O'
```

The script prints structured JSON with runtime metadata, pKa count, and pKa
values.

## Limitations

- The first wrapper does not split acidic and basic pKa sites.
- `molgpka_min_pka` and `molgpka_max_pka` require at least one predicted pKa
  value.
- `molgpka_pka_count` can score molecules with zero predicted pKa values.
- The current image is amd64 and may run through emulation on arm64 Docker
  Desktop.
- External Docker is the development deployment path. A future official
  verifier image should switch this backend to `runtime: local` while keeping
  the property scripts and result schema unchanged.
